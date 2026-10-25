"""Offline package inspection: python -m manager.validate_mod PATH."""
import argparse
from .packages import load_package


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path')
    arguments = parser.parse_args(argv)
    try:
        snapshot = load_package(arguments.path)
        for mod in snapshot.mods:
            kinds = ', '.join(entry['type'] for entry in mod.get('entrypoints', [{'type':'lua'}]))
            print('%s (%s) - %d files, %d settings' % (mod['id'], kinds, len(mod['files']) + len(mod.get('default_files', [])), len(mod.get('settings', []))))
        return 0
    except (ValueError, OSError) as exc:
        print('Invalid package: ' + str(exc))
        return 1


if __name__ == '__main__': raise SystemExit(main())
