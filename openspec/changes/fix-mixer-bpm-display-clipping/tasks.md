## 1. Reproduce and confirm root cause

- [ ] 1.1 Launch the Docker/simulated Zynthian (`run_zynthian_docker.sh` or VNC) with the `device`/`device_cables` keypad style, open the mixer screen, and confirm the BPM text is clipped as in the reported screenshot.
- [ ] 1.2 Add temporary logging (or use a debugger) in `/zynthian/zynthian-ui/zyngui/zynthian_gui_config.py` and `zynthian_gui_base.py` to print the live values of `display_width`, `screen_width`, `font_size`, `topbar_fs`, `status_l`, and `status_fs` in this environment.
- [ ] 1.3 Measure the actual rendered pixel width of the tempo string (e.g. via `tkFont.Font(font=("forkawesome", status_fs)).measure("120.0 bpm")`) and compare it against the available room (`status_l - status_fs*3.5`) to confirm the overflow amount.
- [ ] 1.4 Check whether the same clipping reproduces under `classic`/`standard` keypad styles or only `device`/`device_cables`, and note the result in design.md's Open Questions.
- [ ] 1.5 Confirm whether `forkawesome` is actually available as an installed font in the Docker image for plain digit/letter glyphs, or whether Tk is silently substituting a fallback font with different metrics.

## 2. Fix font sizing to match the actual content area

- [ ] 2.1 In `/zynthian/zynthian-ui/zyngui/zynthian_gui_config.py`, change `font_size`'s derivation (and anything computed from it that affects topbar layout, e.g. `topbar_fs`) to key off `screen_width` instead of `display_width` wherever they differ, so hardware behavior (`display_width == screen_width`) is unchanged.
- [ ] 2.2 Re-verify `status_l`'s derivation in `/zynthian/zynthian-ui/zyngui/zynthian_gui_base.py` still uses `screen_width`-derived `topbar_width`, so both quantities are consistent.

## 3. Make the status text width self-correcting

- [ ] 3.1 In `/zynthian/zynthian-ui/zyngui/zynthian_gui_mixer.py`, replace the hand-tuned `status_fs * 3.5` / `status_fs * 8.5` offsets with an offset computed from the actual measured text width of the current tempo/time-signature strings (e.g. `tkFont.Font(...).measure(text)`), recomputed whenever the displayed text changes (`update` calls around lines ~1535-1537).
- [ ] 3.2 Confirm the offset calculation accounts for the longest realistic tempo/time-signature strings this UI can show (e.g. 3-digit BPM, larger time signatures like `16/16`), not just the `"120.0 bpm"` default.

## 4. Verify the fix

- [ ] 4.1 Rebuild/relaunch the Docker or native simulator with `device`/`device_cables` keypad style and visually confirm the full BPM and time-signature text now renders without clipping.
- [ ] 4.2 Visually confirm no regression under `classic`/`standard` styles and on a plain (no-keypad) layout.
- [ ] 4.3 Wait for the user's own live-test confirmation of the fix before considering this done (do not mark complete on mechanical/build success alone).

## 5. Regression coverage

- [ ] 5.1 Add a `workflow_testing` screenshot-based check (or extend an existing mixer-screen smoke test) that asserts the topbar status text region has no unexpected clipping under the `device`/`device_cables` style, per `python3 -m workflow_testing.run_all`'s module docstring for how to wire in a new check.

## 6. Commit and push

- [ ] 6.1 Commit the fix in `/zynthian/zynthian-ui` (`vangelis` branch) and push to `Famondir/zynthian-ui`, since the Docker build clones the fork's pushed state, not the local checkout.
- [ ] 6.2 Commit this repo's `workflow_testing` regression check (if added) and mark this change's tasks complete.
