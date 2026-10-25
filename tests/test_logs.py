import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from manager.logs import TailReader, discover_log_sources, INITIAL_READ_BYTES, POLL_READ_BYTES


class TailReaderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'UE4SS.log'

    def test_missing_path_waits_then_reads_creation(self):
        reader = TailReader(self.path)
        self.assertTrue(reader.poll().missing)
        self.path.write_text('created\n', encoding='utf-8', newline='\n')
        result = reader.poll()
        self.assertEqual(result.text, 'created\n')
        self.assertTrue(result.reset)
        self.assertFalse(result.missing)

    def test_initial_tail_and_followup_reads_are_bounded(self):
        self.path.write_bytes(b'x' * (INITIAL_READ_BYTES * 2))
        reader = TailReader(self.path)
        first = reader.poll()
        self.assertLessEqual(first.bytes_read, INITIAL_READ_BYTES)
        self.assertLessEqual(len(first.text), INITIAL_READ_BYTES)
        with self.path.open('ab') as stream:
            stream.write(b'y' * (POLL_READ_BYTES * 3))
        following = reader.poll()
        self.assertLessEqual(following.bytes_read, POLL_READ_BYTES)
        self.assertIn('y', following.text)
        self.assertLessEqual(reader.poll().bytes_read, POLL_READ_BYTES)

    def test_utf8_keeps_split_multibyte_character(self):
        self.path.write_bytes(b'hello ' + b'\xe2\x82')
        reader = TailReader(self.path)
        self.assertEqual(reader.poll().text, 'hello ')
        with self.path.open('ab') as stream:
            stream.write(b'\xac\n')
        self.assertEqual(reader.poll().text, '\u20ac\n')

    def test_utf16_bom_and_invalid_utf8_are_readable(self):
        self.path.write_bytes('hello \u2603\n'.encode('utf-16'))
        self.assertEqual(TailReader(self.path).poll().text, 'hello \u2603\n')
        self.path.write_bytes(b'good\xffbad\n')
        self.assertEqual(TailReader(self.path).poll().text, 'good\ufffdbad\n')

    def test_truncation_and_rotation_reset_without_holding_file_open(self):
        self.path.write_text('old line\n', encoding='utf-8', newline='\n')
        reader = TailReader(self.path)
        reader.poll()
        self.path.write_text('new\n', encoding='utf-8', newline='\n')
        result = reader.poll()
        self.assertTrue(result.reset)
        self.assertEqual(result.text, 'new\n')
        self.path.rename(self.path.with_suffix('.old'))
        self.path.write_text('replacement\n', encoding='utf-8', newline='\n')
        result = reader.poll()
        self.assertTrue(result.reset)
        self.assertEqual(result.text, 'replacement\n')

    def test_discovery_scopes_proton_to_selected_library_and_keeps_expected_paths(self):
        library = Path(self.directory.name) / 'SteamLibrary'
        game = library / 'steamapps/common/Game'
        win64 = game / 'PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64'
        (win64 / 'ue4ss').mkdir(parents=True)
        (win64 / 'ue4ss/UE4SS.dll').write_bytes(b'fixture')
        prefix = library / 'steamapps/compatdata/5253020/pfx/drive_c/users'
        game_log = prefix / 'alice/AppData/Local/PUKEY_GODDESS_SHOT_TRICK/Saved/Logs/Game.log'
        game_log.parent.mkdir(parents=True)
        game_log.write_text('game\n')
        with patch('manager.logs.sys.platform', 'linux'):
            sources = discover_log_sources(win64)
        paths = [source.path for source in sources]
        self.assertIn(win64 / 'ue4ss/UE4SS.log', paths)
        self.assertIn(win64 / 'UE4SS.log', paths)
        self.assertIn(game_log, paths)
        self.assertIn(game / 'PUKEY_GODDESS_SHOT_TRICK/Saved/Logs/PUKEY_GODDESS_SHOT_TRICK.log', paths)
        self.assertTrue(all(str(path).startswith(str(library)) for path in paths))

    def test_windows_discovery_includes_localappdata_without_selected_game(self):
        with patch('manager.logs.sys.platform', 'win32'), patch.dict(os.environ, {'LOCALAPPDATA': self.directory.name}):
            sources = discover_log_sources(None)
        self.assertIn(Path(self.directory.name) / 'PUKEY_GODDESS_SHOT_TRICK/Saved/Logs/PUKEY_GODDESS_SHOT_TRICK.log',
                      [source.path for source in sources])

    def test_tail_does_not_invent_replacement_for_leading_utf8_fragment(self):
        self.path.write_bytes(('\u20ac' * INITIAL_READ_BYTES).encode('utf-8'))
        result = TailReader(self.path).poll()
        self.assertEqual(result.text.count('\ufffd'), 0)
        self.assertLessEqual(result.bytes_read, INITIAL_READ_BYTES)

    def test_empty_log_can_begin_with_utf16_later(self):
        self.path.write_bytes(b'')
        reader = TailReader(self.path)
        self.assertEqual(reader.poll().text, '')
        self.path.write_bytes('later\n'.encode('utf-16'))
        self.assertEqual(reader.poll().text, 'later\n')

    def test_discovery_prefers_existing_sources_to_expected_missing_files(self):
        win64 = Path(self.directory.name) / 'PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64'
        win64.mkdir(parents=True)
        legacy = win64 / 'UE4SS.log'
        legacy.write_text('fixture')
        sources = discover_log_sources(win64)
        self.assertEqual(next(source.path for source in sources if source.kind == 'UE4SS'), legacy)
    def test_utf16le_without_bom_is_readable(self):
        self.path.write_bytes('game line\n'.encode('utf-16-le'))
        self.assertEqual(TailReader(self.path).poll().text, 'game line\n')
