---
name: PUKEY Mod Manager
description: A clear native desktop workbench for selecting and configuring mods.
colors:
  primary: "#e8af42"
  primary-hover: "#efbf65"
  primary-border: "#be882b"
  focus: "#8a5c0d"
  workspace: "#ffffff"
  warm-surface: "#f4f3ef"
  ink: "#252620"
  secondary-text: "#595c53"
  sidebar-muted: "#b8bdb0"
  sidebar-hover: "#393b33"
  border: "#d9dcd3"
  control-hover: "#eeeee7"
  control-pressed: "#dfdfd6"
  disabled-text: "#73766d"
  disabled-background: "#e6e6df"
  disabled-border: "#d0d3c8"
  icon-surface: "#f5e9cf"
  success: "#31633e"
  error: "#a52b2b"
  progress-track: "#dedfd6"
  progress-fill: "#a76d0f"
  scrollbar-thumb: "#a7ad9f"
typography:
  title: {fontFamily: "Qt application font", fontSize: "22pt", fontWeight: 600}
  brand: {fontFamily: "Qt application font", fontSize: "14pt", fontWeight: 600}
  body: {fontFamily: "Qt application font", fontSize: "10.5pt"}
  label: {fontFamily: "Qt application font", fontSize: "10.5pt", fontWeight: 600}
  supporting: {fontFamily: "Qt application font", fontSize: "9.5pt"}
  small: {fontFamily: "Qt application font", fontSize: "9pt"}
rounded: {indicator: "4px", field: "5px", button: "6px", panel: "8px", brand: "9px", icon: "10px"}
spacing: {xs: "4px", sm: "8px", md: "12px", lg: "18px", xl: "22px", frame: "28px"}
components:
  button-primary: {backgroundColor: "{colors.primary}", textColor: "{colors.ink}", rounded: "{rounded.button}", padding: "5px 12px"}
  button-primary-hover: {backgroundColor: "{colors.primary-hover}"}
  button-secondary: {backgroundColor: "{colors.workspace}", textColor: "{colors.ink}", rounded: "{rounded.button}", padding: "5px 12px"}
  field: {backgroundColor: "{colors.workspace}", textColor: "{colors.ink}", rounded: "{rounded.field}", padding: "4px 9px"}
  navigation-selected: {backgroundColor: "{colors.primary}", textColor: "{colors.ink}", rounded: "{rounded.panel}"}
  game-panel: {backgroundColor: "{colors.warm-surface}", rounded: "{rounded.panel}", padding: "11px 14px 12px"}
  tab: {textColor: "{colors.secondary-text}", padding: "12px 14px"}
---

# Design System: PUKEY Mod Manager

## Overview

**Creative North Star: "The clear desktop workbench"**

A charcoal library rail anchors a white workspace. Warm amber gives selection and available primary actions a clear visual identity; compact, labelled native controls keep attention on the selected mod and its actual state. English copy uses familiar desktop verbs.

**Key Characteristics:**
- Persistent charcoal navigation with amber selection.
- A compact game panel and selected-mod actions above scrolling content.
- Separate preferences, keybindings, and capability-dependent media preparation.
- Visible keyboard focus and persistent save/apply feedback. This records PySide6/Qt Widgets in `manager/theme.py`, `manager/widgets.py`, and `manager/gui.py`. Dimensions are Qt logical pixels; fonts use points. Native desktop details live in the sidecar extensions.

## Colors

**Primary.** Warm amber marks selected navigation, installation or update actions, and save/apply buttons. Deeper amber identifies focus and selected tab underlines. Prominence follows the available task; reinstall stays neutral when no update is available.

**Neutral.** Charcoal ink doubles as the sidebar surface. White is the workspace and control surface; warm gray separates the game panel and preview canvas. Muted sidebar text also supplies control borders. Green accompanies enabled and loader-ready text; red accompanies actionable errors.

**The Visible State Rule.** Pair color with explicit text, selection, focus, or control state.

## Typography

Use the Qt application font. The selected-mod title is the strongest heading; the smaller brand, semibold labels, and supporting status text establish the remaining hierarchy. Navigation names use semibold body type and small state text. The empty-state heading is 18pt. Preserve platform font metrics, wrapping for paths/messages, and plain-text rendering. Offscreen font fallbacks are test support, not a shipped font identity.

## Layout

Initial window: 1120 × 800; minimum: 900 × 640. Visual checks cover 1120 × 800 and 1024 × 768. The fixed sidebar is 236 wide, with margins 12/26/12/18 (left/top/right/bottom). Workspace margins are 28/24/28/12 with an 18 gap. No splitter or mobile layout is implemented. The compact game panel precedes the selected-mod header, description, and tabs. Settings and Keybindings use separated rows: minimum height 64, vertical padding 11, label/control gap 20, control width 200. Forms scroll; the save/apply footer, restart guidance, progress, and operation status stay outside scrolling content. Images place a 270–310-wide options column beside an expanding preview, separated by 22. The preview minimum is 160 × 220, with a 300 × 260 size hint. Videos use a single-column import layout. Empty library guidance replaces mod details until a selection exists.

**The Persistent Action Rule.** Keep saving and applying a prepared image accessible while content scrolls.

## Elevation & Depth

Flat surfaces, tonal separation, and thin dividers provide depth. No custom shadows, gradients, or transitions are defined. Qt's indeterminate progress animation communicates active work.

## Shapes

Small curves distinguish fields, buttons, panels, and icon tiles using the recorded radii. Standard borders are one pixel; button and field focus uses a two-pixel deep amber border. Sidebar actions use amber focus; navigation uses an inset dashed focus outline. Tabs use a two-pixel underline rather than filled pills.

## Components

Buttons retain Qt keyboard activation, explicit disabled states, and native tooltips. Activation is a checkable Enabled/Disabled button. Guide and removal actions use named line icons with accessible names. Fields use 28-pixel QSS minimum height before padding/border; image controls use 24 with compact padding. Boolean settings show On/Off beside the amber SVG check indicator. Combo and spin arrows use shipped SVG assets. The custom navigation delegate paints 76-high rows with icons, names, and installation states; amber selection and charcoal hover retain keyboard selection. Settings, Keybindings, and media tabs use a thin shared divider. PreviewCanvas scales images without distortion and paints a 12-pixel white/gray checkerboard beneath transparency, with a labelled empty state. Changed preparation inputs invalidate the preview. Save/apply availability follows actual dirty, installed, and preview state.

## Do's and Don'ts

- **Do** reuse the source-backed Qt tokens, line-icon family, and native keyboard behavior.
- **Do** keep installation, enabled, unsaved, and error states explicit in text.
- **Do** preserve readable paths, labelled controls, persistent actions, and visible focus at checked desktop sizes.
- **Don't** describe web breakpoints, iOS components, or HTML replicas as implemented native UI.
- **Don't** infer gameplay or Linux runtime compatibility from visual and offscreen checks.
