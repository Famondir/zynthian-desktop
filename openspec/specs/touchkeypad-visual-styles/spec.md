## Purpose

The touchkeypad-visual-styles capability governs the on-screen touch keypad's selectable visual styles - `classic`, `standard`, `device`, and `device_cables` - letting the button panel's layout and appearance be chosen at startup (via `ZYNTHIAN_GUI_KEYPAD_STYLE`) without a code change, while preserving the original upstream layout as a baseline, matching the real V5 hardware panel's button arrangement, keeping the app's screen area from shrinking, and (for `device_cables`) showing live audio capture port connections.

## Requirements

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

### Requirement: device_cables cable list stays visible under load
The `device_cables` style's cable/connection indicators SHALL remain fully visible within the cable-graphics margin - no label clipped off the top edge of the canvas, and no overlap between indicators belonging to different port categories (audio-in, MIDI-in, MIDI-out, audio-out, LAN) - for the realistic range of simultaneously connected devices this project's hardware produces.

#### Scenario: Several devices connected across multiple port categories
- **WHEN** enough audio/MIDI devices are connected at once that one or more port-category columns' label stacks would exceed the cable-graphics margin's available height
- **THEN** every label that fits within the enlarged margin renders fully visible and top-aligned within its column, with no label clipped above the canvas edge and no overlap with another column's labels

#### Scenario: A single column's content still exceeds the available margin
- **WHEN** one port-category column's label stack is taller than the cable-graphics margin even after accounting for the sizing this change introduces
- **THEN** that column renders as many labels as fit, followed by a final "+N more" indicator summarizing the rest, rather than clipping a label silently or overlapping a neighboring column

### Requirement: Live press-duration feedback on device/device_cables
While a button is held down on the `device` or `device_cables` keypad style, its press-outline colour SHALL indicate which press-duration bracket (Short/Bold/Long) the hold currently falls into, using the app's actual configured thresholds (`ZYNTHIAN_UI_SWITCH_BOLD_MS`/`ZYNTHIAN_UI_SWITCH_LONG_MS`), without changing when or which press-duration action fires.

#### Scenario: Short hold
- **WHEN** a button is pressed and released before the Bold threshold elapses
- **THEN** the press-outline is yellow for the whole hold, and the release still fires a Short-press action exactly as it did before this change

#### Scenario: Hold crosses into Bold
- **WHEN** a button remains held past the Bold threshold but is released before the Long threshold
- **THEN** the press-outline turns orange once the Bold threshold is crossed, and the release fires a Bold-press action exactly as it did before this change

#### Scenario: Hold crosses into Long
- **WHEN** a button remains held past the Long threshold
- **THEN** the press-outline turns red once the Long threshold is crossed, and stays red for as long as the button remains held

#### Scenario: Release cancels pending colour changes
- **WHEN** a button is released before a threshold's scheduled colour change has fired
- **THEN** that pending colour change is cancelled and never applied, so it cannot bleed into a later, unrelated press of the same button

### Requirement: Topbar status text stays fully visible under every keypad style
The app topbar's status readouts (tempo and time-signature text drawn on the status canvas) SHALL remain fully visible - not clipped by the status canvas's edges - under every supported keypad style (`classic`, `standard`, `device`, `device_cables`) and whenever `zynthian_gui_config.display_width` differs from `screen_width`.

#### Scenario: device/device_cables style with a wider outer display than the mocked screen
- **WHEN** the keypad is started with a style (e.g. `device` or `device_cables`) whose mocked screen's `screen_width` is smaller than the outer `display_width` used to size fonts
- **THEN** the topbar's tempo text (e.g. `"120.0 bpm"`) and time-signature text (e.g. `"1 | 4/4"`) render in full, with no digit or character clipped off by the status canvas's left edge

#### Scenario: Real hardware where display_width equals screen_width
- **WHEN** the keypad is started on a layout where `display_width == screen_width` (matching real V5 hardware)
- **THEN** the topbar status text's size and position are unchanged from before this fix

### Requirement: Topbar sizing stays consistent across a runtime keypad-view toggle
Whenever the touch keypad view is toggled at runtime (shown ↔ hidden, e.g. via a tap on the topbar's status area), the topbar (title font, status icons, and any screen-specific topbar text such as the mixer's tempo/time-signature readout) SHALL be resized to match the new view's actual screen dimensions, consistent with content elsewhere on the same screen that already resizes on this toggle - not remain frozen at whatever size was correct for the view active at startup.

#### Scenario: Toggling from the mocked keypad view to the full-screen view
- **WHEN** the touch keypad is toggled from shown (a style's smaller mocked-screen size) to hidden (the screen expands to the outer display's full size)
- **THEN** the topbar's title font, status icons, and any screen-specific topbar text resize to fit the new, larger screen area - no element stays frozen at its previous, now-mismatched size, and no element overlaps another as a result of only one of them having resized

#### Scenario: Toggling back to the mocked keypad view
- **WHEN** the touch keypad is toggled back from hidden to shown
- **THEN** the topbar returns to the size appropriate for that style's mocked screen, matching what it would have been had the app started directly in that state (per the startup-time requirement this extends)
