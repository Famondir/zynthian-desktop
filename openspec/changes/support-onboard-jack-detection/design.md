## Context

`investigate-jack-bluetooth-audio` (archived) fully de-risked the signal side of this: `hw:sofhdadsp` exposes ALSA jack-detection kcontrols `Mic Jack` (numid=11) and `Headphone Jack` (numid=12), confirmed live to flip reliably on physical insertion/removal. `numid=13` ("Speaker Phantom Jack") is a permanently-`on` false signal (no real sense pin for the built-in speaker output) and must be excluded. `zynautoconnect.py`'s existing hotplug detection (`auto_connect_thread()`) is already a plain ~2s polling loop, not event-driven, so no new dependency is needed - a subprocess `amixer -c sofhdadsp cget numid=11/12` check fits directly into the existing cycle.

What that investigation didn't nail down is *where in the code the actual gating needs to happen*, because the onboard mic-in port doesn't behave like a USB device at all:

- `get_alsa_audio_devices()` (the function behind the USB-hotplug device list, `enable_audio_input_device`/`disabled_audio_in`) explicitly **excludes** `jack_audio_device` (the onboard codec) from its results - it's jackd's own fixed backend, never something bridged in via `alsa_in`, so it was never part of that mechanism to begin with.
- `get_audio_capture_ports()` (used by both the Audio Input screen, `zyngui/zynthian_gui_audio_in.py`, and `device_cables`' cable display) returns `system:capture_*` (the onboard codec's own physical JACK ports, from jackd's fixed backend) **unconditionally**, alongside `zynain:*` (the actually-bridged external devices). The onboard mic-in port is *always* in this list today, regardless of whether anything is plugged into the jack - confirmed by reading the function directly, not assumed.

So today, a user can already select the onboard mic input in the Audio Input screen at any time, jack-sensed or not - selecting it when nothing is plugged in just routes silence/noise into the chain, with no indication anything is wrong. That's a gap to close, but it's not the primary one: `zynthian_chain.py`'s `reset()` sets `self.audio_in = [1, 2]` for every new audio-capable chain ("Default is to route first 2 audio inputs to audio chains"), and since `get_audio_capture_ports()` always lists `system:capture_1/2` (the onboard mic) first, this means **every new chain is auto-wired to the onboard mic by default today**, whether the user ever visits the Audio Input screen or not. This is the concrete, reported symptom (noise on new chains) motivating this change - fixing the Audio Input screen's listing alone wouldn't touch this default-routing path at all, since `get_input_pairs()` reads `self.audio_in` (indices into `get_audio_capture_ports()`), not the screen's own selection state.

## Goals / Non-Goals

**Goals:**
- Poll `Mic Jack`/`Headphone Jack` on the existing ~2s `auto_connect_thread()` cycle, excluding the `numid=13` false signal.
- Stop `zynthian_chain.py`'s `self.audio_in = [1, 2]` default from wiring in the onboard mic when it isn't jack-sensed as present - this is the primary, concrete fix (see Context).
- Make the onboard mic-in port's presence in the Audio Input screen (and `device_cables`' display) reflect actual jack-sense state, so a user isn't offered/auto-routed to a floating, unplugged input either - a secondary fix, same underlying signal.
- Keep this additive to `get_audio_capture_ports()`/its consumers - no changes to the USB-hotplug mechanism (`get_alsa_audio_devices`, `enable_audio_input_device`) at all, since the onboard device was never part of that path.

**Non-Goals:**
- Headphone-out gating symmetry isn't assumed necessary - the investigation's live test confirmed `Headphone Jack` also flips reliably, but whether the *output* side needs the same treatment (vs. just always being available, matching how the onboard speaker output already always works) is this change's own open question, not assumed either way upfront.
- Bluetooth - confirmed a permanent limitation by `investigate-jack-bluetooth-audio`, entirely out of scope here.
- The Docker image - no onboard-jack-sensing concern there in the same sense.
- Real-hardware jack-sensing HAT support or any real-Pi-hardware behavior - this is desktop-port-only, matching this whole family of changes' scope (`zynthian-desktop-runtime`).

## Decisions

**Default-routing fix (primary): when the onboard mic isn't jack-sensed as present, `zynthian_chain.py`'s `reset()` SHALL default `self.audio_in` to `[]` (no input connected) instead of `[1, 2]`, for new audio-capable chains.** `[]` already has clean precedent in the same function (used for the main mix bus and for "MR" processors - "We don't want any direct audio input connections to buses") - reusing that same "no default" value rather than inventing a new state. If the onboard mic *is* jack-sensed present at chain-creation time, `[1, 2]` still applies unchanged (this fix only removes the *floating, unplugged* default, not the feature of having a default at all when something's actually connected). Whether to also skip to the next available external device's indices when the onboard mic is absent but something else is connected (e.g. a USB interface) is an open question for implementation - simplest correct behavior is just `[]` regardless; a smarter fallback is a nice-to-have, not required to fix the reported noise problem.

**Audio Input screen / `device_cables` listing fix (secondary): not yet made** - implementation's first task is confirming exactly how to wire jack-presence into `get_audio_capture_ports()`'s consumers for this part. Two candidate approaches, to be evaluated once implementation starts:
1. Filter `system:capture_*` out of `get_audio_capture_ports()`'s result entirely when not jack-sensed as present (simplest, matches "don't offer a floating input" most directly, but means the port visually disappears/reappears from the Audio Input screen and `device_cables`, which needs checking against how those screens handle a previously-selected-now-gone port - similar to how a USB device's chain routing is handled when it's unplugged, worth reusing that precedent if it exists).
2. Keep it always listed but mark/label it as disconnected when not jack-sensed (less surprising if a chain is already routed to it, more UI work to add a visual state).

## Risks / Trade-offs

- This touches `get_audio_capture_ports()`, which is shared by both the Audio Input screen and `device_cables`' cable display (`fix-cable-list-overflow`'s own recent work touched the latter's rendering) - changes here have two consumers to verify, not one.
- If a chain is already actively routed to the onboard mic input when the jack is unplugged mid-session, what happens to that chain's routing needs deciding (silently keep it connected but now silent, vs. actively disconnect it) - worth checking how the existing USB-hotplug disconnect path (`stop_alsa_in`) handles the equivalent case, if it does, for consistency.
