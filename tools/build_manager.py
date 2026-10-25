"""Build a self-contained manager on the current OS with Python 3.12."""
import importlib.metadata
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def build_environment():
    environment = os.environ.copy()
    if sys.platform == 'win32':
        # DLL discovery must not pick an unrelated tool's ICU/CRT from PATH.
        windows = Path(environment.get('SystemRoot') or environment.get('SYSTEMROOT') or 'C:/Windows')
        paths = [Path(sys.executable).parent, Path(sys.base_prefix), windows / 'System32', windows]
        environment['PATH'] = os.pathsep.join(dict.fromkeys(map(str, paths)))
    return environment


def reject_bundled_game_artwork(root: Path):
    artwork = root / 'manager/assets/game'
    if artwork.exists() or artwork.is_symlink():
        raise RuntimeError('Refusing to bundle game artwork from manager/assets/game; extract it locally at runtime.')


def main():
    if sys.version_info[:2] != (3, 12):
        raise SystemExit('Build standalone bundles with Python 3.12, matching the tested CI environment. Source launch supports Python 3.10+.')
    if sys.platform not in ('win32', 'linux') or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise SystemExit('Build on Windows or Linux x86-64; builds are platform-specific.')
    root = Path(__file__).resolve().parents[1]
    reject_bundled_game_artwork(root)
    sys.path.insert(0, str(root))
    from manager.native_decoder import _library_path, decompress_oodle
    native_decoder = _library_path()
    # Refuse to produce a release with a missing or unusable extraction helper.
    decompress_oodle(b'\x4c\x06\xab', 1)
    name = 'PUKEY-Mod-Manager'
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', name, '--distpath', str(root / 'dist/manager'),
        '--workpath', str(root / 'build/manager'), '--specpath', str(root / 'build'),
        '--copy-metadata', 'PySide6-Essentials', '--copy-metadata', 'shiboken6',
        '--copy-metadata', 'Pillow', '--copy-metadata', 'psutil',
        '--add-data', str(root / 'manager/assets') + os.pathsep + 'manager/assets',
        '--add-binary', str(native_decoder) + os.pathsep + 'manager/assets/native',
        str(root / 'manager_launcher.py'),
    ], cwd=root, env=build_environment(), check=True)
    output = root / 'dist/manager' / name
    shutil.copy2(root / 'docs/mod-manager.md', output / 'README.md')
    shutil.copy2(root / 'manager/THIRD-PARTY.md', output / 'THIRD-PARTY.md')
    shutil.copytree(native_decoder.parent / 'licenses', output / 'licenses/UI-decoder', dirs_exist_ok=True)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.is_file():
        (output / 'licenses/Python').mkdir(parents=True, exist_ok=True)
        shutil.copy2(python_license, output / 'licenses/Python/LICENSE.txt')
    for package in ['PySide6-Essentials', 'shiboken6', 'Pillow', 'psutil']:
        distribution = importlib.metadata.distribution(package)
        for file in distribution.files or []:
            if any(part in ('..', '.') for part in file.parts):
                continue
            if 'license' in str(file).lower() or 'copying' in str(file).lower():
                source = Path(distribution.locate_file(file))
                if source.is_file():
                    target = output / 'licenses' / package / str(file)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    system = 'windows' if sys.platform == 'win32' else 'linux'
    archive = root / 'dist' / ('PUKEY-Mod-Manager-' + system + '-x86_64')
    format_name = 'zip' if system == 'windows' else 'gztar'
    result = shutil.make_archive(str(archive), format_name, output.parent, output.name)
    print('Built ' + result + ' (' + platform.machine() + ')')


if __name__ == '__main__':
    main()
