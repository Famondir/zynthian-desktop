## Why

On the native desktop install no reverb effect works, which blocks the user's actual use case: FISA Suprema right hand → MIDI channel 1 → a FluidSynth chain playing an already-distorted guitar preset ("Distortion Guitar"-style GM sound) → **reverb**. No separate distortion effect is needed - the preset is distorted by itself. The left-hand accompaniment runs through its own audio-input chain without effects; a further chain with NAM was muted and not part of the sound. Root cause found during exploration: `/zynthian/config/engine_config.json` is a verbatim copy of upstream's Raspberry-Pi plugin catalog (1128 entries, 886 Audio Effects), but only 75 of those effects are actually installed on this machine (almost all Guitarix). The engine list in the UI is not filtered against what `lilv` can actually load, so picking almost any reverb (Dragonfly, Calf, MVerb, TAL, …) hits the known `KeyError: Plugin not found` and leaves a broken chain behind - matching the user's "chains are broken/hung and can't be cleaned up".

## What Changes

- Install a curated set of LV2 effect plugin packages from Ubuntu 24.04's apt repos (reverbs first: `dragonfly-reverb-lv2`, `calf-plugins`, `x42-plugins`, `zam-plugins`, `mda-lv2`, `lsp-plugins-lv2`, `swh-lv2`) on the native install, and the same set in `docker/Dockerfile`.
- Regenerate the engine catalog from the actually-installed `lilv` world, so it lists only loadable plugins (existing entries keep their upstream title/category/enabled metadata).
- Keep the not-installed upstream plugins **visible but greyed out** in the engine selection screens (taken from upstream's default catalog in `zynthian-sys`), so the user can see what could be installed. They cannot be selected; their info pane says "not installed" and names the apt package where one is known.
- Enable a small default set of working reverbs in the catalog so the "Reverb" category is usable out of the box.
- Harden `zynthian-ui` so that selecting an LV2 plugin that `lilv` cannot find fails cleanly: an error message, no half-built processor left in the chain, the chain still removable.
- Document a recovery path for chains that are already broken in the current saved state.

Out of scope (separate changes, noted as follow-ups): the MIDI channel filter not isolating channel 1 (left hand still reaching the FluidSynth guitar chain), MIDI notes getting lost, and the FISA-side stereo separation question.

## Capabilities

### New Capabilities
- `lv2-effect-availability`: the desktop install ships a working set of LV2 audio effects (including reverbs); only installed plugins can be selected, and known-but-missing upstream plugins are shown greyed out as an install hint.

### Modified Capabilities
- `desktop-engine-reliability`: adds the requirement that adding a processor whose LV2 plugin cannot be found fails cleanly, without leaving a broken or unremovable chain.

## Impact

- **Native host**: apt packages (system-wide, `/usr/lib/lv2`), regenerated `/zynthian/config/engine_config.json` (not version controlled; back it up before regenerating) and `/zynthian/config/jalv/presets_*.json`.
- **`/zynthian/zynthian-ui`** (fork, branch `vangelis`): availability marking in `zyngine/zynthian_lv2.py`, greyed-out rendering in `zyngui/zynthian_gui_engine.py`, graceful-failure handling in the LV2/jalv engine start / processor-add path (`zyngine/zynthian_engine_jalv.py`). Must be pushed so Docker rebuilds pick it up.
- **This repo**: `docker/Dockerfile` (apt package list + catalog regeneration step), `config/` reference notes if needed, workflow test for "add reverb to a chain".
- Disk: LSP + Calf + x42 together add a few hundred MB; acceptable on a desktop.
