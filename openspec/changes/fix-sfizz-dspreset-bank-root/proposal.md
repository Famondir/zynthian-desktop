## Why

`zynthian_engine_sfizz.py` already lists both `sfz` and `dspreset` in `preset_fexts`, but the top-level (non-subdirectory) branch of `_get_preset_list()` only checked for the `.sfz` extension. A DecentSampler `.dspreset` file placed directly in a bank folder (not inside its own subfolder) was silently skipped, showing "Loaded 0 presets" with no error. Submitted upstream as a standalone PR.

## What Changes

- The top-level file-extension check now accepts any extension listed in `preset_fexts`, matching the subdirectory branch's behaviour.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-engine-reliability`: adds the requirement that sfizz preset discovery honours its own declared supported extensions consistently.

## Impact

- `zyngine/zynthian_engine_sfizz.py` (`_get_preset_list`).
- Submitted upstream as `fix/sfizz-dspreset-bank-root` against `zynthian/zynthian-ui`.
