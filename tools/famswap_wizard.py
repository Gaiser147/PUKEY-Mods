"""FamSwap Wizard - replaces Fam (the opponent) with your own image, step by step.

Start:  double-click FamSwap-Wizard.bat
   or   py famswap_wizard.py

Supported formats: PNG, WebP, JPEG, BMP, GIF, TIFF (decoded by the Windows imaging library).
Works best with a character on a transparent background OR on a green screen (it gets removed).
Requires Windows and Python 3 (the "py" launcher from python.org).
"""
import os
import re
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
COMPOSE = os.path.join(TOOLS, "image_compose.ps1")
APP_ID = "5253020"
MOD_SUBDIR = os.path.join("PUKEY_GODDESS_SHOT_TRICK", "Binaries", "Win64", "ue4ss", "Mods", "FamSwap")

TARGETS = {
    "bar": {
        "title": "Fam behind the bar counter (before the match)",
        "file": "bar.png",
        "width": 1110, "height": 2156,          # same aspect ratio as the original texture (2220x4312)
        "background": "transparent",
        "scale": 100.0, "top": 0.0,
        "note": "The character is placed top-center; the counter hides the legs.",
    },
    "game": {
        "title": "Fam at the table (drinking game; replaces her videos with a still image)",
        "file": "game.png",
        "width": 1920, "height": 1080,
        "background": "green",
        "scale": 130.0, "top": 4.0,
        "note": "The green background is keyed out in-game. The table hides the lower body.",
    },
}

# Green-screen tolerance: (KeyLow, KeyHigh) on the green excess G - max(R, B):
# above KeyLow a pixel becomes partly transparent, above KeyHigh fully transparent.
TOLERANCES = {
    "1": ("weak (only strong green, keeps green clothing)", 70, 150),
    "2": ("normal", 40, 110),
    "3": ("strong (also removes greenish fringes)", 20, 70),
}


def line():
    print("-" * 72)


def ask(text, default=None):
    suffix = f" [{default}]" if default not in (None, "") else ""
    try:
        answer = input(f"{text}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        sys.exit(0)
    return answer if answer else ("" if default is None else str(default))


def yes_no(text, default=True):
    hint = "Y/n" if default else "y/N"
    while True:
        a = ask(f"{text} ({hint})", "").lower()
        if a == "":
            return default
        if a in ("y", "yes", "j", "ja"):
            return True
        if a in ("n", "no", "nein"):
            return False
        print("  Please enter y or n.")


def number(text, default):
    while True:
        a = ask(text, f"{default:g}").replace(",", ".")
        try:
            return float(a)
        except ValueError:
            print("  Please enter a number (e.g. 100 or 92.5).")


def clean_path(p):
    p = p.strip().strip('"').strip("'").strip()
    if p.startswith("& "):          # PowerShell sometimes prepends "& '...'" when a file is dropped in
        p = p[2:].strip().strip("'").strip('"')
    return os.path.expandvars(os.path.expanduser(p))


def run_compose(args):
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", COMPOSE] + args
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def parse_values(text):
    """Turns 'X a=1 b=2,5' into a dict (decimal comma becomes a dot)."""
    values = {}
    for part in text.strip().split():
        if "=" in part:
            k, v = part.split("=", 1)
            values[k] = v.replace(",", ".")
    return values


# ---------------------------------------------------------------------------
# Locating the game via Steam
# ---------------------------------------------------------------------------
def steam_libraries():
    roots = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for name in ("SteamPath", "InstallPath"):
                        try:
                            roots.append(winreg.QueryValueEx(k, name)[0])
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    roots.append(r"C:\Program Files (x86)\Steam")
    libs = []
    for root in roots:
        root = os.path.normpath(root)
        if root not in libs and os.path.isdir(root):
            libs.append(root)
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            for m in re.finditer(r'"path"\s+"([^"]+)"', open(vdf, encoding="utf-8", errors="replace").read()):
                p = os.path.normpath(m.group(1).replace("\\\\", "\\"))
                if p not in libs:
                    libs.append(p)
    return libs


def find_game_dir():
    for lib in steam_libraries():
        acf = os.path.join(lib, "steamapps", f"appmanifest_{APP_ID}.acf")
        if os.path.isfile(acf):
            m = re.search(r'"installdir"\s+"([^"]+)"', open(acf, encoding="utf-8", errors="replace").read())
            if m:
                game = os.path.join(lib, "steamapps", "common", m.group(1))
                if os.path.isdir(game):
                    return game
    return None


def find_mod_dir():
    print("Step 1: Locate the FamSwap mod folder")
    candidates = []
    if os.environ.get("FAMSWAP_MODDIR"):            # for testing
        candidates.append(os.environ["FAMSWAP_MODDIR"])
    game = find_game_dir()
    if game:
        candidates.append(os.path.join(game, MOD_SUBDIR))
    for folder in candidates:
        if os.path.isfile(os.path.join(folder, "Scripts", "main.lua")):
            print(f"  Found: {folder}")
            return folder
    if game:
        print(f"  Game found at {game}, but the FamSwap mod is not installed there.")
        print("  Run Install.bat first (it installs the mod).")
    else:
        print("  Could not find the game automatically.")
    while True:
        folder = clean_path(ask("  Path to the folder ...\\ue4ss\\Mods\\FamSwap (q = quit)"))
        if folder.lower() == "q":
            sys.exit(0)
        if os.path.isfile(os.path.join(folder, "Scripts", "main.lua")):
            return folder
        print(f"  Not a FamSwap mod folder: {folder}")


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------
def choose_target():
    line()
    print("Step 2: What do you want to replace?")
    print("  1 = both: bar counter AND table (recommended)")
    print("  2 = only " + TARGETS["bar"]["title"])
    print("  3 = only " + TARGETS["game"]["title"])
    print("  4 = remove replacement (restore the original Fam)")
    while True:
        a = ask("Choice", "1")
        if a in ("1", "2", "3", "4"):
            return {"1": ["bar", "game"], "2": ["bar"], "3": ["game"], "4": "remove"}[a]
        print("  Please enter 1, 2, 3 or 4.")


def choose_image(previous=None):
    line()
    print("Step 3: Which image do you want to use?")
    print("  Tip: drag the file from Explorer into this window, then press Enter.")
    print("  Works best with a transparent background or a green screen (it gets removed).")
    while True:
        p = clean_path(ask("  Image path", previous or ""))
        if os.path.isfile(p):
            return p
        print(f"  File not found: {p}")


def analyze_image(source):
    """Returns (usable, remove_green)."""
    r = run_compose(["-Src", source, "-Analyze"])
    if r.returncode != 0 or "ANALYSIS" not in r.stdout:
        print("  ERROR: the image could not be read.")
        print("  " + (r.stderr or r.stdout).strip().replace("\n", "\n  "))
        return False, False
    v = parse_values(r.stdout)
    transparent = float(v.get("transparent_pct", "0"))
    green = int(v.get("green_edges", "0/7").split("/")[0])
    print(f"  Image: {v.get('source', '?')} px, format: {v.get('decoder', '?').replace('_', ' ')}, "
          f"transparent: {transparent:.0f} %")
    if transparent < 5 and green >= 4:
        print("  -> Green-screen background detected.")
        return True, yes_no("  Remove the green background?", True)
    if transparent < 1:
        print("  -> Warning: the image has neither a transparent background nor a detectable green screen.")
        print("     The background would show up in-game as a rectangle.")
        if yes_no("  Try to remove green areas anyway?", False):
            return True, True
        return yes_no("  Use the image as it is?", False), False
    print("  -> Transparent background, good.")
    return True, False


def render(source, out_file, t, scale, top, shift_x, remove_green, tolerance):
    args = ["-Src", source, "-Dst", out_file,
            "-Width", str(t["width"]), "-Height", str(t["height"]),
            "-Background", t["background"],
            "-ScalePercent", f"{scale:g}", "-OffsetTopPercent", f"{top:g}",
            "-OffsetXPercent", f"{shift_x:g}"]
    if remove_green:
        _, lo, hi = TOLERANCES[tolerance]
        args += ["-RemoveGreen", "-KeyLow", str(lo), "-KeyHigh", str(hi)]
    r = run_compose(args)
    if r.returncode != 0 or "OK" not in r.stdout:
        print("  ERROR while converting the image:")
        print("  " + (r.stderr or r.stdout).strip().replace("\n", "\n  "))
        return False
    return True


def process_target(name, mod_dir, source, remove_green):
    t = TARGETS[name]
    line()
    print(f"Replacing: {t['title']}")
    print(f"  {t['note']}")
    out_file = os.path.join(mod_dir, t["file"])
    if os.path.isfile(out_file):
        backup = os.path.join(mod_dir, t["file"].replace(".png", "_previous.png"))
        shutil.copy2(out_file, backup)
        print(f"  Existing {t['file']} backed up as {os.path.basename(backup)}")

    scale, top, shift_x, tolerance = t["scale"], t["top"], 0.0, "2"
    while True:
        info = f"size {scale:g} %, top offset {top:g} %, horizontal shift {shift_x:g} %"
        if remove_green:
            info += f", green-screen tolerance {TOLERANCES[tolerance][0].split(' ')[0]}"
        print(f"\n  Creating {t['file']} ({info}) ...")
        if not render(source, out_file, t, scale, top, shift_x, remove_green, tolerance):
            if yes_no("  Choose a different image?", True):
                source = choose_image(source)
                _, remove_green = analyze_image(source)
                continue
            return source, remove_green
        print(f"  Saved: {out_file}")
        print("  -> If the game is running, press F9 there to reload the images. Otherwise they load on start.")
        if yes_no("  Open a preview of the result?", True):
            try:
                os.startfile(out_file)
            except OSError as e:
                print(f"  Could not open the preview: {e}")

        print("\n  Does it look right?")
        print("    Enter = yes, continue")
        print("    s = size   t = top offset   h = horizontal shift   i = different image")
        print("    g = green-screen tolerance   r = reset to defaults")
        a = ask("  Choice", "").lower()
        if a == "":
            return source, remove_green
        if a == "s":
            print("    100 = character fits exactly, larger = bigger character (edges get cut off)")
            scale = number("    New size in %", scale)
        elif a == "t":
            print("    Percent of the image height between the top edge and the head; negative = higher")
            top = number("    New top offset in %", top)
        elif a == "h":
            print("    Percent of the image width; negative = left, positive = right")
            shift_x = number("    Horizontal shift in %", shift_x)
        elif a == "i":
            source = choose_image(source)
            _, remove_green = analyze_image(source)
        elif a == "g":
            if not remove_green:
                remove_green = yes_no("    Green-screen removal is off. Turn it on?", True)
            if remove_green:
                for k, (txt, _, _) in TOLERANCES.items():
                    print(f"    {k} = {txt}")
                tolerance = ask("    Tolerance", tolerance)
                if tolerance not in TOLERANCES:
                    tolerance = "2"
        elif a == "r":
            scale, top, shift_x, tolerance = t["scale"], t["top"], 0.0, "2"


def remove_replacements(mod_dir):
    line()
    for t in TARGETS.values():
        p = os.path.join(mod_dir, t["file"])
        if os.path.isfile(p):
            if yes_no(f"  Delete {t['file']} ({t['title']})?", True):
                os.remove(p)
                print(f"  {t['file']} deleted.")
        else:
            print(f"  {t['file']}: not present (original is active)")
    print("  -> Press F9 in the game or restart it.")


def main():
    os.system("")   # enables ANSI/Unicode handling in the Windows console
    line()
    print(" FamSwap Wizard - replace Fam (the opponent) with your own image")
    line()
    if not os.path.isfile(COMPOSE):
        sys.exit(f"Helper script missing: {COMPOSE}")
    mod_dir = find_mod_dir()
    while True:
        choice = choose_target()
        if choice == "remove":
            remove_replacements(mod_dir)
        else:
            source = choose_image()
            usable, remove_green = analyze_image(source)
            while not usable:
                source = choose_image(source)
                usable, remove_green = analyze_image(source)
            for name in choice:
                source, remove_green = process_target(name, mod_dir, source, remove_green)
        line()
        print("In-game: F8 = toggle between your image and the original, F9 = reload images.")
        if not yes_no("Replace or change something else?", False):
            break
    print("Done. Have fun!")


if __name__ == "__main__":
    main()
