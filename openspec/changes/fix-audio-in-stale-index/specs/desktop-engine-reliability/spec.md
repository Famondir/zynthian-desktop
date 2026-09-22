## ADDED Requirements

### Requirement: Audio Input screen tolerates a stale selection index
The Audio Input screen SHALL NOT raise an unhandled exception when a click is processed against a row index that a concurrent background list refresh has made out of range.

#### Scenario: List rebuilt between click and processing
- **WHEN** `select_action()` is called with an index that is `>= len(list_data)` because `refresh_status()` rebuilt the list in the meantime
- **THEN** the call returns without raising an exception and without changing any chain's audio routing
