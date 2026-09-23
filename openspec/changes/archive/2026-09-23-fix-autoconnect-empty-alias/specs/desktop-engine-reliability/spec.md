## ADDED Requirements

### Requirement: Autoconnect tolerates devices without a port alias
`zynautoconnect` SHALL NOT raise an unhandled exception while holding its autoconnect lock when a MIDI input device has no JACK port alias set.

#### Scenario: Device with no alias under PipeWire's JACK-compat layer
- **WHEN** autoconnect checks a MIDI input device's alias against the configured external clock device name, and that device's `aliases` list is empty
- **THEN** the check treats it as not matching (no crash), and the autoconnect lock is released normally
