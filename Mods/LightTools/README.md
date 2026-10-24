# LightTools

Lighting and visibility controls for exploring dark areas. Useful alongside FreeCam, and also usable independently.

## Install

1. Complete the [UE4SS setup](../../docs/installation.md).
2. With the game closed, copy `Mods/LightTools` into `Win64/ue4ss/Mods/`.
3. Confirm the installed folder contains `Scripts/main.lua` and `enabled.txt`.
4. Launch through Steam and enter a gameplay scene. Press F2 for a headlight, or F4 to toggle the game's post-processing effects.

UE4SS's supplied `shared/UEHelpers` module is required. Python and FreeCam are optional.

## Controls

| Key | Action |
| --- | --- |
| F1 | Toggle floodlight: six shadowless directional lights |
| F2 | Toggle a headlight that follows the camera |
| F3 | Toggle fog visibility where fog components exist |
| F4 | Toggle other post-processing volumes and components |
| F7 | Toggle shadows |
| + / − | Increase / decrease scene brightness |
| Ctrl + / − | Increase / decrease floodlight and headlight strength |
| Num0 or End | Reset all LightTools changes |

Brightness keys support the main keyboard and numeric keypad. Key mappings can vary with the keyboard layout; edit the `Config` table in `Scripts/main.lua` if necessary, then restart the game.

## Behavior and limitations

F4 affects effects such as outlines, cel shading, vignetting, darkening, and the drunk effect. F1 simulates a bright view with lights; the game's Shipping build does not expose a working `viewmode unlit` mode. Brightness uses color grading because exposure controls were ineffective in the tested build.

The tested bar scene has no fog components, so F3 may produce no visible change there. Use End to restore the previous settings before checking a different combination. Log messages use `[LightTools]` and may be in German.

Follow the [shared disable/uninstall steps](../../docs/installation.md#update-disable-or-uninstall) to remove the mod.
