## Why

Tapping the topbar's status area toggles the on-screen touch keypad between shown (small, mocked-screen size) and hidden (screen expands to fill the outer display) - `zynthian_gui_base.py`'s `status_short_touch_action` calling `zynthian_gui_config.toggle_touch_keypad()`. Found live while verifying `fix-mixer-bpm-display-clipping`: after that fix, the topbar (BPM/time-signature text, status icons, title font) renders correctly at startup, but stays frozen at its startup size across this toggle - `update_layout()` has a literal `# TODO Resize topbar elements` and does nothing. Other screen content (e.g. the arranger/pattern grid's `4/4` and pattern-number labels, the mixer's "Main" mixbus label) *does* rescale on toggle, and grows large enough to overlap itself. This predates `fix-mixer-bpm-display-clipping` (the TODO comment is pre-existing) and wasn't reported before because the topbar was already visibly broken either way; it's now the most visible remaining rough edge in that class of bug.

## What Changes

- Investigate why `update_layout()` recomputes `self.width`/`self.height` (which the arranger/mixer's own dynamic elements read) but never touches `topbar_height`/`status_fs`/`font_topbar`/`status_l` (which the topbar and its status icons/text are built from once, at startup) - confirm this is really the same one-time-computation pattern `fix-mixer-bpm-display-clipping` already found for the *initial* keypad style, just never revisited on a *runtime* toggle.
- Make the topbar (title font, status icons, and the mixer's tempo/time-signature text) rescale consistently with the rest of the screen whenever the keypad view is toggled at runtime, so nothing goes stale or ends up mismatched/overlapping relative to freshly-rescaled content.
- Add a regression check (extending `workflow_testing/check_topbar_status_fit.py`'s approach, or a new one) that exercises the runtime toggle, not just a style chosen at startup.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `touchkeypad-visual-styles`: adds a new requirement (as an ADDED delta - `fix-mixer-bpm-display-clipping`'s own startup-time requirement isn't merged into the main spec yet, so this isn't a MODIFIED delta against it) that the app topbar (and any other UI relying on `topbar_height`/`font_size`-derived sizing) stays correctly scaled after a runtime keypad-view toggle, not just at startup.

## Impact

- Affected code: `/zynthian/zynthian-ui/zyngui/zynthian_gui_base.py` (`update_layout()`, the `# TODO Resize topbar elements` site, and the one-time `init_status()` icon placements), `/zynthian/zynthian-ui/zyngui/zynthian_gui_config.py` (`topbar_height`/`topbar_fs`/`font_listbox`/`font_topbar`, currently computed once at module load), `/zynthian/zynthian-ui/zyngui/zynthian_gui_mixer.py` (`layout_status_tempo()`, `status_tempo_font_obj`, currently built once in `__init__`).
- Likely touches every screen with a topbar (this is base-class behavior), not just the mixer - broader blast radius than `fix-mixer-bpm-display-clipping`, so needs its own careful verification pass across screens, not just the mixer.
- No change to audio/MIDI/sequencer behavior; purely desktop-port visual correctness during an interactive toggle.
