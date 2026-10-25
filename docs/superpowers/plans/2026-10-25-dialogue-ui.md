# Dialogue UI Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task.

**Goal:** Implement the user's selected concept C as the native manager interface.

**Architecture:** Keep the installer, catalogue and shared settings map. Replace the sidebar with horizontal mod navigation, a textured main dialogue panel and a separately scrolling editable keybindings sheet. Use the approved local comp at `local/design-studies/game-ui-2026-10-25/C-dialogue-desk.png` in the original workspace as visual authority.

**Tech Stack:** Python, PySide6, existing image/media backend, bundled OFL display fonts.

## Global constraints

Native Windows/Linux; English UI; no installed-game mutations in tests. Preserve configuration, personal files, job handling and unsaved-change protection. The user approved C, including mint selection, smoky black dialogue sheets, pink primary actions and Amarante/Oswald type. Original game textures stay local until the repository's no-extracted-assets instruction is explicitly resolved for distribution.

## Review focus

Future catalogue entries remain reachable by keyboard and horizontal scrolling. Both settings sheets share saving. Media actions remain visible at 1024×768. Game-folder setup, missing UE4SS and first-run states remain recoverable. Fonts/textures must load in frozen bundles.

## Tasks

- [x] Add failing GUI regressions for the separate keybindings sheet, horizontal catalogue overflow, collapsible setup and persistent media controls.
- [x] Implement themed native panels/navigation and bundled font loading in `manager/widgets.py` / `manager/theme.py`; rearrange `Window._build` and field/media layouts without backend changes.
- [x] Run the complete suite, source smoke and one screenshot batch covering both desktop sizes, installed/empty/media/error states and Linux-specific controls; fix material issues in one batch.
- [x] Review against the approved C comp with a fresh Impeccable reviewer, confirm fixes and document the shipped tokens.
- [x] Build and start-test a standalone Windows preview; provide the local bundle with updated instructions and attribution.
- [ ] Resolve asset publication scope, then run Windows/Linux CI and publish the repository/release when authorized.

## Direction contract

**THESIS:** The manager belongs to PUKEY's dialogue interface: a mod selection ribbon leads to a settings sheet and a visible shortcut sheet.

**OWN-WORLD:** Near-black background, irregular smoke-textured sheets, mint selected ribbon/key controls, pink save/install actions, off-white Amarante headings and Oswald labels. Retain readable native inputs and explicit states.

**STORY:** Select a mod, inspect its actual installation state, change preferences or keys, save; prepare media within the same workbench.

**FIRST VIEWPORT:** Game branding/title above four horizontally arranged mod choices; large settings panel left, narrower editable keybindings panel right; setup expands from the header, while save/media actions persist below the sheets.

**FORM:** Dialogue board, grounded structure 3, seed 7c0082be. The user selected C explicitly. The approved study is a Qt render, not a generated comp; core text/controls remain native and editable. Compact views retain side-by-side sheets, with media using the available width.

**FINISH:** unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Verification ledger

Impeccable disposition: ship, for the supplied Windows/offscreen desktop captures compared with C. Code review found video actions scrolling away and unreadable native popup surfaces; both were fixed with observed red/green regressions and independently confirmed resolved. Final Python 3.12 suite: 71 tests, successful with one symbolic-link privilege skip. PNGs carry embedded origins; seven raster files scanned, zero missing provenance. DESIGN.md and the native sidecar were updated from actual code.

Initial ruling: keep extracted UI artwork local until the user answers the explicit distribution-exception question. The user subsequently chose runtime extraction from the installed game; this is implemented by `2026-10-25-installed-game-ui.md`. No artwork exception was granted: code and layout/hash metadata may be published, original game images may not.

A frozen-startup failure traced to the build environment's PATH: PyInstaller selected Poppler's versioned ICU DLL, while Qt requires Windows' unversioned ICU exports. This explains the prior locally frozen Qt failure more precisely than Python version alone. The Windows build now passes a minimal Python/system PATH to PyInstaller; Linux retains its toolchain PATH. Tests cover both paths without changing the parent environment.

The actual Windows bundle passed offline startup and rendered the installed fake-game screen with its bundled fonts/textures. A local copy is available at `C:/Users/Leo/Documents/PUKEY-Mods/dist/PUKEY-Mod-Manager-0.3.0-preview/`. Non-default uppercase SYSTEMROOT handling was independently reviewed and confirmed fixed. Actual Linux rendering and Linux packaged startup await authorized CI publication. No source changes or game artwork were pushed; the installed game remains untouched.
