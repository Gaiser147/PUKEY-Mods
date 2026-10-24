# Installing the mods

These instructions apply to the Windows Steam demo. Each playable mod can be installed separately. Start with one mod so that its behavior is easy to check.

For guided installation, updates, activation and configuration, use the [desktop Mod Manager](mod-manager.md). The steps below remain available for manual installation. The manager also runs on Linux to manage a Proton installation; gameplay compatibility there has not been verified.

## 1. Locate the game

In Steam, right-click the demo → **Manage → Browse local files**. This opens the game root. From there open:

```text
PUKEY_GODDESS_SHOT_TRICK\Binaries\Win64\
```

This guide calls that folder **Win64**. It contains `PUKEY_GODDESS_SHOT_TRICK_Demo-Win64-Shipping.exe`. Close the game before installing or updating files.

## 2. Install UE4SS once

1. Visit the [official UE4SS experimental release](https://github.com/UE4SS-RE/RE-UE4SS/releases/tag/experimental-latest).
2. Download the regular `UE4SS_v….zip` asset rather than a `zDEV` or `zCustom` package. The previously tested build is recorded in the [project notes](project-notes.md); newer experimental builds can behave differently.
3. Extract it into **Win64**, retaining its directory structure:

   ```text
   Win64/
     PUKEY_GODDESS_SHOT_TRICK_Demo-Win64-Shipping.exe
     dwmapi.dll
     ue4ss/
       UE4SS.dll
       UE4SS-settings.ini
       Mods/
   ```

The experimental release uses the `ue4ss` subfolder. See its release notes and the [official installation documentation](https://docs.ue4ss.com/installation-guide.html) for the loader's general setup. These mods use paths relative to **Win64** and expect the layout above.

### Disable incompatible UE4SS example mods

This project observed crashes caused by `ClientRestart` hooks in these bundled examples. Set their existing entries in `ue4ss/Mods/mods.txt` to:

```text
CheatManagerEnablerMod : 0
ConsoleEnablerMod : 0
ConsoleCommandsMod : 0
```

If `mods.json` contains these mods, also set their `mod_enabled` fields to `false`. Remove any `enabled.txt` markers inside those three example-mod folders. Preserve unrelated entries and keep the supplied `shared/UEHelpers` files; FreeCam and LightTools use them.

## 3. Copy and enable your chosen mod

Copy the **mod folder itself** from this repository's `Mods/` folder into `Win64/ue4ss/Mods/`. For example:

```text
Win64/ue4ss/Mods/FreeCam/
  enabled.txt
  Scripts/
    main.lua
```

Do not create an extra `Mods/Mods/` layer. The four playable mod folders already include an empty `enabled.txt` activation marker. If you manage activation using `mods.txt`, add or update `<ModName> : 1` above its `Keybinds` entry; keep `mods.json` consistent if you use it. Diagnostic mods have no activation markers and should remain disabled for normal play.

Continue with the mod's setup and controls:

- [FreeCam](../Mods/FreeCam/README.md)
- [LightTools](../Mods/LightTools/README.md)
- [FamSwap](../Mods/FamSwap/README.md): add images or run the wizard.
- [MovieSwap](../Mods/MovieSwap/README.md): add your own MP4 replacements.

## 4. Launch and verify

Launch through Steam, or run `Start-Process "steam://rungameid/5253020"` in PowerShell. Avoid launching a second game instance. Check `Win64/ue4ss/UE4SS.log` for the installed mod's prefix, such as `[FreeCam]`. Load a gameplay scene before testing its controls.

Lua source changes require a game restart. FamSwap F9 reloads images, and MovieSwap F11 rescans video replacements; neither reloads Lua scripts.

## Update, disable, or uninstall

- **Update:** close the game, back up replacement media and `FreeCam/positions.txt`, then copy the new mod files over the installed folder. Keep your existing user media.
- **Disable:** close the game, remove that mod's `enabled.txt`, set any matching `mods.txt` entry to `0`, and set any matching `mods.json` entry to `false` for `mod_enabled`. Restart the game.
- **Uninstall a mod:** close the game, back up personal files, remove only its folder from `ue4ss/Mods/`, and remove or disable its configuration entries.
- **Uninstall UE4SS:** close the game and remove `dwmapi.dll` and the `ue4ss` folder. This also removes installed mods and their stored media unless backed up.

See [troubleshooting](troubleshooting.md) if the game crashes or a mod does not load.
