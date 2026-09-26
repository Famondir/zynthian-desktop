## 1. Resolve open design questions

- [x] 1.1 Decided: MAC address argument (exact match) or a case-insensitive name-substring match against `bluetoothctl devices Connected`; if omitted and exactly one device is connected, that one is auto-selected. No interactive picker (kept it scriptable/non-interactive-friendly for the common one-device case).
- [x] 1.2 Decided: printed warning (prominent, runtime output) plus an interactive `Type 'yes' to continue` confirmation by default, skippable via a `--yes` flag for repeat/scripted runs - real friction without inventing a separate documented `--i-understand-the-latency` flag name.
- [x] 1.3 Decided: `systemctl --user is-active --quiet pipewire.service` - matches the exact unit `run_zynthian.sh`'s own "Stopping PipeWire for this session" step stops, confirmed by reading that script directly.

## 2. Implement the script

- [x] 2.1 Created `run_zynthian_bluetooth_audio.sh` at the repo root with a header comment covering independence from `run_zynthian.sh`, the PipeWire-stopped precondition, the latency warning, and what it does/doesn't do - matching `run_zynthian_docker.sh`/`setup_virtual_devices.sh`'s convention.
- [x] 2.2 Checks `command -v bluealsa-aplay` and `systemctl is-active --quiet bluealsa.service` (system-scope, not `--user` - confirmed via `systemctl list-unit-files` that `bluealsa.service` is a system unit), fails with `sudo apt install bluez-alsa-utils`/`sudo systemctl start bluealsa.service` instructions.
- [x] 2.3 Reused `setup_virtual_devices.sh`'s exact `lsmod`/`modprobe`/`aplay -l` Loopback-card-detection logic verbatim.
- [x] 2.4 Implemented per 1.3.
- [x] 2.5 Implemented per 1.1; if `bluealsa-aplay -L` doesn't yet list a PCM for the selected MAC, does a `bluetoothctl disconnect`/`connect` cycle and polls (up to 10s) for the PCM to appear before giving up with a clear error.
- [x] 2.6 Implemented, but not as a literal shell pipe - used a named FIFO with `arecord`/`aplay` each backgrounded separately so their PIDs can be tracked and killed individually on cleanup (a plain `cmd1 | cmd2 &` only exposes the last command's PID via `$!`, which isn't enough to guarantee no orphaned process on shutdown - relevant for task 3.3). Logs both to `/tmp/zynthian_bluetooth_audio.log`, `trap cleanup EXIT INT TERM`.
- [x] 2.7 Printed as a boxed runtime warning before the confirmation prompt, not just in the header comment.

## 3. Validate

- [x] 3.1 Live test: confirmed audible on AirPods Pro, end-to-end through the full app (VMPK → active FluidSynth chain → chain's Audio Out routed to the `zynaout_Loopback` output pair → this script's bridge). Found and fixed along the way: `arecord -D hw:Loopback,1,0` failed outright (`Sample format non available`) because `zynautoconnect`'s own `alsa_out -d hw:Loopback` already holds the card's cross-connected playback side open in `FLOAT_LE`, which a plain `hw:` capture can't renegotiate - switched to `plughw:Loopback,1,0` so ALSA's plug layer converts.
- [x] 3.2 Live test: confirmed - with PipeWire running (no Zynthian session active), the script fails immediately with the clear precondition error rather than silently producing no audio.
- [ ] 3.3 Live test: confirm clean shutdown (Ctrl-C or script exit) - no orphaned `arecord`/`aplay` processes, no dangling `bluealsa` transport.
- [ ] 3.4 Confirm the existing native install (`run_zynthian.sh`, `run_zynthian_vnc.sh`) and other `Loopback`-using workflows (`setup_virtual_devices.sh`) aren't disturbed by this script running alongside them.

## 4. Follow-up (tracked, not part of this change)

- [ ] 4.1 Once this output-only script is validated (section 3 complete), propose a new change (e.g. `support-bluetooth-audio-input`) for Bluetooth *input* (mic/headset, via the HFP/HSP profile rather than A2DP) - not implemented here because HFP/HSP wasn't tested or de-risked by `investigate-jack-bluetooth-audio`, unlike the A2DP output path this change builds on. Expect a different `bluealsa` profile/startup flags and its own latency characterization, not a small extension of this script.
