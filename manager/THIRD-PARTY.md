# Bundled components

The standalone application includes Python, PySide6 / Qt, Shiboken, Pillow, and psutil. Dependency versions are recorded by the build; vendor license files are copied into `licenses/` and package metadata is retained in the bundle.

- Python: https://www.python.org/downloads/source/
- Qt for Python (PySide6 / Shiboken): https://code.qt.io/pyside/pyside-setup.git/
- Qt: https://code.qt.io/qt/
- Pillow: https://github.com/python-pillow/Pillow
- psutil: https://github.com/giampaolo/psutil

UE4SS is downloaded separately from its official repository when requested. The manager does not bundle game artwork, executables, gameplay videos, UE4SS, or FModel.

## Interface fonts

Amarante and Oswald are distributed under the SIL Open Font License 1.1. Their license texts accompany the fonts in `_internal/manager/assets/fonts/` in standalone builds. Sources: [Amarante](https://github.com/google/fonts/tree/main/ofl/amarante), [Oswald](https://github.com/google/fonts/tree/main/ofl/oswald). The neutral body font comes from the operating system.

## Game interface artwork

No original game UI images are distributed. For a present, selected and supported installation, the manager reads seven UI textures from the demo's archives into a private local cache. Only layout descriptions and integrity hashes are shipped in `manager/assets/game-ui-layout.json`. The game logo and artwork belong to their respective rights holders; the fonts' OFL does not apply to them. The mod manager is an unofficial community tool.

## Open-source archive decoder

The small native UI decoder wraps the MIT-licensed `oozextract` 0.5.6 crate. It is built from pinned source, with registry versions/checksums in `native/ui_decoder/Cargo.lock`. No proprietary Oodle DLL is loaded or distributed. Dependency licenses and attribution accompany the standalone app in `licenses/UI-decoder/`; see `native/ui_decoder/THIRD-PARTY.md` for source details. Rust and FModel are not required on the user's machine.
