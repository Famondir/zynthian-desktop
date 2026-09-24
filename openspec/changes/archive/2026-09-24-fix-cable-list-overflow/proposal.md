## Why

The `device_cables` keypad style's cable-list rendering (`draw_connections()` in `zynthian_gui_touchkeypad_v5.py`) uses a fixed 160px top margin, sized for a small number of devices. With enough real devices connected at once (observed live with a Fisa Suprema + Yamaha AG03MK2, each contributing multiple MIDI/audio port entries across the 4 port-category columns), the label stacks overflow that fixed margin: top rows get clipped off-canvas, and separate categories' labels can visually overlap (e.g. the LAN group's "network" chip landing on top of a MIDI-out row). This defeats the display's own purpose - "so what's physically plugged into this machine is visible at a glance" - once more than ~2-3 devices are connected.

## What Changes

- Increase the fixed `cable_margin` constant (currently 160px) and `run_zynthian.sh`'s matching `DISPLAY_HEIGHT` for `device_cables` (currently 1120 = 960 + 160) together, to a generous worst-case size that comfortably fits realistic simultaneous device counts - the same "size it generously upfront" pattern `run_zynthian_vnc.sh`'s `XVFB_SIZE` height already uses. The canvas/Tk window size is set once at process start (before Python even runs) and locked via `minsize`/`maxsize`, so this can't become a true per-redraw resize - it has to be a larger fixed budget.
- Fix `draw_connections()`'s per-column vertical placement (`y = (cable_margin - block_h) // 2`), which currently centers each column independently with no clamp: a column taller than the margin gets pushed to a negative `y` (clipped off the top), and unrelated columns can end up overlapping if their centered positions happen to collide. Clamp so content never starts above the visible area, and degrades gracefully (e.g. top-aligned, or truncated with a "+N more" indicator) if a column still exceeds the enlarged margin, rather than silently clipping or overlapping a neighboring column.
- Keep the 4 knob hit-areas' vertical offset (`touchkeypad-encoder-controls`' existing "Device_cables style with cable margin" requirement) reading the same `cable_margin` value it already reads, so knob-to-graphic alignment keeps holding at the new, larger constant.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `touchkeypad-visual-styles`: adds a requirement that `device_cables`' cable/connection indicators stay fully visible (no clipping against the canvas edge, no overlap between different port categories) regardless of how many devices are connected at once.

## Impact

- `/zynthian/zynthian-ui/zyngui/zynthian_gui_touchkeypad_v5.py` - `draw_connections()`, the `cable_margin` constant itself, and anywhere else that reads it (chassis image placement, knob hit-area offset).
- `/zynthian/run_zynthian.sh` - the `device_cables` branch's `DISPLAY_HEIGHT=1120` (must grow by the same amount `cable_margin` does, since it's `V5_IMAGE_SIZE[1] + cable_margin`).
- `run_zynthian_vnc.sh`'s `XVFB_SIZE` height (currently 1120, chosen to exactly cover `device_cables`' current height) must grow to at least the new `DISPLAY_HEIGHT`, or the virtual display itself becomes the clipping constraint instead of the margin. `novnc_viewer.sh`'s `track_app_window` needs no changes - it follows the Tk window by X11 window ID, so a taller window is picked up automatically.
- Discovered as a side finding while validating `fix-audio-hotplug-support`'s task 4.4 (device present at app startup) with real hardware; unrelated capability, so split into its own change rather than folded into that one.
