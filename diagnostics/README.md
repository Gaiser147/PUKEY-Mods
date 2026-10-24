# Diagnostic mods

These tools inspect the demo's runtime objects. They are separate from the four playable mods and intentionally omit `enabled.txt`.

## Run one diagnostic

1. Install UE4SS using the [shared instructions](../docs/installation.md).
2. Close the game and copy one folder from `diagnostics/` to `Win64/ue4ss/Mods/`.
3. Add an empty `enabled.txt` inside that installed diagnostic folder, or enable its name through your UE4SS mod configuration.
4. Launch through Steam and wait for its automatic work or use its documented key.
5. Close the game and disable it through all applicable activation mechanisms when finished.

| Diagnostic | Purpose | Trigger and output |
| --- | --- | --- |
| EditionProbe | Reflected demo/edition classes, properties, and localization keys | Automatic dump after 20 seconds; F9 repeats the main/text dump, F8 dumps keys. Writes `probe_out.txt`, `texts_out.txt`, and `keys_out.txt` in its installed folder. |
| FamProbe | Fam components, materials, textures, and media-player state | Repeats every 15 seconds, up to 20 passes; writes changes to installed `FamProbe/fam_out.txt`. |
| MediaProbe | Media-player URLs, media-source paths, and engine file visibility | Timed scans; output goes to `ue4ss/UE4SS.log`. |
| UsmapDump | Class/property mappings for compatible asset inspection tools | Calls `DumpUSMAP` once after 20 seconds; output is `ue4ss/Mappings.usmap`. |

EditionProbe's **F8/F9** bindings overlap with FamSwap. Disable FamSwap when using those probe bindings. Reflection can crash this engine/UE4SS combination, particularly deep structure traversal and TMap iteration; dump incrementally and flush outputs.

Generated dumps are local research, excluded from Git. The pre-organization dumps are preserved under `local/research/EditionProbe/` in the maintainer's workspace. The demo contains only its cooked subset of full-game content; these probes do not supply absent content.
