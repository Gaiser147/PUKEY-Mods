# FreeCam

A free camera with player teleport and five saved camera positions per map.

## Install

1. Complete the [UE4SS setup](../../docs/installation.md).
2. With the game closed, copy this repository's `Mods/FreeCam` folder into `Win64/ue4ss/Mods/`.
3. Confirm `FreeCam/Scripts/main.lua` and `FreeCam/enabled.txt` exist in the installed copy.
4. Launch through Steam, enter a gameplay scene, and press **F5**.

UE4SS's supplied `shared/UEHelpers` module is required. Python is not required.

## Controls

| Key | Action |
| --- | --- |
| F5 | Toggle free camera |
| F6 | Switch `possess` / `viewtarget` mode while FreeCam is off |
| W / A / S / D, mouse | Move and look |
| E / Space; Q / Ctrl | Move up; move down |
| Shift | Move faster |
| Page Up / Page Down | Increase / decrease base speed |
| Home | Reset base speed |
| T | Teleport the player to the camera and leave FreeCam |
| Ctrl+1–5 | Save a camera position in a slot for the current map |
| 1–5 | Jump to a saved position; enables FreeCam if needed |

## Modes and settings

The default `possess` mode spawns a collision-free SpectatorPawn and uses engine movement. `viewtarget` keeps the player pawn and moves a separate camera; try it if the default mode interferes with a scene. Mode changes using F6 last for that game session.

Edit the `Config` table in the installed `Scripts/main.lua` to change the default mode, speed, boost, sensitivity, or keybindings, then restart. Camera bookmarks persist in `FreeCam/positions.txt`; back it up before reinstalling.

## Limitations and removal

Teleport works best in search mode. The drinking-table scene can retain its fixed camera rig and movement restrictions after teleporting. Reloading a save restores the game's saved player position; teleport does not update it.

Toggle off with F5 before changing scenes. To disable or remove the mod completely, follow the [shared removal steps](../../docs/installation.md#update-disable-or-uninstall). Log messages use `[FreeCam]` and may be in German.
