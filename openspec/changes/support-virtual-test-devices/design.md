## Context

The native desktop install (`/zynthian/run_zynthian.sh`) runs its own standalone `jackd` + `a2jmidid`, separate from the host's PipeWire session (which is paused for the duration - see `run_zynthian.sh`'s PipeWire stop/restart dance). MIDI hardware hotplug already works via `a2jmidid`'s ALSA-seq bridging; the Korg Fisa Suprema is the only device that's been used to exercise either MIDI or audio input so far, which means neither path can currently be tested without it physically connected.

During this session, two virtual stand-ins were set up ad hoc and confirmed working:
- **MIDI**: `vmpk` (Virtual MIDI Piano Keyboard, `apt install vmpk`), configured to send over ALSA (its default), bridged into JACK MIDI by the already-running `a2jmidid` exactly like real hardware.
- **Audio**: the `snd-aloop` kernel module (`modprobe snd-aloop`), which creates a genuine ALSA card ("Loopback", with paired playback/capture subdevices) - `modprobe`/`rmmod` produce real udev card add/remove events, the same signal a USB device hotplug produces, unlike PipeWire/PulseAudio monitor-sink routing which never touches ALSA's card list at all.

Getting MIDI actually working surfaced a real bug (not just missing tooling): `zynautoconnect.py`'s `update_hw_audio_ports()` only picks up MIDI source ports that are either JACK-flagged `is_physical` or on a short hardcoded whitelist (`QmidiNet`, `rtpmidi`, `netump`, `TouchOSC Bridge`). `a2jmidid` only sets `JackPortIsPhysical` on ports bridged from ALSA **kernel**-type clients (real hardware, or kernel-backed virtual devices like `snd-virmidi`) - VMPK is a `type=user` ALSA-seq client, so its bridged `a2j:MIDI Out` port was invisible to that scan and never auto-connected to `ZynMidiRouter`, even though `a2jmidid` itself bridged it correctly.

## Goals / Non-Goals

**Goals:**
- A documented, scripted, repeatable way to simulate the Suprema's MIDI input (VMPK) and audio input (`snd-aloop`, optionally fed by `fluidsynth`) on the native desktop install, for dev testing when the physical device isn't at hand.
- VMPK's bridged MIDI port SHALL be auto-connected the same way real MIDI hardware is, with no manual `jack_connect` needed per session.
- Document the `modprobe`/`rmmod snd-aloop` cycle as the standard way to simulate an audio interface's hotplug for dev testing (this change does not fix audio hotplug itself - see `fix-audio-hotplug-support` - it only documents `snd-aloop` as a reliable way to trigger and observe that code path without physical hardware).

**Non-Goals:**
- Fixing the actual audio-hotplug bug - that's `fix-audio-hotplug-support`'s scope; this change only gives that work (and future audio-input work) a way to be exercised without the Suprema.
- Making `snd-aloop` a supported *end-user* audio source (e.g. for routing desktop app audio into Zynthian as a feature) - this is dev/test tooling only.
- The Docker desktop image. `docker/entrypoint.sh` runs its own `jackd`/`a2jmidid` inside the container with `--device /dev/snd` passed through from the host, so host-loaded `snd-aloop`/VMPK-via-ALSA-seq would in principle be visible there too (same kernel, same `/dev/snd`) - but this hasn't been tested and isn't a stated requirement of this change. Left as an open question below rather than assumed.

## Decisions

- **VMPK over alternatives (e.g. `aplaymidi` scripted files, `amidi` raw MIDI, a custom test harness).** VMPK is an interactive GUI keyboard, not just a scripted note-injector - matches the actual use case (a human testing the UI live, the same way they'd play the Suprema), is a standard, already-packaged Linux tool, and needs zero custom code.
- **`snd-aloop` over PipeWire/PulseAudio virtual sinks.** The whole point is exercising the *ALSA-card-level* hotplug path (`get_alsa_audio_devices()`, `update_hw_audio_ports()`) the same way a real USB interface does. A PipeWire monitor sink never registers as an ALSA card and so would test a different (and, for this native install, largely bypassed - PipeWire is stopped) code path entirely.
- **MIDI whitelist fix lives in this change, not `fix-audio-hotplug-support`.** It's a MIDI-side gap (VMPK not recognized), not the audio-hotplug bug; `fix-audio-hotplug-support` is scoped to real USB audio hardware only. Keeping them separate keeps that change's diff focused on its own root cause.
- **Match by ALSA client name substring (`a2j:MIDI Out`), not VMPK's PID/ALSA client number.** `zynautoconnect`'s existing whitelist entries (e.g. `"QmidiNet:out"`) are matched via `jclient.get_ports()`, which does regex/substring matching against the full JACK port name - `"a2j:MIDI Out"` matches `a2j:MIDI Out [128] (capture): [0] out"` regardless of VMPK's per-launch ALSA client number, so no restart-sensitive hardcoding is introduced. Same pattern already used for the other whitelist entries.

## Risks / Trade-offs

- [VMPK's default ALSA client name ("MIDI Out") is generic - the whitelist match could theoretically pick up an unrelated app that happens to register the same ALSA-seq client name] → Low real-world risk (scoped to `a2j:`-prefixed bridge ports, i.e. still requires going through a2jmidid), and matches the precedent already set by the other whitelist entries (also generic-ish names like "aubio").
- [`snd-aloop`'s card is silent by default - testing audio-hotplug *behavior* (ports appearing/disappearing) doesn't confirm actual signal flow] → Documented `fluidsynth -a alsa -o audio.alsa.device=hw:Loopback,0,0` as the way to push a real, audible signal through it when that matters.
- [This whole workflow only covers the native install (`/zynthian/run_zynthian.sh`); Docker desktop image support is unverified] → Called out as an open question, not silently assumed either way.

## Open Questions

- Does this virtual-device setup work unmodified against the Docker desktop image (`run_zynthian_docker.sh`), given it also gets `/dev/snd` passed through? Needs a quick test; if yes, worth a one-line doc note rather than a new script.
