"""Bounded Oodle decoding using only our packaged, open-source helper.

No game DLL, system library search, network download, or external program is
used. Source launches can build the helper with tools/build_ui_decoder.py.
"""
import ctypes
from functools import lru_cache
from pathlib import Path
import sys


MAX_INPUT_SIZE = 64 * 1024 * 1024
MAX_OUTPUT_SIZE = 64 * 1024 * 1024


class NativeDecoderError(ValueError):
    """The compressed block could not be decoded safely."""


class NativeDecoderUnavailable(RuntimeError):
    """The package does not contain a usable native decoder."""


def _library_path() -> Path:
    names = {'win32': 'pukey_ui_decoder.dll', 'linux': 'libpukey_ui_decoder.so'}
    if sys.platform not in names:
        raise NativeDecoderUnavailable('The UI decoder supports Windows and Linux only.')
    return Path(__file__).resolve().parent / 'assets' / 'native' / names[sys.platform]


@lru_cache(maxsize=1)
def _load_library():
    path = _library_path()
    if not path.is_file():
        raise NativeDecoderUnavailable(
            'The packaged UI decoder is missing. Source builds: run python tools/build_ui_decoder.py.')
    try:
        # Windows resolves dependencies only beside the helper or in System32.
        options = {'winmode': 0x00000100 | 0x00000800} if sys.platform == 'win32' else {}
        library = ctypes.CDLL(str(path), **options)
        library.pukey_ui_decoder_abi.argtypes = []
        library.pukey_ui_decoder_abi.restype = ctypes.c_uint32
        if library.pukey_ui_decoder_abi() != 1:
            raise NativeDecoderUnavailable('The packaged UI decoder has an incompatible ABI.')
        library.pukey_ui_decompress.argtypes = [
            ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_ubyte), ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        library.pukey_ui_decompress.restype = ctypes.c_int32
        return library
    except (OSError, AttributeError) as error:
        raise NativeDecoderUnavailable('The packaged UI decoder could not be loaded.') from error


def decompress_oodle(data: bytes, expected_size: int) -> bytes:
    """Decode one Oodle block into exactly expected_size bytes (at most 64 MiB)."""
    if not isinstance(data, bytes):
        raise TypeError('Oodle input must be bytes.')
    if type(expected_size) is not int:
        raise TypeError('The expected decoded size must be an integer.')
    if not 0 < len(data) <= MAX_INPUT_SIZE:
        raise ValueError('Oodle input must contain between 1 byte and 64 MiB.')
    if not 0 < expected_size <= MAX_OUTPUT_SIZE:
        raise ValueError('The expected decoded size must be between 1 byte and 64 MiB.')
    library = _load_library()
    source = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    output = (ctypes.c_ubyte * expected_size)()
    written = ctypes.c_size_t()
    status = library.pukey_ui_decompress(source, len(data), output, expected_size,
                                        ctypes.byref(written))
    if status != 0 or written.value != expected_size:
        raise NativeDecoderError(f'Oodle block decoding failed (status {status}).')
    return bytes(output)
