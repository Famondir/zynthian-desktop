## ADDED Requirements

### Requirement: FluidSynth prompt/output detection tolerates bracketed-paste escapes
The FluidSynth engine's interactive-CLI handling SHALL correctly detect the command prompt and command output even when the underlying readline/libedit emits bracketed-paste-mode ANSI escape sequences around them.

#### Scenario: Loading a soundfont with bracketed paste mode active
- **WHEN** FluidSynth's subprocess emits `"loaded SoundFont has ID N"` on a line preceded by a bracketed-paste ANSI escape or carriage return
- **THEN** `load_soundfont()` recognizes the success message and does not report failure or retry the load

#### Scenario: Detecting the ready prompt
- **WHEN** FluidSynth is ready for the next command and emits its `"> "` prompt wrapped in bracketed-paste escape sequences
- **THEN** `pexpect` matches the prompt and the engine proceeds, regardless of the exact escape/CR layout surrounding it
