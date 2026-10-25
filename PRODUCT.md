# Product

<!-- impeccable:product-schema 1 -->

## Platform

Native desktop: Windows and Linux (Proton game installations).

## Stack

Delegated by the user: Python backend, Qt/PySide6 desktop UI, Pillow image handling, platform-specific PyInstaller bundles. A downloaded bundle must not require a separate Python installation.

## Users and purpose

Players installing PUKEY demo mods who want selection, updates and configuration without Git commands, manual file copying or Lua editing. The maintainer should be able to publish additional ordinary mods through a repository catalogue without rebuilding the manager.

## Capabilities and constraints

Detect Steam libraries or select a game folder; fetch the fixed public GitHub catalogue; install, update, enable, disable and remove selected mods; configure supported settings; prepare FamSwap images and import MovieSwap videos. Preserve user files and show actionable errors. UE4SS is obtained separately from its official release. Linux runtime compatibility is unverified.

## Voice and evidence

Use clear English in the distributed app, matching existing FamSwap distribution text. The conversation with the maintainer is German. Existing Lua mods and their documented controls are product truth; do not invent supported game versions or success metrics.

## Principles

Show actual installation status. Separate settings from code. Preserve personal data by default. Keep every main action accessible by keyboard. Make failures recoverable and state what the user can do next.

## Interface artwork

The user selected the game-derived dialogue design C. Original game artwork is never bundled or committed: read seven verified UI textures from the selected local installation into a private cache. Show a plain native interface when no supported game is present, while extraction runs, or when extraction fails. A cache alone never enables the game artwork. Fonts sourced separately under OFL may be bundled.
