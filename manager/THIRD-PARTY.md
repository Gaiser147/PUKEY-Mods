# Bundled components

The standalone application includes Python, PySide6 / Qt, Shiboken, Pillow, and psutil. Dependency versions are recorded by the build; vendor license files are copied into `licenses/` and package metadata is retained in the bundle.

- Python: https://www.python.org/downloads/source/
- Qt for Python (PySide6 / Shiboken): https://code.qt.io/pyside/pyside-setup.git/
- Qt: https://code.qt.io/qt/
- Pillow: https://github.com/python-pillow/Pillow
- psutil: https://github.com/giampaolo/psutil

UE4SS is downloaded separately from its official repository when requested. The manager does not bundle the game, extracted game media, UE4SS, or FModel.
