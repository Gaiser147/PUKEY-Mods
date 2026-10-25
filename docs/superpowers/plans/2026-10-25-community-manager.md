# Community Manager 0.4 Implementation Plan

**Goal:** Implement the approved contributor/import, configuration assistance and log-viewing plan while retaining Design C and game-read-only artwork loading.

**Spec:** The user's approved plan in this conversation is binding. English product/docs; Windows/Linux native Qt; UE4SS Lua and native Windows DLL mods; no Pak support, runtime installer execution or automatic dependencies.

## Tasks and interfaces

- [x] Packages/sources: independent validated source snapshots, optional `pukey-mod.json`, basic imports, GitHub/HTTPS/local ZIP resolution, durable last-good cache and developer validator. Snapshot retains mods/files/revision and adds source_id/origin. SourceStore persists sources separately from game preferences.
- [x] Configuration: validate_configuration(mod), read_configuration(mod, read), write_configuration(mod, values, read); JSON/INI/literal Lua only, no evaluation, unknown values preserved. Program/default ownership separate.
- [x] Installer integration: source-aware ownership schema 2, migration on successful mutation only, entrypoint-aware Lua/native/mixed status, protected seeds, explicit initial activation and per-source conflict rejection.
- [x] Logs: bounded read-only tailer plus independent modeless window; 512 KiB initial/128 KiB per second/10,000 visible lines, encoding/rotation/missing handling.
- [x] UI: reset/help, fixed-width status ribbons/wheel, source import/selection and local updates, source-aware guides/config access, explicit installation prerequisites, logs link. Preserve dirty forms.
- [ ] Documentation/templates, full validation, fresh code/design review, Windows/Linux bundles, manager-v0.4.0 prerelease and local verified copy.

## Execution ledger

Baseline: existing isolated worktree reused, clean branch `codex/manager-community-04` from origin/main `7a9616b`. Existing 0.3 native helper/dev environment retained as ignored build inputs. Three independent backend tasks delegated under the parallel-agents skill; parent owns service and main GUI integration. All mutation tests use temporary fake games.

Pre-flight: sources/config agree on `configuration` target list, separate `default_files`, and source-bound Snapshot.files keys `Mods/<id>/<relative>`. Native entrypoints are records `{type: lua|native, path: relative}`. Legacy official Snapshot.source_id defaults to `official`; old configuration behavior remains paired settings.json/settings.lua.

Ruling: Configuration defaults are never program payloads. Preserve personal-file classification in game ownership even if a later package attempts to reclassify the file. Source identity belongs in a separate application registry; every installed folder has a single owner.

Implementation validation: 186 local tests passed with two Windows symlink privilege skips. The real GitHub repository resolver returned its pinned main commit and all four mods; source smoke and both official/Lua-template validation passed. No installed-game mutation tests ran. Actual-game UI captures read installation state/artwork only; 12/30-mod, external settings, import and logs captures use synthetic additions or fake games.

Independent safety review found personal media reclassification, ownership lost after removal, invalid merged-cache replacement, activation lost on changed entrypoints and two external-media source routing errors. All were reproduced before fixes and have passing regressions; the reviewer confirmed no unresolved findings. Personal-path history is now independent of active ownership. Generated caches must round-trip all archive validation before registry replacement. Basic imports reject unsupported folder names rather than silently renaming them, and storage reparse checks precede directory creation.

Independent Impeccable review: ship after one bounded fix batch. The final dark scrollable plain-text help, readable requirements and stale release-choice invalidation were confirmed. DESIGN.md and native navigation/action tokens reflect actual code. Screenshots and game images remain ignored. Remaining work is Windows/Linux CI, frozen package checks and publication.
