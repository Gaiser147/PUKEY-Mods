"""Read a verified set of UI textures from a user's installed demo.

Only metadata is shipped. The small allowlisted IoStore layout deliberately fails
closed for game updates; it is not a general Unreal package/archive extractor.
Neither the installation nor its archives are ever written to.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import tempfile
from typing import Callable

from PIL import Image

_LAYOUT_PATH = Path(__file__).with_name('assets') / 'game-ui-layout.json'
_PROJECT = 'PUKEY_GODDESS_SHOT_TRICK'
_CONTAINER = _PROJECT + '-Windows'
_EXE = _PROJECT + '_Demo-Win64-Shipping.exe'
_NAMES = frozenset(('logo.png', 'dialogue.png', 'sheet.png', 'ribbon.png',
                    'button-pink.png', 'heading.png', 'divider.png'))
_MAGIC = b'-==--==--==--==-'
_MAX_TOC = 16 * 1024 * 1024
_MAX_CHUNK = 16 * 1024 * 1024
_MAX_PIXELS = 16 * 1024 * 1024
_CACHE_VERSION = 1


class AssetExtractionError(RuntimeError):
    """The local game cannot safely supply the requested theme."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _no_links(path: Path) -> None:
    """Refuse symlinks and Windows junctions/reparse points, including parents."""
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise AssetExtractionError('Linked installation/cache paths are unsupported.')


def _installation(win64: Path) -> tuple[Path, Path, Path, Path]:
    win64 = Path(os.path.abspath(win64))
    _no_links(win64)
    if win64.name.lower() != 'win64' or win64.parent.name.lower() != 'binaries' or win64.parent.parent.name != _PROJECT:
        raise AssetExtractionError('Select the installed game Binaries/Win64 folder.')
    project = win64.parent.parent
    exe = win64 / _EXE
    paks = project / 'Content' / 'Paks'
    toc, ucas = paks / (_CONTAINER + '.utoc'), paks / (_CONTAINER + '.ucas')
    for path in (exe, toc, ucas):
        _no_links(path)
        if not path.is_file() or path.stat().st_size <= 0:
            raise AssetExtractionError('The installed demo and paired game archives are required.')
    with exe.open('rb') as source:
        if source.read(2) != b'MZ':
            raise AssetExtractionError('The installed game executable is invalid.')
    return project.resolve(), exe.resolve(), toc.resolve(), ucas.resolve()


def game_present(win64: Path) -> bool:
    """Conservatively check the installation, regardless of any existing cache."""
    try:
        _installation(win64)
        return True
    except (OSError, ValueError, AssetExtractionError):
        return False


def _layout() -> dict:
    if _LAYOUT_PATH.stat().st_size > 64 * 1024:
        raise AssetExtractionError('Theme layout metadata exceeds its size limit.')
    layout = json.loads(_LAYOUT_PATH.read_text(encoding='utf-8'))
    if layout.get('schema') != 1 or layout.get('container') != _CONTAINER:
        raise AssetExtractionError('Unsupported theme layout metadata.')
    assets = layout['assets']
    if len(assets) != len(_NAMES) or {a['file'] for a in assets} != _NAMES:
        raise AssetExtractionError('Theme layout must contain exactly seven known images.')
    for asset in assets:
        w, h = asset['width'], asset['height']
        if not isinstance(w, int) or not isinstance(h, int) or not 0 < w <= 8192 or not 0 < h <= 8192 or w*h > _MAX_PIXELS:
            raise AssetExtractionError('Theme image dimensions exceed supported limits.')
        fmt = asset['format']
        expected = w*h*4 if fmt == 'BGRA' else ((w+3)//4)*((h+3)//4)*16
        if fmt not in ('BGRA', 'BC3', 'BC7') or asset['mip_size'] != expected:
            raise AssetExtractionError('Unsupported theme texture format or size.')
        if not 0 < asset['length'] <= _MAX_CHUNK or asset['mip_offset'] < 0 or asset['mip_offset'] + expected > asset['length']:
            raise AssetExtractionError('Theme mip is outside its package chunk.')
        for field in ('chunk_sha256', 'rgba_sha256'):
            if len(bytes.fromhex(asset[field])) != 32:
                raise AssetExtractionError('Invalid texture hash metadata.')
    return layout


def _read_exact(source, offset: int, size: int) -> bytes:
    source.seek(offset)
    data = source.read(size)
    if len(data) != size:
        raise AssetExtractionError('Truncated game archive.')
    return data


def _index(data: bytes, layout: dict, ucas_size: int) -> tuple[int, dict[int, tuple[int, int, int, int]]]:
    if len(data) < 144 or data[:16] != _MAGIC or data[16] != 8:
        raise AssetExtractionError('Unsupported or malformed IoStore header.')
    hs, entries, count, entry_size, methods, name_size, block_size, directory_size, partitions = struct.unpack_from('<9I', data, 20)
    flags = data[80]
    if hs != 144 or entry_size != 12 or partitions != 1 or flags & ~9 or not flags & 8:
        raise AssetExtractionError('Encrypted, signed, partitioned or unsupported archives cannot supply UI assets.')
    if not 0 < entries <= 100000 or not 0 < count <= 200000 or methods > 1 or name_size != 32 or not 0 < block_size <= 65536:
        raise AssetExtractionError('IoStore table limits exceeded.')
    seed_count = struct.unpack_from('<I', data, 84)[0]
    overflow_count = struct.unpack_from('<I', data, 96)[0]
    table = hs + entries*22 + seed_count*4 + overflow_count*4
    method_start = table + count*12
    index_start = method_start + methods*name_size
    if index_start + directory_size > len(data) or table < hs or index_start > len(data):
        raise AssetExtractionError('Truncated IoStore tables.')
    if methods and data[method_start:method_start+32].rstrip(b'\0') != b'Oodle':
        raise AssetExtractionError('Unsupported archive compression method.')
    selected = {}
    for asset in layout['assets']:
        n, offset, length = asset['index'], asset['offset'], asset['length']
        if not 0 <= n < entries or offset < 0 or offset+length > count*block_size:
            raise AssetExtractionError('Invalid theme chunk bounds.')
        if data[hs+n*12:hs+(n+1)*12].hex() != asset['chunk_id']:
            raise AssetExtractionError('Theme package chunk ID changed.')
        stored = data[hs+entries*12+n*10:hs+entries*12+(n+1)*10]
        if int.from_bytes(stored[:5], 'big') != offset or int.from_bytes(stored[5:], 'big') != length:
            raise AssetExtractionError('Theme package chunk layout changed.')
        for bn in range(offset//block_size, (offset+length-1)//block_size+1):
            b = data[table+bn*12:table+(bn+1)*12]
            co, cl, ul, method = int.from_bytes(b[:5], 'little'), int.from_bytes(b[5:8], 'little'), int.from_bytes(b[8:11], 'little'), b[11]
            if not 0 < cl <= 2*65536 or not 0 < ul <= block_size or co+cl > ucas_size or method > methods or (method == 0 and cl != ul):
                raise AssetExtractionError('Invalid compressed block bounds or method.')
            # A selected chunk may not address padding beyond a short final block.
            required_end = min(offset+length, (bn+1)*block_size) - bn*block_size
            if required_end > ul:
                raise AssetExtractionError('Theme chunk exceeds its compression block.')
            selected[bn] = (co, cl, ul, method)
    return block_size, selected


def _decompress_oodle(data: bytes, expected_size: int) -> bytes:
    from .native_decoder import decompress_oodle
    return decompress_oodle(data, expected_size)


def _texture(raw: bytes, asset: dict) -> Image.Image:
    if _sha(raw) != asset['chunk_sha256']:
        raise AssetExtractionError('Game texture package verification failed.')
    w, h = asset['width'], asset['height']
    pix = raw[asset['mip_offset']:asset['mip_offset']+asset['mip_size']]
    fmt = asset['format']
    if fmt == 'BGRA':
        image = Image.frombytes('RGBA', (w, h), pix, 'raw', 'BGRA')
    else:
        header = bytearray(128)
        header[:4] = b'DDS '
        struct.pack_into('<7I', header, 4, 124, 0x81007, h, w, len(pix), 0, 1)
        code = b'DX10' if fmt == 'BC7' else b'DXT5'
        struct.pack_into('<8I', header, 76, 32, 4, int.from_bytes(code, 'little'), 0, 0, 0, 0, 0)
        struct.pack_into('<I', header, 108, 0x1000)
        if fmt == 'BC7':
            header.extend(struct.pack('<5I', 98, 3, 0, 1, 0))
        with Image.open(io.BytesIO(header + pix)) as dds:
            image = dds.convert('RGBA')
    if _sha(image.tobytes()) != asset['rgba_sha256']:
        raise AssetExtractionError('Decoded game image verification failed.')
    return image


def _valid_cache(folder: Path, layout: dict, identity: str) -> bool:
    if not folder.exists():
        return False
    _no_links(folder)
    if not folder.is_dir():
        raise AssetExtractionError('Theme cache path is not a directory.')
    try:
        if {p.name for p in folder.iterdir()} != _NAMES | {'manifest.json'}:
            raise AssetExtractionError('Unexpected files in the private theme cache.')
        manifest_path = folder / 'manifest.json'
        _no_links(manifest_path)
        if manifest_path.stat().st_size > 16384:
            return False
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('identity') != identity or manifest.get('version') != _CACHE_VERSION:
            return False
        for asset in layout['assets']:
            path = folder / asset['file']
            _no_links(path)
            if not 0 < path.stat().st_size <= _MAX_PIXELS*4:
                return False
            payload = path.read_bytes()
            if _sha(payload) != manifest['images'][asset['file']]:
                return False
            with Image.open(io.BytesIO(payload)) as image:
                if image.format != 'PNG' or image.size != (asset['width'], asset['height']) or _sha(image.convert('RGBA').tobytes()) != asset['rgba_sha256']:
                    return False
        return True
    except (OSError, ValueError, KeyError, Image.DecompressionBombError):
        return False


def _stat_identity(path: Path) -> list:
    s = path.stat()
    return [str(path), s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def extract_theme(win64: Path, cache_root: Path, progress: Callable[[str], None] = lambda message: None) -> Path:
    """Return a complete, verified local theme cache or raise AssetExtractionError.

    Actual archive presence, supported TOC identity, relevant compressed bytes and
    cached image pixels are checked on every call, including cache hits.
    """
    temporary = None
    try:
        project, exe, toc, ucas = _installation(win64)
        cache = Path(os.path.abspath(cache_root))
        _no_links(cache)
        # The project root and its Steam installation parent are read-only.
        if cache.resolve().is_relative_to(project.parent):
            raise AssetExtractionError('The image cache must be outside the game installation.')
        layout = _layout()
        if not 144 <= toc.stat().st_size <= _MAX_TOC or ucas.stat().st_size != layout['ucas_size']:
            raise AssetExtractionError('Unsupported game container size; theme layout needs an update.')
        data = toc.read_bytes()
        if _sha(data) != layout['toc_sha256']:
            raise AssetExtractionError('Unsupported game version; theme layout needs an update.')
        initial = [_stat_identity(p) for p in (exe, toc, ucas)]
        block_size, blocks = _index(data, layout, ucas.stat().st_size)
        progress('Checking installed game UI textures…')
        if set(layout['block_sha256']) != {str(n) for n in blocks}:
            raise AssetExtractionError('Theme compression-block metadata changed.')
        if sum(b[1] for b in blocks.values()) > 32*1024*1024 or sum(b[2] for b in blocks.values()) > 64*1024*1024:
            raise AssetExtractionError('Theme extraction exceeds its memory budget.')
        packed = {}
        with ucas.open('rb') as source:
            for bn, (offset, size, _, _) in sorted(blocks.items()):
                packed[bn] = _read_exact(source, offset, size)
                if _sha(packed[bn]) != layout['block_sha256'][str(bn)]:
                    raise AssetExtractionError('Game compression block verification failed.')
        fingerprint = {'version': _CACHE_VERSION, 'installation': initial, 'toc': _sha(data),
                       'layout': _sha(json.dumps(layout, sort_keys=True).encode()),
                       'blocks': [(n, _sha(b)) for n, b in sorted(packed.items())]}
        identity = _sha(json.dumps(fingerprint, sort_keys=True).encode())
        folder = cache / identity
        if _valid_cache(folder, layout, identity):
            if initial != [_stat_identity(p) for p in (exe, toc, ucas)]:
                raise AssetExtractionError('Game installation changed while checking its theme.')
            return folder
        progress('Reading UI images from the installed game…')
        unpacked = {}
        for bn, (_, _, expected, method) in blocks.items():
            raw = _decompress_oodle(packed[bn], expected) if method else packed[bn]
            if len(raw) != expected:
                raise AssetExtractionError('Archive decompressor returned an invalid block size.')
            unpacked[bn] = raw
        cache.mkdir(parents=True, exist_ok=True)
        _no_links(cache)
        temporary = Path(tempfile.mkdtemp(prefix='.extract-', dir=cache))
        hashes = {}
        for asset in layout['assets']:
            offset, length = asset['offset'], asset['length']
            joined = b''.join(unpacked[n] for n in range(offset//block_size, (offset+length-1)//block_size+1))
            raw = joined[offset % block_size:offset % block_size+length]
            image = _texture(raw, asset)
            target = temporary / asset['file']
            image.save(target, format='PNG')
            hashes[asset['file']] = _sha(target.read_bytes())
        (temporary / 'manifest.json').write_text(json.dumps({'version': _CACHE_VERSION, 'identity': identity, 'images': hashes}), encoding='utf-8')
        if initial != [_stat_identity(p) for p in (exe, toc, ucas)]:
            raise AssetExtractionError('Game installation changed during theme extraction.')
        _no_links(folder)
        if folder.exists():
            if _valid_cache(folder, layout, identity):
                return folder
            # Only this known cache directory can be replaced; never follow links.
            stale = cache / ('.stale-' + temporary.name.removeprefix('.extract-'))
            folder.rename(stale)
            temporary.rename(folder)
            temporary = None
            _no_links(stale)
            if not stale.resolve().is_relative_to(cache.resolve()):
                raise AssetExtractionError('Unsafe stale cache path.')
            shutil.rmtree(stale)
        else:
            try:
                temporary.rename(folder)
                temporary = None
            except FileExistsError:
                if not _valid_cache(folder, layout, identity):
                    raise AssetExtractionError('Another extraction produced an invalid cache.')
        return folder
    except AssetExtractionError:
        raise
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error, RuntimeError, ImportError) as exc:
        raise AssetExtractionError(f'Installed game UI extraction unavailable: {exc}') from exc
    finally:
        if temporary is not None:
            _no_links(temporary)
            shutil.rmtree(temporary)
