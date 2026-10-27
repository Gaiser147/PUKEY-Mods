---
name: PUKEY Mod Manager
description: Native dialogue sheets for selecting, configuring, and preparing PUKEY mods.
colors:
  mint: "#02e5a2"
  pink: "#ff0060"
  workspace: "#111012"
  ink-on-mint: "#101113"
  text: "#f0ece8"
  muted: "#b5adb5"
  panel: "#211b24"
  control: "#080709"
  button: "#18151a"
  hover: "#302630"
  pressed: "#422135"
  border: "#766a78"
  divider: "#514452"
  disabled-text: "#a69aa6"
  disabled-surface: "#29232b"
  disabled-field: "#201a22"
  preview: "#141216"
typography:
  brand: {fontFamily: "Amarante", fontSize: "28pt"}
  title: {fontFamily: "Amarante", fontSize: "27pt"}
  empty-title: {fontFamily: "Amarante", fontSize: "22pt"}
  key-heading: {fontFamily: "Amarante", fontSize: "16pt"}
  navigation: {fontFamily: "Oswald", fontSize: "15pt"}
  accent: {fontFamily: "Oswald", fontSize: "13pt"}
  key: {fontFamily: "Oswald", fontSize: "12pt"}
  body: {fontFamily: "Segoe UI, DejaVu Sans", fontSize: "10.5pt"}
  supporting: {fontFamily: "Segoe UI, DejaVu Sans", fontSize: "9.5pt"}
  small: {fontFamily: "Segoe UI, DejaVu Sans", fontSize: "9pt"}
rounded: {field: "2px", button: "3px"}
spacing: {xs: "4px", sm: "8px", md: "10px", row: "12px", sheet: "18px", content: "22px", frame: "24px"}
components:
  button-secondary: {backgroundColor: "{colors.button}", textColor: "{colors.text}", rounded: "{rounded.button}", padding: "4px 11px"}
  button-hover: {backgroundColor: "{colors.hover}"}
  button-pressed: {backgroundColor: "{colors.pressed}"}
  button-primary: {textColor: "{colors.text}", typography: "{typography.accent}", padding: "4px 17px"}
  button-disabled: {backgroundColor: "{colors.disabled-surface}", textColor: "{colors.disabled-text}"}
  field: {backgroundColor: "{colors.control}", textColor: "{colors.text}", rounded: "{rounded.field}", padding: "4px 9px"}
  navigation-selected: {textColor: "{colors.ink-on-mint}", typography: "{typography.navigation}"}
  game-panel: {backgroundColor: "{colors.panel}", rounded: "{rounded.button}", padding: "7px 12px 8px"}
  tab: {textColor: "{colors.muted}", typography: "{typography.accent}", padding: "7px 12px"}
---

# Design System: PUKEY Mod Manager

## Overview

**Creative North Star: "PUKEY's dialogue desk"**

The user-selected Design C brings PUKEY's dialogue language into an editable native desktop workbench: smoky black sheets, a mint selection ribbon, pink primary actions, and off-white ornamental headings. Neutral body type keeps settings, paths, and installation state readable. The approved Qt study is the visual authority; current implementation is recorded in `manager/theme.py`, `manager/widgets.py`, and `manager/gui.py`.

The game-derived identity activates only after the selected supported game supplies its seven verified images. No original PNG is bundled. Extraction runs in a worker into a versioned per-install cache; missing, removed, damaged or unsupported installations use plain native panels, a text wordmark and flat native selection/actions. The layout, editable controls and separately licensed fonts remain available. Cache images are never treated as installation proof.

**Key Characteristics:**
- Horizontal mod navigation above textured dialogue sheets.
- Independently scrolling settings and editable keybindings, sharing one save action.
- Persistent image and video actions, explicit installation state, and visible keyboard focus.
- Native PySide6/Qt Widgets for Windows and Linux; English interface copy.

## Colors

**Primary.** Mint identifies the selected ribbon, key values, enabled state, keyboard focus, and selected tab underline. Pink appears through the primary-action artwork and progress fill; it is an action accent rather than a replacement for the mint selection language.

**Neutral.** Near-black workspace and input wells support off-white text. Smoke textures distinguish the main dialogue sheet and narrower shortcut sheet. Muted lilac-gray supports status and explanatory text; brighter borders identify controls without competing with the textured edges. Native dialogs and combo popups use opaque dark surfaces.

**The Visible State Rule.** Pair color with explicit text, selection, focus, or control state.

## Typography

Amarante supplies the brand, selected-mod title, empty-state heading, and key-sheet heading. Oswald supplies horizontal navigation, tabs, section labels, primary actions, and mint key values. Segoe UI, falling back to DejaVu Sans, supplies body text and ordinary controls. Both display fonts are bundled OFL fonts; do not use them for long descriptions or paths. Sizes in the frontmatter are Qt points, not CSS pixels. Preserve plain-text labels and wrapping for descriptions and messages.

## Layout

Initial window is 1280 × 860; minimum is 900 × 640. Final native captures cover 1280 × 860 and 1024 × 768. Qt logical pixels govern geometry. Outer margins are 24/14/24/10 (left/top/right/bottom), with a 10 gap. A masthead holds the game logo, brand, catalogue controls, catalogue/log/version links, and collapsible game-folder setup. Below 800 high the logo shrinks from 188 × 108 to 112 × 64 so settings keep the height. One bottom bar carries operation status on the left and the persistent actions on the right. Errors show a pink alert icon and state their own next step; background work (detection, artwork, saved sources) never replaces an error until the user starts another action. The horizontal catalogue is 68 high, scrolls on overflow, and remains keyboard selectable.

The expanding main sheet sits beside a fixed 280-wide key sheet with an 18 gap; main-sheet margins are 22/18/22/17 and key-sheet margins 18/16/18/16. Settings rows have a 56 minimum height, 8 vertical padding, 12 control gap, and 180-wide fields. Each has an info control by its label and a reset control by its value. Key rows have an 84 minimum height with label/help above a 116-wide value/reset row. Key values show keyboard names (Page Up, 0) while saving the UE4SS code. When a key is also bound in the same mod or by another installed, enabled mod, the field gets a pink border and a pink line naming the other binding; saving stays allowed. Hide the key sheet when a mod has no keys or media is active. Images use a 270–310-wide options column, 22 gap, and expanding preview; videos use one column. There are no web breakpoints, mobile mode, or splitter.

**The Persistent Action Rule.** Keep saving, image preview/apply/restore, and video import/restore accessible outside scrolling content. Show the actions appropriate to the active capability and actual state.

## Elevation & Depth

Depth comes from smoke, irregular sheet edges, opaque input wells, and thin dividers. There are no custom shadows or decorative transitions. DialoguePanel paints nine image regions, preserving corners with 48-pixel source edges mapped to 16-pixel destination insets. Qt's indeterminate progress animation communicates work.

## Shapes

Sheets and selected ribbons inherit their irregular silhouettes from artwork. Native controls use small curves from the frontmatter, one-pixel borders, and two-pixel mint focus borders. Tabs use a two-pixel mint underline. Navigation keyboard focus is an inset dashed outline, dark on the selected ribbon and mint otherwise. Do not replace the sheet silhouette with generic rounded cards.

## Components

Primary QPushButtons use `button-pink.png` as a six-pixel border image (source slices 18/28/18/28), Oswald type, and 165 minimum width. Hover adds a dark pink backing; disabled actions remove the image and use muted text, fill, and border. Secondary controls retain native keyboard activation, hover/pressed states, tooltips, and explicit enabled/disabled text. Checkboxes pair On/Off text with the mint SVG indicator.

ModNavigation uses Oswald names with a smaller native-body status line. Cells stay 224 wide with a 57 height hint; wheel and trackpad input scroll horizontally without changing selection. Enabled/Disabled/Not installed is always explicit, with update state additional. Mint textured selection, faint hover and elision remain. The right-hand shortcut sheet contains real editable QComboBoxes. Combo popups and QMessageBox/QDialog surfaces remain opaque and dark. PreviewCanvas preserves aspect ratio and invalidates on changed inputs; apply requires a current preview. The bottom bar shares saving across settings and keys, shows "Unsaved changes" beside it only while edits are pending, and retains media actions while their content scrolls. Reset icons are bright when a field differs from its default and recessed to the divider color otherwise. The key-sheet heading draws the plaque in three slices so the scroll ornaments keep their proportions. The video picker groups clips by folder, marks replaced clips with the mint check icon, and states the selected clip's original format.

Info and reset are 26×28 authored line-icon tool buttons with keyboard focus. Hover/focus explains a setting; click opens a dark, bounded scrollable plain-text popup that closes on Escape or an outside click. Reset changes the form only; saving remains explicit. Add mod opens a focused import dialog with source inspection, release choices, package checkboxes and an explicit add action. External entries show origin and configuration/source access. Logs opens a separate modeless dark reader; native typography, plain text and persistent controls carry the same workbench language.

## Do's and Don'ts

- **Do** reuse the native Qt tokens, textured sheets, mint navigation, and Amarante/Oswald hierarchy.
- **Do** preserve explicit state, labelled editable controls, visible focus, and persistent actions at checked desktop sizes.
- **Do** retain extraction metadata in `manager/assets/game-ui-layout.json` and font licenses in `manager/assets/fonts/`.
- **Don't** describe HTML replicas, iOS controls, or web breakpoints as implemented native UI.
- **Don't** infer Linux runtime or gameplay compatibility from visual and offscreen checks.
- **Don't** ship original game artwork. Read it only from a present supported installation; a local cache alone must not enable it.
