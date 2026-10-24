# Repository Guidelines

## Project Structure & Module Organization

UE4SS Lua mods for the Windows Steam demo of **PUKEY GODDESS SHOT TRICK** (AppID `5253020`).

- `Mods/`: FreeCam, LightTools, FamSwap, and MovieSwap; entry points are `Mods/<Mod>/Scripts/main.lua`.
- `diagnostics/`: EditionProbe, FamProbe, MediaProbe, and UsmapDump. Keep diagnostic mods disabled unless needed.
- `tools/`: Python analysis, image preparation, and packaging scripts; `image_compose.ps1` provides Windows WIC/WPF image processing.
- `tests/`: Windows installer regression tests.
- `dist-src/`: release documentation and installer templates; `dist/`: generated packages.
- `docs/`: installation, troubleshooting, development, and runtime notes; `Mods/FamSwap/examples/`: synthetic images.
- Ignored `local/`: extracted videos, indexes, and dumps. An existing in-use `FModel/` installation is ignored in place.

Read `docs/project-notes.md` for engine findings; detailed notes remain in the game installation's `CLAUDE.md`. Check against current source.

## Build, Test, and Development Commands

Use PowerShell and Python 3.8+:

- `py tools/build_famswap_package.py 1.0`: creates `dist/FamSwap-1.0/` and its ZIP, replacing existing outputs for that version. Edit sources, not generated copies.
- `py tools/famswap_wizard.py`: starts the interactive image wizard; normally writes to the installed FamSwap folder.
- `$env:FAMSWAP_MODDIR = "$PWD\scratch\FamSwap"`: redirects wizard output; provide a valid test folder containing `Scripts/main.lua` and verify the printed destination.
- `powershell -ExecutionPolicy Bypass -File dist/FamSwap-1.0/install.ps1 -GameDir "C:\test\GameCopy" -NoDownload -SkipRunningCheck`: tests the packaged installer against a prepared game-folder copy.

Deploy edited mods into `PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64/ue4ss/Mods/`; installed copies are separate. Restart after Lua edits. Launch through Steam, avoiding duplicate instances.

## Coding Style & Naming Conventions

Use four-space indentation. Follow existing Python `snake_case`, PowerShell `Verb-Noun`, and Lua `PascalCase` helper/configuration conventions. Preserve `Scripts/main.lua` entry points and `[ModName]` log prefixes. Keep distributed FamSwap text in English and Python compatible with 3.8. No formatter or linter is configured.

## Testing Guidelines

Run `py -m unittest discover -s tests -v` for Windows installer tests (`tests/test_*.py`, standard-library `unittest`). No coverage threshold is set. Manually check wizard previews, gameplay scenes, toggles, restoration, and FamSwap F8/F9. Inspect `Binaries/Win64/ue4ss/UE4SS.log`; report unverified scenarios.

## Commit & Pull Request Guidelines

No pre-import Git history is available. Use concise imperative subjects, such as `Fix FamSwap texture reload`. Include affected mods, reproduction steps, validation, relevant issues, and screenshots for visual changes.

## Runtime Safety

Validate Unreal objects with `IsValid()` and schedule engine mutations on the game thread. Avoid unsafe TMap traversal and `ClientRestart` hooks. Keep `CheatManagerEnablerMod`, `ConsoleEnablerMod`, and `ConsoleCommandsMod` disabled. Preserve user images and saves.

Do not commit extracted assets, dumps, executables, or personal media. Avoid `git clean -fdx`: it deletes ignored local research.
