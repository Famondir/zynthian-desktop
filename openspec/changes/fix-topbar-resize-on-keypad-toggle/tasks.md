## 1. Reproduce and enumerate what goes stale

- [ ] 1.1 Launch the simulator (`run_zynthian_vnc.sh device_cables`, matching the environment `fix-mixer-bpm-display-clipping` used), open the mixer screen, and reproduce the reported toggle behavior (tap/click the topbar's status area) live.
- [ ] 1.2 With logging/a debugger, capture the live values of `topbar_height`, `status_fs`, `topbar_fs`, `font_listbox`, `font_topbar`, `status_l`, `status_lpad`, `title_canvas_width` before and after a toggle, to confirm which ones change and which stay frozen.
- [ ] 1.3 Identify which other screen elements *do* visibly rescale on the same toggle (e.g. arranger grid, mixer "Main" label) and how they read `self.width`/`self.height` to do so, to use as the working pattern for the fix.
- [ ] 1.4 Confirm this reproduces consistently across `device`, `device_cables`, `standard`, and `classic` styles (all support the toggle, per `zynthian_gui_touchkeypad_v5.py`).

## 2. Make the base-class topbar (title/status icons) rescale on toggle

- [ ] 2.1 In `/zynthian/zynthian-ui/zyngui/zynthian_gui_config.py`, factor `topbar_height`/`topbar_fs`/`font_listbox`/`font_topbar`'s computation (added by `fix-mixer-bpm-display-clipping`) into a function callable again from `set_touch_keypad()`/`toggle_touch_keypad()`, not just once at module load.
- [ ] 2.2 In `/zynthian/zynthian-ui/zyngui/zynthian_gui_base.py`, add a method (called from each open screen's `update_layout()`, replacing the `# TODO Resize topbar elements` comment) that recomputes `status_l`/`status_fs`/`status_lpad`/`title_canvas_width` from the current `zynthian_gui_config` values and repositions/reconfigures the existing status icons (mute/error/rec/play/etc. from `init_status()`) accordingly, reusing `tkFont.Font.configure()` rather than recreating font objects where practical.

## 3. Make the mixer's tempo/time-signature text rescale on toggle

- [ ] 3.1 In `/zynthian/zynthian-ui/zyngui/zynthian_gui_mixer.py`, reconfigure `status_tempo_font_obj`'s size and re-run `layout_status_tempo()` when the base class signals a topbar resize (from task 2.2), so the tempo/time-signature text tracks the new topbar size instead of staying at its startup font.

## 4. Verify no regression to the startup-time fix

- [ ] 4.1 Confirm `fix-mixer-bpm-display-clipping`'s existing regression check (`workflow_testing/check_topbar_status_fit.py`) still passes unmodified.
- [ ] 4.2 Visually confirm the startup-time BPM text and status icons look identical to before this change, across all four keypad styles, when the keypad is never toggled.

## 5. Verify the toggle fix

- [ ] 5.1 Visually confirm, across all four keypad styles, that toggling the keypad view resizes the topbar (title font, status icons, mixer tempo/time-signature text) consistently with the rest of the screen - no frozen-small or oversized/overlapping elements in either toggle direction.
- [ ] 5.2 Spot-check at least one non-mixer screen (e.g. arranger) for the same consistency, since the base-class fix (task 2) should apply to every screen, not just the mixer.
- [ ] 5.3 Wait for the user's own live-test confirmation of the fix before considering this done (do not mark complete on mechanical/build success alone).

## 6. Regression coverage

- [ ] 6.1 Resolve design.md's open question on whether the toggle is reachable via CUIA/OSC injection; if so, extend `workflow_testing/check_topbar_status_fit.py` (or add a new check) to trigger the toggle and assert `layout_status_tempo()`'s `fits=True` still holds afterward. If not reachable that way, document why and settle for the manual visual verification in group 5.

## 7. Commit and push

- [ ] 7.1 Commit the fix in `/zynthian/zynthian-ui` (`vangelis` branch) and push to `Famondir/zynthian-ui`, since the Docker build clones the fork's pushed state, not the local checkout.
- [ ] 7.2 Commit this repo's updated/added regression check (if any) and mark this change's tasks complete.
