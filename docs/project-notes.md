# Project and engine notes

These findings were recorded during local demo investigation on 2026-10-24 and checked against the current mod sources where applicable. They describe the tested build and may change after game or loader updates. Raw asset and localization dumps remain local.

## Tested environment

- Steam demo AppID `5253020`, internal project `Bacchus`, Unreal Engine 5.8.3 Shipping.
- Recorded executable file version: `++UE5+Release-5.8-CL-58210709`.
- Recorded UE4SS experimental build: `v3.0.1-1181-g83330635`, using `Win64/dwmapi.dll` plus `Win64/ue4ss/`.
- Demo-specific edition flags and cooked content were observed. The full game's omitted content is not present to unlock.

## Runtime rules

- Validate reflected object handles using `IsValid()`; helper lookups can return invalid objects rather than `nil`.
- Run engine mutations on the game thread. FreeCam and LightTools key callbacks enter `ExecuteInGameThread`; asynchronous loops also re-enter the game thread.
- Deep reflection and TMap iteration caused access violations. Dump incrementally and flush after each line.
- Do not add `PlayerController:ClientRestart` hooks. The three disabled UE4SS console/cheat example mods used this crash-prone path.
- Imported transient textures can be garbage-collected while held only in Lua. FamSwap checks texture identity and imports close to material assignment; preserve that handling.
- Restart to reload Lua scripts. Image/video reload keys operate on media only.

## Rendering and replacement paths

Fam is represented by flat surfaces rather than a skeletal character:

- Behind the counter: `BP_LookPlayerCamera` in `LV_Sandbox_SearchMode_Fam`, component `Plane`, texture parameter `Texture`, alpha-masked image with original aspect ratio 2220×4312.
- At the table: `BP_BT0000`, component `PlaneMovie`, a material chain containing `MI_Fam_Movie`, texture parameter `Texture00`.
- Media players `MP_MainGame_Fam_00/01` provide most table animations. Paper2D flipbooks and mouth textures are separate.

FamSwap checks cached surfaces on a 200 ms loop and refreshes the component search every ten ticks. It can hide flipbooks while replacement is active but does not supply replacement flipbook or lip-sync animation. The bar target was tested; complete drinking sequences need further validation.

MovieSwap converts relative `FileMediaSource.FilePath` values such as `./Bacchus/Movie/Fam/X.mp4` into absolute paths under its installed `Movies/` directory. It scans every two seconds as assets load.

The analyzed game ignores standalone `.pak` files without a matching `.utoc`/`.ucas` IoStore container. `tools/make_pak.py` alone therefore does not produce a usable content replacement here. Oodle decompression is unavailable in the local Python utilities.

## Windows image tooling

The FamSwap wizard supports Python 3.8 and delegates decoding/composition to WIC/WPF through PowerShell. Keep the WebP `PreservePixelFormat` behavior to retain alpha. Downloaded files can contain WebP data despite a `.png` extension. The pure-Python PNG decoder does not handle those files.

Image analysis can print decimal commas under German locale; the wizard normalizes them. Green-screen composition uses hardened alpha edges to avoid halos in the game's chroma-key material.

## Local workspace material

Extracted videos and their relative-link gallery are in ignored `local/Original-Animationen/`; indexes and old probe output are under `local/research/`. A file-preservation manifest is under `local/audit/`. FModel was open during organization, so its ignored root folder was left in place. No game files or running application sessions were modified by the reorganization.

The original, more detailed machine-specific `CLAUDE.md` remains in the game installation root. This repository's `CLAUDE.md` points contributors to portable documentation instead.
