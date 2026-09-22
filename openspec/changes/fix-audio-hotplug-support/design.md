## Context

`desktop-port-foundation` (archived) chose to run jackd directly against the test interface in use at the time (`-d alsa -C hw:SUPREMA -P hw:sofhdadsp,3`), which was the simplest way to get audio working at all. That decision is now visibly limiting: jackd's native ALSA backend binds to that hardware once at process start and has no supported way to rebind if the device disappears and comes back - contrasted with `a2jmidid`, which bridges MIDI through ALSA-seq, a layer that *does* support hotplug natively, which is why MIDI kept working live in the same test session.

## Goals / Non-Goals

**Goals:**
- Reconnecting/newly-plugging-in a USB audio interface should make it selectable as an audio source without restarting the app, matching how MIDI already behaves.
- This applies to any ALSA-recognized USB audio device - audio interfaces (e.g. Fisa Suprema, Yamaha AG03) and USB microphones alike - not just the specific device used to discover the bug. Any device that enumerates via `get_alsa_audio_devices()`/ALSA should be covered by the same bridging mechanism, since the fix operates at the ALSA-card level, not per-device.

**Non-Goals:**
- Solving hotplug for the *very first* audio device jackd needs at startup (jackd still needs to start against *something* - a dummy backend or a fixed onboard device) - this is about devices connected *after* jackd is already running.
- Multi-device simultaneous audio (multiple independent interfaces used together) - out of scope unless it falls out naturally from the fix.
- 3.5mm jack (onboard codec) microphone insertion. This is not ALSA-card hotplug - the onboard codec (`hw:sofhdadsp`) doesn't disappear/reappear from ALSA when a cable is plugged into its jack. Whether its capture port activates correctly on jack insertion is a kernel/codec jack-sensing concern, unrelated to the `alsa_in`/`alsa_out` bridging this change adds. Not addressed here; open question if it turns out to be broken.
- Virtual/software audio sources (e.g. capturing desktop audio such as Spotify playback via a PipeWire/PulseAudio monitor sink as a JACK input). This is a different mechanism (software audio routing, not ALSA hardware hotplug) and is out of scope for this change - would need its own change if wanted.

## Decisions (proposed, not yet validated)

- **Start jackd against a fixed/dummy backend, bridge real interfaces in via `alsa_in`/`alsa_out`.** This mirrors `zynautoconnect.py`'s own existing `start_alsa_in()`/`start_alsa_out()` functions, gated by `zynthian_gui_config.hotplug_audio_enabled` - machinery already written for real hardware's hotplug support, just never exercised by our desktop `JACKD_OPTIONS`. Needs investigation: does jackd's `-d dummy` backend provide acceptable latency/behaviour on this desktop setup, and do `start_alsa_in`/`start_alsa_out` work correctly when jackd wasn't started via the exact sequence real hardware's boot process uses?
- Alternative (simpler, not yet compared): keep jackd's current fixed-device backend, but add a supervisor in `run_zynthian.sh` that detects the ALSA device disappearing (e.g. jackd erroring out or the device vanishing from `/proc/asound/`) and automatically restarts jackd + reconnects, so the *app* doesn't need restarting even though jackd briefly does. Less elegant, but much smaller change, and doesn't require understanding the full hotplug bridge machinery.

## Risks / Trade-offs

- The bridge-based approach (matching real hardware) is the "correct" fix but touches audio startup, one of the most iteration-heavy and fragile parts of this whole project so far (see `zynthian-desktop-runtime`'s own history of jackd/PipeWire issues) - expect this to need several rounds of live testing, same as most audio-path changes have.
- The supervisor/restart-jackd approach is simpler but means a brief audio dropout on hotplug rather than seamless bridging, and doesn't match how real hardware behaves.
