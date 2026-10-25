# Mod author templates

- `ExampleLua/` is a complete synthetic Lua package with typed settings and a
  literal Lua configuration seed. It only prints a greeting at UE4SS startup.
- `ExampleNative/` contains a source template and packaging manifest. Its declared
  DLL is deliberately absent; build with a matching UE4SS SDK before validation.

These folders are not registered in the official playable-mod catalogue and are
not automatically installed. See [the complete contract](../../docs/mod-catalogue.md).
