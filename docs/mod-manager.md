# PUKEY Mod Manager

A central desktop installer for the playable mods in this repository. It reads the mod catalogue and files from GitHub; adding an ordinary catalogue-compatible mod does not require rebuilding the app.

## Download and start

Download a **PUKEY Mod Manager** prerelease from [GitHub Releases](https://github.com/Gaiser147/PUKEY-Mods/releases). Use the Windows ZIP or Linux x86-64 tar.gz, extract the **entire folder**, and run `PUKEY-Mod-Manager.exe` on Windows or `PUKEY-Mod-Manager` on Linux. Keep the `_internal` folder beside the executable. Python does not need to be installed separately.

On Linux, the executable may need permission to run: `chmod +x PUKEY-Mod-Manager`. The Linux bundle targets desktop Linux x86-64, including Steam Deck desktop mode; actual game/mod behavior under Proton remains unverified. It manages the Windows game files, not a native Linux game build.

## First installation

1. Refresh the catalogue. No GitHub account or Git installation is required.
2. Let **Find in Steam** locate the game, or use **Browse**. You can select the game root, its `PUKEY_GODDESS_SHOT_TRICK` directory, or `Binaries/Win64`.
3. Close the game. If UE4SS is missing, choose **Install UE4SS** to download it from its official experimental release. The manager disables the three incompatible example mods through configuration and activation markers.
4. Select a mod and choose **Install mod**. Repeat for whichever mods you want.
5. Adjust its settings and choose **Save settings**. Restart the game after changing scripts, settings, activation, or removing replacement media.

On Linux/Proton, use **Copy launch option**, then paste the DLL override into the game's Steam launch options:

```bash
WINEDLLOVERRIDES="dwmapi.dll=n,b" %command%
```

The manager does not edit Steam's launch options itself. Flatpak Steam installations can be detected, but folder access still depends on your desktop permissions.

## Images and videos

**FamSwap → Images:** choose bar or table, select an image, adjust size/offsets and optional green-screen removal, then **Preview → Use this image**. Composition uses Pillow on both platforms. Restore original removes the selected custom PNG after backing it up; restart to completely restore previously changed surfaces. A manually installed `bar.jpg` or `game.jpg` can still be used by FamSwap if its PNG is absent, so remove/rename that fallback separately if needed.

**MovieSwap → Videos:** choose the original video path, then import your replacement MP4. Match its original codec, frame rate, dimensions, and duration as described in [the mod guide](../Mods/MovieSwap/README.md). Imports are limited to 32 MB per file in this initial GUI. The manager copies the file and preserves your source. Use **Restore original** and restart to undo a replacement. Disable FamSwap's table image or select its `idle` mode to see the videos.

## Updates, activation, and removal

- **Refresh mods** obtains a new immutable snapshot from the fixed repository. Update availability checks payload contents as well as catalogue versions.
- **Update/Reinstall** replaces declared program files. Settings, images, videos, bookmarks, and unknown files remain. Previous contents are backed up.
- **Enabled** changes the loader's matching activation entries and marker consistently.
- **Remove** deletes only manager-tracked, unchanged program files and disables the mod. Personal files remain. If a tracked file was edited, it remains too.
- Manually installed mods can be adopted using **Reinstall/Update**; originals are backed up. The removal button is available after adoption so that unknown files are not accidentally deleted.
- **Use cached** explicitly opens the last successfully downloaded and validated catalogue when offline. A first run needs a successful network download.

Settings are written to `ue4ss/Mods/<Name>/settings.json` and `settings.lua`; the latter is optionally loaded by the mod. Manager ownership data and backups are under `ue4ss/.pukey-manager/`. Keep backups if you may need to restore local script edits. Interrupted operations attempt rollback; an incomplete rollback reports the backup location. The manager does not uninstall UE4SS as a whole or delete saves.

## Source launch and testing

The new manager requires Python **3.10+**; existing standalone tools retain their previous requirements.

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r manager/requirements-dev.txt
.venv\Scripts\python -m manager
```

On Linux use `python3 -m venv .venv` and `.venv/bin/python` for the subsequent commands. Dependencies include Qt/PySide6, Pillow, and psutil. Development-only Lupa tests execute Lua with stubbed UE4SS APIs; they do not establish in-game compatibility.

```text
python -m unittest discover -s tests -v
python -m manager --smoke-test
python tools/build_manager.py
```

For an offline development session use `python -m manager --source . --game-dir <fake-game-root>`. Never use a real game folder for mutation tests. GitHub Actions tests/builds Windows and Linux separately, then tags named `manager-v*` publish a prerelease only after both build jobs pass.

Standalone packaging is standardized on **Python 3.12**, matching the tested CI environment. Source launch supports Python 3.10+, but the build script rejects other Python versions; a local Python 3.14 frozen Qt build failed startup while the Python 3.12 artifact passed on the same machine.

## Adding a mod

See [the catalogue guide](mod-catalogue.md). Catalogue files are declarative; the manager never executes a downloaded installer script. Downloaded Lua code runs later inside the game when that mod is enabled.
