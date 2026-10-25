# Native UI decoder licenses

The UI decoder wraps **oozextract 0.5.6**, an independent open-source Oodle
decompressor declared under the MIT license in its published Cargo manifest:
<https://github.com/lvlvllvlvllvlvl/oozextract/tree/v0.5.6>.

Its crate archive has no separate license file. `licenses/oozextract-MIT.txt`
retains the standard MIT terms and identifies the upstream contributors.
The source manifest and complete registry dependency checksums are retained in
Cargo.lock. No proprietary Oodle implementation or game asset is distributed.

`valuable` 0.1.1 also omits its MIT license file from its crate archive. The
build retains the upstream license from the matching repository tag:
<https://github.com/tokio-rs/valuable/blob/v0.1.1/LICENSE>.

The build copies each resolved registry crate's license, notice, and copyright
files into the bundle's `licenses/UI-decoder` directory. Individual dependency
versions and declared licenses are listed beside those files in SOURCE.txt.

Rust's standard library is distributed under the MIT and Apache-2.0 licenses:
<https://www.rust-lang.org/policies/licenses>. The helper statically links Rust
code and uses the operating system's normal runtime libraries.
