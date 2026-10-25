import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from manager.catalog import Snapshot, validate_settings


def zipped(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, data in files.items(): archive.writestr(name, data)
    return stream.getvalue()


def manifest(**changes):
    value = dict(schema_version=1, id='Example', name='Example', version='1', description='Demo', files=['Scripts/main.lua'], entrypoints=[{'type':'lua','path':'Scripts/main.lua'}])
    value.update(changes)
    return json.dumps(value).encode()


class PackageTests(unittest.TestCase):
    def test_manifest_defaults_and_native_entrypoint(self):
        from manager.packages import package_from_archive
        snapshot = package_from_archive(zipped({'Wrapper/Native/pukey-mod.json': manifest(files=['dlls/Main.dll'], entrypoints=[{'type':'native','path':'dlls/Main.dll'}], default_files=['config.json']), 'Wrapper/Native/dlls/Main.dll':b'placeholder', 'Wrapper/Native/config.json':b'{}'}))
        self.assertEqual(snapshot.mods[0]['controls'], '')
        self.assertEqual(snapshot.mods[0]['default_files'], ['config.json'])
        self.assertEqual(snapshot.files['Mods/Example/config.json'], b'{}')
        self.assertEqual(snapshot.source_id, 'import')

    def test_infers_multiple_mods_preserving_spelling_and_defaults(self):
        from manager.packages import package_from_archive
        result = package_from_archive(zipped({'repo/Mods/First/scripts/Main.Lua':b'return {}', 'repo/Mods/First/settings.json':b'{}', 'repo/Mods/First/enabled.txt':b'1', 'repo/Mods/Second/dlls/Second.dll':b'placeholder'}))
        self.assertEqual([mod['id'] for mod in result.mods], ['First', 'Second'])
        self.assertEqual(result.mods[0]['entrypoints'], [{'type':'lua','path':'scripts/Main.Lua'}])
        self.assertEqual(result.mods[0]['default_files'], ['settings.json'])
        self.assertNotIn('Mods/First/enabled.txt', result.files)
        self.assertNotIn('settings.json', result.mods[0]['files'])

    def test_rejects_ambiguous_nested_roots_and_unsafe_archives(self):
        from manager.packages import package_from_archive
        for files in ({'Scripts/main.lua':b'', 'Nested/Scripts/main.lua':b''}, {'../Scripts/main.lua':b''}, {'X/dlls/a.dll':b'', 'X/dlls/b.dll':b''}):
            with self.subTest(files=files), self.assertRaises(ValueError): package_from_archive(zipped(files))

    def test_folder_import_and_cli_do_not_execute_code(self):
        from manager.packages import load_package
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'Safe'; (root/'Scripts').mkdir(parents=True)
            (root/'Scripts/main.lua').write_text('raise if executed')
            snapshot = load_package(root)
            self.assertEqual(snapshot.mods[0]['id'], 'Safe')
            result = subprocess.run([sys.executable, '-m', 'manager.validate_mod', str(root)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Safe', result.stdout)

    def test_string_settings_and_plain_help_validation(self):
        mod = dict(id='Example', name='Example', version='1', description='Demo', controls='', files=['Scripts/main.lua'], settings=[dict(key='Title', label='Title', type='string', default='Hello', description='A title')])
        def create(): return Snapshot('local', {'catalog.json':json.dumps(dict(schema_version=1, mods=[mod])).encode(), 'Mods/Example/Scripts/main.lua':b''})
        snapshot = create()
        self.assertEqual(validate_settings(snapshot.mods[0], {'Title':'World'}), {'Title':'World'})
        for text in ['x\ny', 'x\x85y', 'x'*4097]:
            with self.assertRaises(ValueError): validate_settings(mod, {'Title':text})
        mod['settings'][0]['description'] = '<script>bad</script>'
        with self.assertRaises(ValueError): create()

class CatalogueBoundaryTests(unittest.TestCase):
    def test_giant_integer_is_invalid_instead_of_crashing(self):
        mod = dict(settings=[dict(key='Speed', label='Speed', type='number', default=1, min=0, max=10)])
        with self.assertRaises(ValueError): validate_settings(mod, {'Speed':10**1000})

    def test_option_help_and_default_file_conflicts_are_rejected(self):
        from manager.packages import package_from_archive
        for overrides in [dict(default_files=['Scripts/main.lua']), dict(settings=[dict(key='Mode', label='Mode', type='enum', default='a', options=['a'], option_descriptions={'b':'Unknown'})])]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                package_from_archive(zipped({'Demo/pukey-mod.json':manifest(**overrides), 'Demo/Scripts/main.lua':b''}))

class CatalogueFolderTests(unittest.TestCase):
    def test_catalogue_folder_reads_only_declared_payloads(self):
        from manager.packages import load_package
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mod = json.loads(manifest()); del mod['schema_version']; mod['controls'] = ''
            (root/'catalog.json').write_text(json.dumps({'schema_version':1, 'mods':[mod]}))
            (root/'Mods/Example/Scripts').mkdir(parents=True)
            (root/'Mods/Example/Scripts/main.lua').write_text('return {}')
            with (root/'unrelated-research.txt').open('wb') as stream: stream.truncate(33*1024*1024)
            result = load_package(root)
            self.assertEqual(result.mods[0]['id'], 'Example')
            self.assertEqual(result.source_id, 'import')

class ManifestTextTests(unittest.TestCase):
    def test_mod_description_is_bounded_plain_text(self):
        from manager.packages import package_from_archive
        for description in ['<b>markup</b>', 'x'*4097, 'bad\x00text']:
            with self.subTest(description=description[:20]), self.assertRaises(ValueError):
                package_from_archive(zipped({'Demo/pukey-mod.json':manifest(description=description), 'Demo/Scripts/main.lua':b''}))

class InferredFolderIdentityTests(unittest.TestCase):
    def test_native_folder_identity_is_never_silently_renamed(self):
        from manager.packages import package_from_archive
        for folder in ['Example Native', '1Example', 'Example.Mod', 'x' * 65]:
            with self.subTest(folder=folder), self.assertRaisesRegex(ValueError, 'folder.*pukey-mod.json'):
                package_from_archive(zipped({folder + '/dlls/' + folder + '.dll': b'placeholder'}))

    def test_manifest_id_is_explicit_even_when_wrapper_folder_needs_another_name(self):
        from manager.packages import package_from_archive
        snapshot = package_from_archive(zipped({'Example Native/pukey-mod.json': manifest(files=['dlls/main.dll'], entrypoints=[{'type':'native','path':'dlls/main.dll'}]), 'Example Native/dlls/main.dll': b'placeholder'}))
        self.assertEqual(snapshot.mods[0]['id'], 'Example')
