## 1. Geometry constants

- [x] 1.1 Add `V5_KNOB_GROUP = (1711, 197)`, `V5_KNOB_SPACING_Y = 198`, `V5_KNOB_RADIUS = 44` to `zyngui/zynthian_gui_touchkeypad_v5.py`, alongside the existing `V5_BUTTON_*`/`V5_LED_*` constants, with a comment noting they were measured directly against the vendored render (see design.md) and supersede the rough `(1658,125), r=52` note in `touchkeypad-visual-styles/tasks.md` task 5.14 - implemented as `V5_KNOB_CENTER_X`/`V5_KNOB_TOP_Y` (split out instead of one tuple, matching how the group offset is actually used) + `V5_KNOB_SPACING_Y`/`V5_KNOB_RADIUS`
- [x] 1.2 Add `KNOB_RECT_ID`/`KNOB_HL_ID`/`KNOB_TKIMG` (or equivalent) slots to track each knob's per-item canvas ids, separate from the existing 20-button `self.buttons` list - implemented as `KNOB_TKIMG`/`KNOB_HIT_ID`/`KNOB_PRESS_ID`/`KNOB_HOVER_ID` indices into a new `self.knobs` list

## 2. Knob hit-areas and press feedback

- [x] 2.1 Implement `draw_knob_device(index)`: transparent `ImageTk.PhotoImage` hit-area (`w=h=2*V5_KNOB_RADIUS`) centered at `(V5_KNOB_GROUP[0], self.cable_margin + V5_KNOB_GROUP[1] + index * V5_KNOB_SPACING_Y)`, tagged `v5_knob_{index}`
- [x] 2.2 Add a hidden press-outline overlay per knob (circular, same yellow outline convention as `draw_button_device()`'s `RECT_ID`), shown on `<Button-1>` and hidden on `<ButtonRelease-1>`
- [x] 2.3 Call `draw_knob_device(i)` for `i in range(4)` from `__init__`, gated behind `self.style in ("device", "device_cables")`, right after the existing button-drawing loop

## 3. Hover affordance

- [x] 3.1 Bind `<Enter>` on each `v5_knob_{index}` tag: set canvas cursor to a scroll/adjust cursor and draw a highlight ring (`create_oval`, `zynthian_gui_config.color_hl`) around that knob
- [x] 3.2 Bind `<Leave>`: reset the canvas cursor to default and delete the highlight ring
- [x] 3.2b **Bug found during manual testing, fixed (attempt 1 of 2)**: the first implementation of 3.1/3.2 called `create_oval()`/`delete()` per `<Enter>`/`<Leave>`, tagged with the hit-area's own event tag - this livelocked the whole UI via a Tk crossing-event feedback loop. Fixed by pre-creating the ring hidden at `draw_knob_device()` time with no event tag of its own, toggling `state="hidden"`/`"normal"` instead of create/delete.
- [x] 3.2c **Bug recurred (attempt 2 of 2, actual fix)**: user retested and hit the *same class* of livelock via a knob **click**, not hover - `cb_knob_push` (task 5.1) revealed the press-outline via `state="normal"`, which turned out to be just as unsafe as create/delete: any item becoming `"normal"` while overlapping a hit-area can win Tk's "current item" picking and re-trigger `<Leave>`/`<Enter>` on the hit-area's tag, which (if that handler also toggles an overlapping item) ping-pongs forever. Proved the mechanism in isolation using real X11 synthetic input (`XTestFakeMotionEvent` edge-sweeps - Tcl's `event_generate` does *not* reproduce this, it bypasses the same code path) before touching the real app again: `state="normal"` toggling ran away past 500 Enter/Leave pairs under edge-dwelling stress; a lone item sharing the hit-area's own tag (the existing 20-button pattern) stayed safe at 1-2 crossings; `state="disabled"` (visible, permanently excluded from Tk's current-item picking) stayed safe too. Fixed both the hover ring *and* the press-outline (`cb_knob_push`/task 5.1) to toggle `"hidden"`/`"disabled"`, never `"normal"`. Re-verified against the real running app with a combined edge-dwell + click-hold + rapid-click stress test across all 4 knobs (screenshots confirm correct rendering, no livelock, CPU back to idle ~14-15%). See design.md's hover-ring decision (now covers both bugs) and updated Risks entry.
- [x] 3.3 Verify hover ring/cursor don't interfere with the existing press-outline overlay (both visible correctly if a hover-then-press happens in sequence) - confirmed via the combined stress test in 3.2c (click-and-hold while edge-dwelling, i.e. hover + press active simultaneously)

## 4. Scroll-to-turn

- [x] 4.1 Bind `<Button-4>`/`<Button-5>` on each `v5_knob_{index}` tag to a handler that calls `zynthian_gui_config.zyngui.cuia_queue.put_nowait(f"zynpot {index},1")` / `f"zynpot {index},-1"` respectively
- [x] 4.2 Manual test: with `device` style running, scroll over each of the 4 knobs on a screen with a visible controller bound to that zynpot index (e.g. main mixer/selector screen) and confirm the value moves the same direction/amount a keyboard `Comma`/`Period` binding would - confirmed on `device_cables` (screenshot: knob 2 scroll moved the Main Mixbus "level" control to 0.800 with the on-screen arc updating; knob scrolls also navigated the "Add Chain" grid selection). Only tested `device_cables`, not plain `device` - see 6.3.

## 5. Click-to-press

- [x] 5.1 Bind `<Button-1>` on each `v5_knob_{index}` tag: show press-outline, `cuia_queue.put_nowait(f"zynswitch {index},P")`
- [x] 5.2 Bind `<ButtonRelease-1>`: hide press-outline, `cuia_queue.put_nowait(f"zynswitch {index},R")`
- [ ] 5.3 Manual test: short click on each knob reproduces the same effect as the equivalent keyboard binding (`KeyI`/`KeyK`/`KeyO`/`KeyL` → `ZYNSWITCH 0..3`) on at least one screen with distinct short/bold/long behavior

## 6. Style scoping and device_cables alignment

- [x] 6.1 Confirm `classic`/`standard` styles create no knob hit-areas/bindings (no chassis render exists to overlay in those styles) - `draw_knob_device()` is only ever called from inside the `if self.style in ("device", "device_cables")` branch of `__init__`
- [x] 6.2 Confirm `device_cables`'s `cable_margin` offset is applied to knob y-coordinates identically to how it's applied to button/LED y-coordinates, so knobs stay aligned with the render when the cable-graphics strip is present
- [ ] 6.3 Visual pass on both `device` and `device_cables` at the target display resolution; nudge `V5_KNOB_GROUP`/`V5_KNOB_SPACING_Y`/`V5_KNOB_RADIUS` if the hit-areas are visibly offset from the knob artwork (same iterative-tuning workflow used for `V5_BUTTON_*`/`V5_LED_*` in `touchkeypad-visual-styles`)

## 7. Documentation

- [x] 7.1 Update `touchkeypad-visual-styles/tasks.md` task 5.14 to point at this change once implemented, so the deferred-scope note doesn't go stale

## 8. Deferred follow-up (not scheduled - do not start without explicit go-ahead)

- [x] 8.1 Knob press-duration colour feedback to match the buttons. Implemented: added `KNOB_BOLD_TIMER_ID`/`KNOB_LONG_TIMER_ID` slots (extended `self.knobs` from 4 to 6 per-knob entries), `_set_knob_press_duration_color()` mirroring `_set_press_duration_color()`, and updated `cb_knob_push()`/`cb_knob_release()` to schedule/cancel the same `zynswitch_bold_us`/`zynswitch_long_us`-timed `after()` jobs the buttons use. Kept the existing `"hidden"`/`"disabled"` state-toggle safety rule intact (only `outline=` colour is touched by the new code, `state=` toggling is unchanged from the already-fixed knob press-outline logic) - recolouring a canvas item's outline doesn't affect Tk's current-item picking, only `state=` does, so this doesn't reintroduce the 3.2c livelock class of bug. Manually verified live on a running `device_cables` session (fresh restart to pick up the code change): holding a knob transitions yellow → orange (Bold) → red (Long) at the expected thresholds, confirmed by the user.
