## ADDED Requirements

### Requirement: Virtual MIDI input for dev testing
Developers testing the native desktop install SHALL be able to send MIDI input without the Korg Fisa Suprema physically connected, using VMPK bridged through the existing `a2jmidid`/ALSA-seq path, auto-connected the same way real MIDI hardware is (no manual `jack_connect` per session).

#### Scenario: VMPK note reaches the active chain
- **WHEN** VMPK is running (ALSA MIDI driver) while `/zynthian/run_zynthian.sh` is running, and a key is played
- **THEN** the note reaches `ZynMidiRouter` and triggers the currently loaded synth engine, without any manual JACK port connection being made by the developer

### Requirement: Virtual audio-hotplug simulation for dev testing
Developers SHALL be able to simulate a USB audio interface being plugged/unplugged, without physical hardware, using the `snd-aloop` kernel module - which produces genuine ALSA-card-level udev add/remove events - to exercise and observe the same code paths a real device hotplug would.

#### Scenario: Simulating an audio interface appearing
- **WHEN** `snd-aloop` is loaded via `modprobe snd-aloop` while the app is running
- **THEN** a new ALSA card ("Loopback") appears in `/proc/asound/cards` and is discoverable the same way a newly-plugged-in USB audio interface would be

#### Scenario: Simulating an audio interface disappearing
- **WHEN** `snd-aloop` is unloaded via `modprobe -r snd-aloop` while the app is running
- **THEN** the "Loopback" ALSA card disappears the same way an unplugged USB audio interface would

### Requirement: Documented setup workflow
The virtual-device setup SHALL be documented and scripted (matching the existing `run_zynthian_docker.sh`/`run_zynthian_vnc.sh` pattern) so it's repeatable without re-deriving the steps each time.

#### Scenario: Following the documented workflow
- **WHEN** a developer follows the provided script/documentation to set up VMPK + `snd-aloop`
- **THEN** they reach a working virtual MIDI+audio input setup without needing to independently research ALSA/JACK/a2jmidid internals
