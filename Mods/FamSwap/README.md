# FamSwap

Replace Fam with your own still images behind the bar counter and at the drinking table. Missing images leave the original target unchanged on a fresh game start.

## Install from source

1. Complete the [UE4SS setup](../../docs/installation.md).
2. Close the game and copy `Mods/FamSwap` into `Win64/ue4ss/Mods/`.
3. Confirm the installed folder contains `Scripts/main.lua` and `enabled.txt`.
4. Prepare your images using the wizard below, or copy images manually.

## Optional packaged installer

From the repository root, run:

```powershell
py tools/build_famswap_package.py 1.0
```

This creates `dist/FamSwap-1.0/` and `dist/FamSwap-1.0.zip`. Open the generated folder and run `Install.bat`, then `FamSwap-Wizard.bat`. The installer detects the Steam game, offers to download UE4SS if missing, and disables the three incompatible example mods in UE4SS configuration. Existing root-level PNG/JPG images are preserved.

This package installs **FamSwap only**. It does not install FreeCam, LightTools, or MovieSwap. Python 3.8+ with the `py` launcher is needed for building and for the wizard, but not for the Lua mod or manual image installation.

## Prepare replacement images

After installing the mod, run `FamSwap-Wizard.bat` from the repository root, or:

```powershell
py tools/famswap_wizard.py
```

Choose bar, table, or both; drag in an image and adjust the preview. The wizard uses Windows imaging through `tools/image_compose.ps1`, supports transparent or green-screen inputs, and backs up an existing generated image as `*_previous.png`.

For manual setup, place these files directly in the **installed** `ue4ss/Mods/FamSwap/` folder:

| File | Target | Format |
| --- | --- | --- |
| `bar.png` | Behind the counter in search mode | Transparent PNG; 2220×4312 or the same aspect ratio, such as 1110×2156; character top-center |
| `game.png` | At the drinking table | 16:9, such as 1920×1080; pure green RGB(0,255,0) background; character top-center |

Synthetic samples are in `examples/`; copy them out and rename them to the filenames above to try the layout. PNG is recommended; the Lua script also looks for `bar.jpg` and `game.jpg`, which cannot supply transparency for the bar.

## Controls and limitations

- **F8:** toggle replacement on/off.
- **F9:** reload images after adding or changing them.

The table replacement is a still image. In `Scripts/main.lua`, the game target's `Mode = "always"` overrides videos, while `"idle"` allows MovieSwap videos to play. Restart after changing Lua configuration.

Paper2D flipbook animations are hidden when `HideFlipbooks` is enabled; they are not replaced. Mouth textures are not independently replaced. Bar rendering was previously tested; complete drinking sequences still need broader testing. Fam can also be absent behind the counter because of the current save state.

To restore everything after removing images or hiding flipbooks, restart the game. F9 refreshes image loading and does not guarantee restoration of every already modified surface. See the [shared removal steps](../../docs/installation.md#update-disable-or-uninstall) for disabling or uninstalling the mod. Log messages use `[FamSwap]`.
