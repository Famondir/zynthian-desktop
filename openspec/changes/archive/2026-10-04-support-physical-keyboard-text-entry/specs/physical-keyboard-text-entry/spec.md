## ADDED Requirements

### Requirement: Physical keys type into the on-screen keyboard dialog
While the on-screen keyboard screen (`keyboard`, QWERTY or numpad mode) is shown, zynthian-ui SHALL apply physical key presses to the text being edited instead of mapping them through the keybinding table: a printable character is appended, Backspace deletes the last character, Enter confirms (same as the on-screen Enter key), Escape cancels (same as the on-screen cancel key).

#### Scenario: Typing a snapshot name
- **WHEN** the "Save as new snapshot" dialog is open and the user types `Gitarre Dist` and presses Enter on a physical keyboard
- **THEN** the snapshot is saved with the name `Gitarre Dist`

#### Scenario: Keybound letters do not trigger actions while typing
- **WHEN** the keyboard dialog is open with the QWERTY keybinding profile loaded, and the user types a letter that profile maps to a CUIA (e.g. `i` → `ZYNSWITCH 0`)
- **THEN** the letter is appended to the text and no CUIA is executed

#### Scenario: Backspace and Escape
- **WHEN** the user presses Backspace, then Escape
- **THEN** the last character is removed, and then the dialog closes without calling its callback, exactly like the on-screen cancel key

### Requirement: Typed input respects the dialog's constraints
Typed input SHALL obey the same constraints as on-screen input: the dialog's `max_len`, and in numpad mode only characters the numpad itself offers.

#### Scenario: Maximum length
- **WHEN** a dialog opened with `max_len=8` already holds 8 characters and the user types another character
- **THEN** the text stays at 8 characters

#### Scenario: Numpad rejects letters
- **WHEN** a numpad dialog is open and the user types `a`
- **THEN** the text is unchanged

### Requirement: Fast typing keeps character order
Characters typed in quick succession SHALL be applied in the order they were typed, even if several arrive between two processing ticks of the keyboard screen.

#### Scenario: Burst of keys
- **WHEN** `abc` is typed faster than the screen's control-thread refresh
- **THEN** the text reads `abc`, not `cba`

### Requirement: Keybindings unchanged outside the dialog
When the keyboard dialog is not shown, physical key presses SHALL be handled by the keybinding table exactly as before.

#### Scenario: Arrow key on the mixer
- **WHEN** the mixer screen is shown and a key bound to `ARROW_DOWN` is pressed
- **THEN** `ARROW_DOWN` is executed as before
