## ADDED Requirements

### Requirement: One workflow definition runs against both native and Docker sessions
A workflow script (ordered list of MIDI-injected actions and assertions) SHALL be defined once, environment-agnostically, and SHALL be executable against a native session and a Docker session without being separately authored or maintained per environment. Only launch/teardown and audio-capture mechanics MAY differ per environment; the workflow's steps and assertions SHALL NOT.

#### Scenario: Same workflow script runs against both environments
- **WHEN** a workflow script is run against a native session and, separately, against a Docker session
- **THEN** both runs execute the identical sequence of steps and assertions defined in that one script, with no environment-specific step list

#### Scenario: A new workflow requires no environment-specific porting step
- **WHEN** a new workflow script is added to the library
- **THEN** it is immediately runnable against both native and Docker sessions without additional per-environment authoring

### Requirement: Workflow steps are driven via MIDI-injected CUIA actions
The engine SHALL drive UI actions by injecting MIDI note-on/note-off events (via VMPK on the master MIDI channel, matching this project's already-validated VMPK/a2jmidid path) rather than simulated clicks or a new remote-control surface. A step SHALL be either a `ZYNSWITCH <index>` press with a controlled short/bold/long duration (via the note-on-to-note-off time gap) or a direct `SCREEN_<name>` jump.

#### Scenario: Short/bold/long press timing is respected
- **WHEN** a step specifies a `bold` or `long` press
- **THEN** the engine holds the note on for a duration exceeding the target session's configured `zynswitch_bold_us`/`zynswitch_long_us` threshold before releasing it, so the UI classifies the press the same way it would classify a real hardware press of that duration

#### Scenario: Direct screen jump
- **WHEN** a step specifies a `SCREEN_<name>` action
- **THEN** the engine injects the MIDI note mapped to that screen jump in `NoteCuiaDefault` (or the session's configured override) instead of navigating via switch presses

### Requirement: Dangerous CUIA actions cannot be injected
The engine SHALL only inject MIDI notes whose mapped CUIA is on an explicit allow-list; any workflow step referencing a CUIA not on that list SHALL fail before injection, not be silently skipped or injected anyway.

#### Scenario: Workflow references an unlisted CUIA
- **WHEN** a workflow script's step maps to a CUIA not present in the engine's allow-list
- **THEN** the engine refuses to run that step, reports which CUIA was rejected, and does not inject the corresponding MIDI note

#### Scenario: Known-dangerous CUIAs are never on the allow-list by default
- **WHEN** the engine's default allow-list is used unmodified
- **THEN** `POWER`, `RESTART_UI`, and any CUIA the default `NoteCuiaDefault` mapping reaches only via the admin screen's reboot/software-update/factory-reset actions are absent from it

### Requirement: Per-step log-diff assertion
After each injected step, the engine SHALL compare the target session's log output against the tail captured immediately before that step and SHALL fail the step if any new line at `ERROR` level or containing an unhandled traceback appears, without requiring a maintained global allowlist of expected/harmless lines.

#### Scenario: Step introduces a new error
- **WHEN** a step's injected action causes a new `ERROR`-level or traceback line to appear in the log that was not present before the step ran
- **THEN** the engine reports that step as failed, including the new log content, and does not continue past a hard failure without an explicit continue-on-failure option

#### Scenario: Pre-existing harmless log noise does not need allowlisting
- **WHEN** a log line already existed (e.g. from session boot) before a step's pre-step tail marker was captured
- **THEN** that line is outside the step's diff window and does not cause a false failure, without needing to be added to any allowlist

### Requirement: Structural assertion on saved snapshot content
A workflow SHALL be able to save its live-built state as a `.zss` snapshot and assert on that file's parsed JSON structure (e.g. a specific engine code present in a chain's slots) without requiring the session to still be running.

#### Scenario: Saved snapshot contains the expected chain
- **WHEN** a workflow saves a snapshot after building a chain with a specific engine
- **THEN** parsing the saved `.zss` as JSON and inspecting `chains`/`slots` confirms that engine's code is present, independent of whether the session is still live

#### Scenario: Saved snapshot is missing expected content
- **WHEN** a workflow's structural assertion checks for content that is not present in the saved `.zss`
- **THEN** the workflow is reported as failed, naming which expected structure was missing

### Requirement: Round-trip reload verification
A workflow SHALL be able to reload a snapshot it just saved into a fresh session and confirm the resulting audio/behavior matches expectations, reusing the same fixture-load-and-verify mechanism this capability's predecessor used for a committed fixture, now pointed at a freshly-produced file.

#### Scenario: Freshly-saved snapshot reloads and produces expected audio
- **WHEN** a workflow saves a snapshot, then starts a fresh session that loads that same snapshot and injects a note
- **THEN** the resulting audio output is confirmed non-silent, the same way the predecessor capability verified a committed fixture

#### Scenario: Freshly-saved snapshot fails to reproduce the built state
- **WHEN** the reloaded session does not produce the expected audio (e.g. a referenced resource is missing in the reload environment)
- **THEN** the workflow is reported as failed at the round-trip step specifically, distinguishing it from a failure during the original live build

### Requirement: Starting workflow library covers real usage patterns
The initial workflow library SHALL include at least: building a FluidSynth-based chain from scratch, adding an amp-simulator effect to an existing chain, and setting up MIDI recording - matching workflows a real user would perform, not synthetic/arbitrary action sequences.

#### Scenario: Each starting workflow runs end to end
- **WHEN** each of the initial workflow scripts is run against either environment
- **THEN** it completes all its steps, its assertions pass, and it reports overall pass/fail clearly

### Requirement: Clean teardown on every exit path
The engine SHALL leave no orphaned Docker containers, native background processes (Xvfb/VMPK/a2jmidid helpers it started), `snd-aloop` module state it did not itself introduce, or host audio-service state changes behind, regardless of whether a run passed, failed, or was interrupted.

#### Scenario: Run completes (pass or fail)
- **WHEN** a workflow run finishes all its steps, whether they passed or failed
- **THEN** the engine stops whatever session (container or native process group) it started, unloads `snd-aloop` only if this run loaded it, and restores the host's audio service to its pre-run state

#### Scenario: Run is interrupted
- **WHEN** a run is interrupted (e.g. Ctrl+C) before completing
- **THEN** the same teardown still runs via a cleanup trap

### Requirement: Fail-fast on device/session contention
The engine SHALL detect when a conflicting session is already using the resources a run needs (a prior test run's leftover container/process, or a real native/Docker Zynthian session already active) and SHALL refuse to start rather than silently competing for the same audio device.

#### Scenario: A previous test run's session is still present
- **WHEN** a run starts and finds a leftover container or process from a previous run under its fixed identifier
- **THEN** it cleans that up before starting a fresh one, without requiring manual intervention

#### Scenario: A real Zynthian session is already running
- **WHEN** the engine detects a native or Docker Zynthian session already active on the same machine
- **THEN** it exits immediately with a clear message identifying the conflicting session, without attempting to start its own
