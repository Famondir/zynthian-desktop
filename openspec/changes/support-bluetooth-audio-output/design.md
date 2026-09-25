## Context

`investigate-jack-bluetooth-audio` (archived) proved the mechanism live: with PipeWire stopped, a paired Bluetooth device reconnected fresh (so `bluealsa` - not PipeWire's own `bluez5` module - claims the BlueZ A2DP media endpoint), `bluealsa-aplay -L` lists a real PCM (`bluealsa:DEV=<MAC>,PROFILE=a2dp`), and a plain `arecord -D hw:Loopback,1,0 -F 20000 -B 40000 | aplay -D bluealsa:DEV=<MAC>,PROFILE=a2dp -F 20000 -B 40000` pipe moves real, audibly-confirmed audio from the Loopback card's capture side to the Bluetooth device, with the tuned 40ms buffers producing clean, glitch-free playback (verified with a 4-tone sequence, no xruns logged). The existing `alsa_out`/`alsa_in` binaries (`jackd2` package, what `fix-audio-hotplug-support` uses for USB devices) crash immediately (`buffer overflow detected`) on a `bluealsa:...` device string - confirmed reproducible, not an environment fluke (the same binaries work fine with plain `hw:` strings) - so this bridge must use plain ALSA tools (`arecord`/`aplay`), not those binaries.

`zynautoconnect.py` already treats the `Loopback` ALSA card as a normal hotplug-discoverable device (same mechanism `support-virtual-test-devices` already exercises for dev testing) - so once audio lands on the Loopback card's playback side, the existing app picks it up with no changes needed there. This change is entirely about the *other* leg: getting a Bluetooth device's audio from BlueZ into the Loopback card's capture side in the first place.

## Goals / Non-Goals

**Goals:**
- A user can run a new script to bridge a connected Bluetooth device's audio into the Zynthian audio graph (via `Loopback`), for non-real-time use.
- The script clearly documents the latency limitation - not a technical fix, an honest tradeoff the user is accepting.
- Reuses the tuned buffer settings already confirmed clean (40ms, not the untuned ~500ms default).

**Non-Goals:**
- Live/real-time monitoring use - already decided against by `investigate-jack-bluetooth-audio`; this change doesn't revisit that latency finding, only who gets to decide whether to accept it.
- Automatic hotplug detection of Bluetooth devices - `bluealsa` PCMs aren't discoverable via ALSA card enumeration (confirmed during the investigation), so there's no reliable low-level signal to poll the way USB hotplug uses `/proc/asound/cards`. Manual start/stop only.
- Bluetooth *input* (microphone/HFP) implementation within this change - the investigation only tested and confirmed the A2DP *output* (playback) path; HFP/HSP (needed for mic input) wasn't tested and isn't part of what's de-risked here. Not dropped, though: tracked as an explicit follow-up task (see tasks.md section 4) to propose as its own change once this output-only script is validated, rather than expanding this change's scope before HFP/HSP is actually investigated.
- The Docker image - no PipeWire-stop/`bluealsa` story explored there.
- Changing anything about `zynthian-desktop-runtime`'s existing "Bluetooth is a documented gap" requirement - this adds an opt-in mechanism alongside it, doesn't contradict it.

## Decisions

**Manual companion script, not zynautoconnect integration.** Modeled on `run_zynthian_webconf.sh`'s pattern (standalone, independent of `/zynthian/run_zynthian.sh`, per `CLAUDE.md`'s "native launcher is host-local, not version-controlled from this repo" convention) rather than wiring Bluetooth detection into `zynautoconnect`'s polling loop. Reasoning: unlike a USB device (which the kernel unconditionally reports via `/proc/asound/cards` the moment it's plugged in), a Bluetooth device requires an explicit prior pairing/connection step by the user anyway (`bluetoothctl connect`) - it was never going to be truly hotplug-transparent the way USB is. Piggybacking BlueZ D-Bus connection-state watching onto `zynautoconnect` would be meaningfully more code for a feature that's already a deliberate, occasional, manual action.

**Script responsibilities** (exact flags/commands to be finalized during implementation, informed by the investigation's working commands):
1. Check `bluez-alsa-utils` is installed and `bluealsa.service` is active; clear error + install instructions if not (matching how `run_zynthian_webconf.sh` checks for `authbind`).
2. Take a Bluetooth device (by MAC address or by matching a name substring via `bluetoothctl devices`) as an argument or prompt for one.
3. Ensure `snd-aloop` is loaded (reuse `setup_virtual_devices.sh`'s existing modprobe-if-missing pattern rather than duplicating it).
4. Start the `arecord -D hw:Loopback,1,0 -F 20000 -B 40000 | aplay -D bluealsa:DEV=<MAC>,PROFILE=a2dp -F 20000 -B 40000` bridge as a background process, logged to a file (matching `/tmp/zynthian_*.log` convention), with a trap to clean it up on exit.
5. Print the latency caveat prominently before starting, not buried in a comment only.

**Precondition, not handled by this script: PipeWire must already be stopped.** This script assumes it's run alongside an already-running Zynthian session (`run_zynthian.sh`/`run_zynthian_vnc.sh`), which already stopped PipeWire for its own jackd needs - it does not itself manage the PipeWire stop/restart dance. If PipeWire is still running, `bluealsa` can't claim the A2DP endpoint (confirmed during the investigation - required a disconnect/reconnect cycle after stopping PipeWire to get `bluealsa` to hold the transport). The script should detect this precondition and fail with a clear message rather than silently doing nothing.

## Risks / Trade-offs

- A user could reasonably expect "Bluetooth support" to mean live-usable, given this is fundamentally a live-performance instrument - the script's own upfront warning is the main mitigation; worth considering whether it should require an explicit confirmation/flag (e.g. `--i-understand-the-latency`) rather than just a printed warning, to reduce the chance of a confused bug report later.
- `bluealsa` and PipeWire fighting over the same BlueZ media endpoint is a real, somewhat fragile precondition (same category of fragility `zynthian-desktop-runtime` already accepts for jackd/PipeWire time-sharing the ALSA device) - a device that was connected before PipeWire stopped needs an explicit disconnect/reconnect cycle, which this script should handle rather than leaving the user to work out via trial and error (as this session's investigation had to).
- Only A2DP output was proven - HFP/mic input is materially more investigation (different BlueZ profile, different `bluealsa` startup flags), not assumed to be a small extension. Tracked as a follow-up task (tasks.md section 4), not implemented here.
