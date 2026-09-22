## Why

Testing MIDI/audio hotplug behavior (see `fix-audio-hotplug-support`) and general MIDI/audio input on the desktop port currently requires the physical Korg Fisa Suprema to be plugged in - there's no way to exercise those code paths without it. This surfaced while setting up ad hoc dev tooling for exactly that (VMPK for MIDI, `snd-aloop` for audio) during this session; formalizing it as a documented, repeatable workflow means future hotplug/MIDI-input testing (and CI-less manual regression checks) doesn't depend on having the Suprema on hand.

## What Changes

- Add a dev script (matching the existing `run_zynthian_docker.sh`/`run_zynthian_vnc.sh` pattern at the repo root) that sets up `vmpk` (virtual MIDI keyboard, bridged into ALSA-seq/a2jmidid) and the `snd-aloop` kernel module (a real ALSA loopback card - genuine udev add/remove events on `modprobe`/`rmmod`, mechanically equivalent to a USB device hotplug) as stand-ins for the Suprema.
- Fix `zynautoconnect.py`'s `update_hw_audio_ports()` (native install at `/zynthian/zynthian-ui/zynautoconnect/zynthian_autoconnect.py`) to recognize `a2j:MIDI Out` (VMPK's default ALSA client name, bridged by a2jmidid) as a virtual-hardware MIDI source - `a2jmidid` only marks bridged ports `JackPortIsPhysical` for kernel-type ALSA clients (real/virtual-hardware drivers), not VMPK's `type=user` ALSA-seq client, so it was invisible to the existing `is_physical` hardware scan and never got auto-connected to `ZynMidiRouter`. (This code change was already made ad hoc this session and is being formalized/documented here rather than folded into `fix-audio-hotplug-support`, which is scoped to real USB hardware only.)
- Document the `modprobe snd-aloop` / `modprobe -r snd-aloop` cycle as the standard way to simulate an audio interface being plugged/unplugged for dev testing, including feeding it a real signal via `fluidsynth` driven by VMPK.

## Capabilities

### New Capabilities
- `virtual-test-devices`: dev-only tooling and documentation for simulating the Suprema's MIDI and audio input via VMPK + `snd-aloop` on the native desktop install, for use when the physical device isn't available.

### Modified Capabilities
(none - `zynthian-desktop-runtime`'s existing requirements aren't changing; this only makes an already-intended-to-work code path additionally recognize a virtual MIDI source. `fix-audio-hotplug-support` covers the actual audio-hotplug requirement change.)

## Impact

- New script at the repo root (dev-only, native install target `/zynthian/run_zynthian.sh`, not the Docker image).
- `/zynthian/zynthian-ui/zynautoconnect/zynthian_autoconnect.py` (native `zynthian-ui` checkout, `Famondir/zynthian-ui` fork) - small addition to the existing virtual-MIDI-source whitelist in `update_hw_audio_ports()`.
- Documentation only for the `snd-aloop` audio side - no code change identified as necessary there (Zynthian's ALSA device enumeration already treats any ALSA card generically); called out as a task to confirm.
- Out of scope: the Docker desktop image (`docker/`) - noted as a follow-up question in design.md, not assumed either way.
