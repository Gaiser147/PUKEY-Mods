# Mod packages and catalogue contract

The manager accepts the official repository catalogue and independent community
ZIPs or mod folders. Importing inspects data only: it never runs installers, Lua,
DLLs, build scripts or repository commands. Package validation checks structure and
settings declarations. It cannot establish runtime safety, native ABI compatibility
or game compatibility.

## Public package manifest

Put `pukey-mod.json` at each mod root. A ZIP can contain one mod directly, a common
wrapper folder, or several mod roots such as `Mods/First/` and `Mods/Second/`.
Overlapping mod roots, case-colliding paths, symlinks/reparse points, traversal paths,
missing declared files and ambiguous native entrypoints are rejected. Preserve the
actual spelling of paths, including `Scripts/main.lua` and native DLL names.

```json
{
  "schema_version": 1,
  "id": "ExampleLua",
  "name": "Example Lua",
  "version": "1.0.0",
  "description": "Explain what the mod changes.",
  "controls": "F12: toggle",
  "author": "Your name",
  "homepage": "https://example.com/mod",
  "requires": ["A working UE4SS installation for your game"],
  "files": ["Scripts/main.lua", "README.md"],
  "entrypoints": [{"type": "lua", "path": "Scripts/main.lua"}],
  "default_files": ["settings.lua"],
  "settings": [
    {
      "key": "Mode", "label": "Mode", "type": "enum", "default": "idle",
      "options": ["idle", "always"],
      "description": "Choose when this feature runs.",
      "option_descriptions": {"idle": "Run while idle.", "always": "Run continuously."}
    }
  ],
  "configuration": [
    {"file": "settings.lua", "format": "lua", "bindings": {"Mode": {"key": "Mode"}}}
  ]
}
```

`schema_version` must be integer `1`. `id`, `name`, `version`, `description` and
`files` are required. IDs start with a letter, followed by letters, digits, `_` or
`-`, at most 64 characters; they must be unique ignoring case within a source.
`description` is plain text of at most 4096 characters. `controls` defaults to an empty string. `settings` and `default_files` default to
empty arrays. `author` and `homepage` are optional strings up to 4096 characters;
`homepage`, when nonempty, uses HTTP or HTTPS. `requires` is an optional array of
strings, each at most 4096 characters; these are informational prerequisites, not
an automatic dependency installer. Unknown schema features are rejected.

`entrypoints` is a nonempty list of `{ "type": "lua" | "native", "path": "..." }`
objects. Every path must also appear in `files`, with a `.lua` or `.dll` extension
matching its type. When omitted in schema 1, the entrypoint is `Scripts/main.lua`.
A native package normally uses `dlls/main.dll`; UE4SS also supports
`dlls/<mod-folder>.dll`. Match the UE4SS architecture, SDK, C++ runtime and build
configuration when building native code. See the official
[installation layout](https://docs.ue4ss.com/dev/guides/installing-a-c%2B%2B-mod.html)
and [C++ authoring guide](https://docs.ue4ss.com/guides/creating-a-c%2B%2B-mod.html).
The manager does not build DLLs or verify these prerequisites.

## Program files, defaults and personal data

`files` contains all owned program payloads, relative to the mod root. Every listed
file must be present in the package. Do not list activation marker `enabled.txt` or
personal `settings.lua`/`settings.json` as program files. Program updates compare
payload contents as well as the mod version. Increment the version when changing
program behavior.

`default_files` contains initial configuration seeds. They must exist in the
package, be disjoint from program files and may not contain `enabled.txt`. A seed
is copied only if its destination is missing. Existing files remain personal data
and survive program updates and removal. A `configuration` target is also personal
data, whether or not a seed exists. Generated images, videos and extracted game
assets do not belong in program payloads.

Without a public manifest or schema-1 catalogue, basic packages can be inferred
from `Scripts/main.lua` (case insensitive) or a supported native DLL layout. The
manager preserves actual entrypoint spelling and uses the existing mod folder name
as its ID. An inferred folder name must already satisfy the ID rules above; it is
never silently renamed or truncated. For other names, package the mod under a valid
folder with matching runtime paths, or ask its author for an explicit manifest. It
uses version `unversioned`, adds an explanatory description, and supplies no
settings or controls. It recognizes `config.ini`, `config.json`, `settings.json`,
`config.lua`, `settings.lua` and contents of `Config/` as seeds; it excludes
`enabled.txt`. Add a manifest to remove uncertainty about ownership or settings.
No settings are guessed from executable Lua/C++ source.

## Typed settings, help and reset

Each setting needs `key`, `label`, `type` and `default`. Keys are unique identifiers
matching `[A-Za-z_][A-Za-z0-9_]*`. Supported types are:

```json
[
  {"key":"Mode","label":"Mode","type":"enum","default":"idle","options":["idle","always"]},
  {"key":"Speed","label":"Speed","type":"number","default":100,"min":1,"max":1000,"step":1},
  {"key":"ToggleKey","label":"Toggle key","type":"key","default":"F12"},
  {"key":"Visible","label":"Visible","type":"boolean","default":true},
  {"key":"Caption","label":"Caption","type":"string","default":"Hello"}
]
```

Numbers must be finite and within inclusive bounds; booleans are not numbers.
An optional numeric `step` must be positive and finite. Enum options are unique,
nonempty string arrays, and the default must be an option. Key names are F1-F12,
A-Z, HOME, END, PAGE_UP, PAGE_DOWN, INSERT, DELETE, SPACE, and ZERO-NINE. String
values are at most 4096 characters, single line, with no control characters.

A setting's optional `description` is plain text, at most 4096 characters.
`option_descriptions` is an enum-only object mapping existing option values to
plain text explanations with the same limit. HTML/markup tags are rejected. The
help button explains the setting, options, default and numeric range; it supports
keyboard focus and activation. Reset changes that field to its declared default
in the form. Save settings to apply the form, then restart the game.

## Declarative configuration bindings

`configuration` is an optional nonempty array of targets. A target has exactly
`file`, `format` and `bindings`; `format` is `json`, `ini` or `lua`, and must match
the file extension. Paths are relative to the mod root and cannot overlap program
files, entrypoints, activation markers or another configuration target. Each
setting must bind exactly once; unknown setting keys and duplicate or overlapping
destinations are rejected. Do not include the same `settings` declaration in
multiple examples below; choose the format your mod actually consumes.

```json
{"file":"config.json","format":"json","bindings":{
  "Speed":{"path":["camera","speed"]},
  "Visible":{"path":["camera","visible"]}
}}
```

JSON paths are nonempty arrays of nonempty string object keys. Arrays are not
addressable; a path crossing an existing scalar or array is rejected. Missing keys
use declared defaults and can be created on save. Unknown object keys are
preserved. JSON is parsed and serialized as data, with duplicate keys and
nonfinite numbers rejected.

```json
{"file":"config.ini","format":"ini","bindings":{
  "Speed":{"section":"Camera","key":"Speed"},
  "Visible":{"section":"Camera","key":"Visible"}
}}
```

INI bindings identify a section and key, compared without case. Simple `key=value`
and `key:value` records are supported. Existing comments, unrelated lines, newline
style and BOM are preserved. Unsupported or ambiguous syntax, duplicate
sections/keys, interpolation, multiline values and control/line separator injection
are rejected before any write. Values use their declared types rather than
unrestricted string replacement.

```json
{"file":"settings.lua","format":"lua","bindings":{
  "Speed":{"key":"Speed"},
  "Visible":{"key":"Visible"}
}}
```

Lua configuration is restricted to one returned table of scalar literals, for
example `return { Speed = 100, Visible = true }`. String-key syntax such as
`["Speed"] = 100` is also supported. No function calls, expressions, nested tables
or executable statements are evaluated. Saving preserves unknown scalar keys but
may normalize formatting. Unsupported Lua syntax leaves the original intact and
reports an actionable error. All configuration targets are checked before changes
are committed together with backups.

For legacy schema-1 mods without `configuration`, the manager retains its
`settings.json`/generated `settings.lua` behavior. The mod must consume its chosen
file at runtime, validate values and retain sensible defaults if it is missing.
Declaring a settings form alone does not make a mod use those values. Runtime Lua
loading belongs to the mod; the manager never evaluates it during inspection.

## Sources and updates

Every community source has an independent UUID and cache. Mod identity includes
its source; identical IDs from different sources remain separate library entries.
They still target UE4SS's same folder name, so the manager reports a folder
ownership conflict instead of overwriting another source's installed mod.

- A public GitHub repository follows the default branch saved when it was added.
  Each refresh resolves that branch to an immutable commit and downloads its ZIP.
  A later change to the repository's default branch does not silently switch it.
- A release tag follows that tag; a latest-release source follows the latest
  release. The manager selects a compatible ZIP asset. Multiple assets require an
  explicit choice; a renamed/disappeared selected asset offers the current ZIPs.
  Source-only repositories offer release choices when available. The manager never
  compiles them or runs their installers.
- A direct HTTPS ZIP follows its saved URL. HTTP downloads and redirects away from
  HTTPS are rejected; downloads and expanded packages have size limits.
- Local ZIPs/folders remain on their saved snapshot until explicitly replaced.
  Use **Update from ZIP** and reselect a package. Refresh sources does not reread a
  local path automatically.

Refresh retains selected mod IDs. A previously known mod absent upstream remains
in the library as unavailable so installed content can still be managed; it cannot
be installed from that source until it returns. Corrupt downloads, invalid
packages, checksum mismatches and failed registry updates retain the previous
valid cached source. Adding or refreshing a source does not install its mods.

## Official catalogue, images and videos

The official repository uses root `catalog.json` with `schema_version: 1` and a
`mods` array. Each mod object uses the fields above except `schema_version`, which
belongs to the catalogue. Payloads live at `Mods/<ID>/<relative-path>`. Existing
entries that omit `entrypoints` retain `Scripts/main.lua` as their entrypoint.
The official source keeps its fixed identity `official`.

Optional `images` describe personal PNG targets separately from payloads:

```json
[{"file":"portrait.png","label":"Portrait","width":1110,"height":2156,"background":"transparent","scale":100,"top":0}]
```

Use `transparent` or `green` backgrounds, dimensions at most 8192 per side and
16 million total pixels, scale 1-500 percent, and top offset -100 to 100 percent.
The GUI supplies composition controls and backs up prior images when applying.

Set both `video_list` and `video_folder` to enable video targets. `video_list` must
be a declared program text file such as `VIDEOS.txt`; each line identifies an
allowed game-relative MP4 path, for example `Bacchus/Movie/Fam/T_FAM_BOW_A.mp4`.
The current UI supports these `Bacchus/Movie/` paths. Use a separate media folder
such as `Movies`; do not target program/config directories. Personal video files
are not package payloads.

## Validation and examples

From the repository root:

```powershell
python -m manager.validate_mod path/to/mod-folder
python -m manager.validate_mod path/to/package.zip
python -m manager.validate_mod examples/manager-mods/ExampleLua
python -m unittest discover -s tests
```

The CLI prints identified mod IDs, Lua/native types, file counts and setting
counts. Exit `0` means structurally valid; exit `1` means invalid. It never starts
the game, installs mods, runs build scripts or loads mod code. For the official
working tree, `python -m manager.validate_mod .` validates its declared catalogue.

See [the synthetic templates](../examples/manager-mods/README.md). The Lua template
is complete. The native template contains source and a manifest; its DLL is
intentionally absent, so validation fails until a matching build is staged.
Test installation, settings, updates, disable and removal with a disposable fake
game folder first. Runtime game testing is separate; no template or validation
result guarantees behavior in the actual game. Never add diagnostic probes or
these synthetic templates to the public playable-mod catalogue.
