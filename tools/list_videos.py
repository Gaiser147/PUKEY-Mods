"""Schreibt eine Liste aller Spielvideos (Pfad für MovieSwap + Originalformat).

Benutzung: py list_videos.py <ausgepackter Ordner .../Content/Bacchus/Movie>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mp4_info  # noqa: E402

root = sys.argv[1]
print("Alle Spielvideos: Pfad unter MovieSwap/Movies/ | Originalformat")
print("Ersatz unter genau diesem Pfad ablegen. Fam-Videos: Greenscreen RGB(0,255,0), Figur oben mittig.")
print()
for dirpath, _, names in sorted(os.walk(root)):
    for name in sorted(names):
        full = os.path.join(dirpath, name)
        rel = "Bacchus/Movie/" + os.path.relpath(full, root).replace(os.sep, "/")
        print(rel)
        print("    " + mp4_info.info(full))
