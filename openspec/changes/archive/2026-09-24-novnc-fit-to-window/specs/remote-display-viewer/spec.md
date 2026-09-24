## ADDED Requirements

### Requirement: View fits the running GUI style's actual window size
The noVNC view SHALL show only the running Zynthian window's actual content area, not a larger virtual display padded with empty space, regardless of which GUI style (`classic`, `standard`, `device`, `device_cables`) is running.

#### Scenario: A smaller-than-maximum style is running
- **WHEN** `classic` or `standard` (both smaller than `device_cables`, the largest style) is running under either launcher
- **THEN** the noVNC view's exported framebuffer matches that window's actual size, with no black margin around the content

#### Scenario: Window-tracking can't find the app's window
- **WHEN** the app's window doesn't appear within the tracking timeout (e.g. an unrelated startup failure)
- **THEN** the noVNC view falls back to exporting the full virtual display (today's behavior) rather than the session failing or a viewer error being surfaced
