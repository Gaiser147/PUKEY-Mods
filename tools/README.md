# Tools

Run from the repository root on Windows with the Python `py` launcher. These scripts use the Python standard library; image composition additionally uses Windows PowerShell and WIC/WPF. Set `$env:PYTHONIOENCODING = "utf-8"` when processing non-ASCII asset names.

## User-facing and release tools

| Command | Purpose |
| --- | --- |
| `py tools/famswap_wizard.py` | Find installed FamSwap and prepare bar/table images interactively. |
| `py tools/build_famswap_package.py 1.0` | Build `dist/FamSwap-1.0/` and its ZIP; replaces existing outputs for that version. |
| `powershell -NoProfile -ExecutionPolicy Bypass -File tools/image_compose.ps1 -Src "input.png" -Analyze` | Inspect image dimensions, transparency, and green edges. |
| `py tools/png_util.py testimage_alpha "scratch/sample.png" 111 216` | Generate a synthetic transparent PNG; create `scratch/` first. |

`image_compose.ps1` accepts `-Dst`, `-Width`, `-Height`, `-Background transparent|green`, scale/offset controls, and green-screen removal parameters. Read its header for the full interface. `png_util.py` also provides `fit`, `greenscreen`, `testimage`, and `testimage_alpha`; its decoder is limited to supported non-interlaced 8-bit PNG variants. The wizard uses Windows decoding for broader format support.

## Local analysis

Use your own game installation or locally extracted data as input. Write generated output to ignored `local/` or `scratch/`.

| Command | Purpose |
| --- | --- |
| `py tools/utoc_list.py "input.utoc"` | List paths from an IoStore directory index. |
| `py tools/pak_list_extract.py "input.pak" "local/extracted" [filters...]` | List entries and extract uncompressed entries matching optional substring filters. |
| `py tools/exe_strings.py "game.exe" "local/strings.txt"` | Dump ASCII and UTF-16 strings. |
| `py tools/mp4_info.py "local/Original-Animationen"` | Inspect MP4 formats recursively. |
| `py tools/list_videos.py "local/Original-Animationen/Bacchus/Movie"` | Print MovieSwap paths with observed video formats. |
| `py tools/make_gallery.py "local/Original-Animationen" "local/Original-Animationen/Uebersicht.html"` | Build a local video gallery with relative media links. |
| `py tools/make_pak.py "input-folder" "scratch/example_P.pak"` | Experimental uncompressed pak writer; its output alone is ignored by this game. |

The archive scripts are narrow research utilities for the analyzed formats, not general extraction tools. They cannot decompress Oodle entries in this environment. Asset replacements require matching IoStore containers; use MovieSwap for runtime video replacement instead.

The old `pak_files.txt`, `utoc_files.txt`, and `Asset-Liste.txt` inventories are preserved under `local/research/` and excluded from Git. FModel is downloaded and managed separately; it is not a repository dependency.
