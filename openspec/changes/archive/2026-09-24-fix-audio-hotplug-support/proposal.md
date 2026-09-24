## Why

Discovered while testing `device_cables`: MIDI capture/playback ports update live when the Korg Fisa Suprema is powered on/off (confirmed working - `a2jmidid`'s ALSA-seq bridging supports real hotplug), but audio capture ports do **not** - the user had to restart the whole app to even select the Suprema as an audio source after it reconnected. This is a real usability regression from the native install's design, not specific to the cable-display feature that surfaced it.

The Suprema is just the device that surfaced the bug during testing - it is not the target. The user also has a Yamaha AG03 audio interface and USB microphones they'd want to hotplug the same way, so the fix needs to work for any ALSA-recognized USB audio device, not be tied to the Suprema specifically.

## What Changes

- Root cause (already identified, not yet fixed): `run_zynthian.sh` starts `jackd` with `-d alsa -C hw:SUPREMA -P hw:sofhdadsp,3 ...` - the device names are baked directly into jackd's own ALSA backend at startup. jackd's native ALSA backend does not tolerate its backing hardware disappearing/reappearing at runtime the way `a2jmidid`'s ALSA-seq bridging does for MIDI.
- Real Zynthian hardware/hotplug design (see `zynautoconnect.update_hw_audio_ports()`, `start_alsa_in()`/`start_alsa_out()`) expects jackd's own backend to be fixed (e.g. the onboard codec or a dummy backend) and *external* audio devices to be bridged in dynamically via separate `alsa_in`/`alsa_out` helper processes per hotplugged device - not wired directly into jackd's `-C`/`-P` flags. Our desktop setup never adopted this pattern; it just pointed jackd straight at the one interface being tested.
- This change proposes adapting `run_zynthian.sh`/`JACKD_OPTIONS` to use the same bridge-based hotplug pattern real hardware uses, so a reconnected (or newly plugged in) USB audio interface is picked up without restarting the app.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `zynthian-desktop-runtime`: adds a requirement that audio hardware hotplug behaves the same way MIDI hotplug already does (no app restart needed).

## Impact

- `run_zynthian.sh` (jackd startup / `JACKD_OPTIONS`), possibly `/zynthian/config/zynthian_envars_custom.sh`.
- Depends on understanding `zynautoconnect.py`'s existing `start_alsa_in`/`start_alsa_out`/`update_hw_audio_ports` hotplug machinery (already present in the codebase for real hardware, just not exercised by our desktop jackd startup).
- **Status: proposed, not yet implemented.** Root cause is diagnosed with reasonable confidence from code review (`JACKD_OPTIONS`'s direct `-C hw:SUPREMA` binding vs `a2jmidid`'s bridging), but not yet verified by an actual fix-and-retest cycle - needs the user's live setup to confirm.
