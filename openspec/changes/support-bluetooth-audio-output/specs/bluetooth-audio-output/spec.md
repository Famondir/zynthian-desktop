## ADDED Requirements

### Requirement: Opt-in Bluetooth audio output bridge
A new native-install script SHALL bridge a connected Bluetooth device's audio output into the Zynthian audio graph via `bluealsa` and a `snd-aloop` intermediary, as an explicit, manually-started action independent of `/zynthian/run_zynthian.sh`.

#### Scenario: Starting the bridge with a connected device
- **WHEN** a user runs the script with a paired, connected Bluetooth audio device and an already-running Zynthian session (PipeWire already stopped)
- **THEN** that device's audio output becomes available on the `Loopback` ALSA card, discoverable by the running app the same way any other `Loopback`-routed source already is

#### Scenario: PipeWire not yet stopped
- **WHEN** the script is run while PipeWire is still running
- **THEN** it fails with a clear error explaining that PipeWire must be stopped first (e.g. via an active `run_zynthian.sh`/`run_zynthian_vnc.sh` session), rather than silently producing no audio

### Requirement: Latency limitation is clearly documented to the user
The script SHALL prominently state the ~150-190ms latency and that this makes the bridge unsuitable for live/real-time monitoring while playing, before starting the bridge.

#### Scenario: Running the script
- **WHEN** a user runs the script
- **THEN** the latency caveat is printed clearly as part of normal output, not only documented in a source comment
