## MODIFIED Requirements

### Requirement: Bluetooth audio is a documented hotplug gap
Bluetooth audio pairing SHALL be explicitly documented as not covered by the "Audio hardware hotplug without restarting the app" requirement, with the underlying mechanism recorded, so this doesn't get silently rediscovered as a surprise or mistaken for a regression of that requirement.

#### Scenario: Pairing or connecting a Bluetooth audio device
- **WHEN** a Bluetooth audio device (e.g. headphones with mic) is paired or connected while the app is running
- **THEN** its audio does not currently become available as a source or sink, and this is recorded as a known consequence of `run_zynthian.sh` stopping the host's PipeWire/WirePlumber stack for the session (the only Bluetooth-audio-capable routing path on this machine), not a defect in the hotplug bridging itself, and as a permanent limitation for live/real-time musical use given A2DP's inherent ~150ms transport latency

## ADDED Requirements

### Requirement: Onboard 3.5mm jack presence gates capture-port availability
The onboard 3.5mm audio jack's ALSA jack-detection signal SHALL determine whether the onboard mic-in capture port is offered as an available audio source and used as a new chain's default audio input, so a user isn't offered, or auto-routed by default, to a floating, unplugged input.

#### Scenario: Creating a new audio-capable chain with nothing plugged in
- **WHEN** a new audio-capable chain is created while the onboard 3.5mm jack has nothing plugged into it
- **THEN** the chain's default audio input is empty (no source connected), not the onboard mic-in port

#### Scenario: Creating a new audio-capable chain with a device plugged in
- **WHEN** a new audio-capable chain is created while a device is plugged into the onboard 3.5mm jack
- **THEN** the chain's default audio input is the onboard mic-in port, matching today's existing default behavior

#### Scenario: Plugging a device into the onboard 3.5mm jack
- **WHEN** a headset or microphone is plugged into the laptop's onboard 3.5mm jack while the app is running
- **THEN** the onboard mic-in capture port reflects that presence within one polling cycle (the same ~2s cycle the existing USB-hotplug detection already uses), without restarting the app

#### Scenario: Unplugging a device from the onboard 3.5mm jack
- **WHEN** a device is removed from the laptop's onboard 3.5mm jack while the app is running
- **THEN** the onboard mic-in capture port reflects that absence within one polling cycle, without restarting the app

#### Scenario: A false-positive jack control is ignored
- **WHEN** the onboard codec reports its `Speaker Phantom Jack` control (a control with no real physical sense pin, permanently `on`)
- **THEN** it is not treated as a presence signal for gating purposes
