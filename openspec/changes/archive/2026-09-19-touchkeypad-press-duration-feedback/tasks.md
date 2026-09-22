## 1. Timer infrastructure

- [x] 1.1 Add two new button-config slots (or a small per-button dict keyed by button index) to hold the pending "Bold" and "Long" `after()` job IDs
- [x] 1.2 In `cb_button_push()` (device/device_cables branch): set the outline to yellow, then schedule the Bold-colour and Long-colour callbacks via `self.after(...)` using `zynthian_gui_config.zynswitch_bold_us // 1000` and `zynswitch_long_us // 1000`
- [x] 1.3 In `cb_button_release()` (device/device_cables branch): `self.after_cancel()` both timer IDs if still pending, before hiding the outline

## 2. Colour staging

- [x] 2.1 Bold-threshold callback: `self.itemconfig(outline, outline="<orange>")`
- [x] 2.2 Long-threshold callback: `self.itemconfig(outline, outline="<red>")`
- [x] 2.3 Pick specific hex values for orange/red consistent with the app's existing palette (e.g. `zynthian_gui_config.color_low_on`/`color_warn` or similar - check for an existing constant before hardcoding a new one)

## 3. Validation

- [x] 3.1 Manual test: tap quickly (<300ms) - outline stays yellow the whole time (confirmed)
- [x] 3.2 Manual test: hold ~1s - outline turns orange partway through, stays orange until release (confirmed: turns orange right at 300ms, matching `zynswitch_timing()`'s actual Bold threshold - no gap category between 300ms-1s)
- [x] 3.3 Manual test: hold >2s - outline turns red, stays red until release (confirmed: turns red at 2s as configured)
- [x] 3.4 Manual test: press and release quickly, then press again immediately - confirm no leftover orange/red flash from the previous press's cancelled timers (confirmed)
- [x] 3.5 Confirm actual CUIA behaviour (which action fires) is unchanged from before this change for all three brackets (confirmed: Long-press on OPT/ADMIN still fires its pre-existing WLAN-status CUIA action, which errors on `nmcli dev show wlan0` because the Docker container has no `wlan0` - a pre-existing environment limitation, unrelated to and unaffected by this change)
