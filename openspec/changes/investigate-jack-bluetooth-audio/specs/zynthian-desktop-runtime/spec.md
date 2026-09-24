## ADDED Requirements

### Requirement: Onboard 3.5mm jack and Bluetooth audio are documented hotplug gaps
The onboard 3.5mm audio jack's insertion-detection and Bluetooth audio pairing SHALL be explicitly documented as not covered by the "Audio hardware hotplug without restarting the app" requirement, with the underlying mechanism recorded, so this doesn't get silently rediscovered as a surprise or mistaken for a regression of that requirement.

#### Scenario: Plugging a device into the onboard 3.5mm jack
- **WHEN** a headset or microphone is plugged into the laptop's onboard 3.5mm jack while the app is running
- **THEN** the corresponding capture/playback port does not currently activate, and this is recorded as a known gap distinct from ALSA-card hotplug (the codec exposes ALSA jack-detection kcontrols, but `zynautoconnect` does not yet act on control-change events, only card add/remove)

#### Scenario: Pairing or connecting a Bluetooth audio device
- **WHEN** a Bluetooth audio device (e.g. headphones with mic) is paired or connected while the app is running
- **THEN** its audio does not currently become available as a source or sink, and this is recorded as a known consequence of `run_zynthian.sh` stopping the host's PipeWire/WirePlumber stack for the session (the only Bluetooth-audio-capable routing path on this machine), not a defect in the hotplug bridging itself
