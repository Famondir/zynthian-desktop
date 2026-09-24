## 1. Pick the new size budget

- [ ] 1.1 With Fisa Suprema + AG03MK2 both connected (the config that surfaced the bug), note the actual `block_h` each of the 4 port-category columns needs today (MIDI-in/MIDI-out are the tall ones per the screenshot: 5 entries each including `zynsmf`/`zynseq`/`CV-Gate`/`ZynMaster`/`ZynMidiRouter`).
- [ ] 1.2 Pick a new `cable_margin` value with headroom above that observed max (not a theoretical bound - see design.md's "Decisions").

## 2. Update the three synced constants

- [ ] 2.1 `zynthian_gui_touchkeypad_v5.py`: update `cable_margin`'s value (line ~168), and add a one-line comment cross-referencing the other two locations that must move with it (design.md's "Risks" notes this coupling is otherwise implicit).
- [ ] 2.2 `run_zynthian.sh`: update the `device_cables` branch's `DISPLAY_HEIGHT` (currently `1120 = V5_IMAGE_SIZE[1] 960 + margin 160`) to match the new margin.
- [ ] 2.3 `run_zynthian_vnc.sh`: update `XVFB_SIZE`'s height so the virtual display itself isn't the new clipping constraint.

## 3. Fix the overflow/overlap layout bug

- [ ] 3.1 In `draw_connections()`, clamp the per-column `y` placement (`y = (self.cable_margin - block_h) // 2`) so it never goes negative - e.g. `y = max(2, (self.cable_margin - block_h) // 2)` - so a too-tall column top-aligns instead of clipping its top rows off-canvas.
- [ ] 3.2 Add the "+N more" truncation fallback for a column whose content still exceeds the margin after the clamp, so it degrades to a clearly-marked summary instead of overlapping a neighboring column.

## 4. Validate

- [ ] 4.1 Live test with Fisa Suprema + AG03MK2 both connected (same config as the bug report): confirm all labels in every column are fully visible, no clipping, no cross-column overlap.
- [ ] 4.2 Confirm via `./run_zynthian_vnc.sh device_cables` that the noVNC view's window crop (`track_app_window`) follows the now-taller window correctly, with no black margin or clipping introduced by the VNC layer itself.
- [ ] 4.3 Confirm the 4 knob hit-areas (`touchkeypad-encoder-controls`) still align with their graphics at the new `cable_margin` value.
- [ ] 4.4 Disconnect down to a single device and confirm the display still looks correct (not overly spaced out / regressed) at the new, larger margin.
