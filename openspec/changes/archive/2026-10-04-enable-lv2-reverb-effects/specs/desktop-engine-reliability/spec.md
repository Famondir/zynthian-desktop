## ADDED Requirements

### Requirement: Adding an unavailable LV2 plugin fails cleanly
When a processor is added whose LV2 plugin URI cannot be found in the `lilv` world (e.g. a stale catalog entry), zynthian-ui SHALL abort the add with a logged error and a user-visible message, and SHALL NOT leave a half-initialised processor in the chain.

#### Scenario: Stale catalog entry selected
- **WHEN** the user selects an engine whose `URL` is not in the `lilv` world (`KeyError: Plugin not found`)
- **THEN** no processor is added to the chain, the GUI shows an error instead of hanging, and the chain's existing processors keep working

#### Scenario: Chain remains removable
- **WHEN** a processor add has failed this way
- **THEN** the chain can still be removed and "Clean Chains" completes without hanging

### Requirement: Saved state with an unavailable plugin still loads
Loading a snapshot or the last state that references an LV2 plugin which is no longer installed SHALL skip that processor with a logged warning and load the rest of the state.

#### Scenario: Last state contains a broken reverb processor
- **WHEN** zynthian-ui starts and the last saved state contains a processor whose plugin cannot be found
- **THEN** the UI comes up, the other chains and processors are restored, and the broken processor is absent
