# Troubleshooting

## The game crashes at startup

Close all game instances. Check the [expected loader layout](installation.md#2-install-ue4ss-once), then disable `CheatManagerEnablerMod`, `ConsoleEnablerMod`, and `ConsoleCommandsMod` in all applicable activation mechanisms. Their `ClientRestart` hooks caused crashes in the tested setup.

Avoid launching the Shipping executable a second time while the game is running; a duplicate instance can fail during UE4SS startup and overwrite the useful log. Launch through Steam. If an update broke loading, compare the game and UE4SS versions with the [historical tested configuration](project-notes.md).

## A mod does not load

- Check for `Win64/ue4ss/Mods/<ModName>/Scripts/main.lua`, without another nested `Mods/` directory.
- Check `enabled.txt` and any entries in `mods.txt` or `mods.json` for consistent activation.
- Keep UE4SS's `shared/UEHelpers` module for FreeCam and LightTools.
- Restart after changing Lua. Image/video reload keys do not reload scripts.
- Read `Win64/ue4ss/UE4SS.log` and search for `[FreeCam]`, `[LightTools]`, `[FamSwap]`, or `[MovieSwap]`.

If no log is produced, check UE4SS loading before investigating the individual Lua mod. The game's Shipping build does not provide a useful engine log in its user configuration directory.

## Controls do nothing

Enter a gameplay scene and focus the game window. FreeCam F6 only switches modes while FreeCam is off. Keyboard layouts can change the plus/minus bindings. Change the relevant `Config` table and restart if needed.

EditionProbe uses F8/F9, which conflicts with FamSwap. Keep diagnostic mods disabled during normal play. The console example mods remain disabled; F10 is not an in-game console in this setup.

## FamSwap images are missing or look wrong

Confirm the files are in the **installed** FamSwap folder, rather than only in the repository. Check the [required image formats](../Mods/FamSwap/README.md#prepare-replacement-images). The bar image needs transparency; the table image needs a green background. Use the wizard's size, position, and green-screen tolerance controls to adjust framing and edges.

Fam can be absent behind the bar in some save states even with FamSwap off. Compare using F8 before diagnosing the mod. The table image, videos, mouth textures, and flipbooks are separate rendering paths. Restart after removing replacement files or to restore hidden flipbooks; reloading images alone is insufficient for complete restoration.

## MovieSwap does not show the replacement

Match the exact path from [VIDEOS.txt](../Mods/MovieSwap/VIDEOS.txt), including `Movies/Bacchus/Movie/`. Use the listed codec, dimensions, and frame rate for that specific video. Trigger the scene that actually plays it, then check the redirect messages in the log. Restart after removing a replacement or replacing a file that was in use.

Disable FamSwap or set its game target to `Mode = "idle"` if its still image covers the table videos. A plain `.pak` from `make_pak.py` is not an alternative in this game: the tested build ignores it without a matching IoStore container.

## The wizard cannot find Python or the mod

Run `py --version`. Install Python with its launcher if missing; `python` can resolve to the Microsoft Store placeholder. Install FamSwap before running the wizard. If Steam discovery fails, enter the installed `ue4ss/Mods/FamSwap` path when prompted.

For isolated development checks, set `FAMSWAP_MODDIR` to a test FamSwap folder containing `Scripts/main.lua`. If that folder is invalid, the current wizard can fall back to Steam discovery, so verify the printed destination before proceeding.

## Reporting an issue

Include the mod name, game build, UE4SS version, reproduction steps, relevant log excerpt, and expected versus actual behavior. Attach a screenshot for rendering issues. Do not attach saves, personal media, or complete asset/localization dumps unless specifically needed and suitable to share.
