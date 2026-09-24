## 1. Resolve open questions before building the engine

- [x] 1.1 Investigate whether "current screen" is readable from outside the process (log line, `.zss`-adjacent state file, or similar) - confirm whether `screen_is` assertions are feasible, or whether initial workflows rely on log-diff + structural checks only. Update design.md with the finding. Resolved: no external channel exists (`zynsigman` is in-process-only); decided to add one `logging.debug` line to the fork instead of relying on log-diff/structural checks alone - see design.md.
- [x] 1.2 Decide the workflow-script format (plain data file vs. small Python DSL) - pick whichever keeps step/assertion definitions environment-agnostic with the least ceremony. Note the decision in design.md. Resolved: plain YAML step list.
- [x] 1.3 Enumerate the exact CUIA allow-list entries needed by the three starting workflows (task 7) - confirm each against `zynconf/zynthian_config.py`'s `NoteCuiaDefault` table. Resolved: `ZYNSWITCH 0-3`, `SCREEN_CHAIN_MANAGER`, `SCREEN_MIXER`, `SCREEN_MIDI_RECORDER`, `ALL_NOTES_OFF` - see design.md.
- [x] 1.4 (found while resolving 1.1) Add the one-line `logging.debug(f"SHOW SCREEN '{screen}'")` patch to `show_screen()` in the `Famondir/zynthian-ui` fork (`zyngui/zynthian_gui.py`, next to the existing `zynsigman.send(...)` call), so `screen_is` assertions can run through the same log-diff mechanism as error detection. Commit directly to the fork per `CLAUDE.md`'s convention (code fixes for the desktop port go there, not into this repo).

## 2. Core CUIA injection mechanism (OSC-based - see design.md's correction)

- [x] 2.1 Write the shared injection primitive: `ZYNSWITCH <i>` press of a given duration (short/bold/long) via `/CUIA/ZYNSWITCH <i> P` then a timed `/CUIA/ZYNSWITCH <i> R` over OSC (port 1370, `zynconf.ServerPort["cuia_osc"]`), and a `SCREEN_<name>` jump via a single `/CUIA/SCREEN_<NAME>` message. No VMPK/Xvfb/pixel-coordinate dependency for these steps (superseded design.md's earlier VMPK-click plan once the OSC path was found). Implemented in `workflow_testing/injection.py` using `pyliblo3`.
- [x] 2.2 Implement the CUIA allow-list check: reject any step whose target CUIA (or, for `ZYNSWITCH`, whose switch index) is not on the list, before sending anything over OSC. Implemented in `workflow_testing/allowlist.py`.
- [x] 2.3 Confirm press-duration timing against the target session's actual `zynswitch_bold_us`/`zynswitch_long_us` (read from its environment, don't hardcode the 300ms/2000ms defaults in the engine). Covered by 2.1's implementation (`injection.py` reads thresholds from the target's env, falling back to the 300ms/2000ms defaults only if unset).
- [ ] 2.4 Musical-note injection for audio verification (separate concern from 2.1-2.3 - CUIA has no generic "play this note" message): reuse `test_zynthian_docker.sh`'s proven VMPK mouse-click technique, unchanged, only for `reload_and_check_audio` (task 6.2) - narrower scope than originally planned (was going to cover switch/screen steps too).

## 3. Log-diff assertion

- [ ] 3.1 Implement per-step log tail capture + diff: mark the tail position before a step, inject, poll (bounded timeout, not a fixed sleep) for the log to stabilize, then diff for new `ERROR`-level/traceback lines.
- [ ] 3.2 Confirm this catches a real regression: temporarily reintroduce one of `enable-webconf-access`'s fixed bugs (or an equivalent zynthian-ui-side crash) and verify a workflow step correctly fails on it, then revert.

## 4. Native environment adapter

- [ ] 4.1 Launch: private Xvfb display + native `zynthian_main.py` session, matching `run_zynthian_vnc.sh`'s technique (not calling that script directly - see its own design precedent for why a dedicated invocation is cleaner than reusing the interactive script).
- [ ] 4.2 Audio capture for round-trip checks: `jack_rec` directly against the host JACK graph's mixbus (no `docker exec` indirection needed - simpler than the Docker adapter).
- [ ] 4.3 Teardown: stop the Xvfb/VMPK/a2jmidid processes this run started, restore audio-service state, matching the cleanup-trap pattern already used by `run_zynthian_vnc.sh`/`run_zynthian_docker.sh`.
- [ ] 4.4 Contention check: refuse to start if a native or Docker Zynthian session is already running (port the existing `pgrep`-based check from `test_zynthian_docker.sh`).

## 5. Docker environment adapter

- [ ] 5.1 Launch: headless container (`docker run -d --name ...`), mirroring `run_zynthian_docker.sh`'s flags per `docker-desktop-image/design.md`'s documented list - own invocation, not a call into the interactive script (same reasoning `docker-automated-smoke-test` already used).
- [ ] 5.2 Audio capture for round-trip checks: `jack_rec` via `docker exec` against the container's mixbus (port directly from `test_zynthian_docker.sh`'s already-solved approach).
- [ ] 5.3 Teardown: stop/remove the container, unload `snd-aloop` only if this run loaded it, restore host audio-service state.
- [ ] 5.4 Contention check: refuse to start if a leftover test container or a real native/Docker session is already active (port from `test_zynthian_docker.sh`).

## 6. Structural and round-trip assertions

- [x] 6.1a Implement the JSON-based structural assertion helper (`assert_chain_has_engine`, `assert_chain_count`) against `chains`/`slots` content. Implemented in `workflow_testing/zss_assert.py`, verified against a real `.zss` on this machine (`/zynthian/zynthian-my-data/snapshots/default.zss` - confirmed chain count, FluidSynth engine code present/absent detection, missing-file handling all correct).
- [ ] 6.1b Implement `save_snapshot` (trigger a save via CUIA, locate the resulting `.zss` in the session's `zynthian-my-data/snapshots`) - needs a live session to confirm which CUIA triggers a save and where it lands, deferred.
- [ ] 6.2 Implement `reload_and_check_audio`: start a fresh session (either environment) that loads the just-saved `.zss` as its default snapshot, inject a note, confirm non-silent audio via the existing `jack_rec`+`sox` technique.

## 7. Starting workflow library

- [ ] 7.1 Workflow: build a FluidSynth-based chain from scratch (navigate to chain manager, add chain, select FluidSynth engine, confirm active) - the ported equivalent of `test_zynthian_docker.sh`'s single scenario, now built live instead of loaded from a fixture.
- [ ] 7.2 Workflow: add an amp-simulator effect to an existing chain.
- [ ] 7.3 Workflow: set up MIDI recording (start/stop via CUIA, confirm a capture file was produced).
- [ ] 7.4 Run all three against both environments; confirm pass/fail reporting is clear per workflow and per step.

## 8. Remove the superseded capability

- [ ] 8.1 Delete `test_zynthian_docker.sh` and `docker/fixtures/smoke-test-default.zss` once task 7.1's ported workflow passes reliably in both environments.
- [ ] 8.2 Confirm no other script/doc in the repo still references the deleted script/fixture (grep before deleting).

## 9. Documentation

- [ ] 9.1 Document the new engine's usage (how to run a workflow, how to add one) in its own header comment, matching this repo's convention of inline rationale over separate docs files.
- [ ] 9.2 Update `CLAUDE.md`/top-level references that mention `test_zynthian_docker.sh` (if any) to point at the new mechanism.
