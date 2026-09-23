## Context

`zynautoconnect.py` iterates known MIDI input devices and checks `devices_in[devnum].aliases[0]` to match against a configured external clock device name. On real JACK, any client can set an alias on any port. PipeWire's `pipewire-jack` refuses `jack_port_set_alias()` on ports it doesn't own (errno -22), so under PipeWire a device can legitimately have an empty `aliases` list.

## Goals / Non-Goals

**Goals:**
- Never crash inside a locked autoconnect section, regardless of alias state.

**Non-Goals:**
- Fixing PipeWire's alias rejection itself (out of our control) - see `zynthian-desktop-runtime`'s decision to use real jackd instead.

## Decisions

- Guard the check with `devices_in[devnum].aliases and ...` before indexing `[0]`, rather than wrapping the whole function in a broad try/except, to keep the fix minimal and the failure mode explicit (device has no alias -> just doesn't match the clock device, nothing more).

## Risks / Trade-offs

- None identified; this is a strict safety fix with no behavioural change when an alias is present.
