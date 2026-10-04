## 1. Fork CUIAs (`/zynthian/zynthian-ui`)

- [ ] 1.1 Add `find_index_by_name(name)` to `zynthian_gui_selector`: whitespace-normalised exact match on `list_data[i][2]`, separators skipped. Return the list of matching indices.
- [ ] 1.2 Add the same helper to `zynthian_gui_selector_grid`, matching `config[i]["title"]`.
- [ ] 1.3 Add `find_category_by_name(name)` to `zynthian_gui_engine`, matching `engine_cats`.
- [ ] 1.4 Add `cuia_select_name` and `cuia_select_category` to `zynthian_gui.py`. On exactly one match: select (or `set_cat`) and log INFO `SELECT_NAME '<text>' => <i>`. On none or several: log ERROR and leave the selection unchanged. If the current screen doesn't support it: log ERROR.
- [ ] 1.5 Smoke-test both CUIAs manually via OSC on the native UI (engine screen, chain options, Add Chain grid), checking found, missing and ambiguous cases.
- [ ] 1.6 Commit and push the fork (`vangelis`).

## 2. Runner (this repo)

- [ ] 2.1 Add `SELECT_NAME` and `SELECT_CATEGORY` to `workflow_testing/allowlist.py` and `select_name()`/`select_category()` to `injection.py` (string argument).
- [ ] 2.2 Add `Step` fields `select_name` and `category` (and their `describe()`, loader and exactly-one-action check).
- [ ] 2.3 Add the bounded wait in `_run_step` for the success or error line (regex constants). Fail on the error line or on timeout.
- [ ] 2.4 If decision 5 needs it, accept a `{native: …, docker: …}` mapping for `select_name`, resolved from the run's `--env`.
- [ ] 2.5 Add `assert_chain_lacks_engine` to `zss_assert.py` and wire `chain_lacks_engine` into `assert_zss`. The report names the offending chain.
- [ ] 2.6 Update the runner docstring: the new steps, plus the rule that positional `select:` is only for intrinsically positional choices.

## 3. Convert workflows

- [ ] 3.1 Look up the exact titles and categories in the native catalog (`/zynthian/config/engine_config.json`) for every engine used, and pick the greyed engine for `select_unavailable_effect` that is unavailable in both environments (design decision 5).
- [ ] 3.2 Convert `build_fluidsynth_chain` and `record_midi` (Add Chain grid → `Instrument`, `category: Sampler`, `select_name: FluidSynth`).
- [ ] 3.3 Convert `add_reverb_effect`, `add_amp_effect` and `type_chain_name` (chain options by label: `Add Audio-FX processor`, `Rename chain`).
- [ ] 3.4 Convert `add_sooperlooper`, `add_aeolus`, `add_internet_radio` and `add_puredata`.
- [ ] 3.5 Convert `select_unavailable_effect`: select the greyed engine by name, confirm, then `chain_lacks_engine` plus `chain_has_engine: FS`.
- [ ] 3.6 Negative check: temporarily point one workflow at a non-existent name and confirm the step fails with a clear message (not committed).

## 4. Verification

- [ ] 4.1 Native suite: back up `last_state.zss`/`default.zss`, run all workflows, restore them. All pass.
- [ ] 4.2 Rebuild Docker (fork pushed first) and run the Docker suite. All pass.
- [ ] 4.3 Commit and push this repo. Note the upstream PR candidate in `submit-upstream-fix-prs` (task only, no PR without the user's go-ahead).
