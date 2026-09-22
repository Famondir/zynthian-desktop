## 1. Confirm root cause

- [x] 1.1 Reproduce: start the app, disconnect the audio interface, reconnect it, confirm it's still not selectable without a restart. Reproduced using `snd-aloop` as a stand-in device (see `support-virtual-test-devices`) rather than the physical Suprema/AG03 - mechanically equivalent (real ALSA-card-level udev add/remove), and confirmed the pre-fix behavior: with the audio device baked into `JACKD_OPTIONS`'s own `-C`/`-P` flags, a device appearing/disappearing after jackd startup was never picked up.
- [x] 1.2 Check jackd's own log during a disconnect/reconnect cycle. With the old fixed-device config, jackd simply never referenced the hotplugged device at all (it wasn't part of its own backend) - no crash, no xrun-storm, just silent non-recognition, confirming the root cause is "never looked" rather than "looked and failed".

## 2. Investigate the real-hardware hotplug path

- [x] 2.1 Read `zynautoconnect.py`'s `update_hw_audio_ports()`, `start_alsa_in()`, `start_alsa_out()`, `get_alsa_audio_devices()` in full to understand the intended architecture
- [x] 2.2 Determine what jackd backend real Zynthian hardware actually starts with (onboard codec fixed, or dummy?) - check `zynthian-sys` boot scripts/`zynthian_envars_V5.sh`-equivalent for the real hardware's `JACKD_OPTIONS`. Answer: onboard codec fixed (e.g. `-d hw:sndrpihifiberry` in `zynthian_envars_V5.sh`), never dummy, never the external device.
- [x] 2.3 Decide between the two approaches sketched in design.md (bridge-based, matching real hardware vs a simpler jackd-supervisor/restart approach) based on findings from 2.1-2.2. Decision: bridge-based - `update_hw_audio_ports()`/`start_alsa_in()`/`start_alsa_out()` are already fully implemented and match real hardware's pattern exactly; they were just never engaged (see 3.1/3.2).

## 3. Implement

- [x] 3.1 Adjust `JACKD_OPTIONS` in `/zynthian/config/zynthian_envars_custom.sh`: now `-d alsa -d hw:sofhdadsp,0` (laptop's onboard analog codec, fixed - was `-C hw:SUPREMA -P hw:sofhdadsp,3`, i.e. the Suprema baked in directly, playback wrongly on HDMI1 instead of the laptop speakers). Also fixed a related bug found along the way: `zynautoconnect.py`'s `jack_audio_device` parsing (line ~140) didn't strip a `,N` subdevice suffix, so a multi-device onboard card like `sofhdadsp` (unlike real hardware's single-device HATs) wouldn't have been recognised as jackd's own device and would've been redundantly hotplug-bridged too.
- [x] 3.2 If bridge-based: ensure `zynthian_gui_config.hotplug_audio_enabled` is set appropriately for the desktop build. Set `ZYNTHIAN_HOTPLUG_AUDIO=1` in `zynthian_envars_custom.sh`.

## 4. Validate

- [x] 4.1 Reconnect the same audio interface while the app is running - confirm selectable without restart. Validated with `snd-aloop`: `modprobe snd-aloop` while the app was running got bridged in (`zynain_Loopback`/`zynaout_Loopback` JACK ports appeared) within ~2s, no restart. Real-hardware confirmation (actual Suprema unplug/replug) still pending - needs @simon with the physical device.
- [ ] 4.2 Plug in a different/second audio interface while running - confirm selectable without restart. Not yet tried with a second concurrent device.
- [ ] 4.3 Repeat 4.1/4.2 with a different device type (e.g. Yamaha AG03 and/or a USB microphone, not just the Fisa Suprema) - confirm the fix is device-agnostic, not tuned to one interface. Needs physical hardware - not yet done.
- [ ] 4.4 Confirm the original always-worked case (device present at startup) still works. Not yet tried (current testing has all started with no external interface present).
- [x] 4.5 Confirm MIDI hotplug (already working) isn't broken by whatever audio changes are made. VMPK MIDI hotplug (a2j bridging + auto-connect) continued working correctly throughout all the audio changes/restarts in this session.
- [ ] 4.6 Note (don't fix): check whether the onboard 3.5mm mic jack's capture port activates correctly on cable insertion - out of scope per design.md, but worth confirming it isn't newly broken. Not yet checked.
