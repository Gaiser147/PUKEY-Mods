# Example Lua

Synthetic authoring template; it prints a greeting and does not change gameplay.
Rename the ID, folder and installed settings path together when adapting it.
The `settings.lua` seed is personal data after installation. Update the manifest's
`settings` defaults when changing the initial values; existing users keep theirs.

From the repository root:

```powershell
python -m manager.validate_mod examples/manager-mods/ExampleLua
```

The settings form edits a restricted literal Lua table. This template itself reads
that table during normal UE4SS startup. Package validation never executes Lua.
Validation does not prove compatibility with any game or UE4SS build.
