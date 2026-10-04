## ADDED Requirements

### Requirement: Workflows select list entries and engine categories by name
The engine SHALL provide `select_name: <text>` and `category: <text>` steps. `select_name` highlights the entry whose visible label equals the text on the current screen: a selector list or a grid screen such as Add Chain. Whitespace runs, including line breaks in grid titles, are compared as a single space. `category` switches the engine screen's category column to the named category. Both steps SHALL be carried out by fork CUIAs (`SELECT_NAME`, `SELECT_CATEGORY`) that log which index they chose. The step SHALL succeed only once that success line appears. Workflows SHALL NOT pick engines or engine categories by position. A positional `select: <index>` is allowed only where the position itself is the intent, for example "first free MIDI channel".

#### Scenario: Entry found by name
- **WHEN** a step specifies `select_name: <text>` and exactly one entry on the current screen carries that label
- **THEN** that entry is highlighted, the fork logs the chosen index, and the step passes regardless of the entry's position in the list

#### Scenario: Name not present fails the step
- **WHEN** a step specifies `select_name: <text>` or `category: <text>` and no entry or category carries that label (for example because a package is missing or a title changed)
- **THEN** the selection is left unchanged, the fork logs an error naming the missing label, and the step fails. No other entry is selected in its place.

#### Scenario: Ambiguous name fails the step
- **WHEN** more than one entry on the current screen carries the requested label
- **THEN** the step fails with an error naming the label and the matching indices instead of picking one silently

#### Scenario: CUIA dropped while busy
- **WHEN** the UI ignores the `SELECT_NAME`/`SELECT_CATEGORY` CUIA (for example because it is busy starting an engine), so no success or error line appears
- **THEN** the step fails after a bounded wait instead of passing silently

#### Scenario: Installing more packages does not change what is tested
- **WHEN** additional LV2 or standalone engine packages are installed, so entries move within a category or categories appear or disappear
- **THEN** every engine workflow still selects the same engine as before, or fails explicitly if that engine is gone

### Requirement: Snapshot assertion that a chain lacks an engine
The `assert_zss` block SHALL support `chain_lacks_engine: <engine key>`, which passes only if no chain in the saved snapshot contains a processor with that engine key.

#### Scenario: Greyed engine is not added
- **WHEN** a workflow selects and confirms an unavailable (greyed) engine and then saves a snapshot asserting `chain_lacks_engine: <that engine's key>`
- **THEN** the assertion passes, because the unavailable engine was not added to the chain

#### Scenario: Engine unexpectedly present
- **WHEN** the saved snapshot does contain a processor with the given engine key
- **THEN** the workflow fails and the report names the chain that contains it
