## ADDED Requirements

### Requirement: Sfizz preset discovery honours all declared preset extensions at bank root
The sfizz engine's preset discovery SHALL recognize any file extension listed in `preset_fexts` when the preset file sits directly in a bank folder, not only `.sfz`.

#### Scenario: DecentSampler preset at bank root
- **WHEN** a bank folder directly contains a `.dspreset` file (not inside its own subfolder)
- **THEN** that file appears in the preset list for that bank, the same way a `.sfz` file at that location would
