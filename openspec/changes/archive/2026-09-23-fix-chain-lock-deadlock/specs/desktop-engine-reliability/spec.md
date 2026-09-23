## ADDED Requirements

### Requirement: Chain graph rebuild never leaves the autoconnect lock held
`zynthian_chain`'s audio/MIDI graph rebuild functions SHALL release the autoconnect lock even if an exception occurs while rebuilding the graph.

#### Scenario: Exception during audio graph rebuild
- **WHEN** `rebuild_audio_graph()` raises an exception after acquiring the autoconnect lock (e.g. a processor's engine is `None` after a failed start)
- **THEN** the autoconnect lock is released before the exception propagates, so subsequent chain operations do not hang

#### Scenario: Exception during MIDI graph rebuild
- **WHEN** `rebuild_midi_graph()` raises an exception after acquiring the autoconnect lock
- **THEN** the autoconnect lock is released before the exception propagates, so subsequent chain operations do not hang
