## Why

Zynthian classifies a button press as Short/Bold/Long purely by held duration, measured only once the button is released, with no visual feedback anywhere (confirmed: neither our desktop port nor, as far as found, the original hardware/UI shows anything during the hold). On real hardware this is learned by feel over time; on a mouse-driven touch keypad it's harder to calibrate. `device`/`device_cables` already have a per-button press-outline overlay (shown while held, hidden on release) and a backlight-rectangle mechanism, both cheap to extend into a live timer indicator.

## What Changes

- While a `device`/`device_cables` button is held, its press-outline colour progresses yellow (just pressed) -> orange (past the Bold threshold) -> red (past the Long threshold), using the actual configured `ZYNTHIAN_UI_SWITCH_BOLD_MS`/`ZYNTHIAN_UI_SWITCH_LONG_MS` thresholds (defaults 300ms/2000ms) rather than hardcoded values.
- Purely visual: does not change which CUIA action fires or when - Short/Bold/Long classification still happens exactly as today, only on release.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `touchkeypad-visual-styles`: adds a requirement that `device`/`device_cables` show live press-duration feedback while a button is held.

## Impact

- `zyngui/zynthian_gui_touchkeypad_v5.py`: `cb_button_push`/`cb_button_release` (schedule/cancel timers), a new small helper for the colour-staged outline update.
- No change to `zynthian_gui.py`'s actual press-duration classification (`zynswitch_timing`) or timing thresholds - this only visualizes them.
- `classic`/`standard` styles are out of scope for this change (see design.md's Non-Goals) - they have no per-button outline overlay to repurpose the same way.
