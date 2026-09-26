## ADDED Requirements

### Requirement: Topbar status text stays fully visible under every keypad style
The app topbar's status readouts (tempo and time-signature text drawn on the status canvas) SHALL remain fully visible - not clipped by the status canvas's edges - under every supported keypad style (`classic`, `standard`, `device`, `device_cables`) and whenever `zynthian_gui_config.display_width` differs from `screen_width`.

#### Scenario: device/device_cables style with a wider outer display than the mocked screen
- **WHEN** the keypad is started with a style (e.g. `device` or `device_cables`) whose mocked screen's `screen_width` is smaller than the outer `display_width` used to size fonts
- **THEN** the topbar's tempo text (e.g. `"120.0 bpm"`) and time-signature text (e.g. `"1 | 4/4"`) render in full, with no digit or character clipped off by the status canvas's left edge

#### Scenario: Real hardware where display_width equals screen_width
- **WHEN** the keypad is started on a layout where `display_width == screen_width` (matching real V5 hardware)
- **THEN** the topbar status text's size and position are unchanged from before this fix
