# Desktop design

Operate mode. Use a restrained light workspace suitable for reading file paths and settings in desktop mode; selected rows and primary actions use warm amber, with dark text for contrast. Native Qt controls retain keyboard/focus behavior.

Tokens: background #f4f3ef, panel #ffffff, text #252620, secondary #595c53, border #d9dcd3, selection #f5e9cf, primary #e8af42, danger #a52b2b, success #31633e. System UI font, body 10–11 pt, headings 17–22 pt. Space in 4/8/12/16/24 px steps. Corners 4–8 px; no decorative cards or gradients.

Structure: game-folder and loader status above a left mod list/right scrolling details split. Put one installation action and one enable toggle next to the selected mod title. Use tabs for settings/media when present. Show progress and recoverable errors in a persistent bottom status region. At 1280×800 and 1024×768, lists and forms scroll without hiding main actions.

Empty, loading, error, disabled and unsaved states are explicit. Network and file work runs outside the GUI thread; all mutation controls are blocked during an operation. Removal confirms which program files are removed and that personal files remain. No fabricated metrics, imagery, or backend jargon in the normal flow.
