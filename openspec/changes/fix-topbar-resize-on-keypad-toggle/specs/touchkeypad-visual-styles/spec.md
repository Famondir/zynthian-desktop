## ADDED Requirements

### Requirement: Topbar sizing stays consistent across a runtime keypad-view toggle
Whenever the touch keypad view is toggled at runtime (shown ↔ hidden, e.g. via a tap on the topbar's status area), the topbar (title font, status icons, and any screen-specific topbar text such as the mixer's tempo/time-signature readout) SHALL be resized to match the new view's actual screen dimensions, consistent with content elsewhere on the same screen that already resizes on this toggle - not remain frozen at whatever size was correct for the view active at startup.

#### Scenario: Toggling from the mocked keypad view to the full-screen view
- **WHEN** the touch keypad is toggled from shown (a style's smaller mocked-screen size) to hidden (the screen expands to the outer display's full size)
- **THEN** the topbar's title font, status icons, and any screen-specific topbar text resize to fit the new, larger screen area - no element stays frozen at its previous, now-mismatched size, and no element overlaps another as a result of only one of them having resized

#### Scenario: Toggling back to the mocked keypad view
- **WHEN** the touch keypad is toggled back from hidden to shown
- **THEN** the topbar returns to the size appropriate for that style's mocked screen, matching what it would have been had the app started directly in that state (per the startup-time requirement this extends)
