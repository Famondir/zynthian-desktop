## Why

Text entry in Zynthian (snapshot names, bank names, chain titles, … - 26 call sites of `show_keyboard`/`show_numpad`) only works by clicking/touching the on-screen keyboard. On the desktop port, where a real keyboard is always present, that is slow and surprising; found while naming a snapshot (2026-10-04). The same is true on real Zynthian hardware with a USB keyboard - upstream (`origin/vangelis`) has the identical code. Worse, physical keys are not ignored: every key press goes to the global `cb_keybinding`, and the QWERTY keybinding profile maps letters like `i`, `k`, `o`, `l` and Tab to ZYNSWITCH presses, so "typing" into the dialog can confirm or navigate away instead.

## What Changes

- While the on-screen keyboard/numpad screen is shown, physical key presses go to it instead of the keybinding/CUIA mapping: printable characters are inserted, Backspace deletes, Enter confirms, Escape cancels.
- The on-screen keyboard keeps working unchanged in parallel (touch, mouse, encoders); `max_len` limits and numpad-only input still apply.
- Fix the keyboard screen's deferred keypress queue processing order (it pops from the end, so several keys queued between two control-thread ticks are applied in reverse) - harmless for touch, but fast physical typing hits it.
- Workflow test coverage: a new step type that types text into the X display, and a workflow that names a snapshot by typing.
- Candidate for an upstream PR (same as `submit-upstream-fix-prs`), since upstream is affected too.

## Capabilities

### New Capabilities
- `physical-keyboard-text-entry`: physical keyboard input into Zynthian's on-screen keyboard/numpad dialogs.

### Modified Capabilities
- `workflow-smoke-testing`: workflows gain a step that types text via the X display (keyboard input, not CUIA).

## Impact

- **`/zynthian/zynthian-ui`** (fork, branch `vangelis`): `zynthian_main.py` (`cb_keybinding`), `zyngui/zynthian_gui_keyboard.py`. Pushed so Docker rebuilds pick it up.
- **This repo**: `workflow_testing/` (new step type, new workflow). The typing step runs `xdotool` on the host against the session's X display - the same way `play_note` already runs VMPK - so the Docker image needs nothing new.
- No config/keybinding format change; keybindings work exactly as before whenever the keyboard dialog is not open.
