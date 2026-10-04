## 1. Keyboard screen (`/zynthian/zynthian-ui`, `zyngui/zynthian_gui_keyboard.py`)

- [x] 1.1 Change `plot_zctrls()` to drain `keypress_queue` FIFO (`pop(0)`) (design D3)
- [x] 1.2 Add `physical_key(event)`: KeyPress only; map `BackSpace`/`Return`/`KP_Enter`/`Escape` to `btn_delete`/`btn_enter`/`btn_cancel`; queue printable `event.char` as a typed character (design D2, D3)
- [x] 1.3 Execute typed characters: append, numpad filter (D4), `max_len`, redraw, TTS - sharing the tail of `execute_key_press` instead of duplicating it

## 2. Key routing (`zynthian_main.py`)

- [x] 2.1 In `cb_keybinding`, route events to `screens["keyboard"].physical_key()` while `current_screen == "keyboard"` and the screen is shown; skip the keybinding lookup; keep Ctrl/Alt combos on the keybinding path (design D1)
- [x] 2.2 Manually verify on the native desktop: snapshot name with `i k o l`, capitals, umlauts, Backspace, Escape; numpad dialog rejects letters; arrow keys on the mixer still work afterwards

## 3. Workflow test (this repo, `workflow_testing/`)

- [x] 3.1 Add `type:`/`key:` step kinds to `runner.py` (`xdotool` against `session.display`), refused unless the tracked screen is `keyboard`; log `SHOW SCREEN 'keyboard'` in the fork so it can be tracked (design D5)
- [x] 3.2 Add `chain_has_title` to `zss_assert` / `assert_zss`
- [ ] 3.3 Add `workflows/type_chain_name.yaml`; run native (PASS, negative control FAIL as expected) and Docker

## 4. Ship

- [ ] 4.1 Commit and **push** the fork changes to `fork/vangelis`; rebuild Docker with `CACHEBUST` and rerun 3.3 there
- [x] 4.2 Add an upstream PR entry for this fix to `submit-upstream-fix-prs`
