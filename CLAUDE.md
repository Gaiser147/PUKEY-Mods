# Project guidance

Read [AGENTS.md](AGENTS.md) for repository structure, commands, style, and runtime safety rules.

- [README.md](README.md): mod overview and user entry point.
- [docs/installation.md](docs/installation.md): game-relative installation paths and activation.
- [docs/development.md](docs/development.md): source deployment, packaging, and verification.
- [docs/project-notes.md](docs/project-notes.md): engine findings, object lifetimes, threading, and known crash paths.
- [diagnostics/README.md](diagnostics/README.md): default-disabled diagnostic mods and key conflicts.

Sources are in `Mods/` and `diagnostics/`. Installed copies live separately under the game's `Binaries/Win64/ue4ss/Mods/`; do not change the game installation merely to reorganize this repository. Preserve ignored `local/` research and any existing ignored `FModel/` installation.
