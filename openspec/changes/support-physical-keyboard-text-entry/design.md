## Context

- `zynthian_main.py` binds `<KeyPress>`/`<KeyRelease>` on the Tk root to `cb_keybinding()`, which only looks the key up in `zynthian_gui_keybinding` (keycode + modifier → CUIA string) and queues that CUIA. Nothing ever forwards a character anywhere.
- `zyngui/zynthian_gui_keyboard.py` (screen `keyboard`, opened by `zyngui.show_keyboard()`/`show_numpad()`, 26 call sites) handles only canvas clicks (`<Button-1>`) plus encoder/switch navigation. Clicks are deferred: `on_key_press` appends `(key_index, bold)` to `keypress_queue`, and `plot_zctrls()` (called from the control thread) drains it with `pop()` - i.e. **LIFO**. Harmless for one touch at a time; reverses fast multi-key input.
- `execute_key_press(key, bold)` implements all semantics by on-screen key index: append `self.keys[key]`, `btn_enter` (close + callback), `btn_cancel` (`cuia_back()`), `btn_delete` (bold = clear), `btn_space`, shift/alt toggles, then `max_len` clipping and redraw.
- The QWERTY keybinding profile maps plain letters to CUIAs (`31`=i, `45`=k, `32`=o, `46`=l → `ZYNSWITCH 0..3`, Tab → `ZYNSWITCH 1`, Space → `ALL_NOTES_OFF`), so today typing into the dialog fires navigation.
- Upstream `origin/vangelis` has the identical code, so this affects real hardware with a USB keyboard too.

## Goals / Non-Goals

**Goals:**
- Type into every `show_keyboard`/`show_numpad` dialog with a physical keyboard; Enter/Escape/Backspace work.
- No CUIA fires from keys typed into the dialog.
- Zero behaviour change outside the dialog.
- Small, self-contained fork change suitable for an upstream PR.

**Non-Goals:**
- Text cursor movement/editing inside the string (on-screen keyboard has none either).
- A physical keyboard for list navigation in general (already covered by keybindings).
- Changing keybinding profiles.

## Decisions

### D1: Intercept in `cb_keybinding`, keyed on the current screen
At the top of `cb_keybinding`, if `zyngui.current_screen == "keyboard"`, hand the event to `zyngui.screens["keyboard"].physical_key(event)` and return without the keybinding lookup. Only KeyPress events act; KeyRelease is swallowed too, so no zynswitch press/release emulation is left half-done. *Alternative*: bind `<Key>` on the keyboard frame itself - rejected: Tk focus on this app is unreliable (the existing Tab/focus hack shows it), and the root binding would still fire the CUIA.

**Exception - Ctrl/Alt combinations** still go to the keybinding table (e.g. Ctrl+F12 shortcuts for restart/power in the QWERTY profile), since they're never text. Plain keys and Shift/AltGr combos (needed for capitals and `@`, `{`… on German layouts) are text.

### D2: Characters from X, not from the on-screen key table
Use `event.char` (already layout- and Shift-resolved by X/Tk) for printable input; `event.keysym` for `BackSpace`, `Return`/`KP_Enter`, `Escape`. Typed characters bypass the on-screen shift/alt state (a physical Shift already did that) and don't reset it. *Alternative*: map keycodes to on-screen key indices - rejected: breaks non-US layouts and characters not on the on-screen layout.

### D3: Same queue, typed items, FIFO
Typed input is queued as `("char", c)` / `("special", name)` items on the existing `keypress_queue` and executed in `plot_zctrls()` on the control thread, like clicks, so text mutation stays single-threaded as today. Change the drain to FIFO (`pop(0)`). Specials map onto the existing key indices (`btn_enter`, `btn_cancel`, `btn_delete`) so callbacks/cancel behave identically. Printable chars go through a small helper that appends, applies `max_len`, redraws and announces (TTS) - shared with `execute_key_press`'s tail rather than duplicated.

### D4: Numpad filtering
In numpad mode accept only characters present in that mode's key table (digits etc.); everything else is ignored silently.

### D5: Testing via host-side `xdotool`
New workflow step `type: "<text>"` plus optional `key: <keysym>` (e.g. `Return`), executed with `xdotool type --delay 40` / `xdotool key` against `session.display` on the host - the same display VMPK already uses for `play_note`, so native and Docker work without image changes. The safety allow-list is about CUIA injection; typing is bounded to the dialog by D1 itself, so no allow-list entry is needed - but the runner refuses `type`/`key` unless the tracked current screen is `keyboard`, so a misplaced step can't type into a list screen where keys mean CUIAs. New workflow `type_chain_name.yaml`: build a FluidSynth chain, Chain options → "Rename chain", type a name with characters that collide with QWERTY bindings (`i k o l`), a capital and an umlaut, BackSpace, Return, save the snapshot and assert a chain carries exactly that title (new `chain_has_title` in `zss_assert`).

### Findings during implementation
- **Entry point:** the snapshot screen was the first idea, but its list depends on the session's existing banks/snapshots and only offers "Save as new snapshot" for a non-empty state - on the user's native data, index 0 is "Default", and confirming it would *load* that snapshot. "Rename chain" on a chain the workflow builds itself has a fixed position (index 6 for a fresh FluidSynth chain).
- **Screen tracking:** `show_keyboard()`/`show_numpad()` set `current_screen` directly and logged nothing, so the runner couldn't tell the dialog was open. They now log `SHOW SCREEN 'keyboard'` in the same format as `show_screen()` (fork).
- **xdotool:** the Zynthian window's WM_CLASS is plain `Tk` (`tkinter.Tk()` without a className); the window is focused explicitly before typing. With only `DISPLAY` in the environment there's no UTF-8 locale and `xdotool type` fails on an umlaut - the full environment is passed.
- **Negative control:** with the fork fix stashed, the same workflow fails - typed letters fire ZYNSWITCH presses and the dialog bounces between `keyboard` and `chain_options`, which is the original bug.

## Risks / Trade-offs

- [`current_screen` is `"keyboard"` but the modal isn't really visible (e.g. during a screen transition)] → check `screens["keyboard"].shown` too.
- [Dead keys / IME produce empty `event.char`] → ignored; composed characters arrive as a later event with `char` set.
- [A user relies on a plain-letter keybinding *while* the dialog is open] → by design they now type; Escape still leaves the dialog.
- [Upstream may prefer a different hook] → keep the patch minimal and in two places, describe it as such in the PR.

## Migration Plan

Fork change, committed and pushed to `Famondir/zynthian-ui` `vangelis`; Docker rebuild with `CACHEBUST`. No config migration. Rollback = revert the commit.

## Open Questions

- Should Tab move to the on-screen Enter key (accessibility parity), or just be ignored? Default: ignored.
