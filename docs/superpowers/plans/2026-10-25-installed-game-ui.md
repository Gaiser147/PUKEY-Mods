# Installed Game UI Implementation Plan

> **For agentic workers:** Use the independent extraction/native-decoder tasks and execute GUI integration inline.

**Goal:** Preserve approved Design C while loading its seven UI images only from a present, selected game installation.

**Architecture:** A bounded IoStore reader uses allowlisted layout/hash metadata and an open-source decoder to read the current demo without modifying it. PNGs are written atomically to a local per-install/version cache. The Qt UI starts without game artwork and applies a verified theme asynchronously after selecting the game; no original game images ship in source or releases.

**Tech stack:** Existing Python/PySide6/Pillow, pinned MIT oozextract Rust cdylib built on Windows/Linux CI. Users require no Rust, Python, .NET or FModel installation.

## Constraints and interfaces

- Retain C's layout, editable keys and persistent actions; installer/backend behavior stays unchanged.
- `manager.game_assets.extract_theme(win64, cache_root, progress) -> Path` returns complete verified PNG cache or raises AssetExtractionError; `game_present(win64) -> bool` requires Shipping EXE and the paired game archives.
- `manager.native_decoder.decompress_oodle(data, expected_size) -> bytes` uses only the packaged open-source native helper. Never load a library from the game/cache or download proprietary codecs.
- A missing, changed or unsupported game must not activate cached images; ordinary manager controls remain usable.
- Only metadata/hashes, source code, OFL fonts and authored SVGs may be committed. Native helper binaries are build outputs. Extracted images and real game fixtures remain ignored.

## Tasks

- [ ] Derive and test bounded extraction metadata from the local demo; compare the seven decoded images against local reference exports without committing either.
- [ ] Build/test a portable decoder from pinned open-source source; verify a synthetic stream on both CI platforms and package its license.
- [ ] Add GUI tests for artwork-free startup, missing-game cache rejection and clearing artwork when installation disappears. Integrate background loading with generation checks and neutral fallback rendering.
- [ ] Remove original images from shipping paths and prove bundles contain none. Update guide, attribution and source-backed design documentation.
- [ ] Run full tests, read-only actual-game extraction, GUI review and Windows/Linux packaged startup; publish the verified manager update and local bundle.

## Review focus

Bound all archive offsets, counts, decoding sizes and image dimensions. Reject cache redirects and partial/corrupt outputs. Key cache identity to the selected installation and exact supported data. Ignore stale asynchronous results after game changes. Keep extraction out of the GUI thread and preserve unsaved settings across theme loads/failures. Unknown game updates fall back rather than guessing offsets.

## Ruling

The user chose runtime extraction in response to the asset distribution question. No exception to the no-extracted-assets rule was granted or is needed. The previous C preview stays local; this source/release will contain no game artwork.
