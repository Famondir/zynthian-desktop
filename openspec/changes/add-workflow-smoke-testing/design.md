## Context

Three things already exist and this design builds directly on them rather than re-inventing:

- `test_zynthian_docker.sh` / the `docker-smoke-testing` capability: proved a private Xvfb display + VMPK (via a2jmidid) + `snd-aloop` + `jack_rec`-against-the-mixbus is enough to headlessly boot the Docker image, inject a real MIDI note, and confirm audio without a human. Its own `design.md` (archived at `openspec/changes/archive/2026-09-23-docker-automated-smoke-test/`) already worked through and solved several sharp edges this change reuses verbatim: `arecord` against `snd-aloop`'s capture side is unreliable (`EIO` on read) - use `jack_rec` against the mixbus instead; a committed fixture snapshot needs a soundfont path that exists in the target environment, which is exactly the class of problem live-building state (this change's core idea) avoids structurally.
- `support-virtual-test-devices` / `setup_virtual_devices.sh`: proved VMPK + `snd-aloop` work identically on the native install, not just Docker - MIDI reaches the active chain via `a2jmidid` with no manual `jack_connect`, confirmed live on this machine.
- `run_zynthian_vnc.sh`: proves a fully headless Xvfb display is enough to run the real Tk GUI natively, the same technique `test_zynthian_docker.sh` already uses for Docker.

New for this change, found during exploration: `zyngine/zynthian_state_manager.py` (~line 812) maps MIDI note-on/note-off on the configured "master MIDI channel" directly to CUIA (Callable UI Action) dispatch, via `zynthian_gui_config.master_midi_note_cuia` - defaulting (no config needed) to `zynconf.NoteCuiaDefault` in `zynconf/zynthian_config.py`: notes 90-118 map to `ZYNSWITCH 0` through `ZYNSWITCH 28` (all virtual encoder/button switches), with **note-on = press, note-off = release** - the real time gap between them runs through the same `zynswitch_bold_us`/`zynswitch_long_us` (300ms/2000ms defaults, `zyngui/zynthian_gui_config.py`) threshold logic that classifies real hardware presses into short/bold/long. Notes 60-77 map to direct `SCREEN_*` jumps (`SCREEN_CHAIN_MANAGER`, `SCREEN_ADMIN`, `SCREEN_MIXER`, etc.). This is reachable through the exact same VMPK→a2jmidid MIDI path already proven for both environments - no new remote-control surface needs to be added to `zynthian-ui`.

`.zss` snapshot files (`$ZYNTHIAN_MY_DATA_DIR/snapshots/*.zss`) are plain JSON (`schema_version`, `chains` with `slots` referencing engine codes like `"FS"` for FluidSynth, `zs3` for scenes) - confirmed by reading a real snapshot on this machine. Directly parseable/assertable without booting anything.

## Goals / Non-Goals

**Goals:**
- One shared mechanism that drives workflow scripts against *either* native or Docker sessions, so adding a new workflow automatically covers both - not two independently-maintained scripts.
- Replace `test_zynthian_docker.sh`/`docker-smoke-testing` outright (see proposal's BREAKING note) rather than keep it running alongside the new system.
- A small, real starting library of workflows (build a FluidSynth chain, add an amp-sim effect, set up MIDI recording), designed to keep growing - each new workflow is a script addition, not new engine code.
- Three complementary assertion layers (log-diff, structural `.zss` check, round-trip reload) usable per-step or per-workflow as appropriate, not just "screenshot non-blank + one audio check" as today.
- A safety deny-list preventing automated runs from ever triggering `POWER`, `RESTART_UI`, or admin-screen-reachable reboot/update/factory-reset actions.

**Non-Goals:**
- Hosted CI integration - unchanged from the capability this supersedes; still a locally-triggered dev tool (no `/dev/snd`/X11/`audio`-group on a typical CI runner).
- Pixel-perfect visual regression testing - screenshots (if used at all) stay a "did something render" check, not a golden-image diff.
- Exhaustive fuzzing of every switch × duration × screen combination - explicitly considered during exploration and rejected in favor of deliberate, hand-designed workflow scripts (real usage patterns, not random input coverage). Could be a cheap future addition on top of the same injection mechanism, but out of scope here.
- Testing `zynthian-webconf` (a completely different technique - HTTP, not MIDI/GUI) - deferred, not part of this change.
- Real-hardware-specific validation (physical Suprema, physical switches) - unchanged Non-Goal from the capability this supersedes.

## Decisions

### Shared step-execution core, thin per-environment adapters
The workflow *definitions* (ordered list of steps: MIDI CUIA injection + assertion) live in one place and are environment-agnostic. Only two things differ per environment, both already solved by existing scripts:
- **Launch/teardown**: native uses a private Xvfb display (`run_zynthian_vnc.sh`'s technique); Docker uses a headless container (`test_zynthian_docker.sh`'s technique, `docker run -d --name ... zynthian-desktop:latest`).
- **Audio capture for the round-trip check**: Docker uses `jack_rec` via `docker exec` against the container's own JACK graph (already solved, see Context); native runs `jack_rec` directly on the host, no `docker exec` indirection needed - actually simpler than the Docker case.

This directly answers the user's "muss nativ und docker synchron halten" requirement: a new workflow script is written once and runs against both by construction, rather than needing a matching native port authored separately each time.

### MIDI/CUIA injection via VMPK key events, not a new library
Same technique `docker-automated-smoke-test`'s design already chose and validated: launch real `vmpk` on the private Xvfb display, `xdotool key` to send the QWERTY-mapped note on/off VMPK's own UI would receive, at controlled intervals to produce short/bold/long press timing. Reproduces the exact real signal path (VMPK → a2jmidid → master MIDI channel → CUIA dispatch) instead of a synthetic approximation.
- *Alternative considered*: a Python MIDI library (`mido`, already a dependency pulled in by `enable-webconf-access` for an unrelated reason) writing directly to an ALSA sequencer port. Rejected for the same reason `docker-automated-smoke-test` rejected it originally - it bypasses VMPK/a2jmidid entirely, no longer re-validating that bridging path on every run, and this project already has the VMPK+`xdotool` mechanism working.

### Workflow scripts as an ordered list of (CUIA action, assertions) steps
Each step names one MIDI-injected action - either `zynswitch <i> <short|bold|long>` or a direct `screen <name>` jump - and the assertions to run immediately after it. Available assertions, composable per step:
- `no_new_errors`: diff the log tail before/after the step, fail on any new `ERROR`/`Traceback` line.
- `screen_is <name>`: optional, only where the expected resulting screen is worth pinning down (see Open Questions - exact mechanism for reading current screen from outside the process still needs to be nailed down during implementation).
- (workflow-level, not per-step) `save_snapshot` + `assert_zss <jsonpath-like-check>`: save state at the end of a workflow, parse the resulting `.zss`, assert on its `chains`/`slots` content.
- (workflow-level) `reload_and_check_audio`: the existing fixture-load-and-verify-audio mechanism, pointed at the just-saved `.zss` instead of a committed file.

### `no_new_errors` via per-step log tail diff, not a global allowlist
Rejected the originally-considered "maintain an allowlist of known-harmless ERROR lines" approach (`i2cdetect: not found`, `wlan0 not found`-style lines seen during `enable-webconf-access`'s manual testing) - an allowlist needs constant upkeep and a new harmless line silently added upstream would need a matching allowlist update before tests pass again. Comparing only the log lines emitted *during this one step* against zero tolerance is self-scoping: a pre-existing harmless startup warning is outside every step's diff window by construction (it happened once, at boot, before step 1's tail marker), so it never needs allowlisting at all.

### CUIA/MIDI-note safety deny-list, checked before every injection
`NoteCuiaDefault` maps note 0 → `POWER`, note 4 → `RESTART_UI`, and several notes are direct `SCREEN_ADMIN`/etc. jumps from which further real switch-presses could reach reboot/software-update/factory-reset. The workflow engine SHALL refuse to inject any note whose mapped CUIA is not on an explicit allow-list (safer default than a deny-list, given how easy it'd be to miss one dangerous admin-reachable path) - workflow scripts can only use CUIAs the engine already knows are safe, new ones added deliberately as workflows need them, not discovered by accident during a run.

### `.zss` structural assertions via plain JSON parsing, no snapshot-schema library
Confirmed live (see Context) that `.zss` is plain JSON with a stable enough top-level shape (`schema_version`, `chains`, `zs3`) to assert against directly - `assert any(slot.get(k) == "FS" for slot in chain["slots"] for k in slot)`-style checks, no need for a schema-validation dependency. If `schema_version` itself changes in a future `zynthian-ui` update, structural assertions written against the old shape will fail loudly and visibly (a `KeyError`/assertion failure naming the workflow) rather than silently accepting a differently-shaped file - itself a useful regression signal, not just a maintenance cost.

### Removing `test_zynthian_docker.sh` and its committed fixture outright
Per the proposal's BREAKING note: rather than keep the old single-scenario script running alongside the new system (which would mean two independently-evolving test mechanisms, one of which only covers Docker), its one scenario becomes the first workflow script on the new engine and the old script/fixture are deleted. `docker/fixtures/smoke-test-default.zss` is no longer needed - workflows build and save their own snapshot, closing the exact soundfont-path staleness problem that fixture already hit once.

## Risks / Trade-offs

- **Live-building state per run is slower than loading a static fixture** → acceptable trade-off for the coverage/reliability gain (exercises real UI code paths, not just audio-signal plumbing); workflows can still `save_snapshot` partway through and a later, separate workflow could `reload` from an earlier workflow's saved output if reuse becomes worth optimizing for - not needed for the initial library.
- **Determining "did the UI reach the expected screen" without a new remote-introspection channel** → no CUIA/OSC/websocket read-path was found during exploration (see design's Context) for querying `self.current_screen` externally; initial implementation may need to rely on log-diff + `.zss` structural checks alone for most steps, using screenshot-based screen confirmation only where it's cheap and useful, not as a universal per-step check. Worth a focused look during implementation before assuming it's unsolvable.
- **Deny/allow-list maintenance** → a workflow needing a CUIA not yet on the allow-list fails closed (refuses to inject) rather than failing open (injecting something unreviewed) - safe default, but means the initial allow-list needs to cover whatever the starting workflow library actually needs, checked explicitly during implementation rather than assumed complete.
- **Log-diff timing races** (log line for a given action arriving after the script's post-step check runs) → poll with a bounded timeout for the tail to stabilize (no new lines for N ms) rather than a fixed sleep, same class of fix already applied in `docker-automated-smoke-test`'s design for boot-sequencing races.

## Migration Plan

- Delete `test_zynthian_docker.sh` and `docker/fixtures/smoke-test-default.zss` once the new engine's ported version of that same scenario (fixture-free: build a FluidSynth chain live, connect it, inject a note, confirm audio) passes.
- Archive `docker-smoke-testing`'s spec with a `REMOVED Requirements` delta (Reason: superseded by `workflow-smoke-testing`; Migration: use the new engine's equivalent workflow script) rather than silently deleting the historical record.
- No data migration - purely dev-tooling.

## Open Questions

- Exact mechanism (if any) for asserting "the UI is now showing screen X" from outside the process - resolve during implementation (see Risks).
- Exact shape of the workflow-script format (YAML/JSON step list vs. small Python DSL) - not architecturally significant, decide during implementation based on what's easiest to keep native/Docker-agnostic.
- Full contents of the CUIA allow-list beyond what the initial 3 workflows need - grow it deliberately alongside the workflow library, not upfront.
