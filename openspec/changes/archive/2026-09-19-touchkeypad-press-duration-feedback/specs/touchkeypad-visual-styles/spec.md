## ADDED Requirements

### Requirement: Live press-duration feedback on device/device_cables
While a button is held down on the `device` or `device_cables` keypad style, its press-outline colour SHALL indicate which press-duration bracket (Short/Bold/Long) the hold currently falls into, using the app's actual configured thresholds (`ZYNTHIAN_UI_SWITCH_BOLD_MS`/`ZYNTHIAN_UI_SWITCH_LONG_MS`), without changing when or which press-duration action fires.

#### Scenario: Short hold
- **WHEN** a button is pressed and released before the Bold threshold elapses
- **THEN** the press-outline is yellow for the whole hold, and the release still fires a Short-press action exactly as it did before this change

#### Scenario: Hold crosses into Bold
- **WHEN** a button remains held past the Bold threshold but is released before the Long threshold
- **THEN** the press-outline turns orange once the Bold threshold is crossed, and the release fires a Bold-press action exactly as it did before this change

#### Scenario: Hold crosses into Long
- **WHEN** a button remains held past the Long threshold
- **THEN** the press-outline turns red once the Long threshold is crossed, and stays red for as long as the button remains held

#### Scenario: Release cancels pending colour changes
- **WHEN** a button is released before a threshold's scheduled colour change has fired
- **THEN** that pending colour change is cancelled and never applied, so it cannot bleed into a later, unrelated press of the same button
