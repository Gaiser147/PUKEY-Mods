# Desktop UI Refinement

The user rejected the rudimentary interface and explicitly requested Impeccable. This is a visual/interaction refinement of the existing native Qt manager; the previously delegated implementation judgment remains applicable. Keep the warm palette and all installer/data-preservation behavior.

## Direction

Use a dark navigation rail with the existing charcoal/white/amber colors, quieter catalogue controls, a compact game-location panel, clear selected-mod status/actions, and a larger white editing workspace. Separate keybindings from preferences, preserving one settings map/save operation. Put image controls beside a responsive transparency preview; retain the fixed apply action. Use one authored line-icon family and native input/keyboard semantics. No web scaffold, fabricated metrics, game artwork, or backend changes.

## Steps

- [x] Capture and inspect the current running UI; use the explicit user critique as direction.
- [x] Add regression coverage for separated keybindings, selection/status, and saving across settings views.
- [x] Implement reusable theme/native presentation widgets; replace the crowded layout and media arrangement.
- [x] Run the complete tests and batch screenshots at 1120×800 and 1024×768, with installed/empty/media/error states. Fix one bounded batch of material issues.
- [x] Obtain a fresh Impeccable finish review using screenshots and source. Update source-backed design documentation.
- [x] Build/start-test Windows and Linux bundles, publish the updated app, and verify its downloads/startup.

Native Qt desktop is outside the Impeccable launcher's web/iOS/Android enums. Preserve accurate PRODUCT.md platform text and use desktop screenshot/keyboard QA rather than a web detector. Runtime and Proton gameplay claims remain unchanged.

Delivered through PR #2 and `manager-v0.2.0`. All 64 tests completed successfully with platform-specific skips. Linux CI exposed an extra Proton row pushing media actions below the small viewport; moving its copy action into the game-panel heading fixed the regression, now exercised on Windows too. Impeccable's four visual findings were resolved and confirmed. Release workflow 40183578740 passed both platform builds and packaged startup, including SVG loading. The downloaded Windows ZIP matched its published SHA-256 digest and its executable passed startup locally. The Linux 1024×768 render was inspected. The Windows bundle is also available in the original workspace's `dist/PUKEY-Mod-Manager-0.2.0/`; the installed game was not changed.
