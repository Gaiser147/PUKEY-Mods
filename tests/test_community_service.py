import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from manager.service import Manager


def package(source='community-a', native=False, seeds=None, files=None):
    entry = 'dlls/main.dll' if native else 'scripts/main.lua'
    payload = files or {entry: b'synthetic program'}
    seeds = seeds or {}
    mod = {'id': 'Community', 'name': 'Community', 'version': '1', 'description': '', 'controls': '',
           'files': list(payload), 'default_files': list(seeds), 'settings': [],
           'entrypoints': [{'type': 'native' if native else 'lua', 'path': entry}]}
    return SimpleNamespace(source_id=source, revision='synthetic-1', mods=[mod],
                           files={'Mods/Community/' + k: v for k, v in {**payload, **seeds}.items()})


class CommunityServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        win64 = self.root / 'PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64'
        win64.mkdir(parents=True)
        (win64 / 'PUKEY_GODDESS_SHOT_TRICK_Demo-Win64-Shipping.exe').write_bytes(b'MZfake')
        self.guard = patch('manager.service.game_running', return_value=False)
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def test_native_install_can_start_disabled_then_toggle_and_remove(self):
        manager = Manager(self.root, package(native=True))
        manager.install('Community', enabled=False)
        state = manager.status('Community')
        self.assertTrue(state['installed'])
        self.assertFalse(state['enabled'])
        manager.set_enabled('Community', True)
        self.assertTrue(manager.status('Community')['enabled'])
        manager.remove('Community')
        self.assertFalse(manager.status('Community')['installed'])

    def test_schema_one_read_is_read_only_and_mutation_migrates(self):
        manager = Manager(self.root, package(source='official'))
        manager.state_dir.mkdir(parents=True)
        old = {'schema_version': 1, 'mods': {}, 'loader': {'files': {}}}
        raw = json.dumps(old).encode()
        manager.state_file.write_bytes(raw)
        manager.status('Community')
        self.assertEqual(manager.state_file.read_bytes(), raw)
        manager.install('Community')
        current = json.loads(manager.state_file.read_bytes())
        self.assertEqual(current['schema_version'], 2)
        self.assertEqual(current['mods']['Community']['source_id'], 'official')

    def test_other_source_cannot_adopt_or_mutate_owned_folder(self):
        owner = Manager(self.root, package())
        owner.install('Community')
        before = owner.state_file.read_bytes()
        other = Manager(self.root, package(source='community-b'))
        self.assertTrue(other.status('Community')['conflict'])
        for operation in (lambda: other.install('Community'), lambda: other.set_enabled('Community', False),
                          lambda: other.remove('Community'), lambda: other.settings('Community'),
                          lambda: other.save_settings('Community', {})):
            with self.subTest(operation=operation), self.assertRaisesRegex(ValueError, 'source|owned|conflict'):
                operation()
        self.assertEqual(owner.state_file.read_bytes(), before)

    def test_seed_is_preserved_on_update_reclassification_and_removal(self):
        snapshot = package(seeds={'config.ini': b'[Camera]\nSpeed=1\n'})
        manager = Manager(self.root, snapshot)
        manager.install('Community')
        config = manager.mods_dir / 'Community/config.ini'
        config.write_bytes(b'personal changes')
        manager.install('Community')
        self.assertEqual(config.read_bytes(), b'personal changes')
        # A later package may not take ownership of a previously personal path.
        revised = copy.deepcopy(snapshot)
        revised.mods[0]['default_files'] = []
        revised.mods[0]['files'].append('config.ini')
        revised.files['Mods/Community/config.ini'] = b'new upstream program'
        manager.snapshot = revised
        manager.install('Community')
        self.assertEqual(config.read_bytes(), b'personal changes')
        manager.remove('Community')
        self.assertEqual(config.read_bytes(), b'personal changes')

    def test_case_colliding_unowned_folder_is_not_created(self):
        manager = Manager(self.root, package())
        existing = manager.mods_dir / 'COMMUNITY'
        existing.mkdir(parents=True)
        (existing / 'personal.txt').write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'case|folder|conflict'):
            manager.install('Community')

    def test_personal_ownership_survives_remove_and_reinstall(self):
        manager = Manager(self.root, package(seeds={'config.ini': b'initial'}))
        manager.install('Community')
        target = manager.mods_dir / 'Community/config.ini'
        target.write_bytes(b'personal')
        manager.remove('Community')
        replacement = package(files={'scripts/main.lua': b'program', 'config.ini': b'upstream'})
        manager.snapshot = replacement
        manager.install('Community')
        self.assertEqual(target.read_bytes(), b'personal')

    def test_media_cannot_be_reclassified_by_later_package(self):
        snapshot = package()
        snapshot.mods[0]['images'] = [{'file': 'portrait.png'}]
        manager = Manager(self.root, snapshot)
        manager.install('Community')
        manager.write_user_file('Community', 'portrait.png', b'personal image')
        snapshot.mods[0].pop('images')
        snapshot.mods[0]['files'].append('portrait.png')
        snapshot.files['Mods/Community/portrait.png'] = b'upstream image'
        manager.install('Community')
        target = manager.mods_dir / 'Community/portrait.png'
        self.assertEqual(target.read_bytes(), b'personal image')
        manager.remove('Community')
        self.assertEqual(target.read_bytes(), b'personal image')

    def test_changed_entrypoint_preserves_disabled_state_on_update(self):
        manager = Manager(self.root, package())
        manager.install('Community', enabled=False)
        manager.snapshot = package(native=True)
        self.assertTrue(manager.status('Community')['installed'])
        manager.install('Community')
        self.assertFalse(manager.status('Community')['enabled'])

    def test_changed_source_entrypoint_does_not_prevent_disabling_installed_version(self):
        manager = Manager(self.root, package())
        manager.install('Community')
        manager.snapshot = package(native=True)
        manager.set_enabled('Community', False)
        self.assertFalse(manager.status('Community')['enabled'])

    def test_failed_migration_keeps_original_manifest(self):
        manager = Manager(self.root, package())
        manager.state_dir.mkdir(parents=True)
        old = b'{"schema_version":1,"mods":{},"loader":{"files":{}}}'
        manager.state_file.write_bytes(old)
        with patch.object(manager, '_transaction', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                manager.install('Community')
        self.assertEqual(manager.state_file.read_bytes(), old)


if __name__ == '__main__':
    unittest.main()
