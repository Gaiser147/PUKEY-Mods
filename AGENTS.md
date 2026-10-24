# Repository Guidelines

## Project Structure & Module Organization

UE4SS Lua mods for the Windows Steam demo of **PUKEY GODDESS SHOT TRICK** (AppID `5253020`).

- `Mods/`: FreeCam, LightTools, FamSwap, MovieSwap; entry points are `Scripts/main.lua` within each mod.
- `manager/`: Qt desktop application, validated GitHub downloads, Steam discovery, transactional installation, configuration, and media composition.
- `catalog.json`: declarative mod payloads/settings; see `docs/mod-catalogue.md` before extending it.
- `diagnostics/`: default-disabled inspection mods. Keep probes out of the playable catalogue.
- `tests/`: standard-library backend, installer, Qt, media, and Lua-configuration tests.
- `tools/`: analysis and packaging; `dist-src/`: legacy FamSwap release templates; `docs/`: user/developer guides.
- Ignored `local/`, `scratch/`, `dist/`: research, test data, generated packages. Existing `FModel/` is ignored in place.

## Build, Test, and Development Commands

The manager requires Python 3.10+; legacy tools retain Python 3.8 support.

- `python -m pip install -r manager/requirements-dev.txt`: install development dependencies in a virtual environment.
- `python -m manager`: open the desktop manager.
- `python -m manager --source . --game-dir <fake-game-root>`: offline development using local catalogue files.
- `python -m unittest discover -s tests -v`: run tests; Windows-only cases skip elsewhere.
- `python -m manager --smoke-test`: check offline application startup.
- `python tools/build_manager.py`: build the current platform's standalone bundle.
- `py tools/build_famswap_package.py 1.0`: rebuild the legacy FamSwap package.

## Coding Style & Naming Conventions

Use four spaces, Python `snake_case`, PowerShell `Verb-Noun`, and existing Lua helper/configuration naming. Keep distributed text in English and preserve `[ModName]` log prefixes. No formatter is configured. Configuration belongs in optional `settings.lua`, not source rewrites.

## Testing Guidelines

Use `tests/test_*.py`. Include path/archive rejection, rollback, activation, configuration, and personal-file preservation cases for installer changes. Tests use temporary fake games, never the installed game. Qt runs offscreen; Lupa executes Lua with stubbed engine APIs. These checks do not verify gameplay. Manually check affected scenes and logs before claiming runtime compatibility. No coverage threshold is set.

## Commit & Pull Request Guidelines

Use concise imperative subjects. Describe affected mods, reproduction, validation, relevant issues, and screenshots for UI changes. Windows/Linux CI builds must pass before publishing `manager-v*` releases.

## Runtime Safety

Validate Unreal objects with `IsValid()`, use the game thread for mutations, and avoid unsafe TMap traversal or `ClientRestart` hooks. Disable the three incompatible console/cheat examples consistently. Preserve media, settings, bookmarks, saves, and unknown files. Never commit extracted assets or binaries, and avoid `git clean -fdx`, which deletes ignored research.
