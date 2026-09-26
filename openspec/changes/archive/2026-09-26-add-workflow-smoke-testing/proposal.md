## Why

The only automated regression coverage today is `test_zynthian_docker.sh`: Docker-only, one hardcoded scenario (load a committed `.zss` fixture, inject one MIDI note, confirm audio). It doesn't cover the native install at all, and every session so far that found a real bug (`enable-webconf-access`'s three desktop-port crashes, all three surfaced only by a human clicking through the browser) had zero automated help. Growing coverage to real workflows ("build a FluidSynth chain", "add an amp effect") by hand-authoring more fixture `.zss` files was already shown to be fragile in this project's own history - the current fixture's soundfont path only worked on the machine it was saved on, and the fixture schema itself has already drifted once (`index/mixer/layers` → `schema_version/chains/zs3`). Now that this project has independently confirmed real Zynthian hardware's `master_midi_note_cuia` MIDI mapping (MIDI notes 90-118 → `ZYNSWITCH 0..28`, note-on/note-off timing → short/bold/long press, notes 60-77 → direct screen jumps) works unmodified over the same VMPK/a2jmidid path already validated for MIDI testing, workflows can be *driven live* through the real UI instead of loaded from a static file - closing the fixture-staleness problem structurally instead of by hand-maintenance discipline.

## What Changes

- **BREAKING**: `test_zynthian_docker.sh` and the `docker-smoke-testing` capability it implements are replaced, not kept alongside the new system - avoids permanently maintaining two independent test mechanisms (one Docker-only, one Docker+native) that could drift apart. Its one existing scenario (fixture load → note → audio) becomes the first workflow script ported onto the new engine.
- Add a workflow-script engine that drives either environment (native, via a private Xvfb display like `run_zynthian_vnc.sh`; Docker, via a headless container like the current script) through the same steps: each step is a MIDI-injected CUIA action (`ZYNSWITCH <i> <short|bold|long>` or a direct `SCREEN_*` jump) followed by an assertion.
- Three assertion layers, usable per-workflow as needed:
  - **Log-diff**: no new `ERROR`/`Traceback` lines appear in `zynthian_main.py`'s output between the pre- and post-step log tail.
  - **Structural**: parse a saved `.zss` as JSON and assert on its `chains`/`slots` content (e.g. a FluidSynth engine code present) - fast, no live process needed.
  - **Round-trip**: reload a workflow-saved `.zss` fresh (reusing the existing fixture-load-and-check-audio mechanism, now pointed at a freshly-produced file instead of a committed one) to confirm it's faithfully reproducible, not just well-formed.
- A small starting library of concrete workflow scripts, matching real usage patterns: build a FluidSynth chain from scratch, add an amp-sim effect to an existing chain, set up MIDI recording. Designed to keep growing over time as new workflows/regressions are found (see `enable-webconf-access`'s pattern of finding bugs by hand and fixing forward - the goal is to convert workflows exercised that way into permanent scripts).
- A safety deny-list for CUIA/MIDI-note actions that must never be triggered by an automated run (`POWER`, `RESTART_UI`, and anything admin-screen-reachable that leads to reboot/software-update/factory-reset).
- No hosted CI integration (same Non-Goal as the capability this supersedes - no `/dev/snd`/X11/`audio`-group on a typical CI runner); this stays a locally-triggered dev tool for both environments.

## Capabilities

### New Capabilities
- `workflow-smoke-testing`: driving native and Docker Zynthian sessions through scripted, MIDI/CUIA-injected workflows and asserting on log output, saved-snapshot structure, and round-trip reload - covering both environments from one shared mechanism, replacing the single-scenario Docker-only smoke test.

### Modified Capabilities
- `docker-smoke-testing`: superseded entirely by `workflow-smoke-testing` (its existing requirements are removed, with the one existing scenario carried forward as the new capability's first workflow script rather than left behind).

## Impact

- Removes/replaces: `test_zynthian_docker.sh`, `docker/fixtures/smoke-test-default.zss` (no longer committed - workflows build and save their own snapshots).
- New: a shared workflow-engine script/library (native+Docker), a small set of workflow-script definitions, a safety deny-list for CUIA actions.
- Depends on already-validated infrastructure from this project: `run_zynthian_vnc.sh` (native headless display), `run_zynthian_docker.sh`/`docker/entrypoint.sh` (Docker), `setup_virtual_devices.sh`/VMPK/`snd-aloop` (`support-virtual-test-devices`), and the archived `docker-automated-smoke-test` design's audio-capture technique (`jack_rec` against the mixbus, not ALSA loopback capture).
- No application code changes to `zynthian-ui` itself expected - `master_midi_note_cuia`'s default mapping already covers what's needed without configuration.
