"""Exercise the installer against temporary fake game folders, never Steam."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ('CheatManagerEnablerMod', 'ConsoleEnablerMod', 'ConsoleCommandsMod')


@unittest.skipUnless(os.name == 'nt' and shutil.which('powershell'), 'Requires Windows PowerShell')
class InstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='pukey-installer-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / 'Package'
        self.package.mkdir()
        shutil.copy2(ROOT / 'dist-src/install.ps1', self.package / 'install.ps1')
        shutil.copytree(ROOT / 'Mods/FamSwap', self.package / 'Mods/FamSwap')
        self.game = self.root / 'GameCopy'
        self.win64 = self.game / 'PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64'
        self.win64.mkdir(parents=True)

    def run_installer(self):
        return subprocess.run([
            'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            str(self.package / 'install.ps1'), '-GameDir', str(self.game),
            '-NoDownload', '-SkipRunningCheck',
        ], capture_output=True, text=True, errors='replace', timeout=40)

    def test_missing_ue4ss_prints_manual_steps_without_installing(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('Install UE4SS manually', result.stdout)
        self.assertFalse((self.win64 / 'ue4ss/Mods/FamSwap').exists())

    def test_install_preserves_images_and_disables_all_example_activation(self):
        (self.win64 / 'dwmapi.dll').write_bytes(b'fake loader')
        ue4ss = self.win64 / 'ue4ss'
        ue4ss.mkdir()
        (ue4ss / 'UE4SS.dll').write_bytes(b'fake loader')
        mods = ue4ss / 'Mods'
        target = mods / 'FamSwap'
        target.mkdir(parents=True)
        for name in EXAMPLES + ('OtherMod',):
            folder = mods / name
            folder.mkdir()
            (folder / 'enabled.txt').touch()
        (mods / 'mods.txt').write_text(
            '\n'.join(name + ' : 1' for name in EXAMPLES + ('OtherMod', 'Keybinds')) + '\n',
            encoding='utf-8')
        (mods / 'mods.json').write_text(json.dumps([
            {'mod_name': name, 'mod_enabled': True} for name in EXAMPLES + ('OtherMod',)
        ]), encoding='utf-8')
        for name in ('bar.png', 'game.jpg'):
            (target / name).write_bytes(b'user image')
            (self.package / 'Mods/FamSwap' / name).write_bytes(b'package image')

        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((target / 'Scripts/main.lua').read_bytes(),
                         (ROOT / 'Mods/FamSwap/Scripts/main.lua').read_bytes())
        self.assertTrue((target / 'enabled.txt').exists())
        for name in ('bar.png', 'game.jpg'):
            self.assertEqual((target / name).read_bytes(), b'user image')
        settings = (mods / 'mods.txt').read_text(encoding='utf-8')
        for name in EXAMPLES:
            self.assertIn(name + ' : 0', settings)
        self.assertIn('OtherMod : 1', settings)
        self.assertIn('Keybinds : 1', settings)
        entries = json.loads((mods / 'mods.json').read_text(encoding='utf-8'))
        self.assertEqual({entry['mod_name']: entry['mod_enabled'] for entry in entries},
                         dict([(name, False) for name in EXAMPLES] + [('OtherMod', True)]))
        self.assertTrue((mods / 'OtherMod/enabled.txt').exists())
        for name in EXAMPLES:
            self.assertFalse((mods / name / 'enabled.txt').exists(), name + ' still enabled by marker')

    def test_empty_and_singleton_json_arrays_keep_their_shape(self):
        (self.win64 / 'dwmapi.dll').write_bytes(b'fake loader')
        ue4ss = self.win64 / 'ue4ss'
        ue4ss.mkdir()
        (ue4ss / 'UE4SS.dll').write_bytes(b'fake loader')
        mods = ue4ss / 'Mods'
        mods.mkdir()
        for entries in ([{'mod_name': 'OtherMod', 'mod_enabled': True}], []):
            with self.subTest(entries=entries):
                (mods / 'mods.json').write_text(json.dumps(entries), encoding='utf-8')
                result = self.run_installer()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads((mods / 'mods.json').read_text(encoding='utf-8')), entries)


if __name__ == '__main__':
    unittest.main()
