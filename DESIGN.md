---
name: PUKEY Mod Manager
description: A clear native desktop workspace for installing and configuring mods.
colors:
  primary: "#e8af42"
  primary-hover: "#efbf65"
  primary-border: "#be882b"
  focus: "#8a5c0d"
  background: "#f4f3ef"
  panel: "#ffffff"
  text: "#252620"
  secondary-text: "#595c53"
  border: "#d9dcd3"
  control-border: "#b8bdb0"
  selection: "#f5e9cf"
  control-hover: "#eeeee7"
  control-pressed: "#dfdfd6"
  navigation-hover: "#e9eae2"
  disabled-text: "#73766d"
  disabled-background: "#e6e6df"
  disabled-border: "#d0d3c8"
  error: "#a52b2b"
  progress-track: "#dedfd6"
  progress-fill: "#a76d0f"
  scrollbar-track: "#efefe9"
  scrollbar-thumb: "#a7ad9f"
typography:
  headline:
    fontFamily: "Qt application font"
    fontSize: "20pt"
    fontWeight: 600
  title:
    fontFamily: "Qt application font"
    fontSize: "22pt"
    fontWeight: 600
  body:
    fontFamily: "Qt application font"
    fontSize: "10pt"
  label:
    fontFamily: "Qt application font"
    fontSize: "10pt"
    fontWeight: 600
  supporting:
    fontFamily: "Qt application font"
    fontSize: "9pt"
rounded:
  field: "4px"
  control: "5px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  frame: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "5px 12px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-secondary:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "5px 12px"
  button-secondary-hover:
    backgroundColor: "{colors.control-hover}"
  button-disabled:
    backgroundColor: "{colors.disabled-background}"
    textColor: "{colors.disabled-text}"
  field:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.field}"
    padding: "3px 8px"
  navigation-item-selected:
    backgroundColor: "{colors.selection}"
    textColor: "{colors.text}"
    rounded: "{rounded.control}"
    padding: "16px 12px"
  scroll-panel:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.control}"
  tab:
    backgroundColor: "{colors.navigation-hover}"
    padding: "9px 16px"
  tab-selected:
    backgroundColor: "{colors.panel}"
---

# Design System: PUKEY Mod Manager

## Overview

**Creative North Star: "The clear desktop workbench"**

A quiet, practical workspace keeps attention on the selected mod, its real installation state, and the next available action. Warm amber identifies actions and selection; pale neutral surfaces support long file paths and labelled settings. English copy uses familiar desktop verbs.

This document records the implemented PySide6/Qt Widgets interface in `manager/gui.py`. The application runs on Windows and Linux desktops and retains native Qt keyboard, dialog, and control behavior. The YAML tokens describe existing QSS values; pixels are Qt logical pixels and typography uses points. The sidecar records native geometry and QSS details that the frontmatter cannot express.

**Key Characteristics:**

- Flat light surfaces with warm amber emphasis.
- A persistent game location above mod navigation and details.
- Native labelled controls, visible focus, and explicit state text.
- Scrolling settings and media with persistent main actions and feedback.

## Colors

Amber supplies the single action accent, supported by white panels and warm gray neutrals. Token values in the frontmatter are authoritative.

### Primary

- **Warm amber** (`primary`, `primary-hover`, `primary-border`) marks installation actions and the footer image-apply action. The pale `selection` fill and amber border identify the selected mod.
- **Deep amber** (`focus`) gives keyboard focus a visible outline. `progress-fill` uses a darker amber against its neutral track.

### Neutral

- **Warm workspace** (`background`) surrounds the white settings and media panels.
- **Ink** (`text`) carries headings, labels, and button text. **Secondary gray** (`secondary-text`) carries controls, restart guidance, and supporting status.
- `control-border` outlines interactive fields and buttons; `border` separates panes and frames scrollable content. Distinct hover, pressed, disabled, tab, and scrollbar colors preserve their implemented state roles.

Error feedback uses `error` alongside readable explanatory text. Installed and enabled states are conveyed in text and native checkboxes; there is no separate success-color treatment in the current UI.

**The Visible State Rule.** Pair color with text, selection, focus, or a native control state so the user can identify what changed.

## Typography

Use the Qt application font, which follows the desktop's configured font. No custom font ships with the application. The offscreen screenshot fallback loads Segoe UI on Windows or DejaVu Sans on Linux only when Qt has no font database; that fallback is not a new brand font.

- **Headline:** the application title uses the headline role.
- **Title:** the selected mod uses the title role.
- **Body:** descriptions, field labels, controls, and buttons use the body role.
- **Label:** section labels and primary actions use semibold emphasis.
- **Supporting:** controls summaries, source state, restart guidance, and the footer use the smaller secondary role.

Qt supplies line metrics and native number formatting. Descriptions and status labels wrap. The application title and version footer stay on one line. Preserve plain-text rendering for user-visible paths and messages.

## Layout

The initial window is 1120 × 800 logical pixels; the minimum is 900 × 640. The documented screenshot checks cover 1120 × 800 and 1024 × 768. The desktop layout keeps its two panes at these sizes, using scrollable content rather than switching to a mobile navigation pattern.

The outer layout uses horizontal margins of 24, top 20, bottom 16, and a vertical gap of 16. The header places the application title left and catalogue actions right. Game location, folder selection, and loader status occupy the next full-width block, with an 8-pixel internal gap.

A horizontal splitter starts with a 235-pixel navigation pane and gives remaining space to details. The mod list has a 200-pixel minimum width. Details use a 20-pixel left inset and 12-pixel vertical gaps. The selected title, description, controls, and install/enable/remove/guide actions remain above the tabbed scroll area.

Settings use a `QFormLayout` with margins of 16 horizontally and 20 vertically, plus 16 between rows. Expandable fields use Qt's `ExpandingFieldsGrow` policy. The media layout uses 16-pixel margins and 12-pixel gaps. The restart/save or image-apply footer sits outside scrolling content. Progress, a selectable status message, and version/source navigation follow below the splitter.

**The Persistent Action Rule.** Keep saving and applying a prepared image accessible when settings or media content scrolls.

## Elevation & Depth

The application defines no shadows or gradients. White content panels, neutral workspace color, thin borders, and selection fill provide separation. Native menus and dialogs retain their platform's rendering. There are no animated transitions; the slim indeterminate Qt progress bar communicates work in progress.

## Shapes

Controls and content panels have small, consistent curves. Fields and scrollbar thumbs use the field radius; buttons, mod rows, and scroll panels use the control radius. Borders are generally one pixel. Keyboard focus on buttons, line edits, combo boxes, and numeric fields changes to a two-pixel deep amber border. Tabs are flat adjoining shapes with a small gap, rather than rounded pills.

## Components

### Buttons

Primary buttons use warm amber, dark text, semibold weight, and the shared button padding. Secondary buttons use white with a muted border. Secondary hover and pressed states use neutral fills; primary hover uses lighter amber. Disabled buttons use the disabled palette. The QSS minimum height is 24 pixels before padding and border contribution. Preserve native keyboard activation and visible focus.

### Inputs / Fields

`QLineEdit`, `QComboBox`, and `QDoubleSpinBox` share white fill, a subtle border, field radius, and field padding. Their QSS minimum height is 26 pixels before padding and border contribution. Form labels have buddies and accessible names. Key choices and enums use combo boxes; numbers use bounded spin boxes; booleans use native checkboxes.

### Navigation

Each mod list row shows the name and current state with generous vertical padding. The active row uses pale amber with an amber border; hovering an unselected row uses a neutral fill. Retain the keyboard behavior of `QListWidget`. A thin splitter separates navigation from details.

### Tabs / Containers

The white scroll panel contains settings or media. The selected tab matches that panel and uses semibold text; inactive tabs use a neutral fill. Add an Images or Videos tab only when the selected mod declares the corresponding capability.

### Media Preview

Image preparation uses native target selection, source browsing, size and offset spin boxes, optional green removal, and an explicit Preview action. The image area is centered with a minimum height of 120 pixels. A valid prepared image enables applying it; changing preparation inputs invalidates that preview. The footer repeats the apply action so it stays accessible when preview controls scroll. Video import uses a bounded native combo box for game-relative paths.

### Status / Progress

Keep a persistent, selectable status message with a minimum height of 38 pixels. Errors turn this text red and explain recovery. The four-pixel progress bar appears while a worker is active, and controls reflect unavailable actions. Unsaved settings and restart requirements remain explicit near Save settings. Native confirmation dialogs explain removal and restoration.

## Do's and Don'ts

### Do:

- **Do** use the recorded Qt tokens and native widget behavior when extending the manager.
- **Do** keep paths, setting labels, installation state, and recovery text readable at the documented desktop sizes.
- **Do** preserve visible focus, label associations, accessible names, and keyboard shortcuts.
- **Do** keep progress, restart guidance, and save/apply actions outside scrolling form content.

### Don't:

- **Don't** add decorative cards, gradients, or invented status metrics to this practical workspace.
- **Don't** substitute color alone for installed, enabled, busy, error, or unsaved state text.
- **Don't** introduce web breakpoints, mobile navigation, or fixed cross-platform font assumptions into the native desktop specification.
- **Don't** describe unimplemented colors, shadows, animations, or component states as existing design tokens.
