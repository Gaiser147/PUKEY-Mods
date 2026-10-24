# Adding mods to the central installer

Create `Mods/<ID>/Scripts/main.lua`, add an English README, and register the mod in root `catalog.json`. IDs must be unique even ignoring case and use letters, digits, `_` or `-`, starting with a letter.

Minimal entry inside the `mods` array:

```json
{
  "id": "ExampleMod",
  "name": "Example Mod",
  "version": "1.0.0",
  "description": "Explain what the mod changes.",
  "controls": "F12: toggle",
  "files": ["Scripts/main.lua", "README.md"],
  "settings": []
}
```

Keep `schema_version` at `1` for supported features. List every program file relative to the mod folder; it must exist in the same repository snapshot. Include `Scripts/main.lua`. Do not list `enabled.txt`, `settings.lua`, or `settings.json`: activation and personal configuration belong to the manager/user. Do not include personal media or extracted game assets. Increment the mod version when changing its program files; updates also compare payload contents.

The manager discovers these entries at refresh time. It rejects unknown schema features with an upgrade message; new behavior that cannot be described by this schema needs a manager change.

## Settings

Supported field types generate their own form controls:

```json
[
  {"key":"Mode","label":"Mode","type":"enum","default":"idle","options":["idle","always"]},
  {"key":"Speed","label":"Speed","type":"number","default":100,"min":1,"max":1000,"step":1},
  {"key":"ToggleKey","label":"Toggle key","type":"key","default":"F12"},
  {"key":"Visible","label":"Visible","type":"boolean","default":true}
]
```

Keys must be Lua identifiers. Numbers must be finite and within bounds; booleans are not numbers. Supported key names are F1–F12, A–Z, HOME, END, PAGE_UP, PAGE_DOWN, INSERT, DELETE, SPACE, and ZERO–NINE.

The mod must **optionally load** its installed `settings.lua` after defining defaults, validate values, and map key-name strings through `Key[value]`. Follow the current mods' hooks rather than evaluating text replacements against Lua source. No file means the original defaults. Generic generated forms alone do not make a mod consume its settings.

## Image targets

Optional `images` entries describe user-produced PNGs, separate from program payloads:

```json
[{"file":"portrait.png","label":"Portrait","width":1110,"height":2156,"background":"transparent","scale":100,"top":0}]
```

Use `transparent` or `green` backgrounds. Keep image dimensions within 8192 per side and 16 million pixels to match the composer, scale between 1 and 500 percent, and the initial top offset between -100 and 100 percent. The GUI supplies percentage scale/offset and optional green removal; applying writes a PNG with a backup of any prior file.

## Video targets

Set `video_list` to a listed text payload such as `VIDEOS.txt` and `video_folder` to `Movies`. List allowed game-relative MP4 paths as separate lines, for example `Bacchus/Movie/Fam/T_FAM_BOW_A.mp4`. The current media UI supports these `Bacchus/Movie/` paths and validates the selected destination. Do not allow a program/config directory as the media folder.

## Validation

Run the full tests and `python -c "from pathlib import Path; from manager.catalog import Snapshot; print(len(Snapshot.from_directory(Path('.')).mods))"`. Test with a fake game folder, including installation, settings, update, disable and removal. Never activate diagnostic probes by adding them to the public playable-mod catalogue.
