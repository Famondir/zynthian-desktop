## ADDED Requirements

### Requirement: Desktop install ships working LV2 reverb effects
The native desktop install and the Docker image SHALL provide at least three LV2 reverb plugins from different plugin families that can be added to a chain and process audio.

#### Scenario: Reverb added after a MIDI synth
- **WHEN** the user adds an Audio Effect from the "Reverb" category to a chain containing a MIDI synth, and plays a note
- **THEN** the processor starts without error and the reverb tail is audible/measurable on the chain's output

#### Scenario: Same reverbs available in Docker
- **WHEN** the Docker image is built from `docker/Dockerfile`
- **THEN** the same curated LV2 effect packages are installed there as on the native install

### Requirement: Engine catalog file lists only installed plugins
The engine catalog file (`$ZYNTHIAN_CONFIG_DIR/engine_config.json`) SHALL contain LV2 entries only for plugins that the `lilv` world on that machine can find.

#### Scenario: Catalog regenerated after installing plugins
- **WHEN** the catalog is regenerated after the LV2 effect packages are installed
- **THEN** every `JV/*` entry's `URL` resolves to a plugin in the `lilv` world

#### Scenario: Existing metadata is preserved
- **WHEN** a plugin was already present in the previous catalog (same `JV/<name>` key)
- **THEN** its title, category, ranking and enabled state are carried over unchanged

### Requirement: Not-installed upstream plugins are shown greyed out
The engine selection screens SHALL also list plugins that are in upstream's default catalog (`$ZYNTHIAN_SYS_DIR/config/engine_config.json`) and enabled there, but not installed on this machine, rendered greyed out after the installed entries of the same category. They SHALL NOT be selectable.

#### Scenario: Missing reverb visible as install hint
- **WHEN** the user opens Add Audio Effect → "Reverb" and e.g. "TAL-Reverb" is not installed
- **THEN** "TAL-Reverb" appears greyed out below the installed reverbs, and its info pane says it is not installed, naming the apt package if one is known

#### Scenario: Greyed entry cannot be added
- **WHEN** the user presses select on a greyed-out entry
- **THEN** no processor is created and no `Plugin not found` error occurs

#### Scenario: Becomes selectable after installation
- **WHEN** the plugin's package is installed and the catalog regenerated
- **THEN** the entry is shown normally and can be added

### Requirement: A default set of reverbs is enabled
After this change at least the curated reverbs SHALL be enabled in the catalog, so the "Reverb" category shows usable entries without visiting webconf first.

#### Scenario: Reverb category has usable entries
- **WHEN** the user opens Add Audio Effect → "Reverb" category
- **THEN** at least three selectable (not greyed) reverb plugins are listed, and each can be added successfully
