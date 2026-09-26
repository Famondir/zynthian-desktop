## Context

`fix-mixer-bpm-display-clipping` traced the mixer topbar's BPM-clipping bug to `topbar_height` (and everything sized from it - `status_fs`, `topbar_fs`, `font_listbox`, `font_topbar`, and the mixer's own `layout_status_tempo()` font measurements) being computed exactly once, at `zynthian_gui_config` module load / screen `__init__` time, from whatever `screen_width`/`screen_height` happened to be at that instant. That fix made the *startup* value correct for every keypad style. It did not address a second, related gap found live during the user's own verification: `zynthian_gui_config.toggle_touch_keypad()` (wired to a runtime tap on the topbar's status area via `zynthian_gui_base.py`'s `status_short_touch_action`) updates the module-level `screen_width`/`screen_height` globals, but nothing re-derives `topbar_height`/`status_fs`/`font_topbar`/`status_l`/the mixer's cached font object from the new values - `zynthian_gui_base.py`'s `update_layout()` (bound to Tk's `<Configure>` event and called after every toggle) only refreshes `self.width`/`self.height`, with a literal `# TODO Resize topbar elements` where the rest should happen.

This asymmetry is why the two toggle states look inconsistent: elements whose sizing reads `self.width`/`self.height` live at draw/redraw time (e.g. the arranger's `grid_height = self.height - self.timebase_track_height`-style calculations) correctly track the toggle, while the topbar's own sizing - baked into Tk font tuples and `int()` pixel offsets computed once - does not, so it can end up too small (blends in, hard to read) or, if some other proportional element scales up unbounded expecting the same toggle to have "fixed" everything, too large and overlapping.

## Goals / Non-Goals

**Goals:**
- Confirm live exactly which quantities go stale across a runtime toggle (repeat `fix-mixer-bpm-display-clipping`'s "read live values, don't just read code" approach) - likely `topbar_height`, `status_fs`, `topbar_fs`, `font_topbar`, `font_listbox`, `status_l`/`status_lpad`/`title_canvas_width`, and the mixer's `status_tempo_font_obj`.
- Make every one of those recompute consistently on toggle, on every screen with a topbar, not just the mixer.
- Preserve `fix-mixer-bpm-display-clipping`'s fix for the startup case exactly (no regression there).

**Non-Goals:**
- Redesigning the topbar's layout/look.
- Making arbitrary window resizing (beyond this specific keypad-toggle affordance) responsive - real hardware never resizes at runtime, and this project's `run_zynthian_vnc.sh` locks the window's min/max size to `DISPLAY_WIDTH`/`DISPLAY_HEIGHT` (per that script's own comments) precisely to avoid needing general-purpose responsive resizing.

## Decisions

- **Decision: recompute topbar sizing inside `set_touch_keypad()`/`toggle_touch_keypad()` itself, not via a generic resize-handler rewrite.**
  The toggle is a known, discrete, small set of transitions (keypad shown ↔ hidden), not arbitrary window resizing - `set_touch_keypad()` (`zynthian_gui_config.py`) already owns updating `screen_width`/`screen_height` for exactly this transition. Recomputing `topbar_height`/`topbar_fs`/`font_listbox`/`font_topbar` there (reusing the same formula `fix-mixer-bpm-display-clipping` already established) keeps the fix scoped to the actual trigger, rather than making `update_layout()`/`<Configure>` handle a general case this project doesn't otherwise need. Each live screen's own `status_l`/`status_fs`/`status_lpad` (currently computed once in `zynthian_gui_base.__init__`, per-instance) then need a matching recompute-and-redraw path - likely a method on the base class that every open screen's `update_layout()` can call, since `<Configure>` already fires per-screen on the toggle.
  Alternative considered: only fix the mixer's `layout_status_tempo()`-equivalent path - rejected, since the base class's status icons (mute/error/rec/play/etc., shared by every screen) would still go stale, just less visibly than the mixer's own tempo text.
- **Decision: regression check extends the existing native_adapter-based approach, exercising the toggle via CUIA/OSC injection rather than a raw X11 click.**
  `workflow_testing/check_topbar_status_fit.py` already launches a real session and reads `layout_status_tempo()`'s log line; the natural extension is to also inject whatever triggers `toggle_touch_keypad()` (needs finding the corresponding CUIA/zynswitch equivalent, since the existing injector goes through OSC, not raw clicks) and assert the log line's `fits=True` still holds *after* the toggle, and that a parallel measurement for the base-class status icons/title font also stays consistent. Alternative (raw X11 `xdotool click` on the status canvas, as manual verification used) rejected for automation - fragile to window geometry, and the existing CUIA-injection-based engine already has a cleaner mechanism if the toggle is reachable that way; needs confirming during implementation.

## Risks / Trade-offs

- [Risk] The toggle's rescale path may need to touch every screen subclass (each may have its own topbar-adjacent elements sized off `font_topbar`/`topbar_fs`), not just the mixer → Mitigation: fix at the `zynthian_gui_base` level first (shared status icons/title), then verify the mixer (already has its own `layout_status_tempo()` from the prior change) and at least one non-mixer screen (e.g. arranger, since it's already confirmed to rescale its own grid) don't regress.
- [Risk] Recomputing fonts/geometry on every toggle could introduce a visible flicker or measurable delay if done naively (e.g. rebuilding `tkFont.Font` objects repeatedly) → Mitigation: `layout_status_tempo()`'s existing `tkFont.Font` object can be *reconfigured* (`Font.configure(size=...)`) rather than recreated; toggling is a rare, explicit user action (not a hot path), so a small amount of work here is acceptable regardless.
- [Risk] This is confirmed to be a real, live-reproducible bug (screenshots from the user's own testing), but the exact set of "everything that needs to recompute" is not yet fully enumerated - only traced by inspection so far → Mitigation: first implementation task is to reproduce live and enumerate every stale quantity before writing the fix, matching `fix-mixer-bpm-display-clipping`'s own investigation-first approach.

## Migration Plan

- No data migration. Fix lands in the `zynthian-ui` fork (`vangelis` branch), same as `fix-mixer-bpm-display-clipping`. Steps: fix, commit, push to `Famondir/zynthian-ui` (required for the Docker image to pick it up), then verify visually across styles and the runtime toggle in the simulator.
- Rollback: revert the fork commit(s); no persisted state touched.

## Open Questions

- Is there a CUIA/zynswitch equivalent for the topbar-tap toggle, reachable via OSC injection for an automated regression check, or does verifying this require a raw-click-based check (e.g. `xdotool`) instead?
- Beyond the mixer and arranger, which other screens have topbar-adjacent elements that might also need a fix (full enumeration is an implementation-time task, not resolved here)?
