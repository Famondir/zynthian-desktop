## Why

`investigate-jack-bluetooth-audio` (archived) confirmed a working technical path for Bluetooth audio output (via `bluealsa` + a `snd-aloop` intermediary), but recommended against building it for live/real-time musical monitoring given the ~150ms AVDTP protocol floor. That recommendation still stands for live use - but the user wants it available anyway as an explicitly optional, clearly-labeled feature for non-critical use (background audio, casual listening, testing), understanding and accepting the latency tradeoff. This is a deliberate reversal of that investigation's "don't implement" call, not a re-litigation of the latency finding itself.

## What Changes

- A new native-install script (sibling to `run_zynthian_webconf.sh`, independent of `/zynthian/run_zynthian.sh` per this repo's `CLAUDE.md` convention) that bridges a connected Bluetooth device's audio output through `bluealsa` and a `snd-aloop` card, using the tuned low-latency buffer settings already confirmed clean (`-F 20000 -B 40000`, ~40ms, not the untuned ~500ms default) - not the existing `alsa_out`/`alsa_in` binaries, which are confirmed to crash outright on a `bluealsa` device string.
- The script's own header comment (matching this repo's convention, e.g. `run_zynthian_docker.sh`'s `xhost`/network-exposure documentation) clearly states the ~150-190ms latency and that this is unsuitable for live monitoring while playing.
- Manual start/stop, not automatic hotplug detection - `bluealsa` PCM devices aren't discoverable via ALSA card enumeration the way USB devices are (confirmed during the investigation), so there's no reliable "device appeared" signal to poll for the way `zynautoconnect`'s existing hotplug detection works. The user runs the script when they want Bluetooth output active, matching how Bluetooth pairing/connecting itself is already an explicit user action, not truly hotplug-transparent.
- Bluetooth *input* (mic/HFP) is out of this change's implementation scope (only A2DP output was de-risked by the investigation), but is tracked as an explicit follow-up task rather than dropped - see tasks.md section 4.

## Capabilities

### New Capabilities
- `bluetooth-audio-output`: opt-in, explicitly-latency-limited Bluetooth audio output on the native desktop install, bridged via `bluealsa` and a `snd-aloop` intermediary.

### Modified Capabilities
(none - `zynthian-desktop-runtime`'s existing "Bluetooth audio is a documented hotplug gap" requirement, from `investigate-jack-bluetooth-audio`, remains accurate: Bluetooth still doesn't become available *automatically* via the hotplug mechanism, and is still not suitable for live use. This change adds a separate, explicit, opt-in mechanism alongside that documented gap, not a change to the gap itself.)

## Impact

- New script at the repo root (native desktop install only - not the Docker image, which has no PipeWire-stop/`bluealsa` story explored at all).
- Depends on `bluez-alsa-utils` (the `bluealsa` package) as a new system dependency, and on `snd-aloop` being loaded (already documented dev-tooling convention from `support-virtual-test-devices`, though here it's an end-user runtime dependency, not just dev/test tooling).
- Requires PipeWire to already be stopped (same precondition `run_zynthian.sh`/`run_zynthian_vnc.sh` already establish for a Zynthian session) - `bluealsa` and PipeWire both try to claim the same BlueZ A2DP media endpoint, only one can hold it at a time.
- **Status: proposed, not yet implemented.**
