## Why

`zynthian_gui_audio_in.py`'s `refresh_status()` can rebuild `list_data` in the background (polling for capture-port changes) between a row being clicked and the click being processed - e.g. right after opening the screen, while ports are still settling. The stale index then goes out of range for `select_action()`, raising an unhandled exception. Submitted upstream as a standalone PR.

## What Changes

- `select_action()` bounds-checks the index against the current `list_data` length before using it.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-engine-reliability`: adds the requirement that GUI selector screens are safe against list rebuilds racing with pending clicks.

## Impact

- `zyngui/zynthian_gui_audio_in.py` (`select_action`).
- Submitted upstream as `fix/audio-in-stale-index` against `zynthian/zynthian-ui`.
