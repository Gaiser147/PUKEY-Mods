# Mod Manager Implementation Plan

> Execute inline using superpowers:executing-plans and test-driven-development. The user approved the standalone desktop approach and delegated implementation details.

**Goal:** A downloadable Windows/Linux desktop app that fetches the repository catalogue and installs/configures existing and future mods.

**Architecture:** A validated immutable GitHub snapshot feeds a UI-independent transactional service. Qt presents catalogue-driven settings/media forms. Optional settings.lua files preserve defaults and survive source updates.

**Tech Stack:** Python 3.10+, PySide6, Pillow, psutil, PyInstaller; existing tools stay Python 3.8 compatible.

**Spec:** `docs/superpowers/specs/2026-10-24-mod-manager-design.md` (desktop choice approved 2026-10-25).

## Global constraints

Preserve personal media/settings/bookmarks; never change the real game during development. Only the fixed public GitHub repository and official UE4SS release supply executable content. Reject unsupported schemas, escaping paths/symlinks, corrupt configuration, and writes while the game runs. Linux means management of a Proton installation, not proven gameplay compatibility.

## Review focus

Archive traversal/collisions; partial-write rollback; manually installed mods; conflicting loader activation; preservation of unknown user files; offline state; Qt background-work lifecycle; actual downloadable artifact startup.

## Task 1 — Backend and catalogue

- [x] Write `tests/test_manager.py` covering malicious snapshots/catalogues, Steam library fixtures, install/update/remove/disable, rollback, game-running refusal, activation markers, JSON shapes and preserved user files; observe failures.
- [x] Implement `manager/catalog.py` (`Snapshot`, `fetch_latest`, `load_cached`), `manager/platforms.py` (`find_games`, `game_directory`, `game_running`), and `manager/service.py` (`Manager.install`, `set_enabled`, `remove`, `save_settings`, `install_loader`).
- [x] Add `catalog.json`; validate every listed payload before writes. Run backend tests.

## Task 2 — Configuration and media

- [x] Test typed configuration/Lua serialization, image dimensions/alpha/chroma, backups and video-path restrictions in `tests/test_media.py`.
- [x] Implement `manager/media.py` and optional configuration loading in the four Lua entry points. Add Lua execution smoke tests with Lupa.
- [x] Keep defaults and existing standalone installer behavior. Run relevant suites.

## Task 3 — Desktop and packaging

- [x] Implement `manager/gui.py` with background jobs, real status, catalogue settings, image preview and video import; `manager/__main__.py` supplies source/smoke-test modes.
- [x] Add Qt smoke tests and screenshots at desktop and Steam Deck desktop dimensions. One inspection/fix round, then confirmation.
- [x] Add dependency manifests, launch/build entry points, and Windows/Linux CI artifact builds. Build and smoke-test a local Windows bundle.

## Task 4 — Review and delivery

- [x] Update user/developer/catalogue docs and contributor guidance. Check links and staged files.
- [x] Review code/UI with a fresh reviewer, fix material findings, and rerun justified checks.
- [x] Publish source through GitHub, run Windows/Linux build jobs, inspect results, and publish the verified artifacts in a release. Verify repository and artifact URLs.

## Progress

Implementation has its own managed worktree. Native Qt desktop is not a web/iOS/Android surface; apply accessibility and Operate-mode principles directly, without a web scaffold or mobile-specific design.

Validation: 60 tests completed successfully, with one Windows symbolic-link privilege skip and native junction coverage passing. Actual official UE4SS ZIP validated. GitHub Windows/Linux builds and bundled startup passed. The CI-built Windows bundle also starts on the maintainer machine. A local Python 3.14 frozen Qt build failed; distribution builds are now guarded to Python 3.12, matching CI. In-game behavior remains unverified.

Delivery complete: PR #1 merged, manager-v0.1.0 prerelease published with Windows ZIP and Linux x86-64 tar.gz. Release workflow 40139579787 passed both platform builds and packaged startup checks. The downloaded Windows release executable also passed startup on the maintainer machine. Live main catalogue fetch/cache and actual UE4SS installation into a disposable game folder passed. Original workspace synchronized; installed game untouched.
