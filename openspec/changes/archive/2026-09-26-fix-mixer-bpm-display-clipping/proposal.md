## Why

On the simulated/desktop Zynthian (V5 touchkeypad style), the mixer screen's topbar BPM readout is clipped almost entirely away - only a fragment like `)bpm` is visible instead of e.g. `120.0 bpm`. The tempo value itself is very likely correct (zynseq is still reporting a real BPM); the digits are just being cut off by the topbar's status canvas, so the screen visually reads as if tempo were missing or zero. This is misleading during live use (no visible tempo reference) and needs root-causing and fixing rather than papering over.

## What Changes

- Investigate why `zynthian_gui_mixer`'s tempo/time-signature status text (drawn in `zynthian_gui_base.init_status`/`zynthian_gui_mixer`) renders far enough left that it is clipped by the topbar's `status_canvas` boundary, and confirm this reproduces specifically under the desktop touchkeypad's `device`/`device_cables` styles (where `zynthian_gui_config.display_width` includes the extra on-screen button panel while `screen_width` stays pinned to the real V5's native 800px) rather than on a plain/no-keypad layout.
- Fix the layout/font-sizing calculation so the topbar status text (BPM and time signature) always fits fully within its allotted canvas area, regardless of keypad style or display resolution.
- Add a regression check (workflow-testing screenshot or unit-level geometry assertion) so this class of clipping cannot silently regress again.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `touchkeypad-visual-styles`: add a requirement that the app topbar's status readouts (tempo/time-signature) remain fully visible - not clipped by the status canvas - under every supported keypad style, since today's screen-area-preservation requirement only covers the main screen area, not the topbar text budget.

## Impact

- Affected code: `/zynthian/zynthian-ui/zyngui/zynthian_gui_base.py` (topbar `status_l`/`status_fs` geometry), `/zynthian/zynthian-ui/zyngui/zynthian_gui_mixer.py` (tempo/time-signature text placement), `/zynthian/zynthian-ui/zyngui/zynthian_gui_config.py` (`font_size`/`topbar_fs` derivation from `display_width` vs `screen_width`), `/zynthian/zynthian-ui/zyngui/zynthian_gui_touchkeypad_v5.py` (`V5_SCREEN_RECT`, `screen_width`/`display_width` relationship).
- No spec-level behavior change to this repo's own tooling; the actual code fix lands in the `zynthian-ui` fork per this repo's `CLAUDE.md`, not in this repo's `docker/`/`workflow_testing/` code.
- Affects only the desktop/simulated port's visual correctness (topbar readability); no change to audio, MIDI, or sequencer behavior.
