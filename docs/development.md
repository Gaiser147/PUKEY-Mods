# Development and releases

## Work on the source copy

Edit playable mods in `Mods/<Name>/Scripts/main.lua` and probes in `diagnostics/<Name>/Scripts/main.lua`. Installed game copies are separate. With the game closed, copy the changed mod into `Win64/ue4ss/Mods/`, preserve personal media/bookmarks, then restart through Steam.

Use four spaces and follow each language's existing naming style. Keep Python 3.8 compatibility, English user-facing FamSwap text, and `[ModName]` log prefixes. There is no configured formatter or automated in-game test suite. Avoid changing Lua runtime behavior as part of repository housekeeping.

## Build the FamSwap package

```powershell
py tools/build_famswap_package.py 1.0
```

The builder takes release text and installer files from `dist-src/`, scripts from `tools/`, and runtime files/examples from `Mods/FamSwap/`. It outputs `dist/FamSwap-1.0/` and `dist/FamSwap-1.0.zip`, replacing previous outputs with that version. Use a simple version identifier such as `1.0` or `1.1`; do not pass paths.

Edit source templates instead of generated copies. Verify the version text in `dist-src/README.md`, `Mods/FamSwap/README.txt`, and the Lua header when making an actual version release. This builder packages FamSwap only; the other mods are installed from their source folders.

## Installer smoke tests

Run the standard-library regression suite on Windows:

```powershell
py -m unittest discover -s tests -v
```

`tests/test_installer.py` creates temporary fake game folders, never starts the game or downloads UE4SS, and checks loader-present/missing behavior, image preservation, all example-mod activation methods, and empty/singleton JSON arrays. The tests are skipped outside Windows PowerShell. No coverage threshold is configured.

Use a fake game root under `scratch/` with `PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64/`. For the loader-present case, provide placeholder `dwmapi.dll` and `ue4ss/UE4SS.dll` files plus sample `mods.txt` and `mods.json`. These placeholders are only for installer file-copy tests; they cannot run the game.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File dist/FamSwap-1.0/install.ps1 -GameDir "$PWD\scratch\GameCopy" -NoDownload -SkipRunningCheck
```

Verify that missing UE4SS exits with manual setup instructions, installed UE4SS receives the mod files, existing root-level PNG/JPG images are preserved, and the three incompatible examples are disabled without changing unrelated mod entries. The `-SkipRunningCheck` switch is for fake copies only.

For wizard checks, set `$env:FAMSWAP_MODDIR = "$PWD\scratch\GameCopy\PUKEY_GODDESS_SHOT_TRICK\Binaries\Win64\ue4ss\Mods\FamSwap"` after populating that folder. Confirm the wizard prints that test path; an invalid override can fall back to the real Steam installation. Clear the variable afterward with `Remove-Item Env:FAMSWAP_MODDIR`.

## Manual game validation

- FreeCam: toggle both modes, return to the player, adjust speed, save/load a slot, and check teleport in search mode.
- LightTools: test each toggle where relevant, then End to restore settings.
- FamSwap: test missing images, both targets, F8/F9, transparent edges, green-screen edges, and a full drinking round. Restart to check complete restoration after removing images.
- MovieSwap: verify the redirected path, trigger the corresponding scene, rescan additions with F11, and restart after removing files.

Record game/UE4SS versions and any untested scenarios. Installer checks do not establish in-game compatibility.

## Version control and contributions

Use concise imperative commit subjects and focused changes. Pull requests should explain the affected mod, reproduction steps, validation, and screenshots for visual changes. Link issues where relevant.

Before committing, inspect `git diff --cached --stat` and `git ls-files`. Keep game assets, raw dumps, third-party binaries, user media, logs, and generated packages out of Git. `local/` preserves local research; an existing in-use `FModel/` folder is ignored in place. Do not use `git clean -fdx` in this workspace: it would remove those ignored local files.

See [AGENTS.md](../AGENTS.md) and the [runtime notes](project-notes.md) before changing reflection or threading behavior.
