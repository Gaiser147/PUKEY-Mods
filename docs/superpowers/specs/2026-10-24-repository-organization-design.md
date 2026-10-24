# Repository organization and GitHub publication

## Intent

Make the existing PUKEY demo mods easy to find, install independently, and maintain in one GitHub repository. Preserve the local research material and installed game.

## Proposed approach

Group the four player-facing mods in `Mods/`, inspection mods in `diagnostics/`, and installation/development notes in `docs/`. Keep Python and PowerShell utilities in `tools/`, FamSwap release templates in `dist-src/`, and generated packages in ignored `dist/`. Move extracted videos, FModel, asset indexes, and reflection dumps into ignored `local/`, preserving their contents.

Execution adjustment: FModel is currently running and holds its log open. Leave the existing ignored `FModel/` directory in place rather than closing the user's session. All other planned moves proceed; FModel can be moved into `local/` after it is closed.

Alternatives: retaining root-level mod directories minimizes path changes but leaves the workspace mixed; separate repositories per mod make installation focused but duplicate setup and maintenance. The user selected a single grouped repository and authorized proceeding with implementation judgment.

## Deliverables

- A root README with a mod comparison, quick start, compatibility scope, and links to detailed English guides.
- Shared UE4SS setup, per-mod install/use/uninstall guides for FreeCam, LightTools, FamSwap, and MovieSwap, troubleshooting, diagnostic notes, and contributor instructions.
- Updated FamSwap packaging paths and contributor guidance. Runtime Lua behavior stays unchanged.
- Review fixes to installer configuration safety: remove incompatible example-mod activation markers and preserve empty/singleton `mods.json` arrays; cover both with Windows regression tests.
- Git exclusions for local research, third-party binaries, generated output, personal media, logs, and camera positions.
- A clean initial Git commit and a public GitHub repository under `Gaiser147/PUKEY-Mods`, as selected by the user.

## Constraints

Windows, Python 3.8+, PowerShell, and the installed Steam demo are the existing toolchain. Download UE4SS separately from its official release; do not bundle it or FModel. Retain original videos locally. Do not publish raw localization dumps or game assets. Do not choose a software license on the user's behalf.

Keep diagnostic mods disabled by default, including their F8/F9 conflicts with FamSwap. Document known crash-prone UE4SS example mods. Source organization must not change the installed mod paths inside `ue4ss/Mods/`.

## Validation

Check preserved-file hashes after moves, build the FamSwap package, validate its contents and Python 3.8 syntax, and exercise the packaged installer in isolated fake game folders with UE4SS absent/present. Verify existing user images survive installation and unsafe example mods are disabled. Validate local Markdown links and inspect the staged Git file list before any push. In-game behavior is not revalidated by this organization task.

## Builder decisions

Use manual installation for the four mods and retain FamSwap's existing optional installer; a new universal installer is outside this task. Keep helper filenames stable to reduce changes. Add concise per-mod READMEs and use relative links suitable for GitHub. Do not modify game files or personal configuration during validation.
