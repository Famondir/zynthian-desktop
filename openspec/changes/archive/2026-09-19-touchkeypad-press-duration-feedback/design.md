## Context

`zynthian_gui.py`'s `zynswitch_timing()` classifies a press as `"S"`/`"B"`/`"L"` purely from elapsed time between push and release, against `zynthian_gui_config.zynswitch_bold_us` (default 300ms) and `zynswitch_long_us` (default 2000ms). `zynthian_gui_touchkeypad_v5.py`'s `cb_button_push()`/`cb_button_release()` already show/hide a yellow press-outline rectangle (`draw_button_hitarea()`'s `RECT_ID` item, `outline="#F0F000"`) for `device`/`device_cables` - that's the thing this change animates over time instead of leaving it a single static colour.

## Goals / Non-Goals

**Goals:**
- While held, the outline visibly tells the user which bracket (Short/Bold/Long) they're currently in, using the actual configured thresholds.
- No change to actual press classification/timing - purely additive visual feedback on top of the existing mechanism.

**Non-Goals:**
- `classic`/`standard` styles - they show press feedback via a 2px button nudge, not an outline overlay; extending them would need a different mechanism (e.g. animating `self.text_color`) and wasn't asked for.
- Changing the Bold/Long thresholds themselves, or any CUIA behaviour - this only visualizes existing values.
- A numeric/countdown readout (e.g. "0.4s") - colour staging was the requested approach.

## Decisions

- **Two `Canvas.after()` timers per press**, scheduled in `cb_button_push()`: one at `zynthian_gui_config.zynswitch_bold_us // 1000` ms to recolour the outline orange, one at `zynthian_gui_config.zynswitch_long_us // 1000` ms to recolour it red. This mirrors the existing long-press timer pattern already used elsewhere in the codebase (e.g. `zynthian_gui_controller.py`'s `self.press_id = self.after(...)`), rather than inventing a new polling/animation mechanism.
- **Store both timer IDs on the button's config row** (two new slots, alongside the existing `RECT_ID` etc.) so `cb_button_release()` can `self.after_cancel()` any still-pending timer - critical: without cancelling, a released-before-Bold press would still flip to orange/red later while hidden, and (worse) could bleed into a subsequent unrelated press on the same button if timed unluckily.
- **Colours: yellow (0) -> orange (Bold) -> red (Long)**, matching the user's own suggested staging and the existing outline's yellow default, so "yellow" continues to mean "just pressed, nothing decided yet" rather than introducing a fourth unstyled state.
- **Outline resets to yellow on every new press** (already implicit - `cb_button_push` sets it before scheduling the timers), so there's no stale colour carried over from a previous hold.

## Risks / Trade-offs

- Two extra `after()` calls per press/release cycle is negligible overhead (Tkinter's event loop already handles many of these elsewhere in the app).
- If a user holds past Long and keeps holding, the outline simply stays red (no further staging) - matches `zynswitch_timing()`, which has no bracket beyond Long either.
