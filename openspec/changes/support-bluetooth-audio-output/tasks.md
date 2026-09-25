## 1. Resolve open design questions

- [ ] 1.1 Decide the device-selection UX for the script (MAC address argument, name-substring match against `bluetoothctl devices`, or interactive picker) - not decided in design.md.
- [ ] 1.2 Decide whether starting requires an explicit `--i-understand-the-latency`-style confirmation flag, or a printed warning is enough (design.md's Risks flags this as worth considering, not decided).
- [ ] 1.3 Decide exactly how the script detects "PipeWire is still running" to fail fast per the precondition in design.md (e.g. `systemctl --user is-active pipewire.service`).

## 2. Implement the script

- [ ] 2.1 Create the new script (name TBD, sibling to `run_zynthian_webconf.sh`) with a header comment documenting: its independence from `run_zynthian.sh`, the PipeWire-stopped precondition, and the latency limitation - matching this repo's existing header-comment convention (`run_zynthian_docker.sh`, `setup_virtual_devices.sh`).
- [ ] 2.2 Check for `bluez-alsa-utils`/`bluealsa.service` and fail with clear install instructions if missing.
- [ ] 2.3 Ensure `snd-aloop` is loaded, reusing `setup_virtual_devices.sh`'s existing modprobe-if-missing logic rather than duplicating it.
- [ ] 2.4 Implement the PipeWire-running precondition check from 1.3.
- [ ] 2.5 Implement device selection per 1.1, and if needed, the disconnect/reconnect cycle to get `bluealsa` (not PipeWire) to hold the A2DP transport (only needed if the device was already connected before this script ran).
- [ ] 2.6 Start the `arecord -D hw:Loopback,1,0 -F 20000 -B 40000 | aplay -D bluealsa:DEV=<MAC>,PROFILE=a2dp -F 20000 -B 40000` bridge as a background process, logged to `/tmp/zynthian_bluetooth_audio.log` (or similar), with a cleanup trap on exit.
- [ ] 2.7 Print the latency caveat prominently (2.1's header comment isn't enough on its own - needs to appear as runtime output too, per the spec's second requirement).

## 3. Validate

- [ ] 3.1 Live test: start a Zynthian session, run the new script with a connected Bluetooth device, confirm audio reaches it end-to-end through the full app (not just the raw `arecord`/`aplay` pipe this was prototyped with) - play something through an actual chain and confirm it's audible via Bluetooth.
- [ ] 3.2 Live test: run the script while PipeWire is still running, confirm the precondition check fails clearly rather than silently producing no audio.
- [ ] 3.3 Live test: confirm clean shutdown (Ctrl-C or script exit) - no orphaned `arecord`/`aplay` processes, no dangling `bluealsa` transport.
- [ ] 3.4 Confirm the existing native install (`run_zynthian.sh`, `run_zynthian_vnc.sh`) and other `Loopback`-using workflows (`setup_virtual_devices.sh`) aren't disturbed by this script running alongside them.

## 4. Follow-up (tracked, not part of this change)

- [ ] 4.1 Once this output-only script is validated (section 3 complete), propose a new change (e.g. `support-bluetooth-audio-input`) for Bluetooth *input* (mic/headset, via the HFP/HSP profile rather than A2DP) - not implemented here because HFP/HSP wasn't tested or de-risked by `investigate-jack-bluetooth-audio`, unlike the A2DP output path this change builds on. Expect a different `bluealsa` profile/startup flags and its own latency characterization, not a small extension of this script.
