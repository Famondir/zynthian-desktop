## 1. Resolve open questions before building the engine

- [ ] 1.1 Investigate whether "current screen" is readable from outside the process (log line, `.zss`-adjacent state file, or similar) - confirm whether `screen_is` assertions are feasible, or whether initial workflows rely on log-diff + structural checks only. Update design.md with the finding.
- [ ] 1.2 Decide the workflow-script format (plain data file vs. small Python DSL) - pick whichever keeps step/assertion definitions environment-agnostic with the least ceremony. Note the decision in design.md.
- [ ] 1.3 Enumerate the exact CUIA allow-list entries needed by the three starting workflows (task 7) - confirm each against `zynconf/zynthian_config.py`'s `NoteCuiaDefault` table.

## 2. Core MIDI/CUIA injection mechanism

- [ ] 2.1 Write the shared injection primitive: given a target session's VMPK/a2jmidid setup, send a `ZYNSWITCH <i>` press of a given duration (short/bold/long) via note-on + timed note-off, and a `SCREEN_<name>` jump via a single note-on/off pair - reusing `xdotool key` against VMPK's on-screen keyboard mapping, same technique as the archived `docker-automated-smoke-test`.
- [ ] 2.2 Implement the CUIA allow-list check: reject any step whose target note maps (via `NoteCuiaDefault` or a configured override) to a CUIA not on the list, before injecting anything.
- [ ] 2.3 Confirm press-duration timing against the target session's actual `zynswitch_bold_us`/`zynswitch_long_us` (read from its environment, don't hardcode the 300ms/2000ms defaults in the engine).

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

- [ ] 6.1 Implement `save_snapshot` (trigger a save via CUIA/MIDI, locate the resulting `.zss` in the session's `zynthian-my-data/snapshots`) and a JSON-based structural assertion helper (`assert_zss`) against its `chains`/`slots` content.
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
