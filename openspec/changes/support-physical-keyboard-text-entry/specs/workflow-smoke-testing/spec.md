## MODIFIED Requirements

### Requirement: Workflow steps are driven via MIDI-injected CUIA actions
The engine SHALL drive UI actions by injecting MIDI note-on/note-off events (via VMPK on the master MIDI channel, matching this project's already-validated VMPK/a2jmidid path) rather than simulated clicks or a new remote-control surface. A step SHALL be either a `ZYNSWITCH <index>` press with a controlled short/bold/long duration (via the note-on-to-note-off time gap) or a direct `SCREEN_<name>` jump. The single exception is a `type` step, which types text as physical key presses into the session's X display, because physical keyboard input is itself the behaviour under test there and has no CUIA equivalent.

#### Scenario: Short/bold/long press timing is respected
- **WHEN** a step specifies a `bold` or `long` press
- **THEN** the engine holds the note on for a duration exceeding the target session's configured `zynswitch_bold_us`/`zynswitch_long_us` threshold before releasing it, so the UI classifies the press the same way it would classify a real hardware press of that duration

#### Scenario: Direct screen jump
- **WHEN** a step specifies a `SCREEN_<name>` action
- **THEN** the engine injects the MIDI note mapped to that screen jump in `NoteCuiaDefault` (or the session's configured override) instead of navigating via switch presses

#### Scenario: Typing text into the session
- **WHEN** a step specifies `type: <text>` (optionally followed by a named key such as `Return`)
- **THEN** the engine sends those key presses to the session's X display (native and Docker alike) and the step gets the same per-step log-diff check as every other step
