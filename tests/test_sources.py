import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.test_packages import zipped


class SourceTests(unittest.TestCase):
    def test_add_load_are_source_scoped_and_validate_cache_digest(self):
        from manager.sources import SourceStore
        from manager.packages import package_from_archive
        with tempfile.TemporaryDirectory() as directory:
            store = SourceStore(Path(directory))
            first = store.add(package_from_archive(zipped({'Demo/Scripts/main.lua':b'first'})), 'local-one.zip', ['Demo'])
            second = store.add(package_from_archive(zipped({'Demo/Scripts/main.lua':b'second'})), 'local-two.zip', ['Demo'])
            self.assertNotEqual(first, second)
            self.assertEqual(store.load(first).files['Mods/Demo/Scripts/main.lua'], b'first')
            self.assertEqual(store.load(second).source_id, second)
            store.records[0]['selected_ids'].clear()
            self.assertEqual(SourceStore(Path(directory)).records[0]['selected_ids'], ['Demo'])
            record = store.records[0]
            (Path(directory)/record['cache']).write_bytes(b'corrupt')
            with self.assertRaises(ValueError): store.load(first)

    def test_refresh_retains_selections_and_missing_mod_metadata_and_failed_cache(self):
        from manager.sources import SourceStore
        from manager.packages import load_package
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); archive = root/'package.zip'
            archive.write_bytes(zipped({'One/Scripts/main.lua':b'old', 'Two/Scripts/main.lua':b'two'}))
            store = SourceStore(root/'library')
            identity = store.add(load_package(archive), str(archive), ['One', 'Two'])
            archive.write_bytes(zipped({'One/Scripts/main.lua':b'new'}))
            result = store.update_from_package(identity, archive)
            self.assertEqual(result.files['Mods/One/Scripts/main.lua'], b'new')
            self.assertFalse(next(mod for mod in result.mods if mod['id']=='Two')['available'])
            self.assertEqual(store.records[0]['selected_ids'], ['One', 'Two'])
            archive.write_bytes(b'invalid')
            with self.assertRaises(ValueError): store.update_from_package(identity, archive)
            self.assertEqual(store.load(identity).files['Mods/One/Scripts/main.lua'], b'new')

    def test_resolve_default_branch_uses_immutable_commit(self):
        from manager.sources import SourceStore
        urls = []
        def fetch(url, limit=None):
            urls.append(url)
            if url.endswith('/repos/owner/repo'): return json.dumps({'default_branch':'develop'}).encode()
            if '/commits/' in url: return json.dumps({'sha':'b'*40}).encode()
            return zipped({'repo-b/Mods/Demo/Scripts/main.lua':b'code'})
        with tempfile.TemporaryDirectory() as directory, patch('manager.sources.download', side_effect=fetch):
            snapshot = SourceStore(Path(directory)).resolve('https://github.com/owner/repo')
            self.assertEqual(snapshot.revision, 'b'*40)
            self.assertEqual(snapshot.origin['branch'], 'develop')
            self.assertEqual(urls[-1], 'https://codeload.github.com/owner/repo/zip/' + 'b'*40)

    def test_release_choices_preserve_channel_and_source_only_repo_exposes_releases(self):
        from manager.sources import SourceStore, SourceChoices
        release = {'tag_name':'v1', 'name':'Version 1', 'assets':[{'name':'one.zip','browser_download_url':'https://example.com/one.zip'}, {'name':'two.zip','browser_download_url':'https://example.com/two.zip'}]}
        def fetch(url, limit=None):
            if url.endswith('/repos/owner/repo'): return json.dumps({'default_branch':'main'}).encode()
            if '/commits/' in url: return json.dumps({'sha':'a'*40}).encode()
            if 'codeload.github.com' in url: return zipped({'repo/README.md':b'source only'})
            if url.endswith('/releases'): return json.dumps([release]).encode()
            if '/releases/' in url: return json.dumps(release).encode()
            return zipped({'Demo/Scripts/main.lua':b'code'})
        with tempfile.TemporaryDirectory() as directory, patch('manager.sources.download', side_effect=fetch):
            store = SourceStore(Path(directory))
            with self.assertRaises(SourceChoices) as releases: store.resolve('https://github.com/owner/repo')
            self.assertIn('/releases/tag/v1', releases.exception.choices[0]['url'])
            with self.assertRaises(SourceChoices) as assets: store.resolve('https://github.com/owner/repo/releases/latest')
            snapshot = store.resolve(assets.exception.choices[1]['url'])
            self.assertEqual(snapshot.origin['channel'], 'latest')
            self.assertEqual(snapshot.origin['asset_name'], 'two.zip')

    def test_insecure_network_origins_are_rejected(self):
        from manager.sources import SourceStore
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError): SourceStore(Path(directory)).resolve('http://example.com/mod.zip')

class DownloadSafetyTests(unittest.TestCase):
    def test_https_redirects_cannot_downgrade_or_include_credentials(self):
        from manager.catalog import HTTPSRedirectHandler
        from urllib.request import Request
        handler = HTTPSRedirectHandler()
        for target in ['http://example.com/mod.zip', 'ftp://example.com/mod.zip', 'https://user:secret@example.com/mod.zip']:
            with self.subTest(target=target), self.assertRaises(ValueError):
                handler.redirect_request(Request('https://example.com/start'), None, 302, '', {}, target)
        request = handler.redirect_request(Request('https://example.com/start'), None, 302, '', {}, 'https://cdn.example.com/mod.zip')
        self.assertEqual(request.full_url, 'https://cdn.example.com/mod.zip')

    def test_registry_failure_preserves_previous_valid_source(self):
        import manager.sources as sources
        from manager.packages import package_from_archive
        with tempfile.TemporaryDirectory() as directory:
            store = sources.SourceStore(Path(directory))
            first = package_from_archive(zipped({'Demo/Scripts/main.lua':b'first'}))
            identity = store.add(first, 'local.zip', ['Demo'])
            second = package_from_archive(zipped({'Demo/Scripts/main.lua':b'second'}))
            atomic = sources._atomic
            def fail_registry(path, data):
                if path.name == 'sources.json': raise OSError('simulated disk failure')
                return atomic(path, data)
            with patch('manager.sources._atomic', side_effect=fail_registry), self.assertRaises(OSError):
                store.add(second, 'local.zip', ['Demo'], identity)
            self.assertEqual(store.load(identity).files['Mods/Demo/Scripts/main.lua'], b'first')

class SourceRefreshBranchTests(unittest.TestCase):
    def test_refresh_follows_saved_branch_when_repository_default_changes(self):
        from manager.sources import SourceStore
        urls = []
        def fetch(url, limit=None):
            urls.append(url)
            if url.endswith('/repos/owner/repo'): return json.dumps({'default_branch':'develop'}).encode()
            if '/commits/' in url: return json.dumps({'sha':'c'*40}).encode()
            return zipped({'repo/Mods/Demo/Scripts/main.lua':b'code'})
        with tempfile.TemporaryDirectory() as directory, patch('manager.sources.download', side_effect=fetch):
            store = SourceStore(Path(directory))
            snapshot = store.resolve('https://github.com/owner/repo')
            identity = store.add(snapshot, 'https://github.com/owner/repo', ['Demo'])
            urls.clear()
            refreshed = store.refresh(identity)
            self.assertEqual(refreshed.origin['branch'], 'develop')
            self.assertIn('https://api.github.com/repos/owner/repo/commits/develop', urls)
            self.assertNotIn('https://api.github.com/repos/owner/repo', urls)


class ExplicitUpdateTests(unittest.TestCase):
    def test_local_source_refresh_requires_explicit_package_reselection(self):
        from manager.sources import SourceStore
        from manager.packages import load_package
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); archive = root/'package.zip'
            archive.write_bytes(zipped({'Demo/Scripts/main.lua':b'code'}))
            store = SourceStore(root/'library')
            identity = store.add(load_package(archive), str(archive), ['Demo'])
            with self.assertRaisesRegex(ValueError, 'Update from ZIP'): store.refresh(identity)

    def test_latest_release_asset_rename_offers_current_assets(self):
        from manager.sources import SourceStore, SourceChoices
        release = {'tag_name':'v2', 'assets':[{'name':'mod-v2.zip','browser_download_url':'https://example.com/v2.zip'}]}
        with tempfile.TemporaryDirectory() as directory, patch('manager.sources.download', return_value=json.dumps(release).encode()):
            with self.assertRaises(SourceChoices) as result:
                SourceStore(Path(directory)).resolve('https://github.com/owner/repo/releases/latest?asset=mod-v1.zip')
            self.assertEqual(result.exception.choices[0]['label'], 'mod-v2.zip')
            self.assertIn('latest?asset=mod-v2.zip', result.exception.choices[0]['url'])

class AcceptedSourceUpdateTests(unittest.TestCase):
    def test_explicit_resolved_update_keeps_disappeared_selected_mod(self):
        from manager.sources import SourceStore
        from manager.packages import package_from_archive
        with tempfile.TemporaryDirectory() as directory:
            store = SourceStore(Path(directory))
            identity = store.add(package_from_archive(zipped({'One/Scripts/main.lua':b'1', 'Two/Scripts/main.lua':b'2'})), 'https://example.com/mod.zip', ['Two'])
            next_snapshot = package_from_archive(zipped({'One/Scripts/main.lua':b'next'}))
            next_snapshot.origin = dict(kind='https', origin='https://example.com/mod.zip')
            updated = store.update(identity, next_snapshot)
            self.assertFalse(next(mod for mod in updated.mods if mod['id']=='Two')['available'])
            self.assertEqual(store.records[0]['selected_ids'], ['Two'])

class GeneratedCacheSafetyTests(unittest.TestCase):
    def test_retained_removed_mods_cannot_commit_an_oversized_cache(self):
        from manager.sources import SourceStore
        from manager.packages import package_from_archive
        with tempfile.TemporaryDirectory() as directory:
            store = SourceStore(Path(directory))
            old = package_from_archive(zipped({'Old/Scripts/main.lua': b'o' * 800}))
            identity = store.add(old, 'https://example.com/mod.zip', ['Old'])
            previous_registry = store.registry.read_bytes()
            previous_record = store.records[0]
            previous_cache = (store.root / previous_record['cache']).read_bytes()
            previous_files = set(store.root.rglob('*'))
            current = package_from_archive(zipped({'New/Scripts/main.lua': b'n' * 800}))
            with patch('manager.catalog.MAX_EXPANDED', 1800):
                with self.assertRaisesRegex(ValueError, 'Expanded archive'):
                    store.update(identity, current)
                self.assertEqual(store.registry.read_bytes(), previous_registry)
                self.assertEqual((store.root / previous_record['cache']).read_bytes(), previous_cache)
                self.assertEqual(set(store.root.rglob('*')), previous_files)
                self.assertEqual(store.load(identity).files['Mods/Old/Scripts/main.lua'], b'o' * 800)

    def test_generated_file_directory_collision_cannot_replace_valid_cache(self):
        from manager.sources import SourceStore
        from manager.catalog import Snapshot
        from manager.packages import package_from_archive
        with tempfile.TemporaryDirectory() as directory:
            store = SourceStore(Path(directory))
            valid = package_from_archive(zipped({'Demo/Scripts/main.lua': b'original'}))
            identity = store.add(valid, 'https://example.com/mod.zip', ['Demo'])
            previous_registry = store.registry.read_bytes()
            previous_files = set(store.root.rglob('*'))
            mod = valid.mods[0]
            mod['files'] += ['Nested', 'Nested/value.txt']
            payload = dict(valid.files)
            payload.update({'Mods/Demo/Nested': b'file', 'Mods/Demo/Nested/value.txt': b'nested',
                            'catalog.json': json.dumps({'schema_version': 1, 'mods': [mod]}).encode()})
            malformed = Snapshot('replacement', payload)
            with self.assertRaisesRegex(ValueError, 'collision'):
                store.add(malformed, 'https://example.com/mod.zip', ['Demo'], identity)
            self.assertEqual(store.registry.read_bytes(), previous_registry)
            self.assertEqual(set(store.root.rglob('*')), previous_files)
            self.assertEqual(store.load(identity).files['Mods/Demo/Scripts/main.lua'], b'original')

class SourceStorageRedirectTests(unittest.TestCase):
    def test_atomic_write_checks_ancestors_before_creating_parent_directories(self):
        from manager.sources import _atomic
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            redirect = root / 'junction'
            redirect.mkdir()
            target = redirect / 'outside-cache' / 'record.json'
            with patch('manager.sources.is_redirect', side_effect=lambda path: path == redirect):
                with self.assertRaisesRegex(ValueError, 'reparse'):
                    _atomic(target, b'{}')
            self.assertFalse(target.parent.exists())
            self.assertFalse(target.exists())
