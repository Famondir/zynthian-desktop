## Why

`touchkeypad-visual-styles` (still open, not yet archived) added `device`/`device_cables` on-screen keypad styles that render the real V5 panel's official chassis mockup, including its 4-knob rotary-encoder column - but that column is purely decorative pixels baked into the render (tracked as deferred task 5.14 in that change: "Knob column ... has no interactive overlay yet - decorative-only was the agreed scope ..., revisit only if requested"). The user is now requesting exactly that: on a desktop test rig there's no physical encoder to turn or press, so anyone using `device`/`device_cables` currently has no way to drive per-screen encoder actions (value scroll, menu navigation, the encoder's push-switch shortcuts) by interacting with the knob graphics themselves, even though the rest of the panel (all 20 buttons) is already fully clickable.

## What Changes

- Add four invisible, per-knob hit-areas over the V5 render's knob column (same "transparent `PhotoImage` overlay" technique `draw_button_device()` already uses for the 20 buttons), gated behind `style in ("device", "device_cables")`, positioned/sized from measured render coordinates (knob 1 center ≈ (1711, 197) in the 1910x960 render, ≈198px vertical spacing, ≈40-44px hit radius - refines task 5.14's `(1658,125) group offset, r=52` note against the actual pixel art; exact values tuned visually during implementation like every other V5_* geometry constant in this file).
- **Hover feedback**: entering a knob's hit-area changes the cursor (e.g. to a resize/scroll-style cursor) and/or highlights the knob with a subtle glow ring, so it reads as interactive instead of decorative; leaving clears it.
- **Scroll-to-turn**: `<Button-4>`/`<Button-5>` (Linux mouse wheel) over a knob's hit-area sends a `zynpot {index},{+1|-1}` CUIA event on the existing `cuia_queue` - the same event the real hardware encoder's rotation (and the pre-existing keyboard/on-screen-controller scroll bindings) already produce - so it drives whatever the currently-active screen has bound to that encoder index, with no new dispatch logic needed.
- **Click-to-press**: `<Button-1>`/`<ButtonRelease-1>` over a knob's hit-area sends `zynswitch {index},P`/`zynswitch {index},R` CUIAs, mirroring the real encoder's push-button exactly like `draw_button_device()`'s existing buttons already do for the 20 keypad switches (`button + 4`) - so short/bold/long press timing and whatever function is currently bound to that switch index (SELECT/BACK/LAYER/SNAPSHOT-equivalent, context-dependent) work unchanged, since that dispatch logic already exists and only needs the same CUIA fired.
- Visual press feedback on click matching the existing button convention (yellow outline overlay while held).

## Capabilities

### New Capabilities
- `touchkeypad-encoder-controls`: interactive mouse-hover/scroll/click behavior for the V5 mockup's on-screen rotary-encoder graphics in the `device`/`device_cables` keypad styles, mapped onto the same `zynpot`/`zynswitch` CUIA events the real hardware encoders produce.

### Modified Capabilities
(none - `touchkeypad-visual-styles` isn't in `openspec/specs/` yet since it hasn't been archived; this change instead depends on it as a sibling in-progress change, see Impact)

## Impact

- `zyngui/zynthian_gui_touchkeypad_v5.py` (`Famondir/zynthian-ui`, branch `vangelis`, cloned by `docker/Dockerfile`): new knob geometry constants + `draw_knob_device()`/hover/wheel/click handlers alongside the existing `draw_button_device()`.
- Depends on `touchkeypad-visual-styles` (in-progress sibling change) for the `device`/`device_cables` styles, the V5 render asset, and the `cuia_queue`/CUIA-string plumbing this change reuses unchanged.
- No changes to `zyngui/zynthian_gui.py`'s CUIA thread, `zynthian_gui_keybinding.py`'s keyboard map, or any per-screen `zynpot_cb`/`cuia_v5_zynpot_switch` handler - this change only adds a second *input source* (mouse) feeding the same existing event pipeline the keyboard bindings (`Comma`/`Period`, `KeyI/K/O/L`) already use.
- No `run_zynthian.sh` or geometry-constant changes beyond the new knob hit-area constants; screen sizing established by `touchkeypad-visual-styles` is untouched.
