# Repository Organization Implementation Plan

> Execute in this session using superpowers:executing-plans. The user selected the grouped layout and authorized proceeding with judgment.

**Goal:** Organize the workspace and publish a public GitHub repository with independent installation guides for all four playable mods.

**Architecture:** Keep runtime code unchanged under `Mods/` and diagnostic code under `diagnostics/`. Preserve research in ignored `local/`; update only packaging source paths and documentation.

**Tech Stack:** UE4SS Lua, Python 3.8+, Windows PowerShell, Git, GitHub CLI.

**Spec:** `docs/superpowers/specs/2026-10-24-repository-organization-design.md`

## Global Constraints

- Preserve every existing file; do not alter installed game files or saves.
- No bundled UE4SS, FModel, extracted game assets, personal images, or raw dumps in Git.
- English installation guides; keep Python compatible with 3.8.
- Preserve installed runtime paths and default-disabled diagnostic mods.
- Create the public repository under `Gaiser147/PUKEY-Mods`.

## Review Focus

- Moved source files must retain their hashes; inspect a before/after manifest.
- FamSwap packages must contain the expected installed paths after source relocation.
- Installer checks must use fake game folders and preserve existing user images.
- Document disabling through every activation mechanism, not only removing `enabled.txt`.
- Inspect staged files and Markdown links before publishing; exclude local research and binary tools.

## Task 1: Organize sources and preserve local material

- [x] Record a file/hash manifest and verify all move targets are inside the workspace.
- [x] Move playable mods to `Mods/`, diagnostics to `diagnostics/`, research/tool binaries to `local/`.
- [x] Add `.gitignore` and `.gitattributes`; update FamSwap packaging source paths.
- [x] Verify moved file hashes and run `py tools/build_famswap_package.py 1.0`.

## Task 2: Write installation and contributor documentation

- [x] Create root README, shared installation/troubleshooting guides, and four mod READMEs.
- [x] Document diagnostics and analysis tools; update `AGENTS.md` and add portable project notes.
- [x] Check local Markdown links and source-specific keybindings, paths, and limitations.

## Task 3: Validate and publish

- [x] Check Python 3.8 syntax, PowerShell syntax, and built ZIP contents.
- [x] Test packaged installer with missing/present UE4SS, user images, and example-mod configuration.
- [x] Initialize Git, inspect staged file inventory, and commit the organized project.
- [x] Review the final tree; correct material findings before pushing.
- [x] Create the public repository with GitHub CLI, push, and verify remote content/visibility.

## Execution Notes

Work in place because this task organizes an existing non-Git workspace; an isolated Git worktree is unavailable before repository initialization. Runtime Lua is relocated without edits. The packaging path adjustment is validated by building and inspecting its real distributable; no new runtime feature is introduced.

Review found existing installer safety gaps: example activation markers were retained and PowerShell serialization collapsed empty/singleton JSON arrays. New `tests/test_installer.py` regression tests reproduced both failures before minimal fixes were applied. All three tests now pass, including checks that unrelated mod configuration and user images survive installation.

Final verification: 170 task-local checks passed; all three committed installer tests passed, including a fresh Git checkout. The fresh checkout built the FamSwap package and stayed clean. Reviewer findings were resolved. GitHub confirmed PUBLIC visibility, default branch main, the expected source-only tree, and matching local/remote commit IDs. FModel remained ignored in place because its running process held a file lock. In-game behavior and live UE4SS downloading were not re-tested.
