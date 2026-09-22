## Why

The on-screen touch keypad (substitute for the real V5's physical buttons/encoders, see `zynthian-desktop-runtime`) crammed 20 buttons into 6 uneven rows, nothing like the real panel's clean 4x5 grid, making it hard to find things by muscle memory from reference photos/videos. Beyond just fixing the grid, there's an appetite for a more device-like look (chassis background, live cable indicators for what's actually plugged in) - but different people/moments may want the plain original back for comparison, so all looks need to coexist and be selectable, not replace each other outright.

## What Changes

- Four parallel, selectable keypad styles via `ZYNTHIAN_GUI_KEYPAD_STYLE` (passed as `run_zynthian.sh`'s first argument): `classic` (verbatim original layout), `standard` (default; same idea but grid matches the real V5 panel), `device` (adds a chassis-style background/bezel + top port strip), `device_cables` (device + live cable graphics for whatever audio capture ports are actually present, from `zynautoconnect` data).
- `zynthian_gui_config.set_touch_keypad()` reads panel width/top margin/button height from the keypad instance instead of duplicating its geometry formulas.
- `run_zynthian.sh` widens the window for non-classic styles so the actual app screen area (where dialogs like "Add Chain" render) stays the same physical size as under `classic`, instead of shrinking when more width is reserved for a wider button panel.

## Capabilities

### New Capabilities
- `touchkeypad-visual-styles`: the on-screen keypad's selectable visual styles and the screen-area sizing that keeps other GUI screens rendering correctly under each style.

### Modified Capabilities
(none)

## Impact

- `zyngui/zynthian_gui_touchkeypad_v5.py`, `zyngui/zynthian_gui_config.py`, `run_zynthian.sh`.
- **Status: in progress.** User feedback in progress (screenshots + comments comparing styles); known open items are tracked in `tasks.md` and this proposal is intentionally not archived yet.
