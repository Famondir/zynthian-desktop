## 1. Pick the new size budget

- [x] 1.1 With Fisa Suprema + AG03MK2 both connected (the config that surfaced the bug), note the actual `block_h` each of the 4 port-category columns needs today. Measured offline (tkinter font metrics, same wrap logic as `draw_connections()`, fed the real label text from the screenshot - see `/tmp/.../measure_cable_block_h.py`): MIDI-in **185px** (exceeds 160px margin - the clipped column), MIDI-out **161px** (also over, barely - the "network" overlap), audio columns **93px** each (fit fine). Root cause of the height isn't device count alone - MIDI devices without a short alias fall back to `dev.name`, the full a2j port name (e.g. `a2j:FISA SUPREMA [24] (capture): [0] FISA SUPREMA MIDI 1`), which wraps to 3 lines (55px) vs. 1 line (21px) for a short label.
- [x] 1.2 Pick a new `cable_margin` value with headroom above that observed max (not a theoretical bound - see design.md's "Decisions"). Chosen: **240px** (up from 160px) - roughly 30% headroom over the observed 185px max, enough for e.g. one more long-named device before hitting the truncation fallback from task 3.2.

## 2. Update the three synced constants

- [x] 2.1 `zynthian_gui_touchkeypad_v5.py`: update `cable_margin`'s value (line ~168), and add a one-line comment cross-referencing the other two locations that must move with it (design.md's "Risks" notes this coupling is otherwise implicit).
- [x] 2.2 `run_zynthian.sh`: update the `device_cables` branch's `DISPLAY_HEIGHT` (currently `1120 = V5_IMAGE_SIZE[1] 960 + margin 160`) to match the new margin. Set to `1200 = 960 + 240`.
- [x] 2.3 `run_zynthian_vnc.sh`: update `XVFB_SIZE`'s height so the virtual display itself isn't the new clipping constraint. Set to `1200` to match. Also caught and fixed the same `XVFB_SIZE=...1120x24` pattern in `run_zynthian_docker.sh`'s noVNC path (not originally listed here, but the identical bug via the identical coupling - `test_zynthian_docker.sh`'s own `XVFB_SIZE` was already `1920x1200x24`, so no change needed there).

## 3. Fix the overflow/overlap layout bug

- [x] 3.1 In `draw_connections()`, clamp the per-column `y` placement (`y = (self.cable_margin - block_h) // 2`) so it never goes negative - e.g. `y = max(2, (self.cable_margin - block_h) // 2)` - so a too-tall column top-aligns instead of clipping its top rows off-canvas.
- [x] 3.2 Add the "+N more" truncation fallback for a column whose content still exceeds the margin after the clamp, so it degrades to a clearly-marked summary instead of overlapping a neighboring column. Verified offline (`/tmp/.../verify_cable_fix.py`, same font-metric simulation as 1.1): real MIDI-in (185px)/MIDI-out (161px)/audio (93px) all fit fully within the new 240px margin (top_y clamped to 2-39px, bottom edge 166-212px, no clipping); a synthetic stress case (MIDI-in + 1 extra long-named device, block_h=243px, over budget) correctly renders 5/6 rows plus a "+1 more" chip, staying within the margin (bottom edge 211px).

## 4. Validate

- [x] 4.1 Live test with Fisa Suprema + AG03MK2 both connected (same config as the bug report): confirm all labels in every column are fully visible, no clipping, no cross-column overlap. Confirmed: enough room at startup, no clipping.
- [x] 4.2 Confirm via `./run_zynthian_vnc.sh device_cables` that the noVNC view's window crop (`track_app_window`) follows the now-taller window correctly, with no black margin or clipping introduced by the VNC layer itself. Confirmed: viewed via noVNC, no black margin.
- [x] 4.3 Confirm the 4 knob hit-areas (`touchkeypad-encoder-controls`) still align with their graphics at the new `cable_margin` value. Confirmed: rotary knobs still aligned correctly.
- [x] 4.4 Disconnect down to a single device and confirm the display still looks correct (not overly spaced out / regressed) at the new, larger margin. Confirmed: with neither device connected, there's visibly more room and no regression; unplug/replug hotplug behaviour (fix-audio-hotplug-support) still works unaffected by this UI change.
