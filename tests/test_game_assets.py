"""Synthetic fixtures only: no game bytes are distributed with these tests."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from manager import game_assets

NAMES = ('logo.png', 'dialogue.png', 'sheet.png', 'ribbon.png', 'button-pink.png', 'heading.png', 'divider.png')


class GameAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'game' / 'PUKEY_GODDESS_SHOT_TRICK'
        self.win64 = self.project / 'Binaries' / 'Win64'
        self.win64.mkdir(parents=True)
        (self.win64 / 'PUKEY_GODDESS_SHOT_TRICK_Demo-Win64-Shipping.exe').write_bytes(b'MZsynthetic')
        self.paks = self.project / 'Content' / 'Paks'
        self.paks.mkdir(parents=True)
        self.cache = self.root / 'cache'
        self.layout_file = self.root / 'layout.json'
        self.fixture()
        self.patch_layout = patch.object(game_assets, '_LAYOUT_PATH', self.layout_file)
        self.patch_layout.start()
        self.addCleanup(self.patch_layout.stop)

    def fixture(self, *, flags=9, method=0, bad_block=False, mip_offset=0):
        name = 'PUKEY_GODDESS_SHOT_TRICK-Windows'
        chunks = [bytes((n, 20, 30, 255)) * 4 for n in range(7)]
        toc = bytearray(144)
        toc[:16] = b'-==--==--==--==-'
        toc[16] = 8
        struct.pack_into('<9I', toc, 20, 144, 7, 7, 12, int(bool(method)), 32, 16, 0, 1)
        toc[80] = flags
        struct.pack_into('<Q', toc, 88, 2**64-1)
        rows = []
        for i, filename in enumerate(NAMES):
            cid = i.to_bytes(8, 'little') + b'\0\0\0\1'
            toc.extend(cid)
            rows.append(dict(file=filename, index=i, chunk_id=cid.hex(), offset=i*16, length=16,
                             width=2, height=2, format='BGRA', mip_offset=mip_offset, mip_size=16,
                             chunk_sha256=hashlib.sha256(chunks[i]).hexdigest(),
                             rgba_sha256=hashlib.sha256(Image.frombytes('RGBA', (2, 2), chunks[i], 'raw', 'BGRA').tobytes()).hexdigest()))
        for i in range(7):
            toc.extend((i*16).to_bytes(5, 'big') + (16).to_bytes(5, 'big'))
        for i in range(7):
            co = 999999 if bad_block and i == 0 else i*16
            toc.extend(co.to_bytes(5, 'little') + (16).to_bytes(3, 'little') + (16).to_bytes(3, 'little') + bytes([method]))
        if method:
            toc.extend(b'Oodle\0'.ljust(32, b'\0'))
        self.toc = self.paks / (name + '.utoc')
        self.ucas = self.paks / (name + '.ucas')
        self.toc.write_bytes(toc)
        self.ucas.write_bytes(b''.join(chunks))
        self.layout = dict(schema=1, container=name, toc_sha256=hashlib.sha256(toc).hexdigest(), ucas_size=112, assets=rows,
                           block_sha256={str(i): hashlib.sha256(chunk).hexdigest() for i, chunk in enumerate(chunks)})
        self.layout_file.write_text(json.dumps(self.layout))

    def test_extracts_seven_verified_images_and_reuses_cache(self):
        messages = []
        output = game_assets.extract_theme(self.win64, self.cache, messages.append)
        self.assertTrue(game_assets.game_present(self.win64))
        self.assertTrue(output.is_relative_to(self.cache.resolve()))
        for i, name in enumerate(NAMES):
            with Image.open(output / name) as image:
                self.assertEqual(image.size, (2, 2))
                self.assertEqual(image.getpixel((0, 0)), (30, 20, i, 255))
        before = (output / 'logo.png').stat().st_mtime_ns
        self.assertEqual(game_assets.extract_theme(self.win64, self.cache), output)
        self.assertEqual((output / 'logo.png').stat().st_mtime_ns, before)
        self.assertTrue(messages)

    def test_cache_cannot_replace_missing_installation(self):
        game_assets.extract_theme(self.win64, self.cache)
        self.ucas.unlink()
        self.assertFalse(game_assets.game_present(self.win64))
        with self.assertRaises(game_assets.AssetExtractionError):
            game_assets.extract_theme(self.win64, self.cache)

    def test_modified_container_rejected_even_with_valid_cache_and_restored_mtime(self):
        game_assets.extract_theme(self.win64, self.cache)
        import os
        stat = self.ucas.stat()
        data = bytearray(self.ucas.read_bytes()); data[0] ^= 1
        self.ucas.write_bytes(data)
        os.utime(self.ucas, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with self.assertRaises(game_assets.AssetExtractionError):
            game_assets.extract_theme(self.win64, self.cache)

    def test_corrupt_cached_png_is_regenerated(self):
        output = game_assets.extract_theme(self.win64, self.cache)
        Image.new('RGBA', (2, 2), 'red').save(output / 'logo.png')
        output = game_assets.extract_theme(self.win64, self.cache)
        with Image.open(output / 'logo.png') as image:
            self.assertEqual(image.getpixel((0, 0)), (30, 20, 0, 255))

    def test_cache_inside_installation_is_rejected(self):
        with self.assertRaises(game_assets.AssetExtractionError):
            game_assets.extract_theme(self.win64, self.project / 'cache')

    def test_rejects_unsupported_malformed_encrypted_and_unsafe_layout(self):
        mutations = [lambda: self.toc.write_bytes(b'bad'),
                     lambda: self.fixture(flags=11), lambda: self.fixture(flags=13),
                     lambda: self.fixture(bad_block=True), lambda: self.fixture(mip_offset=100),
                     lambda: self.layout['assets'][0].update(file='../escape.png'),
                     lambda: self.layout['assets'][0].update(width=1000000),
                     lambda: self.layout.update(container='../escape')]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.fixture(); mutate()
                if self.layout['assets'][0]['file'].startswith('..') or self.layout['assets'][0]['width'] > 10000 or self.layout['container'].startswith('..'):
                    self.layout_file.write_text(json.dumps(self.layout))
                with self.assertRaises(game_assets.AssetExtractionError):
                    game_assets.extract_theme(self.win64, self.cache)

    def test_oodle_decoder_is_bounded_and_checked(self):
        self.fixture(method=1)
        with patch('manager.game_assets._decompress_oodle', side_effect=lambda data, size: data) as decoder:
            output = game_assets.extract_theme(self.win64, self.cache)
            self.assertTrue((output / 'logo.png').is_file())
            self.assertEqual(decoder.call_count, 7)
        self.fixture(method=1)
        with patch('manager.game_assets._decompress_oodle', return_value=b'x'):
            with self.assertRaises(game_assets.AssetExtractionError):
                game_assets.extract_theme(self.win64, self.root / 'cache2')

    def test_failure_leaves_no_partial_theme(self):
        self.fixture(method=1)
        with patch('manager.game_assets._decompress_oodle', side_effect=RuntimeError('unavailable')):
            with self.assertRaises(game_assets.AssetExtractionError):
                game_assets.extract_theme(self.win64, self.cache)
        self.assertFalse(list(self.cache.glob('*/logo.png')) if self.cache.exists() else [])

    def test_cache_directory_symlink_is_rejected(self):
        destination = self.root / 'elsewhere'; destination.mkdir()
        try:
            self.cache.symlink_to(destination, target_is_directory=True)
        except OSError:
            self.skipTest('Windows symlink permission unavailable')
        with self.assertRaises(game_assets.AssetExtractionError):
            game_assets.extract_theme(self.win64, self.cache)

    def test_image_hash_cannot_be_forged_by_editing_cache_manifest(self):
        output = game_assets.extract_theme(self.win64, self.cache)
        Image.new('RGBA', (2, 2), 'red').save(output / 'logo.png')
        manifest_file = output / 'manifest.json'
        manifest = json.loads(manifest_file.read_text())
        manifest['images']['logo.png'] = hashlib.sha256((output / 'logo.png').read_bytes()).hexdigest()
        manifest_file.write_text(json.dumps(manifest))
        game_assets.extract_theme(self.win64, self.cache)
        with Image.open(output / 'logo.png') as image:
            self.assertEqual(image.getpixel((0, 0)), (30, 20, 0, 255))

    def test_missing_executable_invalidates_cached_theme(self):
        game_assets.extract_theme(self.win64, self.cache)
        (self.win64 / 'PUKEY_GODDESS_SHOT_TRICK_Demo-Win64-Shipping.exe').unlink()
        self.assertFalse(game_assets.game_present(self.win64))
        with self.assertRaises(game_assets.AssetExtractionError):
            game_assets.extract_theme(self.win64, self.cache)

    def test_cache_identity_includes_actual_installation_path(self):
        import shutil
        first = game_assets.extract_theme(self.win64, self.cache)
        second_project = self.root / 'second-game' / self.project.name
        shutil.copytree(self.project, second_project)
        second = game_assets.extract_theme(second_project / 'Binaries' / 'Win64', self.cache)
        self.assertNotEqual(first, second)

    def test_existing_oodle_cache_does_not_need_decoder(self):
        self.fixture(method=1)
        with patch('manager.game_assets._decompress_oodle', side_effect=lambda data, size: data):
            output = game_assets.extract_theme(self.win64, self.cache)
        with patch('manager.game_assets._decompress_oodle', side_effect=RuntimeError('no decoder')):
            self.assertEqual(game_assets.extract_theme(self.win64, self.cache), output)

    def test_invalid_compressed_block_is_rejected_before_decoder(self):
        self.fixture(method=1, bad_block=True)
        with patch('manager.game_assets._decompress_oodle', side_effect=AssertionError('unsafe decode attempted')):
            with self.assertRaises(game_assets.AssetExtractionError):
                game_assets.extract_theme(self.win64, self.cache)

    def test_game_change_during_extraction_is_rejected(self):
        def mutate(message):
            if message.startswith('Reading'):
                self.ucas.write_bytes(b'changed')
        with self.assertRaises(game_assets.AssetExtractionError):
            game_assets.extract_theme(self.win64, self.cache, mutate)
        self.assertFalse(list(self.cache.glob('*/logo.png')))

    def test_manifest_symlink_cannot_bypass_validation(self):
        import os
        import subprocess
        if os.name != 'nt':
            self.skipTest('Windows junction test')
        elsewhere = self.root / 'other-cache'; elsewhere.mkdir()
        junction = self.cache
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(elsewhere)], capture_output=True)
        if result.returncode:
            self.skipTest('Windows junction creation unavailable')
        with self.assertRaises(game_assets.AssetExtractionError):
            game_assets.extract_theme(self.win64, junction)

    def test_corrupt_compressed_bytes_are_rejected_before_native_decode(self):
        self.fixture(method=1)
        data = bytearray(self.ucas.read_bytes()); data[0] ^= 1
        self.ucas.write_bytes(data)
        with patch('manager.game_assets._decompress_oodle', side_effect=AssertionError('corrupt native input')):
            with self.assertRaises(game_assets.AssetExtractionError):
                game_assets.extract_theme(self.win64, self.cache)
