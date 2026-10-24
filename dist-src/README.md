# FamSwap 1.0 – replace the opponent in PUKEY GODDESS SHOT TRICK Demo

FamSwap replaces **Fam** (the opponent, in-game title *Drunken Goddess Reflux*) with any character image you like:

- **behind the bar counter** (search mode, before a match), and
- **at the table** during the drinking game (as a still image instead of her animations).

It works at runtime through [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) and does **not** modify any game files.

## Requirements

- Windows 10/11
- *PUKEY GODDESS SHOT TRICK Demo* (Steam)
- [Python 3](https://www.python.org/downloads/) for the image wizard (keep the "py launcher" option checked during setup)

## Installation

1. Close the game.
2. Extract this zip anywhere (e.g. your Desktop).
3. Double-click **`Install.bat`**.
   - It finds the game through Steam automatically (or asks for the folder).
   - If UE4SS is missing, it offers to download the latest build from the official UE4SS GitHub release
     and extracts it next to the game's executable.
   - It copies the FamSwap mod and disables three UE4SS example mods
     (`CheatManagerEnablerMod`, `ConsoleEnablerMod`, `ConsoleCommandsMod`) that crash this game.
4. Double-click **`FamSwap-Wizard.bat`** and follow the steps:
   - choose what to replace (default: bar counter **and** table),
   - drag your image into the window (PNG, WebP, JPEG, … – transparent background or green screen),
   - check the preview and adjust size/position if needed.
5. Start the game.

### Manual installation (without Install.bat)

1. Download `UE4SS_v….zip` from the [UE4SS experimental-latest release](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/experimental-latest)
   and extract it into `…\PUKEY GODDESS SHOT TRICK Demo\PUKEY_GODDESS_SHOT_TRICK\Binaries\Win64\`
   (`dwmapi.dll` and the `ue4ss` folder must sit next to `PUKEY_GODDESS_SHOT_TRICK_Demo-Win64-Shipping.exe`).
2. Copy `Mods\FamSwap` into `…\Binaries\Win64\ue4ss\Mods\`.
3. In `…\ue4ss\Mods\mods.txt` set `CheatManagerEnablerMod`, `ConsoleEnablerMod` and `ConsoleCommandsMod` to `0`.
   If present in `mods.json`, also set their `mod_enabled` fields to `false`. Remove any `enabled.txt` files inside those three example-mod folders, since those markers can enable them independently.
4. Put your images as `bar.png` / `game.png` into `…\ue4ss\Mods\FamSwap\` (or use the wizard).

## In-game keys

| Key | Action |
|-----|--------|
| F8  | Toggle between your image and the original Fam |
| F9  | Reload the images (after running the wizard again – no restart needed) |

## Image files

The wizard creates these for you; you can also make them yourself:

| File | Where | Format |
|------|-------|--------|
| `bar.png`  | behind the bar counter | transparent PNG, 2220×4312 or same aspect ratio (e.g. 1110×2156), character top-center |
| `game.png` | at the table | 16:9 (e.g. 1920×1080), pure green background RGB(0,255,0), character top-center |

If a file is missing, the original Fam is shown there.

## Limitations

- At the table your character is a still image; Fam's animations are videos and are replaced by it.
- A few short animations (puking, winning) are sprite flipbooks; they are hidden while the replacement is active.
- Depending on your progress there may be no Fam behind the counter in search mode – that is the game, not the mod.

## Uninstall

- Close the game and back up your custom images first.
- Remove only FamSwap: delete `…\Binaries\Win64\ue4ss\Mods\FamSwap`.
- If you added FamSwap to `mods.txt` or `mods.json`, remove or disable that entry too.
- Remove UE4SS completely: delete `dwmapi.dll` and the `ue4ss` folder in `…\Binaries\Win64\`.

## Troubleshooting

- Log file: `…\Binaries\Win64\ue4ss\UE4SS.log` – FamSwap lines start with `[FamSwap]`.
- After a game update UE4SS may need an update too (download the newest experimental build).
- Restart after removing image files or to restore hidden flipbook layers; F9 only refreshes image loading.
