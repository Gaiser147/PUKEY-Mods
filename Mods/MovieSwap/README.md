# MovieSwap

Replace game videos at runtime with your own MP4 files. No asset repacking is required; videos without replacements continue using the originals.

## Install

1. Complete the [UE4SS setup](../../docs/installation.md).
2. Close the game and copy `Mods/MovieSwap` into `Win64/ue4ss/Mods/`.
3. Confirm `Scripts/main.lua` and `enabled.txt` exist in the installed folder.
4. Create a `Movies/` folder inside the installed MovieSwap folder and add your own replacement files using the paths below.
5. Launch through Steam and reach the scene that plays the chosen video. The mod scans loaded media sources every two seconds.

Python is not required. The repository does not include replacement or extracted game videos.

## Replacement paths

Preserve the original relative filename and folders. For example, replace `Bacchus/Movie/Fam/T_FAM_BOW_A.mp4` with:

```text
Win64/ue4ss/Mods/MovieSwap/Movies/Bacchus/Movie/Fam/T_FAM_BOW_A.mp4
```

The included [VIDEOS.txt](VIDEOS.txt) lists video paths and the formats observed in the analyzed demo. Event, logo, player, and Fam videos have different formats; use the listed properties for your target rather than applying one format to every video.

For most Fam animations, use H.264 (`avc1`) in MP4, 2560×1440 at 24 fps, a pure green RGB(0,255,0) background, and a character positioned top-center. Match the original duration where possible. The game material removes the green background.

## Reload and interaction with FamSwap

Press **F11** after adding replacement videos. Assets load at different times, so a successful scan does not mean the video will play immediately. `[MovieSwap]` entries in `ue4ss/UE4SS.log` show redirected paths; some messages are in German.

FamSwap's default table mode overrides the video material with a still image. To see MovieSwap videos, disable FamSwap or change its game target to `Mode = "idle"` and restart. Boot and other non-table videos use their own surfaces.

## Remove replacements

Close the game before replacing files that may be in use. Remove the custom MP4 and restart to restore the original video path. F11 rescans; it does not restore an already redirected source whose replacement has been removed.

To disable or uninstall MovieSwap itself, follow the [shared removal steps](../../docs/installation.md#update-disable-or-uninstall).
