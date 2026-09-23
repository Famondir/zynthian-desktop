## Why

Under PipeWire's JACK-compatibility layer, `zynautoconnect` crashes with an `IndexError` while holding its autoconnect lock, permanently deadlocking every later chain operation (add/remove chain, exit) until the app is restarted. Submitted upstream as a standalone PR since it's a general robustness bug, not desktop-specific.

## What Changes

- `zynautoconnect.py`'s MIDI-device alias check now tolerates a device having no alias at all, instead of assuming `aliases[0]` always exists.

## Capabilities

### New Capabilities
- `desktop-engine-reliability`: robustness requirements for zynthian-ui's core engines/GUI against conditions the original code didn't handle (crashes, deadlocks, wrong file recognition) - discovered while desktop-porting, but not desktop-specific bugs themselves. This change adds the first requirement: autoconnect must not crash on devices without a JACK port alias.

### Modified Capabilities
(none - first change to introduce this capability)

## Impact

- `zynautoconnect/zynthian_autoconnect.py` (one line).
- Submitted upstream as `fix/autoconnect-empty-alias` against `zynthian/zynthian-ui`.
