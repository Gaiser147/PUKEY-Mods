# Packaged UI decoder

`python tools/build_ui_decoder.py` runs Rust tests and builds this cdylib with
`cargo build --release --locked`. Build hosts need the stable Rust toolchain
and the platform linker (MSVC on Windows, GCC/Clang on Linux). Normal app users
need neither those tools nor any proprietary Oodle DLL.

The generated helper goes into `manager/assets/native`; do not commit binaries
or generated dependency licenses. `tools/build_manager.py` includes the helper
as a PyInstaller binary and copies its license notices into the final bundle.
Windows uses a static VC runtime. Linux builds target Ubuntu 22.04 or newer.

The C ABI reports its version through `pukey_ui_decoder_abi()`. The function
`pukey_ui_decompress(input, input_len, output, output_len, written)` accepts
caller-owned buffers, caps each buffer at 64 MiB, and reports success only if
the decoder writes exactly output_len bytes. It contains Rust panics and
rejects empty, oversized, null, or overlapping buffers. Callers must supply
valid non-overlapping allocations; discard output whenever status is nonzero.

Tests use generated uncompressed Oodle block framing and repeated synthetic
bytes. No game-derived fixture or artwork is stored here. Set
`PUKEY_REQUIRE_NATIVE_DECODER=1` to make Python tests fail if the helper has not
been built; CI sets this after compiling it on both supported systems.
