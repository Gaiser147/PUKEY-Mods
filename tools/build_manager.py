"""Build a self-contained manager on the current OS (Python 3.10+)."""
import importlib.metadata
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def main():
    if sys.version_info[:2] != (3, 12):
        raise SystemExit('Build standalone bundles with Python 3.12, matching the tested CI environment. Source launch supports Python 3.10+.')
    if sys.platform not in ('win32', 'linux') or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise SystemExit('Build on Windows or Linux x86-64; builds are platform-specific.')
    root = Path(__file__).resolve().parents[1]
    name = 'PUKEY-Mod-Manager'
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', name, '--distpath', str(root / 'dist/manager'),
        '--workpath', str(root / 'build/manager'), '--specpath', str(root / 'build'),
        '--copy-metadata', 'PySide6-Essentials', '--copy-metadata', 'shiboken6',
        '--copy-metadata', 'Pillow', '--copy-metadata', 'psutil',
        str(root / 'manager_launcher.py'),
    ], cwd=root, check=True)
    output = root / 'dist/manager' / name
    shutil.copy2(root / 'docs/mod-manager.md', output / 'README.md')
    shutil.copy2(root / 'manager/THIRD-PARTY.md', output / 'THIRD-PARTY.md')
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
