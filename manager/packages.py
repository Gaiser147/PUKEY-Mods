"""Inspect ZIPs and folders as data, and normalize supported mod layouts."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from .catalog import MAX_EXPANDED, MAX_FILE, Snapshot, is_redirect, parse_json, read_archive, safe_path


def _id(name):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', name):
        raise ValueError('The inferred mod folder name %r is not a supported ID. Use a folder starting with a letter and containing only letters, digits, _ or - (at most 64 characters), or ask the author to supply pukey-mod.json with an explicit ID and matching runtime paths.' % name)
    return name


def _under(name, root):
    return not root or name.startswith(root + '/')


def _normalize(files, name='Imported', source_id='import'):
    """Find explicit roots first; reject intersecting independently detected roots."""
    folded = {path.casefold(): path for path in files}
    catalogs = [path for path in files if PurePosixPath(path).name.casefold() == 'catalog.json']
    if len(catalogs) > 1: raise ValueError('Multiple catalogues found; import each package separately.')
    if catalogs:
        path = catalogs[0]
        root = str(PurePosixPath(path).parent)
        root = '' if root == '.' else root
        prefix = root + '/' if root else ''
        selected = {path[len(prefix):]:data for path, data in files.items() if _under(path, root)}
        # Preserve compatibility with schema-1 repository archives.
        selected['catalog.json'] = selected.pop(path[len(prefix):])
        return Snapshot('package-' + _digest(files)[:24], selected, source_id)
    manifests = {}
    for path, data in files.items():
        if PurePosixPath(path).name.casefold() == 'pukey-mod.json':
            root = str(PurePosixPath(path).parent)
            root = '' if root == '.' else root
            mod = parse_json(data)
            if not isinstance(mod, dict) or type(mod.get('schema_version')) is not int or mod['schema_version'] != 1:
                raise ValueError('Unsupported pukey-mod.json schema_version; expected 1.')
            mod = dict(mod); del mod['schema_version']
            mod.setdefault('controls', ''); mod.setdefault('settings', []); mod.setdefault('default_files', [])
            manifests[root] = mod
    candidates = {}
    for path in files:
        parts = path.split('/')
        if len(parts) >= 2 and parts[-2].casefold() == 'scripts' and parts[-1].casefold() == 'main.lua':
            root = '/'.join(parts[:-2]); candidates.setdefault(root, []).append({'type':'lua', 'path':'/'.join(parts[-2:])})
        if len(parts) >= 2 and parts[-2].casefold() == 'dlls' and parts[-1].casefold().endswith('.dll'):
            root = '/'.join(parts[:-2]); folder = root.split('/')[-1] if root else name
            if parts[-1].casefold() in ('main.dll', folder.casefold() + '.dll'):
                candidates.setdefault(root, []).append({'type':'native', 'path':'/'.join(parts[-2:])})
    roots = sorted(set(manifests) | set(candidates))
    if not roots: raise ValueError('No supported mod found. Include pukey-mod.json, Scripts/main.lua, or dlls/main.dll (or dlls/<mod-folder>.dll).')
    for index, root in enumerate(roots):
        for other in roots[index+1:]:
            if _under(other, root): raise ValueError('Overlapping mod roots: %s and %s. Import each mod separately.' % (root or '.', other))
    mods = []; normalized = {}
    for root in roots:
        prefix = root + '/' if root else ''
        payload = {path[len(prefix):]:data for path, data in files.items() if _under(path, root)}
        if root in manifests:
            mod = manifests[root]
        else:
            folder = root.split('/')[-1] if root else name
            entrypoints = candidates[root]
            native = [entry for entry in entrypoints if entry['type'] == 'native']
            if len(native) > 1: raise ValueError('Multiple native entrypoints in %s; declare entrypoints in pukey-mod.json.' % (root or '.'))
            program = []; defaults = []
            for path in payload:
                base = PurePosixPath(path).name.casefold()
                if base in ('enabled.txt', 'pukey-mod.json'): continue
                if base in ('config.ini', 'config.json', 'settings.json', 'config.lua', 'settings.lua') or path.split('/')[0].casefold() == 'config': defaults.append(path)
                else: program.append(path)
            mod = dict(id=_id(folder), name=folder, version='unversioned', description='Imported mod; no public manifest was supplied.', controls='', settings=[], files=sorted(program), default_files=sorted(defaults), entrypoints=entrypoints)
        mods.append(mod)
        for relative in mod.get('files', []) + mod.get('default_files', []):
            safe_path(relative)
            if relative not in payload: raise ValueError('Missing declared payload: ' + relative)
            normalized['Mods/%s/%s' % (mod['id'], relative)] = payload[relative]
    normalized['catalog.json'] = json.dumps({'schema_version':1, 'mods':mods}).encode('utf-8')
    return Snapshot('package-' + _digest(files)[:24], normalized, source_id)


def _digest(files):
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode('utf-8') + b'\0'); digest.update(hashlib.sha256(files[name]).digest())
    return digest.hexdigest()


def package_from_archive(data: bytes, source_id: str = 'import') -> Snapshot:
    return _normalize(read_archive(data, strip_root=False), source_id=source_id)


def load_package(path: Path) -> Snapshot:
    path = Path(path)
    if any(is_redirect(parent) for parent in [path] + list(path.parents)): raise ValueError('Symbolic links and reparse points are not supported.')
    if not path.is_dir():
        if path.stat().st_size > 128 * 1024 * 1024: raise ValueError('Package is too large.')
        result = package_from_archive(path.read_bytes())
    elif (path / 'catalog.json').is_file():
        result = Snapshot.from_directory(path)
        result.source_id = 'import'
    else:
        files = {}; total = 0; spellings = {}
        for entry in path.rglob('*'):
            if is_redirect(entry): raise ValueError('Symbolic links and reparse points are not supported.')
            relative = entry.relative_to(path).as_posix(); safe_path(relative)
            folded = relative.casefold()
            if folded in spellings: raise ValueError('Case-colliding folder paths.')
            spellings[folded] = relative
            if entry.is_dir(): continue
            if not entry.is_file(): raise ValueError('Unsupported special file.')
            size = entry.stat().st_size; total += size
            if size > MAX_FILE or total > MAX_EXPANDED or len(files) >= 20000: raise ValueError('Folder package exceeds size limits.')
            files[relative] = entry.read_bytes()
        result = _normalize(files, name=path.name)
    result.origin = {'kind':'local', 'origin':str(path.resolve())}
    return result
