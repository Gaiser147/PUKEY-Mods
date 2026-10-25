"""Read-only, bounded log discovery and tailing; no handles survive a poll."""
import codecs
from dataclasses import dataclass
import os
from pathlib import Path
import sys

INITIAL_READ_BYTES = 512 * 1024
POLL_READ_BYTES = 128 * 1024
GAME_NAME = 'PUKEY_GODDESS_SHOT_TRICK'


@dataclass(frozen=True)
class ReadResult:
    text: str = ''
    reset: bool = False
    missing: bool = False
    error: str = ''
    bytes_read: int = 0


class TailReader:
    """One stream cursor. Call poll serially from a worker, at most once/second.

    Results contain only newly decoded text. ``reset`` tells a consumer to discard
    its previous display after initial loading, truncation, or replacement. Missing
    files are normal and are retried on the next poll. Reads never create a file.
    """
    def __init__(self, path: Path):
        self.path = Path(path)
        self._identity = None
        self._position = 0
        self._decoder = None
        self._prefix = b''
        self._modified = None

    def poll(self) -> ReadResult:
        initial = self._identity is None
        limit = INITIAL_READ_BYTES if initial else POLL_READ_BYTES
        try:
            with self.path.open('rb') as stream:
                stat = os.fstat(stream.fileno())
                identity = (stat.st_dev, stat.st_ino)
                prefix = stream.read(min(64, limit))
                count = len(prefix)
                # A prefix also catches truncate-and-regrow between polls.
                reset = (initial or self._position == 0 or identity != self._identity or stat.st_size < self._position
                         or prefix[:len(self._prefix)] != self._prefix
                         or (stat.st_size == self._position and stat.st_mtime_ns != self._modified))
                if reset:
                    # Unreal also emits UTF-16LE without a BOM. ASCII-rich log
                    # headers have alternating NUL bytes in that encoding.
                    utf16le = (len(prefix) >= 4 and prefix[1::2].count(0) >= len(prefix[1::2]) * .6
                               and prefix[::2].count(0) < len(prefix[::2]) * .2)
                    encoding = ('utf-16-le' if prefix.startswith(codecs.BOM_UTF16_LE) or utf16le else
                                'utf-16-be' if prefix.startswith(codecs.BOM_UTF16_BE) else 'utf-8')
                    self._decoder = codecs.getincrementaldecoder(encoding)(errors='replace')
                    start = max(0, stat.st_size - (limit - count))
                    if encoding.startswith('utf-16'):
                        start += start % 2
                    self._position = start
                stream.seek(self._position)
                raw = stream.read(limit - count)
                self._position += len(raw)
                count += len(raw)
                if reset and start:
                    if encoding == 'utf-8':
                        # A tail can start in the middle of a valid character.
                        while raw and raw[0] & 0xC0 == 0x80:
                            raw = raw[1:]
                    elif len(raw) >= 2:
                        order = 'little' if encoding.endswith('le') else 'big'
                        if 0xDC00 <= int.from_bytes(raw[:2], order) <= 0xDFFF:
                            raw = raw[2:]
                text = self._decoder.decode(raw, final=False)
                if reset:
                    text = text.lstrip('\ufeff')
                self._identity = identity
                self._prefix = prefix
                self._modified = stat.st_mtime_ns
                return ReadResult(text=text, reset=reset, bytes_read=count)
        except FileNotFoundError:
            reset = self._identity is not None
            self._identity = None
            self._decoder = None
            self._position = 0
            self._prefix = b''
            return ReadResult(reset=reset, missing=True)
        except OSError as error:
            return ReadResult(error=str(error))


@dataclass(frozen=True)
class LogSource:
    kind: str
    label: str
    path: Path


def discover_log_sources(game_root: Path | None) -> list[LogSource]:
    """Inspect only the selected installation, its Steam prefix, and local app data."""
    sources = []
    seen = set()

    def add(kind, label, path):
        path = Path(path)
        if path not in seen:
            seen.add(path)
            sources.append(LogSource(kind, label, path))

    def logs_in(directory, label):
        add('Game', label + ' (waiting if missing)', directory / (GAME_NAME + '.log'))
        try:
            logs = sorted((p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == '.log'),
                          key=lambda p: p.stat().st_mtime_ns, reverse=True)
        except OSError:
            return
        for path in logs:
            add('Game', label + ': ' + path.name, path)

    if game_root is not None:
        selected = Path(game_root)
        if selected.name.lower() == 'win64':
            win64 = selected
            project = selected.parent.parent
            root = project.parent
        elif selected.name.upper() == GAME_NAME:
            project = selected
            root = project.parent
            win64 = project / 'Binaries/Win64'
        else:
            root = selected
            project = root / GAME_NAME
            win64 = project / 'Binaries/Win64'
        add('UE4SS', 'UE4SS / ue4ss', win64 / 'ue4ss/UE4SS.log')
        add('UE4SS', 'UE4SS / legacy Win64', win64 / 'UE4SS.log')
        logs_in(project / 'Saved/Logs', 'Game installation')
        # The selected Steam library is the only Proton prefix searched.
        steamapps = next((p for p in (root, *root.parents) if p.name.lower() == 'steamapps'), None)
        if steamapps is not None:
            users = steamapps / 'compatdata/5253020/pfx/drive_c/users'
            logs_in(users / 'steamuser/AppData/Local' / GAME_NAME / 'Saved/Logs', 'Proton steamuser')
            try:
                homes = sorted(p for p in users.iterdir() if p.is_dir() and p.name != 'steamuser')
            except OSError:
                homes = []
            for home in homes:
                logs_in(home / 'AppData/Local' / GAME_NAME / 'Saved/Logs', 'Proton ' + home.name)
    if sys.platform == 'win32' and os.environ.get('LOCALAPPDATA'):
        logs_in(Path(os.environ['LOCALAPPDATA']) / GAME_NAME / 'Saved/Logs', 'Local app data')
    def missing(source):
        try:
            return not source.path.is_file()
        except OSError:
            return True
    return sorted(sources, key=missing)
