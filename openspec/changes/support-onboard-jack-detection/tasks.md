## 1. Confirm the gating points

- [ ] 1.1 Decide between design.md's two candidate approaches for the Audio Input screen/`device_cables` listing (filter out of `get_audio_capture_ports()` entirely vs. keep listed but marked disconnected) - check how the Audio Input screen (`zyngui/zynthian_gui_audio_in.py`) and `device_cables` handle a port disappearing from that list already (precedent from the USB-hotplug path), and prefer consistency with that over inventing a new pattern.
- [ ] 1.2 Decide what happens to an already-routed chain if the jack is unplugged mid-session (silently keep connected but now silent, vs. actively disconnect) - check `stop_alsa_in`'s equivalent handling for the USB case, if any, for consistency. Applies to both a chain that got the new-default input (task 2) and one where the user explicitly selected the onboard mic via the Audio Input screen.

## 2. Implement jack-presence polling and the default-routing fix

- [ ] 2.1 Add a jack-presence check (`amixer -c sofhdadsp cget numid=11` for `Mic Jack`, excluding `numid=13`) to `zynautoconnect.py`'s `auto_connect_thread()`, on the same ~2s cycle as the existing `update_hw_audio_ports()`/`update_hw_midi_ports()` checks, exposing the current state somewhere `zynthian_chain.py`'s `reset()` can read it.
- [ ] 2.2 In `zynthian_chain.py`'s `reset()`, change the `self.audio_in = [1, 2]` default (for audio-capable, non-bus, non-"MR" chains) to `[]` when the onboard mic isn't jack-sensed present, per design.md's primary decision - keep `[1, 2]` unchanged when it is present.
- [ ] 2.3 Wire the presence state into `get_audio_capture_ports()`'s onboard `system:capture_*` entries for the Audio Input screen/`device_cables` listing, per the 1.1 decision.
- [ ] 2.4 Handle the mid-session unplug case per the 1.2 decision.

## 3. Validate

- [ ] 3.1 Live test (primary fix): with nothing in the onboard jack, create a new audio-capable chain (e.g. an audio effect/vocoder-style chain), confirm its default input is empty, not the onboard mic - this is the concrete noise problem this change exists to fix.
- [ ] 3.2 Live test: repeat 3.1 with a device plugged into the onboard jack, confirm the default input is the onboard mic as before (unchanged behavior when present).
- [ ] 3.3 Live test: start the app with nothing in the onboard jack, confirm the mic-in port's state (hidden/marked per 1.1's decision) in both the Audio Input screen and `device_cables`.
- [ ] 3.4 Live test: plug a device into the onboard jack while the app is running, confirm the port becomes available within ~2s, no restart needed.
- [ ] 3.5 Live test: unplug it again, confirm the port reflects that within ~2s, and confirm the mid-session-unplug behavior from 1.2/2.4 works as decided.
- [ ] 3.6 Confirm the existing USB-hotplug path (`fix-audio-hotplug-support`) and `device_cables` overflow handling (`fix-cable-list-overflow`) aren't disturbed by this change - both share code/rendering paths this change touches.
- [ ] 3.7 Confirm `Speaker Phantom Jack` (numid=13) is never treated as a presence signal (it's permanently `on` - a regression here would mean gating never actually excludes anything).
