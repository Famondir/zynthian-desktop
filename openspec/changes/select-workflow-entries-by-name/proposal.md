## Why

Every engine workflow picks list entries and engine categories by position (`select: 5`, seven `arrow: right` steps). Positions shift whenever packages are installed or removed, when unavailable engines are sorted to the end of a category, or when `cat_index` carries over from a previous engine-screen visit. A shifted index does not fail. It silently tests a different entry: the old amp workflow tested the SysEx tool for weeks before anyone noticed. With the LV2/standalone package sets now differing between native and Docker, index-based workflows are no longer trustworthy.

## What Changes

- New fork CUIA `SELECT_NAME <text>` in `zynthian-ui`: highlights the entry whose label matches the text in the current screen's list (selector lists via their labels, grid screens such as Add Chain via their titles). It logs a success line naming the index it chose. If the label is missing or ambiguous it logs an error and leaves the selection unchanged.
- New fork CUIA `SELECT_CATEGORY <text>`: switches the engine screen's category column to the named category through the existing `set_cat()`. It logs success or error the same way.
- Runner: new step kinds `select_name: <text>` and `category: <text>`. Each step waits a bounded time for the CUIA's success line and fails on the error line or on timeout. Both CUIAs are added to the injection allow-list.
- New `assert_zss` assertion `chain_lacks_engine: <key>`.
- Every engine workflow switches to `category:`/`select_name:`: `add_reverb_effect`, `add_amp_effect`, `select_unavailable_effect`, `type_chain_name`, `add_sooperlooper`, `add_aeolus`, `add_internet_radio`, `add_puredata`, `build_fluidsynth_chain`, `record_midi`. A plain `select: <index>` stays only where the position itself is the intent, for example "first free MIDI channel" or "first bank".
- `select_unavailable_effect` selects a greyed engine by name and asserts that it did **not** end up in the chain. Today it only asserts that FluidSynth is present.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `workflow-smoke-testing`: adds the requirements for name-based list and category selection that fails loudly when the name is missing, and for a negative snapshot assertion (the chain lacks an engine).

## Impact

- `/zynthian/zynthian-ui` (fork, branch `vangelis`): `zyngui/zynthian_gui.py` (two CUIA handlers), plus a small name-lookup helper on `zynthian_gui_selector`, `zynthian_gui_selector_grid` and `zynthian_gui_engine`. Must be pushed before the Docker rebuild.
- This repo: `workflow_testing/runner.py`, `injection.py`, `allowlist.py`, `zss_assert.py`, and every file in `workflow_testing/workflows/`.
- No behaviour change for normal UI use: the CUIAs only run when something sends them. This could be an upstream PR candidate, since `select_listbox_by_name` exists upstream without a CUIA.
