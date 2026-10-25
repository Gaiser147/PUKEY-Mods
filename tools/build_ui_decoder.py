"""Build the open-source Oodle helper for the current Windows/Linux x86-64 host.

Requires Rust only on the build machine. Nothing is downloaded at application
runtime. Cargo.lock pins the complete dependency tree and crate checksums.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def collect_licenses(root: Path, packages: list, destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / 'native/ui_decoder/THIRD-PARTY.md', destination / 'THIRD-PARTY.md')
    for path in (root / 'native/ui_decoder/licenses').glob('Rust-LICENSE-*'):
        shutil.copy2(path, destination / path.name)
    for package in packages:
        if not package.get('source'):
            continue
        crate_root = Path(package['manifest_path']).parent
        target = destination / (package['name'] + '-' + package['version'])
        licenses = [path for path in crate_root.iterdir()
                    if path.name.lower().startswith(('license', 'licence', 'copying', 'notice', 'copyright'))]
        target.mkdir(parents=True, exist_ok=True)
        for path in licenses:
            if path.is_dir():
                shutil.copytree(path, target / path.name, dirs_exist_ok=True)
            else:
                shutil.copy2(path, target / path.name)
        # These pinned crates omit license files from their crate archives.
        # Retain upstream text (valuable) or the declared MIT terms (oozextract).
        if not licenses:
            fallbacks = {'oozextract': 'oozextract-MIT.txt', 'valuable': 'valuable-LICENSE.txt'}
            if package['name'] not in fallbacks or package.get('license') != 'MIT':
                raise RuntimeError('No license file found for dependency ' + package['name'])
            shutil.copy2(root / 'native/ui_decoder/licenses' / fallbacks[package['name']], target / 'LICENSE')
        (target / 'SOURCE.txt').write_text(
            f"{package['name']} {package['version']}\nLicense: {package.get('license', '')}\n"
            f"Source: {package['source']}\n", encoding='utf-8')


def build_decoder(root: Path, cargo: str = 'cargo') -> Path:
    if sys.platform not in ('win32', 'linux') or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('The UI decoder supports Windows and Linux x86-64 builds.')
    root = root.resolve()
    manifest = root / 'native/ui_decoder/Cargo.toml'
    environment = os.environ.copy()
    target = root / 'build/ui-decoder/target'
    environment['CARGO_TARGET_DIR'] = str(target)
    if sys.platform == 'win32':
        # Keep the VC runtime in our helper; users need no Rust/VC installation.
        # Pass an explicit host target: proc-macro host DLLs cannot be crt-static.
        environment['RUSTFLAGS'] = environment.get('RUSTFLAGS', '') + ' -C target-feature=+crt-static'
        target_options = ['--target', 'x86_64-pc-windows-msvc']
        release = target / 'x86_64-pc-windows-msvc/release'
    else:
        target_options = []
        release = target / 'release'
    base = ['--locked', '--manifest-path', str(manifest)]
    subprocess.run([cargo, 'test', *base, *target_options], cwd=root, env=environment, check=True)
    subprocess.run([cargo, 'build', '--release', *base, *target_options],
                   cwd=root, env=environment, check=True)
    metadata = subprocess.run([cargo, 'metadata', '--format-version', '1', *base],
                              cwd=root, env=environment, check=True, capture_output=True, text=True)
    filename = 'pukey_ui_decoder.dll' if sys.platform == 'win32' else 'libpukey_ui_decoder.so'
    output = root / 'manager/assets/native' / filename
    output.parent.mkdir(parents=True, exist_ok=True)
    collect_licenses(root, json.loads(metadata.stdout)['packages'], output.parent / 'licenses')
    shutil.copy2(release / filename, output)
    print('Built ' + str(output))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cargo', default='cargo', help='Path to the build machine Cargo executable')
    arguments = parser.parse_args()
    try:
        build_decoder(Path(__file__).resolve().parents[1], arguments.cargo)
    except FileNotFoundError as error:
        raise SystemExit('Rust build tools are required on the build machine: ' + str(error)) from error


if __name__ == '__main__':
    main()
