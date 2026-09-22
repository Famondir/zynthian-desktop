## ADDED Requirements

### Requirement: Selectable keypad visual style
The on-screen touch keypad SHALL support at least four selectable visual styles (`classic`, `standard`, `device`, `device_cables`), chosen at startup via `ZYNTHIAN_GUI_KEYPAD_STYLE`, without requiring a code change to switch between them.

#### Scenario: Launching with a given style
- **WHEN** `run_zynthian.sh` is launched with a style argument (`classic`, `standard`, `device`, or `device_cables`)
- **THEN** the keypad renders with that style's layout/appearance, and an unrecognized style argument is rejected with an error instead of silently falling back

### Requirement: Classic style matches the original upstream layout
The `classic` style SHALL reproduce the original, pre-redesign upstream keypad layout exactly (button grid arrangement, geometry formulas, and labels), so it remains available as a fallback/comparison baseline.

#### Scenario: Comparing classic to standard
- **WHEN** the keypad is started with `ZYNTHIAN_GUI_KEYPAD_STYLE=classic`
- **THEN** the button grid, spacing, and labels match the original upstream implementation byte-for-byte, including its `"CTRL/PRSET"` label

### Requirement: Standard style's button grid matches the real V5 panel
The `standard` style's button grid SHALL be arranged as a 4-column, 5-row grid in the same left-to-right, top-to-bottom button order as the real V5 hardware panel.

#### Scenario: Visual comparison against the real panel
- **WHEN** the keypad is started with `ZYNTHIAN_GUI_KEYPAD_STYLE=standard`
- **THEN** each of the 20 buttons appears in the same relative row/column position as its counterpart on the real V5 panel

### Requirement: Non-classic styles preserve the app's screen area size
Styles that reserve a wider button panel than `classic` SHALL NOT shrink the usable app-screen area below what `classic` provides, so existing dialogs and screens continue to render without overlapping text/icons.

#### Scenario: Add Chain dialog under the standard style
- **WHEN** the keypad is started with a style that reserves a wider button panel (e.g. `standard`)
- **THEN** the app's screen area (where dialogs like "Add Chain" render) is at least as wide as it is under `classic`, achieved by widening the overall window rather than shrinking the screen area

### Requirement: device_cables shows live capture port connections
The `device_cables` style SHALL display, for each audio capture port currently present, a visual indicator (label showing the port's alias or name) that updates periodically to reflect ports being plugged in or removed.

#### Scenario: A capture device is present
- **WHEN** the keypad is running in `device_cables` style and an audio capture port exists (e.g. from a connected USB audio interface)
- **THEN** a cable/connection indicator labelled with that port's alias (or name, if no alias is set) is shown, refreshed at a regular interval

#### Scenario: Zynautoconnect not yet ready at startup
- **WHEN** the keypad is constructed before `zyncoder`'s core library has finished initializing
- **THEN** the keypad does not crash or leave `zynautoconnect`'s internal library reference permanently unusable for the rest of the process
