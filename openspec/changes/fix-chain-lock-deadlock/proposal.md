## Why

`zynthian_chain.py`'s `rebuild_audio_graph()`/`rebuild_midi_graph()` acquire the autoconnect lock and release it at the end of the function body. Any exception in between (e.g. `proc.engine` being `None` after a failed engine start) skips the release, leaving the lock held forever - every later chain operation (including "Clean Chains" and app exit) hangs indefinitely. Submitted upstream as a standalone PR.

## What Changes

- Both functions' bodies are wrapped in `try:`/`finally: zynautoconnect.release_lock()` so the lock is always released regardless of what happens inside.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-engine-reliability`: adds the requirement that the autoconnect lock is never left held after an exception during chain graph rebuilding.

## Impact

- `zyngine/zynthian_chain.py` (`rebuild_audio_graph`, `rebuild_midi_graph`).
- Submitted upstream as `fix/chain-lock-try-finally` against `zynthian/zynthian-ui`.
