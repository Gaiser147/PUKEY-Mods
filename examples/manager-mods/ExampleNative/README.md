# Example Native

This is a synthetic **source template**, not an installable mod. No DLL or SDK is
included. Validation intentionally reports `Missing declared payload` until you
build and stage a real `dlls/main.dll` beside this manifest. Never use a renamed
text file as a substitute for the DLL.

Use a Windows x64 C++ toolchain and the SDK matching the installed UE4SS build.
Add this directory from a UE4SS build that defines its `UE4SS` CMake target, compile
with matching build configuration/runtime settings, then copy the resulting
`main.dll` into `dlls/` in your own staging directory. Package `pukey-mod.json`,
`README.md` and `dlls/main.dll`; source and CMake files are authoring materials.

The export shape follows the official [UE4SS C++ mod guide](https://docs.ue4ss.com/guides/creating-a-c%2B%2B-mod.html).
UE4SS documents [DLL layout and naming](https://docs.ue4ss.com/dev/guides/installing-a-c%2B%2B-mod.html).
The manager neither compiles nor loads native code during import/validation.
A valid manifest does not establish that a DLL is safe, ABI compatible, functional,
or supported by this game. Test your build separately in a controlled setup.
