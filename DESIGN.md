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
  text-soft: "#d9d2d6"
  sheet: "#1a161c"
  rim: "#3a313c"
  ghost: "#2b2331"
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
  web-display: {fontFamily: "Amarante, Georgia, serif", fontSize: "clamp(48px, 6vw, 80px)", fontWeight: 400, lineHeight: 1.02}
  web-headline: {fontFamily: "Amarante, Georgia, serif", fontSize: "clamp(34px, 3.6vw, 48px)", fontWeight: 400, lineHeight: 1.1}
  web-wordmark: {fontFamily: "Amarante, Georgia, serif", fontSize: "30px", lineHeight: 1}
  web-title: {fontFamily: "Oswald, Arial Narrow, sans-serif", fontSize: "21px", fontWeight: 400, lineHeight: 1.25}
  web-label: {fontFamily: "Oswald, Arial Narrow, sans-serif", fontSize: "16px", fontWeight: 400, lineHeight: 1, letterSpacing: "0.01em"}
  web-action: {fontFamily: "Oswald, Arial Narrow, sans-serif", fontSize: "22px", fontWeight: 700, lineHeight: 1.1, letterSpacing: "0.02em"}
  web-body: {fontFamily: "Segoe UI, system-ui, -apple-system, DejaVu Sans, sans-serif", fontSize: "16px", fontWeight: 400, lineHeight: 1.6}
  web-reading: {fontFamily: "Segoe UI, system-ui, -apple-system, DejaVu Sans, sans-serif", fontSize: "16.5px", fontWeight: 400, lineHeight: 1.7}
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
  web-button-primary: {textColor: "#ffffff", typography: "{typography.web-action}", padding: "12px 36px 13px 30px", height: "56px"}
  web-button-secondary: {backgroundColor: "{colors.button}", textColor: "{colors.text}", rounded: "{rounded.button}", padding: "10px 20px", height: "46px"}
  web-button-secondary-hover: {backgroundColor: "{colors.hover}"}
  web-button-secondary-pressed: {backgroundColor: "{colors.pressed}"}
  web-key-chip: {backgroundColor: "{colors.control}", textColor: "{colors.mint}", typography: "{typography.web-label}", rounded: "{rounded.button}", padding: "0 9px", height: "34px"}
  web-key-chip-active: {backgroundColor: "{colors.mint}", textColor: "{colors.ink-on-mint}"}
  web-ribbon: {backgroundColor: "{colors.mint}", textColor: "{colors.ink-on-mint}", padding: "7px 28px 9px 24px"}
  web-sheet: {backgroundColor: "{colors.sheet}", rounded: "{rounded.button}"}
  web-nav-link: {textColor: "{colors.muted}", typography: "{typography.web-label}", padding: "8px 0"}
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
- GitHub Pages web surface: authored SVG smoke, grain, mint ribbon and pink stroke; no game artwork.

### Web surface (GitHub Pages)

The Jekyll site carries the same desk onto the web without game artwork: a grained near-black ground, authored smoke sheets with an inset rim, a mint torn-edge ribbon for selection and real state, and one pink torn-edge stroke for the primary download. Implementation is `assets/site.css` (tokens on `:root`), `_layouts/base.html`, `_layouts/default.html` (guides, read mode), `index.html` (release page) and `assets/site.js`. Every material is an authored SVG in `assets/img/` (smoke, grain, ribbon, stroke, stroke-hover); Amarante and Oswald are self-hosted WOFF2 subsets in `assets/fonts/` with their OFL texts. The web is a separate implementation of the world, not a replica of native widgets.

## Colors

**Primary.** Mint identifies the selected ribbon, key values, enabled state, keyboard focus, and selected tab underline. Pink appears through the primary-action artwork and progress fill; it is an action accent rather than a replacement for the mint selection language.

**Neutral.** Near-black workspace and input wells support off-white text. Smoke textures distinguish the main dialogue sheet and narrower shortcut sheet. Muted lilac-gray supports status and explanatory text; brighter borders identify controls without competing with the textured edges. Native dialogs and combo popups use opaque dark surfaces.

**The Visible State Rule.** Pair color with explicit text, selection, focus, or control state.

### Web surface

The site reuses the native palette under web names: `--ground` is workspace, `--well` is control, and mint, pink, text, muted, button, hover, border, divider and panel keep their native values. Four web-only neutrals extend it. Soft dialogue text (text-soft) carries pitch lines, ledes, steps and long reading so off-white stays reserved for headings, strong text and links. Sheet plum-black (sheet) is the flat colour under the smoke texture. Rim plum (rim) is the one-pixel inset edge that closes a sheet. Ghost plum (ghost) is reserved for the decorative, `aria-hidden` release numeral and must never carry readable text. Pink exists on the web only inside the primary stroke artwork; hover darkens the stroke fill to #d90051. Faint inner rules between ledger columns, table rows and inline code use the web token `--rule` (#2a2330); secondary buttons press to the native pressed colour through `--pressed`.

**The One Pink Stroke Rule.** Each page shows at most one pink primary action; every other action is a dark secondary button.

## Typography

Amarante supplies the brand, selected-mod title, empty-state heading, and key-sheet heading. Oswald supplies horizontal navigation, tabs, section labels, primary actions, and mint key values. Segoe UI, falling back to DejaVu Sans, supplies body text and ordinary controls. Both display fonts are bundled OFL fonts; do not use them for long descriptions or paths. Sizes in the frontmatter are Qt points, not CSS pixels. Preserve plain-text labels and wrapping for descriptions and messages.

### Web surface

The web keeps the native role split in CSS pixels. Amarante (fallback Georgia) sets the wordmark, the release headline, section headlines, guide h1/h2, the steps numerals and the ghost release numeral. Oswald (fallback Arial Narrow) sets navigation, mod names, step and guide titles, key chips, control names, table headers, breadcrumbs and the primary download. The system sans stack (Segoe UI, system-ui, DejaVu Sans) sets body at 16px/1.6 and guide reading at 16.5px/1.7 within 70ch; code uses a system monospace stack. Headlines use `text-wrap: balance`; guide tables use tabular numerals.

**The Reading Face Rule.** Amarante and Oswald never set paragraphs, list items or table cells; long text stays in the system sans.

## Layout

Initial window is 1280 × 860; minimum is 900 × 640. Final native captures cover 1280 × 860 and 1024 × 768. Qt logical pixels govern geometry. Outer margins are 24/14/24/10 (left/top/right/bottom), with a 10 gap. A masthead holds the game logo, brand, catalogue controls, catalogue/log/version links, and collapsible game-folder setup. Below 800 high the logo shrinks from 188 × 108 to 112 × 64 so settings keep the height. One bottom bar carries operation status on the left and the persistent actions on the right. Errors show a pink alert icon and state their own next step; background work (detection, artwork, saved sources) never replaces an error until the user starts another action. The horizontal catalogue is 68 high, scrolls on overflow, and remains keyboard selectable.

The expanding main sheet sits beside a key sheet with an 18 gap; the key sheet is 280 wide, or 340 from a 1600-wide window. Settings rows stop at 760 wide and align left, so values stay next to their labels on wide screens while the smoke texture fills the rest; main-sheet margins are 22/18/22/17 and key-sheet margins 18/16/18/16. Settings rows have a 56 minimum height, 8 vertical padding, 12 control gap, and 180-wide fields. Each has an info control by its label and a reset control by its value. Key rows have an 84 minimum height with label/help above a 116-wide value/reset row. Key values show keyboard names (Page Up, 0) while saving the UE4SS code. A keyboard tool button beside each key field assigns the next pressed key (mint border while listening, Esc cancels, unsupported keys are explained in the status bar). When a key is also bound in the same mod or by another installed, enabled mod, the field gets a pink border and a pink line naming the other binding; saving stays allowed. Hide the key sheet when a mod has no keys or media is active. Images use a 270–310-wide options column, 22 gap, and expanding preview; videos use one column. There are no web breakpoints, mobile mode, or splitter.

### Web surface

Content sits in a 1312px-wide column with a fluid gutter (clamp 16px to 64px); guides narrow to 860px. The masthead puts the Amarante wordmark left and Oswald links right, with the current page underlined in mint. The release page is one wide smoke sheet in a two-column grid, copy in the right column, then a four-column ruled ledger of mods, then sections spaced 80 to 136px apart. At 1100px the ledger and guide list drop to two columns and the release sheet's empty left column narrows. At 720px everything is one column, the navigation becomes a horizontally scrolling strip with a right fade, release actions stack full width, and step rows move their control names under the text. Guide tables scroll horizontally inside their wrapper.

**The Persistent Action Rule.** Keep saving, image preview/apply/restore, and video import/restore accessible outside scrolling content. Show the actions appropriate to the active capability and actual state.

## Elevation & Depth

Depth comes from smoke, irregular sheet edges, opaque input wells, and thin dividers. There are no custom shadows or decorative transitions. DialoguePanel paints nine image regions, preserving corners with 48-pixel source edges mapped to 16-pixel destination insets. Qt's indeterminate progress animation communicates work.

### Web surface

Web sheets are lifted by one soft, deep drop shadow plus an inset rim and an inset vignette; nothing else casts a shadow. Long-reading guide sheets dim the smoke under a 60% sheet-colour wash, and the release sheet darkens toward its copy so text stays legible. Motion uses one ease-out curve (cubic-bezier(0.16, 1, 0.3, 1)): 160 to 220ms colour transitions on links, buttons and key chips; on the release page only, the ribbon brush-wipes in once (1000ms) and the ghost numeral settles (1400ms), both only under `prefers-reduced-motion: no-preference`.

## Shapes

Sheets and selected ribbons inherit their irregular silhouettes from artwork. Native controls use small curves from the frontmatter, one-pixel borders, and two-pixel mint focus borders. Tabs use a two-pixel mint underline. Navigation keyboard focus is an inset dashed outline, dark on the selected ribbon and mint otherwise. Do not replace the sheet silhouette with generic rounded cards.

On the web, sheets, secondary buttons and key chips use the native 3px button curve and code wells the 2px field curve. Irregular silhouettes come only from the authored ribbon and stroke SVGs, stretched to their box (`preserveAspectRatio="none"`). Focus is a 2px mint outline offset 3px everywhere.

## Components

Primary QPushButtons use `button-pink.png` as a six-pixel border image (source slices 18/28/18/28), Oswald type, and 165 minimum width. Hover adds a dark pink backing; disabled actions remove the image and use muted text, fill, and border. Secondary controls retain native keyboard activation, hover/pressed states, tooltips, and explicit enabled/disabled text. Checkboxes pair On/Off text with the mint SVG indicator.

ModNavigation uses Oswald names with a smaller native-body status line. Cells stay 224 wide with a 57 height hint; wheel and trackpad input scroll horizontally without changing selection. Enabled/Disabled/Not installed is always explicit, with update state additional. Mint textured selection, faint hover and elision remain. The right-hand shortcut sheet contains real editable QComboBoxes. Combo popups and QMessageBox/QDialog surfaces remain opaque and dark. PreviewCanvas preserves aspect ratio and invalidates on changed inputs; apply requires a current preview. The bottom bar shares saving across settings and keys, shows "Unsaved changes" beside it only while edits are pending, and retains media actions while their content scrolls. Reset icons are bright when a field differs from its default and recessed to the divider color otherwise. The key-sheet heading draws the plaque in three slices so the scroll ornaments keep their proportions. The video picker groups clips by folder, marks replaced clips with the mint check icon, and states the selected clip's original format.

Number fields accept both . and , as the decimal mark and never show thousands separators; help, tooltips and reset text use the same formatting. Their tooltip states range and default. Out-of-range or over-precise input is corrected when leaving the field, and a pink 9pt note under the label names the correction until the next edit. Spin boxes and combo boxes take wheel input only while focused, so scrolling the page never edits a field. Image size and offsets use whole percentages. The logo and preview are scaled in device pixels so they stay sharp at 150 % and 200 % display scaling. Info and reset are 26×28 authored line-icon tool buttons with keyboard focus. Hover/focus explains a setting; click opens a dark, bounded scrollable plain-text popup that closes on Escape or an outside click. Reset changes the form only; saving remains explicit. Add mod opens a focused import dialog with source inspection, release choices, package checkboxes and an explicit add action. External entries show origin and configuration/source access. Logs opens a separate modeless dark reader; native typography, plain text and persistent controls carry the same workbench language.

### Web surface

**Primary download.** A pink torn-edge stroke (`stroke.svg`, hover `stroke-hover.svg`) behind white Oswald 700 text and an inline-SVG download icon; no border or radius; pressed nudges down 1px. On desktop Linux, `site.js` moves the primary stroke to the Linux build; the Windows ZIP stays the default otherwise.

**Secondary buttons.** Dark button fill, one-pixel border, 3px curve, system sans 15px, 46px minimum height; hover lightens the fill and brightens the border to text colour; pressed uses the native pressed plum. A muted `small` suffix names the format.

**Ribbon.** The mint torn-edge ribbon (`ribbon.svg`) with ink-on-mint Oswald text marks real state only (release type and date on the home page).

**Key chips.** Dark wells with a divider border and mint Oswald key names, 34px high. Hovering or focusing a ledger entry fills its chips with the mint ribbon and ink-on-mint text. Guide tables whose first header is "Key" render their first column as chips through `site.js`.

**Control names.** Dashed-border muted Oswald labels name the manager's own buttons in instructions; they are labels, not page actions, and are never clickable.

**Navigation.** Muted Oswald 16px links; hover brightens to text; the current page carries a 2px mint underline.

**Ruled lists.** The mod ledger, numbered steps and guide index separate entries with one-pixel divider rules rather than cards. Step numbers are mint Amarante numerals.

**Guide sheet.** Breadcrumbs in Oswald with mint links, prose capped at 70ch with mint list markers, mint-underlined links, mint-ruled blockquotes and dark code wells.

**Release sheet (home only).** The latest manager release on a wide smoke sheet with a ghosted Amarante version numeral bleeding off its lower-left edge. This is the home page's composition, not a pattern for other pages.

## Do's and Don'ts

- **Do** reuse the native Qt tokens, textured sheets, mint navigation, and Amarante/Oswald hierarchy.
- **Do** preserve explicit state, labelled editable controls, visible focus, and persistent actions at checked desktop sizes.
- **Do** retain extraction metadata in `manager/assets/game-ui-layout.json` and font licenses in `manager/assets/fonts/`.
- **Do** build web surfaces from `assets/site.css` tokens, the authored SVG materials and the self-hosted font subsets; keep the OFL texts beside the fonts.
- **Do** keep long web reading in the system sans on dimmed sheets with soft dialogue text.
- **Don't** describe HTML replicas, iOS controls, or web breakpoints as implemented native UI.
- **Don't** put game artwork, extracted textures or screenshots containing them on the web site; web materials are authored SVGs only.
- **Don't** use the mint ribbon as a decorative section label; it marks selection or real state.
- **Don't** infer Linux runtime or gameplay compatibility from visual and offscreen checks.
- **Don't** ship original game artwork. Read it only from a present supported installation; a local cache alone must not enable it.
