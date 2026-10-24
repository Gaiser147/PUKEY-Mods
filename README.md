# PUKEY Mods

UE4SS Lua mods for the Windows Steam demo of **PUKEY GODDESS SHOT TRICK** (in-game title: *Drunken Goddess Reflux*, Steam AppID `5253020`).

Explore with a free camera, adjust lighting, or replace Fam's images and videos. Install only the mods you want; each works independently.

| Mod | What it does | Main controls | Installation and usage |
| --- | --- | --- | --- |
| FreeCam | Free camera, player teleport, five camera bookmarks per map | F5 / F6 / T | [FreeCam guide](Mods/FreeCam/README.md) |
| LightTools | Floodlight, headlight, brightness, fog, shadows, and post-processing controls | F1–F4 / F7 | [LightTools guide](Mods/LightTools/README.md) |
| FamSwap | Custom still images behind the counter and at the table | F8 / F9 | [FamSwap guide](Mods/FamSwap/README.md) |
| MovieSwap | Custom MP4 replacements for game videos | F11 | [MovieSwap guide](Mods/MovieSwap/README.md) |

## Quick start

The recommended route is the **[PUKEY Mod Manager](docs/mod-manager.md)**: download its Windows or Linux desktop bundle from [Releases](https://github.com/Gaiser147/PUKEY-Mods/releases), select the game folder, install UE4SS if needed, and choose your mods. It also manages updates, activation, settings, FamSwap images, and MovieSwap video imports. Linux/Proton gameplay compatibility remains unverified.

For manual installation instead:

1. Download this repository using **Code → Download ZIP** and extract it, or clone it:
   ```powershell
   git clone https://github.com/Gaiser147/PUKEY-Mods.git
   cd PUKEY-Mods
   ```
2. Close the game and follow the [shared UE4SS installation guide](docs/installation.md), including disabling the three incompatible example mods.
3. Copy your chosen folder, such as `Mods/FreeCam`, into the game's `PUKEY_GODDESS_SHOT_TRICK/Binaries/Win64/ue4ss/Mods/` directory.
4. Launch the demo through Steam and use the mod's controls. FamSwap needs replacement images and MovieSwap needs replacement videos; their guides explain where these go.

The four playable mod folders include `enabled.txt`. Diagnostic tools are separate and disabled by default. Do not copy the whole repository into the game.

## Requirements and compatibility

- Windows 10/11 and the Steam demo.
- UE4SS; the local project notes record testing with experimental build `v3.0.1-1181-g83330635` and Unreal Engine 5.8.3. This is a historical tested configuration, not a guarantee for every build.
- Python 3.8+ with the `py` launcher for the optional FamSwap wizard and package builder. The Lua mods themselves do not need Python.

Game or UE4SS updates can require changes. Compatibility with the full game has not been established. The repo supplies mod code and synthetic example images; download UE4SS separately and supply your own replacement media.

## Documentation

- [Shared installation, activation, updates, and uninstall](docs/installation.md)
- [Central desktop mod manager](docs/mod-manager.md)
- [Add future mods to the catalogue](docs/mod-catalogue.md)
- [Troubleshooting and known limitations](docs/troubleshooting.md)
- [Diagnostic mods](diagnostics/README.md)
- [Developer workflow and package building](docs/development.md)
- [Engine findings and runtime pitfalls](docs/project-notes.md)
- [Analysis and image tools](tools/README.md)
- [Contributor guidelines](AGENTS.md)

## Repository layout

```text
Mods/           FreeCam, LightTools, FamSwap, MovieSwap
manager/        Cross-platform desktop installer and configuration
catalog.json    Versioned mod catalogue read by the manager
diagnostics/    EditionProbe, FamProbe, MediaProbe, UsmapDump
docs/           Installation, troubleshooting, and development notes
tools/          Python and PowerShell utilities
tests/          Windows installer regression tests
dist-src/       FamSwap installer and release templates
dist/           Generated packages (ignored)
local/          Extracted media, research output, and audit files (ignored)
```

Existing local FModel installations are ignored as well. Game files, extracted videos, dumps, personal images, and third-party executables are excluded from version control.
