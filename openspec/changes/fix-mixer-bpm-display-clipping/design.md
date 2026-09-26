## Context

The mixer screen's topbar draws two status texts on `zynthian_gui_base`'s `status_canvas`: the tempo (`"120.0 bpm"`) and time signature (`"1 | 4/4"`), both anchored `NE` (top-right) at an x-offset computed as `status_l - status_fs * <multiplier>` (`zynthian_gui_mixer.py:1207-1221`). Because the anchor is top-right, the text grows *leftward* from that point; a `tkinter.Canvas` clips any drawing that falls outside its own pixel width, so if the text is wider than the room between the anchor and the canvas's left edge (x=0), the left portion of the string silently disappears - which matches the screenshot (`)bpm` surviving, the number and `bpm`'s leading letters gone).

Two independently-computed quantities decide whether that fits:

- **Available room** = `status_l` (`zynthian_gui_base.py:114`: `int(self.topbar_width * 0.27)`), where `topbar_width = zynthian_gui_config.screen_width`.
- **Text pixel width** scales with `status_fs` (`0.36 * status_h`, `status_h = topbar_height`), which itself derives from `topbar_fs`/`font_size` in `zynthian_gui_config.py:886-896`: `font_size = ZYNTHIAN_UI_FONT_SIZE or display_width / 40`.

On real V5 hardware, `display_width == screen_width == 800` (the physical LCD *is* the screen; there is no extra chrome), so both quantities scale off the same number and the hand-tuned multipliers (`3.5`, `8.5`) hold.

The desktop/simulated port changes this: `zynthian_gui_touchkeypad_v5.py:80` (`V5_SCREEN_RECT`) pins the mocked screen's content area to a fixed `screen_width = 800`, but renders an *additional* button-panel mockup beside it, so the outer window/display (`zynthian_gui_config.display_width`) is wider than 800 to fit both panel and screen. `font_size` (and everything derived from it, including `status_fs`) is computed from that wider `display_width`, while `status_l` stays pinned to the fixed `screen_width = 800`. The font used to draw the BPM text is inflated relative to the pixel budget reserved for it, so the text overflows past x=0 and gets clipped - a bug specific to `device`/`device_cables` keypad styles (and possibly any layout where `display_width != screen_width`), not present on real hardware or on `classic`/no-keypad layouts.

This needs to be confirmed empirically (§ Open Questions / tasks) before committing to the fix, since it is a hypothesis derived from reading the code, not yet reproduced live.

## Goals / Non-Goals

**Goals:**
- Root-cause why the topbar BPM/time-signature text clips in the simulated/desktop environment.
- Make the fix general: the topbar status text must fit under any current or future keypad style/resolution combination, not just patch the one reported case.
- Preserve the existing look/sizing on real hardware (`display_width == screen_width`) exactly - zero visual regression there.

**Non-Goals:**
- Redesigning the topbar layout or status-icon set.
- Changing tempo/time-signature semantics, zynseq behavior, or any non-visual behavior.
- Touching this repo's own code (`docker/`, `workflow_testing/`) beyond adding a regression check; the runtime fix lives in the `zynthian-ui` fork per this repo's `CLAUDE.md`.

## Decisions

- **Decision: derive topbar font sizing from `screen_width`, not `display_width`, when they differ.**
  `zynthian_gui_config.py`'s `font_size`/`topbar_fs` calculation should key off the actual on-screen content area (`screen_width`), matching what `status_l` already uses, rather than the outer display/window size. Alternative considered: keep font sizing on `display_width` but widen `status_l`'s multiplier for non-hardware styles - rejected because it hard-codes a per-style fudge factor instead of fixing the actual quantity mismatch, and would need re-tuning every time a new keypad style changes the panel width.
- **Decision: make the status text's reserved width self-consistent instead of a hand-tuned constant.**
  Rather than picking new magic multipliers (`3.5`, `8.5`) that happen to fit today's string lengths at today's font, size the reserved offset from the actual rendered text width (e.g. via `tkFont.Font(...).measure(text)` at draw time) so it can never exceed the canvas regardless of font/DPI/style changes going forward. Alternative considered: just retune the constants for the simulator's current numbers - rejected as it would silently break again the next time `display_width` changes (new keypad style, different VNC resolution, different `ZYNTHIAN_UI_FONT_SIZE`).
- **Decision: add a workflow-testing screenshot assertion rather than a pure unit test.**
  This is fundamentally a rendering/clipping bug; a geometry-only unit test (checking `status_l > text_width`) exercises the same formula this bug came from and could pass while the real Tk canvas still clips due to font metrics it doesn't model. A screenshot-based check under `workflow_testing/` (already used for this project's Docker/simulated smoke tests) catches the actual visual regression. Alternative considered: unit-test the geometry formula only - kept as a cheap first-line check, but not treated as sufficient on its own.

## Risks / Trade-offs

- [Risk] Root cause hypothesis (display_width vs screen_width mismatch) turns out to be only part of the story (e.g. `forkawesome` font also missing digit glyphs in the Docker image, changing metrics further) → Mitigation: first task is to reproduce and confirm the exact numbers (`screen_width`, `display_width`, `status_l`, measured text width) live in the running simulator before changing code, per this design's Open Questions.
- [Risk] Changing `font_size` derivation affects other UI elements sized off it (listboxes, buttons, other labels), not just the BPM text → Mitigation: since real hardware's `display_width == screen_width`, this change is a no-op there; verify visually in the simulator that other font-sized elements still look correct after the change.
- [Risk] Measuring text width at draw time (via `tkFont`) adds a small per-refresh cost to a status readout that updates on every tempo change → Mitigation: tempo/time-signature text changes are low-frequency (user-driven or song-position driven), not per-frame, so this is negligible.

## Migration Plan

- No data migration. This is a display-only fix in the `zynthian-ui` fork (`vangelis` branch). Steps: fix in `/zynthian/zynthian-ui`, commit, push to `Famondir/zynthian-ui` (required for the Docker image to pick it up - see this repo's `CLAUDE.md` on unpushed fork commits), then rebuild/relaunch the Docker or native simulator to confirm visually.
- Rollback: revert the fork commit(s); no persisted state is touched.

## Open Questions

- Confirm live (not just by reading code) the actual `screen_width`/`display_width`/`status_l`/rendered-text-width numbers in the currently running Docker simulator, to nail down the exact overflow amount and whether `forkawesome` font-fallback is also a contributing factor.
- Confirm whether the same clipping is visible under `classic`/`standard` keypad styles or only `device`/`device_cables` (this affects how broadly the fix must be scoped).
