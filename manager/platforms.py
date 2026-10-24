"""Steam discovery and conservative runtime guards for Windows and Linux/Proton."""
import os
from pathlib import Path
import re
import sys

WIN64_PART = "PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64"
APP_ID = "5253020"


def game_directory(path):
    path = Path(path).expanduser().absolute()
    candidates = [path, path.parent, path.parent.parent.parent]
    for root in candidates:
        win64 = root / WIN64_PART
        if win64.is_dir() and any(p.is_file() and p.name.lower().endswith("-shipping.exe")
                                  and p.name.lower().startswith("pukey_goddess_shot_trick") for p in win64.iterdir()):
            return root.resolve()
    raise ValueError("Select the game root, PUKEY_GODDESS_SHOT_TRICK folder, or Win64 folder containing the Shipping executable.")


def games_from_steam_roots(roots):
    libraries = []
    for root in roots:
        root = Path(root).expanduser()
        if root not in libraries: libraries.append(root)
        vdf = root / "steamapps/libraryfolders.vdf"
        try: text = vdf.read_text(encoding="utf-8")
        except (OSError, UnicodeError): continue
        for match in re.finditer(r'"(?:path|\d+)"\s+"([^"\r\n]+)"', text):
            path = Path(match.group(1).replace("\\\\", "\\"))
            if path not in libraries: libraries.append(path)
    found = []
    for library in libraries:
        manifest = library / ("steamapps/appmanifest_%s.acf" % APP_ID)
        try: text = manifest.read_text(encoding="utf-8")
        except (OSError, UnicodeError): continue
        match = re.search(r'"installdir"\s+"([^"\r\n]+)"', text)
        if not match: continue
        name = match.group(1)
        if "/" in name or "\\" in name or name in (".", "..") or ":" in name: continue
        try: game = game_directory(library / "steamapps/common" / name)
        except (OSError, ValueError): continue
        if game not in found: found.append(game)
    return found


def find_games():
    roots = []
    if sys.platform == "win32":
        import winreg
        for hive, key in [(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")]:
            try:
                with winreg.OpenKey(hive, key) as handle:
                    for value in ("SteamPath", "InstallPath"):
                        try: roots.append(Path(winreg.QueryValueEx(handle, value)[0]))
                        except OSError: pass
            except OSError: pass
        roots.append(Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam")
    else:
        home = Path.home()
        roots.extend([home / ".steam/steam", home / ".local/share/Steam",
                      home / ".var/app/com.valvesoftware.Steam/.local/share/Steam"])
    return games_from_steam_roots(roots)


def game_running():
    try:
        import psutil
    except ImportError:
        return True
    try:
        for process in psutil.process_iter(["name"]):
            try:
                name = (process.info.get("name") or "").lower()
                if name.startswith("pukey_goddess_shot_trick") or name.startswith("pukey_goddess_"): return True
            except psutil.NoSuchProcess: continue
            except (psutil.AccessDenied, psutil.Error): return True
        return False
    except (psutil.Error, OSError, RuntimeError):
        # No reliable process inventory means writes must stay blocked.
        return True
