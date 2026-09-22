## ADDED Requirements

### Requirement: Audio hardware hotplug without restarting the app
Reconnecting or newly plugging in a USB audio interface SHALL make it selectable as an audio source without requiring the whole app (and its jackd process) to be restarted, matching how MIDI hotplug already behaves.

#### Scenario: Reconnecting the same audio interface
- **WHEN** a previously-connected USB audio interface is unplugged and plugged back in while the app is running
- **THEN** its capture/playback ports become selectable again (e.g. in the Audio Input screen or `device_cables`' live cable display) without restarting the app

#### Scenario: Plugging in a different audio interface
- **WHEN** a USB audio interface that wasn't connected at app startup is plugged in while the app is running
- **THEN** its capture/playback ports become selectable without restarting the app
