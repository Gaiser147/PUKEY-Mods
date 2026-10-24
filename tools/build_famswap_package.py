"""Builds the distributable FamSwap package: dist/FamSwap-<version>/ and dist/FamSwap-<version>.zip

Usage: py build_famswap_package.py [version]
"""
import os
import shutil
import sys

VERSION = sys.argv[1] if len(sys.argv) > 1 else "1.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # PUKEY-Mods
NAME = f"FamSwap-{VERSION}"
OUT = os.path.join(ROOT, "dist", NAME)

FILES = [
    # (source relative to PUKEY-Mods, target relative to the package)
    ("dist-src/README.md", "README.md"),
    ("dist-src/Install.bat", "Install.bat"),
    ("dist-src/install.ps1", "install.ps1"),
    ("dist-src/FamSwap-Wizard.bat", "FamSwap-Wizard.bat"),
    ("tools/famswap_wizard.py", "tools/famswap_wizard.py"),
    ("tools/image_compose.ps1", "tools/image_compose.ps1"),
    ("Mods/FamSwap/Scripts/main.lua", "Mods/FamSwap/Scripts/main.lua"),
    ("Mods/FamSwap/enabled.txt", "Mods/FamSwap/enabled.txt"),
    ("Mods/FamSwap/README.txt", "Mods/FamSwap/README.txt"),
    ("Mods/FamSwap/examples/example_bar.png", "Mods/FamSwap/examples/example_bar.png"),
    ("Mods/FamSwap/examples/example_game.png", "Mods/FamSwap/examples/example_game.png"),
]

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
for src, dst in FILES:
    s = os.path.join(ROOT, src)
    d = os.path.join(OUT, dst)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy2(s, d)
    print("  +", dst)

zip_base = os.path.join(ROOT, "dist", NAME)
if os.path.exists(zip_base + ".zip"):
    os.remove(zip_base + ".zip")
shutil.make_archive(zip_base, "zip", os.path.join(ROOT, "dist"), NAME)
print(f"Package: {OUT}")
print(f"Zip:     {zip_base}.zip ({os.path.getsize(zip_base + '.zip') / 1024:.0f} KB)")
