## Why

`investigate-jack-bluetooth-audio` (archived) confirmed the onboard 3.5mm jack's insertion/removal is a real, reliable ALSA signal (`Mic Jack`/`Headphone Jack` kcontrols on `hw:sofhdadsp`) that `zynautoconnect.py` simply never checks - and that wiring it in is low effort, since the existing hotplug detection is already a plain ~2s polling loop, not event-driven. This closes a real, confirmed gap in the desktop port's input handling: right now, plugging a mic/headset into the onboard jack does nothing, with no signal to the user about why.

## What Changes

- Poll the onboard codec's `Mic Jack`/`Headphone Jack` kcontrols (numid 11/12 on `hw:sofhdadsp`) on `zynautoconnect.py`'s existing ~2s hotplug polling cycle (`auto_connect_thread()`), excluding `numid=13` ("Speaker Phantom Jack"), which is a permanently-`on` false signal with no real sense pin.
- Use jack-presence as a gate on the onboard mic-in port's availability/selection, not as an `alsa_in`/`alsa_out` bridge lifecycle - unlike a USB device, the onboard codec's capture PCM/JACK port already exists permanently regardless of jack-sense state (confirmed live via `jack_lsp`), so there's no card/port to create or destroy here.
- **Stop auto-wiring the onboard mic into every new chain's default input.** Found while scoping this change: `zynthian_chain.py`'s `reset()` sets `self.audio_in = [1, 2]` for every new audio-capable chain ("Default is to route first 2 audio inputs to audio chains") - since `get_audio_capture_ports()` always lists `system:capture_1/2` (the onboard mic) first, *every* new chain gets auto-connected to the (usually unplugged, noisy) onboard mic by default today, independent of anything in this proposal's Audio Input screen scope. This is the concrete, user-reported symptom ("viel Rauschen" - lots of noise) motivating this change, not just a theoretical gap - fixing this default is now this change's primary concrete target, with the Audio Input screen/`device_cables` listing behavior (originally the whole scope) as a secondary, related fix.
- Concrete gating behavior for both the default-routing fix and the Audio Input screen listing (where/how the user sees this) is this change's own first investigation task, not assumed upfront - `get_alsa_audio_devices()` currently explicitly *excludes* the onboard device (`jack_audio_device`) from the external-hotplug-device list entirely, since it's jackd's own fixed backend, not something bridged in - so this needs its own code path, not a trivial extension of the existing USB-hotplug gating (`enable_audio_input_device`/`disabled_audio_in`).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `zynthian-desktop-runtime`: `investigate-jack-bluetooth-audio`'s "Onboard 3.5mm jack and Bluetooth audio are documented hotplug gaps" requirement's first scenario (3.5mm jack) changes from "does not currently activate" to actual jack-presence-aware behavior. The Bluetooth scenario is untouched - out of scope here, confirmed a permanent limitation by that same investigation.

## Impact

- `/zynthian/zynthian-ui/zynautoconnect/zynthian_autoconnect.py` (native `zynthian-ui` fork, `Famondir/zynthian-ui` branch `vangelis`) - `auto_connect_thread()`'s polling cycle, plus wherever the onboard mic-in port's availability actually needs to be surfaced (Audio Input screen and/or `device_cables`' display - to be confirmed by this change's own investigation, since it's a different code path than the existing external-device hotplug gating).
- `/zynthian/zynthian-ui/zyngine/zynthian_chain.py`'s `reset()` (the `self.audio_in = [1, 2]` default) - same fork, same branch.
- Native desktop install only - not the Docker image, which has no onboard-jack-sensing concern in the same sense (per `investigate-jack-bluetooth-audio`'s own scoping).
- **Status: proposed, not yet implemented.**
