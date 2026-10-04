## ADDED Requirements

### Requirement: Standalone engines without their program are shown greyed out
A standalone (non-LV2) engine whose required program or service is not present on the machine SHALL be marked unavailable and shown greyed out in the engine selection screens, not selectable, with an install hint where an installable package is known - the same treatment as not-installed LV2 plugins.

#### Scenario: SooperLooper not installed
- **WHEN** the `sooperlooper` program is not on the PATH and the user opens Add Audio Effect
- **THEN** SooperLooper appears greyed out, selecting it only shows "Not installed (apt package: sooperlooper)", and no `Can't start engine 'SL'` error is logged

#### Scenario: Engine with no simple install path
- **WHEN** MOD-UI's services are not installed
- **THEN** MOD-UI appears greyed out with "Not installed" and no package hint

#### Scenario: Becomes selectable after installation
- **WHEN** the missing program is installed and Zynthian restarted
- **THEN** the engine is shown normally and can be added

### Requirement: Desktop install ships installable standalone engines
The native desktop install and the Docker image SHALL provide every standalone engine that upstream enables by default and that can be installed on Ubuntu 24.04 without root services: SooperLooper, Aeolus, Internet Radio and PureData.

#### Scenario: Adding each engine
- **WHEN** a workflow adds SooperLooper, Aeolus, Internet Radio or PureData to a chain
- **THEN** the engine starts without error, in both the native and the Docker session
