# PUKEY Mod Manager

A desktop library and installer for the official playable mods and independently imported community mods. The official catalogue remains available; community packages keep their own source, selected mods and cached snapshot. Adding a supported mod does not require rebuilding the app.

## Download and start

Download a **PUKEY Mod Manager** prerelease from [GitHub Releases](https://github.com/Gaiser147/PUKEY-Mods/releases). Use the Windows ZIP or Linux x86-64 tar.gz, extract the **entire folder**, and run `PUKEY-Mod-Manager.exe` on Windows or `PUKEY-Mod-Manager` on Linux. Keep the `_internal` folder beside the executable. Python does not need to be installed separately.

On Linux, the executable may need permission to run: `chmod +x PUKEY-Mod-Manager`. The Linux bundle targets desktop Linux x86-64, including Steam Deck desktop mode; actual game/mod behavior under Proton remains unverified. It manages the Windows game files, not a native Linux game build.

## Game-derived interface

The manager ships without original game artwork. After selecting a supported installation, it reads seven UI textures from the game's archives into a local cache beside the manager preferences. This is read-only for the game; neither FModel nor a separate runtime is needed. Without the game, while extraction runs, or after an unsupported game update, a plain interface remains usable. Selecting another installation clears the previous artwork; the app also stops displaying cached artwork if the selected installation disappears.

Only the verified current demo container is supported for artwork extraction. A future game update may need a manager update before its artwork can be shown. This does not prevent ordinary mod management. The cache is versioned and integrity-checked rather than trusted as proof that the game is installed.

## First installation

1. Refresh the catalogue. No GitHub account or Git installation is required.
2. Let **Find in Steam** locate the game, or use **Browse**. You can select the game root, its `PUKEY_GODDESS_SHOT_TRICK` directory, or `Binaries/Win64`.
3. Close the game. If UE4SS is missing, choose **Install UE4SS** to download it from its official experimental release. The manager disables the three incompatible example mods through configuration and activation markers.
4. Select a mod and choose **Install mod**. Repeat for whichever mods you want.
5. Adjust preferences under **Settings** or shortcuts in the **Keybindings** sheet on the right, then choose **Save settings**. Both sheets share the same configuration. Changes and per-field resets stay in the form until you save. Restart the game after changing scripts, settings, activation, or removing replacement media.

Use **Game folder…** in the header to reopen Steam discovery, folder selection and loader setup. Setup collapses automatically when UE4SS is ready. Media tabs expand across the workspace; their preview/apply actions stay below the scrolling content.

On Linux/Proton, use **Copy Proton launch option**, then paste the DLL override into the game's Steam launch options:

```bash
WINEDLLOVERRIDES="dwmapi.dll=n,b" %command%
```

The manager does not edit Steam's launch options itself. Flatpak Steam installations can be detected, but folder access still depends on your desktop permissions.

## Add community mods

1. Choose **Add mod…** in the header. Paste a public GitHub repository, release or direct HTTPS ZIP link, or choose **Browse ZIP…** for a local package.
2. Choose **Inspect source**. If the repository only contains source code, select an offered release. If several ZIP assets are available, choose one and use **Inspect selected release / ZIP**. The manager never builds source code or runs downloaded installers.
3. Review the identified mods, versions, Lua/native types, descriptions, program file counts and author requirements. Check the mods you want and choose **Add selected mods**.
4. The selected mods appear in the library ribbon. Choose a mod tab, review its source and initial enable choice, then choose **Install mod**. Adding a source alone does not install or enable its mods.

Both Lua and native UE4SS layouts are supported. Native imports require a working compatible loader and a DLL built for the right architecture and UE4SS SDK/runtime. Inspection verifies the package structure; it does not prove a mod is safe or works in this game. Code runs later inside the game when enabled.

Library entries remain separate when two sources use the same mod ID. They still target the same UE4SS folder, so a **Source conflict** blocks overwriting another source's installation. Resolve that ownership conflict before installing the other mod.

The ribbon shows **Not installed**, **Enabled** or **Disabled**, and **Update available** where applicable. Each item has a source/status tooltip. Use the mouse wheel or horizontal trackpad gesture over the ribbon to scroll across many tabs; its horizontal scrollbar is also available.

For a local source, **Update from ZIP…** opens inspection for the replacement package you explicitly select. For an online source, **Source options…** opens inspection for its saved source and lets you choose another offered release or asset. Existing selected tabs are retained when a source is updated. A mod that disappears upstream stays visible as unavailable so its existing installation can still be managed.

## Setting help and reset

Each field has an information button with its explanation, default and, where relevant, option descriptions or allowed range. Hover over it, focus it with the keyboard, or activate it to read the details. A field's reset button restores its declared default in the form. **Save settings** commits the current values; reset does not save automatically. The confirmation tells you to restart the game.

Community mods can bind settings to declared JSON, INI or restricted literal Lua configuration files. Existing personal configuration is preserved during program updates; seeds are copied only when their destination is missing. Unsupported or malformed configuration reports an error and leaves the existing files intact. Mods without editable settings show that state instead of a generated empty form.

## Images and videos

**FamSwap → Images:** choose bar or table, select an image, adjust size/offsets and optional green-screen removal, then **Preview → Use preview image**. Controls and a resizing transparency preview sit side by side; the apply action stays in the footer. Composition uses Pillow on both platforms. **Restore** removes the selected custom PNG after backing it up; restart to completely restore previously changed surfaces. A manually installed `bar.jpg` or `game.jpg` can still be used by FamSwap if its PNG is absent, so remove/rename that fallback separately if needed.

**MovieSwap → Videos:** choose the original video path, then import your replacement MP4. Match its original codec, frame rate, dimensions, and duration as described in [the mod guide](../Mods/MovieSwap/README.md). Imports are limited to 32 MB per file in this initial GUI. The manager copies the file and preserves your source. Use **Restore original** and restart to undo a replacement. Disable FamSwap's table image or select its `idle` mode to see the videos.

## Updates, activation, and removal

- **Refresh catalogue** checks the official repository and saved online community sources. Repository sources follow the branch saved when they were added, resolving each download to an immutable commit. Release sources follow their selected tag or latest-release channel; direct HTTPS ZIPs follow their saved URL. Local packages keep their saved copy until you explicitly use **Update from ZIP…**. Refreshing does not install updates. Availability checks compare payload contents as well as versions.
- **Update/Reinstall** replaces declared program files. Settings, images, videos, bookmarks, and unknown files remain. Previous contents are backed up.
- **Enabled** changes the loader's matching activation entries and marker consistently.
- **Remove** deletes only manager-tracked, unchanged program files and disables the mod. Personal files remain. If a tracked file was edited, it remains too.
- Manually installed mods can be adopted using **Reinstall/Update**; originals are backed up. The removal button is available after adoption so that unknown files are not accidentally deleted.
- **Use offline copy** explicitly opens the last successfully downloaded and validated official catalogue when offline. Added community sources retain their own validated cached snapshots. A failed refresh keeps the previous valid copy; first-time online sources need one successful download. Local ZIP imports do not require a network connection.

Legacy official settings are written to `ue4ss/Mods/<Name>/settings.json` and `settings.lua`; the latter is optionally loaded by the mod. Community settings use their declared configuration targets where supplied. The mod itself must consume those values at runtime. Manager ownership data and backups are under `ue4ss/.pukey-manager/`. Keep backups if you may need to restore local script edits. Interrupted operations attempt rollback; an incomplete rollback reports the backup location. The manager does not uninstall UE4SS as a whole or delete saves.

Version 0.4 migrates installation ownership records to schema 2 with the next successful change. Reading status does not modify them. Older managers cannot manage the upgraded records; keep using 0.4 or newer. Personal-file history is retained even after removing a mod so later packages cannot silently overwrite preserved configuration/media.

## Read logs

Choose **Logs…** to open a separate, nonblocking window; the main manager remains usable. Select **UE4SS** or **Game** and a discovered log, or choose **Browse log...** for another file. Some game logs are not created until the game has run, so an empty source list or a missing-file message can be normal.

**Live** pauses or resumes following new text. Use the plain-text filter to narrow visible lines, **Auto-scroll** to follow the end, **Copy visible** to copy the displayed lines, and **Open folder** to locate the selected log. The viewer reads a bounded recent tail and keeps a bounded display for large files; older lines may be omitted. It handles truncation and replacement as the game rotates logs.

The viewer only reads logs. It never clears, truncates or deletes them, and it does not alter mod activation or configuration. Closing the log window leaves the main manager open.

## Source launch and testing

The new manager requires Python **3.10+**; existing standalone tools retain their previous requirements.

Source launches work without the native UI decoder and use the plain interface in that case. To enable archive extraction in a source checkout, install the Rust build toolchain and run `python tools/build_ui_decoder.py`. Standalone releases already include the helper. Distribution builds require Python 3.12 and build the helper before `python tools/build_manager.py`.

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

For package authoring, exact manifest/configuration fields, the offline validation CLI and synthetic Lua/native templates, see [the catalogue guide](mod-catalogue.md). Catalogue files are declarative; the manager never executes a downloaded installer script. Downloaded Lua/native code runs later inside the game when that mod is enabled.
