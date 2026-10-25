"""Persistent source registry with independent validated, digest-checked caches."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
from urllib.parse import parse_qs, quote, urlencode, urlparse
import zipfile

from .catalog import MAX_DOWNLOAD, Snapshot, download, is_redirect, parse_json, read_archive, safe_path
from .packages import load_package, package_from_archive


class SourceChoices(ValueError):
    def __init__(self, message, choices):
        super().__init__(message)
        self.message = message
        self.choices = choices


def _https(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('A public HTTPS URL is required.')
    return parsed


def _zip(snapshot):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in snapshot.files.items(): archive.writestr(name, data)
    return stream.getvalue()


def _atomic(path, data):
    if any(is_redirect(parent) for parent in [path] + list(path.parents)):
        raise ValueError('Source storage cannot contain symbolic links or reparse points.')
    path.parent.mkdir(parents=True, exist_ok=True)
    if any(is_redirect(parent) for parent in [path] + list(path.parents)):
        raise ValueError('Source storage cannot contain symbolic links or reparse points.')
    fd, temporary = tempfile.mkstemp(prefix='.source-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def _api(url):
    return parse_json(download(url, 4 * 1024 * 1024))


def _release(repository, channel, tag=None, asset_name=None, progress=None):
    base = 'https://api.github.com/repos/' + repository
    endpoint = '/releases/latest' if channel == 'latest' else '/releases/tags/' + quote(tag, safe='')
    release = _api(base + endpoint)
    if not isinstance(release, dict) or not isinstance(release.get('tag_name'), str): raise ValueError('Invalid GitHub release response.')
    assets = [asset for asset in release.get('assets', []) if isinstance(asset, dict) and isinstance(asset.get('name'), str) and asset['name'].lower().endswith('.zip') and isinstance(asset.get('browser_download_url'), str)]
    origin = 'https://github.com/' + repository + ('/releases/latest' if channel == 'latest' else '/releases/tag/' + quote(tag, safe=''))
    if asset_name:
        matching = [asset for asset in assets if asset['name'] == asset_name]
        if not matching and assets:
            raise SourceChoices('The previously selected asset is absent. Choose the ZIP for this release.', [{'label':asset['name'], 'url':origin + '?' + urlencode({'asset':asset['name']})} for asset in assets])
        assets = matching
    if not assets: raise ValueError('This release has no compatible ZIP asset. Select another release or import a mod ZIP.')
    if len(assets) > 1:
        raise SourceChoices('Choose the ZIP asset to import.', [{'label':asset['name'], 'url':origin + '?' + urlencode({'asset':asset['name']})} for asset in assets])
    asset = assets[0]; _https(asset['browser_download_url'])
    if progress: progress('Downloading release ZIP…')
    result = package_from_archive(download(asset['browser_download_url']))
    result.origin = dict(kind='github', origin=origin + '?' + urlencode({'asset':asset['name']}), repository=repository, channel=channel, tag=release['tag_name'], asset_name=asset['name'], asset_url=asset['browser_download_url'])
    return result


def _repository(repository, branch=None, progress=None):
    base = 'https://api.github.com/repos/' + repository
    if branch is None:
        metadata = _api(base)
        branch = metadata.get('default_branch') if isinstance(metadata, dict) else None
    if not isinstance(branch, str) or not branch: raise ValueError('GitHub returned no default branch.')
    commit = _api(base + '/commits/' + quote(branch, safe=''))
    sha = commit.get('sha', '') if isinstance(commit, dict) else ''
    if not re.fullmatch('[0-9a-f]{40}', sha): raise ValueError('GitHub returned an invalid commit.')
    if progress: progress('Downloading repository at ' + sha[:10] + '…')
    data = download('https://codeload.github.com/' + repository + '/zip/' + sha)
    try:
        result = package_from_archive(data)
    except ValueError as exc:
        if not str(exc).startswith('No supported mod found.'): raise
        releases = _api(base + '/releases')
        choices = [{'label':release.get('name') or release['tag_name'], 'url':'https://github.com/' + repository + '/releases/tag/' + quote(release['tag_name'], safe='')} for release in releases if isinstance(release, dict) and isinstance(release.get('tag_name'), str) and any(isinstance(asset, dict) and str(asset.get('name', '')).lower().endswith('.zip') for asset in release.get('assets', []))] if isinstance(releases, list) else []
        if choices: raise SourceChoices('This repository contains source code. Choose a release ZIP.', choices) from exc
        raise ValueError('No compatible mod payload or ZIP release found. Build the mod separately and import its output.') from exc
    result.revision = sha
    result.origin = dict(kind='github', origin='https://github.com/' + repository, repository=repository, branch=branch, channel='branch')
    return result


class SourceStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.registry = self.root / 'sources.json'

    @property
    def records(self):
        if not self.registry.exists(): return []
        if is_redirect(self.registry) or self.registry.stat().st_size > 8 * 1024 * 1024: raise ValueError('Invalid source registry.')
        data = parse_json(self.registry.read_bytes())
        if not isinstance(data, dict) or data.get('schema_version') != 1 or not isinstance(data.get('sources'), list): raise ValueError('Invalid source registry.')
        ids = set()
        for record in data['sources']:
            if not isinstance(record, dict) or not isinstance(record.get('id'), str) or not re.fullmatch(r'official|[a-f0-9-]{36}', record['id']) or record['id'] in ids: raise ValueError('Invalid source identity.')
            ids.add(record['id'])
            if not isinstance(record.get('origin'), str) or not isinstance(record.get('selected_ids'), list) or any(not isinstance(value, str) for value in record['selected_ids']): raise ValueError('Invalid source record.')
            safe_path(record.get('cache'))
            if not re.fullmatch(r'cache/[a-f0-9]{64}\.zip', record['cache']) or not re.fullmatch(r'[a-f0-9]{64}', record.get('sha256', '')): raise ValueError('Invalid source cache record.')
        return copy.deepcopy(data['sources'])

    def _record(self, source_id):
        return next((record for record in self.records if record['id'] == source_id), None)

    def load(self, source_id) -> Snapshot:
        record = self._record(source_id)
        if record is None: raise ValueError('Unknown source: ' + str(source_id))
        path = self.root / record['cache']
        if any(is_redirect(parent) for parent in [path] + list(path.parents)) or path.stat().st_size > MAX_DOWNLOAD: raise ValueError('Invalid source cache.')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record['sha256']: raise ValueError('Source cache checksum mismatch.')
        snapshot = Snapshot(record['revision'], read_archive(data, strip_root=False), source_id)
        snapshot.origin = copy.deepcopy(record.get('details', {'kind':record['kind'], 'origin':record['origin']}))
        return snapshot

    def add(self, snapshot, origin: str, selected_ids: list[str], source_id: str | None = None) -> str:
        records = self.records
        source_id = source_id or str(uuid.uuid4())
        if not re.fullmatch(r'official|[a-f0-9-]{36}', source_id): raise ValueError('Invalid source identity.')
        if not isinstance(origin, str) or not origin: raise ValueError('Missing source origin.')
        if not isinstance(selected_ids, list) or any(value not in {mod['id'] for mod in snapshot.mods} for value in selected_ids): raise ValueError('Unknown selected mod.')
        # Revalidate the normalized representation before any durable writes.
        normalized = Snapshot(snapshot.revision, dict(snapshot.files), source_id)
        archive = _zip(normalized)
        if len(archive) > MAX_DOWNLOAD: raise ValueError('Source cache is too large.')
        # Generated/merged packages must satisfy exactly the loader's archive rules
        # before the registry can reference them or any previous cache is replaced.
        Snapshot(normalized.revision, read_archive(archive, strip_root=False), source_id)
        digest = hashlib.sha256(archive).hexdigest()
        cache = 'cache/' + digest + '.zip'
        details = copy.deepcopy(getattr(snapshot, 'origin', {}))
        if not details: details = dict(kind='https' if origin.startswith('https://') else 'local', origin=origin)
        record = dict(id=source_id, kind=details.get('kind', 'local'), origin=origin, details=details, selected_ids=list(dict.fromkeys(selected_ids)), cache=cache, sha256=digest, revision=normalized.revision)
        records = [entry for entry in records if entry['id'] != source_id] + [record]
        _atomic(self.root / cache, archive)
        _atomic(self.registry, json.dumps(dict(schema_version=1, sources=records), indent=2).encode('utf-8'))
        return source_id

    def resolve(self, origin: str, progress=None, asset_url: str | None = None) -> Snapshot:
        if asset_url is not None:
            parsed = _https(asset_url)
            result = package_from_archive(download(asset_url))
            result.origin = dict(kind='https', origin=asset_url)
            return result
        parsed = urlparse(origin)
        if parsed.scheme in ('http', 'https'):
            _https(origin)
            if parsed.hostname.lower() == 'github.com':
                parts = [part for part in parsed.path.split('/') if part]
                if len(parts) >= 2:
                    owner, repo = parts[:2]; repo = repo.removesuffix('.git')
                    if not re.fullmatch(r'[A-Za-z0-9_.-]+', owner) or not re.fullmatch(r'[A-Za-z0-9_.-]+', repo): raise ValueError('Invalid GitHub repository URL.')
                    repository = owner + '/' + repo
                    if len(parts) == 2: return _repository(repository, progress=progress)
                    if len(parts) == 4 and parts[2:] == ['releases', 'latest']: return _release(repository, 'latest', asset_name=parse_qs(parsed.query).get('asset', [None])[0], progress=progress)
                    if len(parts) >= 5 and parts[2:4] == ['releases', 'tag']:
                        from urllib.parse import unquote
                        return _release(repository, 'tag', unquote('/'.join(parts[4:])), parse_qs(parsed.query).get('asset', [None])[0], progress)
            if progress: progress('Downloading ZIP…')
            result = package_from_archive(download(origin)); result.origin = dict(kind='https', origin=origin)
            return result
        if '://' in origin: raise ValueError('Use an HTTPS URL, local ZIP, or mod folder.')
        return load_package(Path(origin))

    def refresh(self, source_id, progress=None) -> Snapshot:
        record = self._record(source_id)
        if record is None: raise ValueError('Unknown source: ' + str(source_id))
        details = record.get('details', {})
        if record.get('kind') == 'local':
            raise ValueError('Local sources require explicit reselection. Use Update from ZIP and choose the new package.')
        if details.get('kind') == 'github' and details.get('channel') == 'branch':
            current = _repository(details['repository'], details['branch'], progress)
        else:
            current = self.resolve(details.get('origin', record['origin']), progress)
        return self._replace(record, current)

    def update_from_package(self, source_id, path: Path, progress=None) -> Snapshot:
        record = self._record(source_id)
        if record is None: raise ValueError('Unknown source: ' + str(source_id))
        if progress: progress('Inspecting the selected package...')
        current = load_package(Path(path))
        record = dict(record, origin=str(Path(path).resolve()))
        return self._replace(record, current)

    def update(self, source_id, snapshot) -> Snapshot:
        """Accept an explicitly resolved replacement while keeping source identity."""
        record = self._record(source_id)
        if record is None: raise ValueError('Unknown source: ' + str(source_id))
        origin = getattr(snapshot, 'origin', {}).get('origin', record['origin'])
        return self._replace(dict(record, origin=origin), snapshot)

    def _replace(self, record, current):
        source_id = record['id']
        previous = self.load(source_id)
        current_ids = {mod['id'] for mod in current.mods}
        missing = [dict(mod, available=False) for mod in previous.mods if mod['id'] not in current_ids]
        if missing:
            files = dict(current.files)
            for mod in missing:
                for relative in mod['files'] + mod.get('default_files', []):
                    name = 'Mods/%s/%s' % (mod['id'], relative); files[name] = previous.files[name]
            files['catalog.json'] = json.dumps(dict(schema_version=1, mods=current.mods + missing)).encode('utf-8')
            merged = Snapshot(current.revision, files, source_id); merged.origin = current.origin
            current = merged
        self.add(current, record['origin'], record['selected_ids'], source_id)
        return self.load(source_id)
