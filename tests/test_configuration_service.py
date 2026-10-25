"""Configuration lifecycle integration uses disposable game roots exclusively."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from manager.catalog import Snapshot
from manager.platforms import WIN64_PART
from manager.service import Manager


def configured_snapshot(version='1', source='community-demo'):
    mod = {
        'id': 'Configured', 'name': 'Configured', 'version': version,
        'description': 'A configurable community package', 'controls': 'F5',
        'files': ['Scripts/main.lua'],
        'entrypoints': [{'type': 'lua', 'path': 'Scripts/main.lua'}],
        'default_files': ['config.json', 'camera.ini'],
        'settings': [
            {'key': 'Speed', 'label': 'Speed', 'type': 'number', 'default': 2, 'min': 1, 'max': 10},
            {'key': 'Visible', 'label': 'Visible', 'type': 'boolean', 'default': True},
            {'key': 'Note', 'label': 'Note', 'type': 'string', 'default': ''},
        ],
        'configuration': [
            {'file': 'config.json', 'format': 'json', 'bindings': {'Speed': {'path': ['Camera', 'Speed']}, 'Note': {'path': ['Camera', 'Note']}}},
            {'file': 'camera.ini', 'format': 'ini', 'bindings': {'Visible': {'section': 'Camera', 'key': 'Visible'}}},
        ],
    }
    files = {
        'catalog.json': json.dumps({'schema_version': 1, 'mods': [mod]}).encode(),
        'Mods/Configured/Scripts/main.lua': ('-- code version ' + version).encode(),
        'Mods/Configured/config.json': b'{"Camera":{"Speed":4,"Note":"seed"},"Other":"kept"}',
        'Mods/Configured/camera.ini': b'; personal settings\r\n[Camera]\r\nVisible=false ; preview\r\nForeign=untouched\r\n',
    }
    result = Snapshot('revision-' + version, files)
    result.source_id = source
    return result


class ConfigurationServiceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        win64 = self.root / WIN64_PART
        win64.mkdir(parents=True)
        (win64 / 'PUKEY_GODDESS_SHOT_TRICK-Win64-Shipping.exe').touch()
        guard = patch('manager.service.game_running', return_value=False)
        guard.start(); self.addCleanup(guard.stop)
        self.manager = Manager(self.root, configured_snapshot())
        self.mod = self.manager.snapshot.mods[0]
        self.folder = self.manager.mods_dir / 'Configured'

    def test_manifest_bindings_load_seeded_values_and_save_actual_targets(self):
        self.manager.install(self.mod)
        self.assertEqual(self.manager.settings(self.mod), {'Speed': 4, 'Visible': False, 'Note': 'seed'})
        self.manager.save_settings(self.mod, {'Speed': 6, 'Visible': True, 'Note': 'literal ";# %value%'})
        self.assertEqual(self.manager.settings(self.mod), {'Speed': 6, 'Visible': True, 'Note': 'literal ";# %value%'})
        saved = json.loads((self.folder / 'config.json').read_bytes())
        self.assertEqual(saved, {'Camera': {'Speed': 6, 'Note': 'literal ";# %value%'}, 'Other': 'kept'})
        self.assertEqual((self.folder / 'camera.ini').read_bytes(), b'; personal settings\r\n[Camera]\r\nVisible=true ; preview\r\nForeign=untouched\r\n')
        manifest = json.loads(self.manager.state_file.read_bytes())
        self.assertEqual(manifest['schema_version'], 2)
        entry = manifest['mods']['Configured']
        self.assertEqual(entry['source_id'], 'community-demo')
        self.assertEqual(set(entry['files']), {'Scripts/main.lua'})
        self.assertEqual(set(entry['personal_files']), {'config.json', 'camera.ini'})
        self.assertFalse((self.folder / 'settings.lua').exists())
        self.assertFalse((self.folder / 'settings.json').exists())

    def test_partial_save_preserves_other_existing_bound_values(self):
        self.manager.install(self.mod)
        self.manager.save_settings(self.mod, {'Speed': 7})
        self.assertEqual(self.manager.settings(self.mod), {'Speed': 7, 'Visible': False, 'Note': 'seed'})

    def test_second_target_replace_failure_rolls_back_first_target(self):
        self.manager.install(self.mod)
        originals = {name: (self.folder / name).read_bytes() for name in ('config.json', 'camera.ini')}
        manifest_before = self.manager.state_file.read_bytes()
        replace = os.replace
        def fail_second_target(source, destination):
            if Path(destination) == self.folder / 'camera.ini' and Path(source).name.startswith('.pukey-stage-'):
                raise OSError('simulated second configuration replacement failure')
            return replace(source, destination)
        with patch('manager.service.os.replace', side_effect=fail_second_target), self.assertRaisesRegex(OSError, 'second configuration'):
            self.manager.save_settings(self.mod, {'Speed': 8, 'Visible': True, 'Note': 'changed'})
        self.assertEqual({name: (self.folder / name).read_bytes() for name in originals}, originals)
        self.assertEqual(self.manager.state_file.read_bytes(), manifest_before)
        self.assertEqual(self.manager.settings(self.mod), {'Speed': 4, 'Visible': False, 'Note': 'seed'})
        self.assertEqual(list(self.folder.rglob('.pukey-stage-*')), [])

    def test_other_source_cannot_read_or_write_owned_configuration(self):
        self.manager.install(self.mod)
        before = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        self.manager.snapshot = configured_snapshot(source='other-community')
        mod = self.manager.snapshot.mods[0]
        with self.assertRaisesRegex(ValueError, 'owned by another source'):
            self.manager.settings(mod)
        with self.assertRaisesRegex(ValueError, 'owned by another source'):
            self.manager.save_settings(mod, {'Speed': 9})
        self.assertEqual({str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}, before)

    def test_existing_personal_configuration_survives_update_and_remove(self):
        self.manager.install(self.mod)
        self.manager.save_settings(self.mod, {'Speed': 9, 'Visible': True, 'Note': 'personal'})
        personal = {name: (self.folder / name).read_bytes() for name in ('config.json', 'camera.ini')}
        self.manager.snapshot = configured_snapshot(version='2')
        mod = self.manager.snapshot.mods[0]
        self.manager.install(mod)
        self.assertEqual((self.folder / 'Scripts/main.lua').read_bytes(), b'-- code version 2')
        self.assertEqual({name: (self.folder / name).read_bytes() for name in personal}, personal)
        self.manager.remove(mod)
        self.assertFalse((self.folder / 'Scripts/main.lua').exists())
        self.assertEqual({name: (self.folder / name).read_bytes() for name in personal}, personal)
        self.assertNotIn('Configured', json.loads(self.manager.state_file.read_bytes())['mods'])

    def test_existing_seed_target_is_never_replaced_on_first_adoption(self):
        self.folder.mkdir(parents=True)
        personal = b'{"Camera":{"Speed":5,"Note":"adopted"},"Other":"original"}'
        (self.folder / 'config.json').write_bytes(personal)
        self.manager.install(self.mod)
        self.assertEqual((self.folder / 'config.json').read_bytes(), personal)
        self.assertEqual(self.manager.settings(self.mod), {'Speed': 5, 'Visible': False, 'Note': 'adopted'})


if __name__ == '__main__':
    unittest.main()
