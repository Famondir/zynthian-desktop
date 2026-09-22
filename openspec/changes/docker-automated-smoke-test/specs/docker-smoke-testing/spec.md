## ADDED Requirements

### Requirement: Headless Docker boot verification
The smoke-test script SHALL run the Zynthian Docker image against a private, headless Xvfb display (not the host's real display) and SHALL verify the GUI actually rendered, without requiring a human to view the session.

#### Scenario: GUI renders successfully
- **WHEN** the smoke-test script starts the Docker image against its private Xvfb display
- **THEN** a screenshot of that display is captured and found to be non-blank (pixel standard deviation above the script's threshold), and the script reports this check as passed

#### Scenario: GUI fails to render
- **WHEN** the container exits early, crashes, or never paints a window before the boot timeout elapses
- **THEN** the script reports this check as failed with a diagnostic message and exits non-zero, without hanging indefinitely

### Requirement: Automated MIDI-to-audio signal path verification
The smoke-test script SHALL drive a virtual MIDI input (VMPK, via the same a2jmidid bridging path validated for native testing) into the running container and SHALL confirm the resulting audio signal actually reaches the container's audio output stage, without requiring the physical Suprema or a human listening. The container's `jackd` SHALL be bound to a `snd-aloop` virtual audio device as its output; the audio capture used to verify non-silence is an implementation detail (see design.md) and is not required to read back through that same loopback device.

#### Scenario: Note reaches an active chain and produces audio
- **WHEN** the script injects a note-on/note-off pair via VMPK against the container's running session, with an active chain (e.g. fluidsynth) connected to the main output
- **THEN** the script captures a short buffer of the resulting output signal and confirms it is non-silent (RMS amplitude above the script's threshold), and reports this check as passed

#### Scenario: MIDI does not reach the chain
- **WHEN** the injected note produces no corresponding JACK MIDI connection, or the captured audio buffer stays silent
- **THEN** the script reports this check as failed, including which stage (MIDI routing vs. audio output) did not produce the expected result, and exits non-zero

### Requirement: Clean teardown on every exit path
The smoke-test script SHALL leave no orphaned Docker containers, `snd-aloop` module state it did not itself introduce, or host audio-service state changes behind, regardless of whether the run passed, failed, or was interrupted.

#### Scenario: Run completes (pass or fail)
- **WHEN** the smoke-test script finishes all checks, whether they passed or failed
- **THEN** it stops the Docker container it started, unloads `snd-aloop` only if this run loaded it, and restores the host's audio service (PipeWire) to the state it was in before the run started

#### Scenario: Run is interrupted
- **WHEN** the script is interrupted (e.g. Ctrl+C) before completing its checks
- **THEN** the same teardown (container stop, conditional `snd-aloop` unload, host audio service restore) still runs via a cleanup trap

### Requirement: Fail-fast on device contention
The smoke-test script SHALL detect when a conflicting session is already using the resources it needs (a prior smoke-test container, or a real native/Docker Zynthian session already running) and SHALL refuse to start rather than silently competing for the same audio device.

#### Scenario: A previous smoke-test container is still present
- **WHEN** the script starts and finds a leftover container from a previous run under its fixed container name
- **THEN** it removes that leftover container before starting a fresh one, without requiring manual cleanup

#### Scenario: A real Zynthian session is already running
- **WHEN** the script detects a native or Docker Zynthian session already active on the same machine
- **THEN** it exits immediately with a clear message identifying the conflicting session, without attempting to start its own
