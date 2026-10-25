"""Source and packaged application entry point."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description='PUKEY Mod Manager')
    parser.add_argument('--source', type=Path, help='Use a local repository snapshot for development')
    parser.add_argument('--game-dir', type=Path, help='Select an installation; changes still require user action')
    parser.add_argument('--smoke-test', action='store_true', help='Construct the app offline and exit')
    parser.add_argument('--screenshot', type=Path, help='Save a development screenshot and exit')
    parser.add_argument('--size', default='1120x800', help='Screenshot window size')
    arguments = parser.parse_args()
    if arguments.smoke_test or arguments.screenshot:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from .catalog import Snapshot
    from .gui import Window
    if arguments.smoke_test:
        from PySide6.QtGui import QPixmap

    app = QApplication(sys.argv[:1])
    app.setOrganizationName('PUKEYMods')
    app.setApplicationName('ModManager')
    app.setStyle('Fusion')
    if arguments.smoke_test:
        for name in ('chevron-down.svg', 'chevron-up.svg', 'check.svg'):
            if QPixmap(str(Path(__file__).resolve().parent / 'assets' / name)).isNull():
                raise RuntimeError('Required interface asset could not be loaded: ' + name)
    temporary = tempfile.TemporaryDirectory(prefix='pukey-smoke-') if arguments.smoke_test or arguments.screenshot else None
    snapshot = Snapshot.from_directory(arguments.source) if arguments.source else None
    if snapshot is None and arguments.smoke_test:
        mod = {'id': 'Smoke', 'name': 'Smoke test', 'version': '1.0', 'description': 'Offline startup check',
               'controls': '', 'files': ['Scripts/main.lua']}
        snapshot = Snapshot('smoke', {'catalog.json': json.dumps({'schema_version': 1, 'mods': [mod]}).encode(),
                                      'Mods/Smoke/Scripts/main.lua': b'print("smoke")'})
    prefs = Path(temporary.name) / 'preferences.json' if temporary else None
    window = Window(snapshot=snapshot, preferences_path=prefs,
                    start_online=not (arguments.source or arguments.smoke_test or arguments.screenshot))
    if arguments.game_dir:
        window.set_game(arguments.game_dir)
    if arguments.smoke_test or arguments.screenshot:
        width, height = map(int, arguments.size.lower().split('x'))
        window.resize(width, height)
    window.show()
    if arguments.smoke_test or arguments.screenshot:
        def done():
            if arguments.screenshot:
                arguments.screenshot.parent.mkdir(parents=True, exist_ok=True)
                if not window.grab().save(str(arguments.screenshot)):
                    raise OSError('Could not save screenshot')
            app.quit()
        QTimer.singleShot(250, done)
    try:
        return app.exec()
    finally:
        if temporary:
            temporary.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
