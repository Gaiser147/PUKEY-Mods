# Central mod manager design

## Purpose

Provide one friendly installer and configuration tool for the current four playable mods and future mods published in `Gaiser147/PUKEY-Mods`. Users should not need Git, edit Lua, or copy files manually. Include Windows and Linux/Proton installation management; distinguish installer support from unverified game/mod runtime compatibility on Proton.

## Approach

Recommended: a standalone desktop application, built from a shared Python backend and Qt/PySide6 interface, with Pillow for cross-platform image composition. Ship separate Windows and Linux bundles containing Python and dependencies. Existing tools retain their Python 3.8 compatibility; this new application targets Python 3.10+ because current Qt for Python requires it.

Alternatives presented: a local browser interface needs a background server and browser lifecycle; a terminal menu is simpler but less suitable for the requested usability. The user approved the standalone desktop application on 2026-10-25 and delegated implementation details.

## User workflow

1. Open the manager. It searches Steam libraries on Windows, native Linux, and Flatpak Steam; the user can choose the game folder manually.
2. Show the selected game folder, loader status, and mod list with installed/enabled/update status. Fetch the catalogue from GitHub without requiring a GitHub login.
3. Select a mod, read its description and controls, then install or update it. Offer UE4SS installation separately if missing. Existing installations are detected, including manually installed mods.
4. Configure supported settings through labelled form controls. FamSwap provides image selection, layout controls, and preview; MovieSwap offers replacement-video import using known game-relative paths. Show when a game restart is required.
5. Enable/disable or remove a mod. Preserve personal media, camera bookmarks, and settings by default, including during updates and removal. Explain any remaining personal files.

## Extensible catalogue

A versioned root `catalog.json` lists mod IDs, descriptions, versions, source file lists, documentation, controls, and optional declarative settings/media specifications. A new ordinary Lua mod is added by committing its folder and catalogue entry; the application does not need a release for each new mod. Unsupported catalogue schema/features fail with a clear upgrade message.

Fetch an immutable GitHub repository snapshot at a resolved commit, then read both catalogue and payloads from that snapshot. Validate catalogue identifiers, paths, types, duplicate entries, and file presence before any installation. Use bounded network reads and ZIP validation; reject traversal paths, symlinks, duplicate/case-colliding archive members, and oversized archives. Cache a previously validated snapshot for explicitly indicated offline use. Never run downloaded setup scripts.

## Installation and persistence

Use the existing installed paths under `PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64/ue4ss/Mods/`. Track manager-owned files and content hashes separately from user files. Modify only selected mods and required loader configuration. Stage writes, save backups, and restore the previous state on failure. Reject symbolic links that could redirect writes outside the selected installation. Block writes while the game is running.

Disable incompatible UE4SS example mods through `mods.txt`, `mods.json`, and activation markers. Enable/disable selected mods consistently across these mechanisms. Removing a managed mod deletes only tracked program files and activation, retaining personal data; unknown/manual program files are handled explicitly rather than recursively deleting arbitrary directories.

Store typed configuration in a separate generated `settings.lua`, loaded optionally by each current mod after its defaults. Missing configuration preserves existing behavior. Only expose supported settings and validate ranges, enums, key names, finite numbers, and booleans. Keep configuration files independent of versioned mod code.

UE4SS is downloaded directly from the official release, validated and staged separately; do not redistribute it inside the manager. The Linux app provides the Proton DLL override as a copyable Steam launch option; it does not silently change Steam's own configuration.

## Desktop surface

Operate mode: a compact game-location header, a navigable mod list, and a scrollable details/settings pane. Keep install/update, enable, and configuration actions clear and state-dependent. Use actual status values, responsive background downloads, keyboard-accessible controls, visible progress, and actionable inline errors. A minimum-width layout must remain usable on a Steam Deck in desktop mode. Distributed copy follows the project's English convention; German labels may be offered if feasible.

## Verification and delivery

- Standard-library backend tests: catalogue/path validation, malicious archives, Steam discovery fixtures, install/update/disable/remove, preserving media/configuration, rollback, JSON array shapes, and disabled example markers.
- Settings/image tests: validation, safe Lua serialization, PNG dimensions/alpha/chroma background, and backups of replaced media.
- Qt smoke tests and two bounded screenshot sizes; check empty, installed, busy, and error states.
- Existing installer tests remain green. Validate Lua parsing/configuration without launching the game.
- Build and smoke-test a Windows bundle locally. Build/test Windows and Linux through GitHub Actions; report which environments actually ran and keep Proton gameplay explicitly unverified until tested.
- Document downloads, source launch, adding catalogue entries, and update/removal behavior. Publish a GitHub release only after its actual artifacts have been built and verified.

## Boundaries

No game launches, real installation changes, save edits, or diagnostic activation are needed for development checks. Use fake installation folders. No self-updater, arbitrary repository sources, remote installer scripts, or game asset distribution in the initial version.
