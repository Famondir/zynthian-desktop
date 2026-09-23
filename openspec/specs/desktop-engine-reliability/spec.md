## Purpose

Robustness requirements for zynthian-ui's core engines/GUI against conditions the original code didn't handle (crashes, deadlocks, wrong file recognition) - discovered while desktop-porting, but not desktop-specific bugs themselves.

## Requirements

### Requirement: Autoconnect tolerates devices without a port alias
`zynautoconnect` SHALL NOT raise an unhandled exception while holding its autoconnect lock when a MIDI input device has no JACK port alias set.

#### Scenario: Device with no alias under PipeWire's JACK-compat layer
- **WHEN** autoconnect checks a MIDI input device's alias against the configured external clock device name, and that device's `aliases` list is empty
- **THEN** the check treats it as not matching (no crash), and the autoconnect lock is released normally

### Requirement: Audio Input screen tolerates a stale selection index
The Audio Input screen SHALL NOT raise an unhandled exception when a click is processed against a row index that a concurrent background list refresh has made out of range.

#### Scenario: List rebuilt between click and processing
- **WHEN** `select_action()` is called with an index that is `>= len(list_data)` because `refresh_status()` rebuilt the list in the meantime
- **THEN** the call returns without raising an exception and without changing any chain's audio routing

### Requirement: Chain graph rebuild never leaves the autoconnect lock held
`zynthian_chain`'s audio/MIDI graph rebuild functions SHALL release the autoconnect lock even if an exception occurs while rebuilding the graph.

#### Scenario: Exception during audio graph rebuild
- **WHEN** `rebuild_audio_graph()` raises an exception after acquiring the autoconnect lock (e.g. a processor's engine is `None` after a failed start)
- **THEN** the autoconnect lock is released before the exception propagates, so subsequent chain operations do not hang

#### Scenario: Exception during MIDI graph rebuild
- **WHEN** `rebuild_midi_graph()` raises an exception after acquiring the autoconnect lock
- **THEN** the autoconnect lock is released before the exception propagates, so subsequent chain operations do not hang

### Requirement: FluidSynth prompt/output detection tolerates bracketed-paste escapes
The FluidSynth engine's interactive-CLI handling SHALL correctly detect the command prompt and command output even when the underlying readline/libedit emits bracketed-paste-mode ANSI escape sequences around them.

#### Scenario: Loading a soundfont with bracketed paste mode active
- **WHEN** FluidSynth's subprocess emits `"loaded SoundFont has ID N"` on a line preceded by a bracketed-paste ANSI escape or carriage return
- **THEN** `load_soundfont()` recognizes the success message and does not report failure or retry the load

#### Scenario: Detecting the ready prompt
- **WHEN** FluidSynth is ready for the next command and emits its `"> "` prompt wrapped in bracketed-paste escape sequences
- **THEN** `pexpect` matches the prompt and the engine proceeds, regardless of the exact escape/CR layout surrounding it

### Requirement: Sfizz preset discovery honours all declared preset extensions at bank root
The sfizz engine's preset discovery SHALL recognize any file extension listed in `preset_fexts` when the preset file sits directly in a bank folder, not only `.sfz`.

#### Scenario: DecentSampler preset at bank root
- **WHEN** a bank folder directly contains a `.dspreset` file (not inside its own subfolder)
- **THEN** that file appears in the preset list for that bank, the same way a `.sfz` file at that location would
