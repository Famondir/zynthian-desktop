## Why

Two validation tasks are sitting open because they require either the physical Korg Fisa Suprema or a human clicking through the GUI: `docker-desktop-image` task 8.2 (compare Docker's behavior against the proven-working native `run_zynthian.sh` session) and `support-virtual-test-devices` task 5.1 (does the VMPK/`snd-aloop` virtual-device workflow even work against the Docker image, given `/dev/snd` passthrough - never checked). Both currently need manual, one-off verification, which doesn't scale to "check again after every change to the Dockerfile or to `zynthian-ui`". This session already built and validated the pieces needed to automate it instead: a headless X display technique (`run_zynthian_vnc.sh`'s Xvfb), a virtual MIDI source (VMPK, bridged via a2jmidid), and a virtual audio interface (`snd-aloop`). Wiring those into a scripted check against the Docker image turns "manually confirm Docker works like native" into a repeatable command.

## What Changes

- Add a repo-root script that runs the Docker image headlessly (Xvfb, same technique as `run_zynthian_vnc.sh`) and automatically verifies:
  - the container's GUI actually renders (screenshot capture, non-blank check)
  - MIDI reaches an active audio chain (VMPK → a2jmidid → JACK port connections, observed via `jack_lsp`/`jack_connect` state inside the container, same signal path validated natively this session)
  - audio is actually produced end-to-end (drive a note through fluidsynth, capture the `snd-aloop` loopback side, confirm non-silence - not just "no crash")
  - clean shutdown: container exits, host PipeWire restarts, no orphaned `jackd`/`a2jmidid` processes
- Script exits non-zero with a diagnostic summary on any failed check, so it's usable as a manual regression gate before/after Dockerfile or `zynthian-ui` changes. This is a local dev script, not a hosted CI job (see Impact) - "automatic" means one command replaces manual clicking, not a GitHub Actions pipeline.
- Resolves `docker-desktop-image` task 8.2 and `support-virtual-test-devices` task 5.1 as a byproduct of building and running this - both get their answer recorded there once this script has been run successfully.

## Capabilities

### New Capabilities
- `docker-smoke-testing`: automated, headless, one-command verification that the Docker desktop image boots, renders its GUI, and correctly passes MIDI through to produced audio output - using the same virtual MIDI/audio devices already validated for native dev testing, so this doesn't depend on the physical Suprema either.

### Modified Capabilities
(none - `zynthian-desktop-runtime`'s requirements aren't changing. `docker-desktop-image` and `support-virtual-test-devices` are themselves still-open in-progress changes, not yet-archived specs to delta against; this change unblocks two of their tasks rather than modifying their scope.)

## Impact

- New script at the repo root (name/language decided in design.md), alongside `run_zynthian_docker.sh`/`run_zynthian_vnc.sh`.
- Depends on `docker-desktop-image`'s image being buildable/runnable (task 8.1, already done) and `support-virtual-test-devices`'s VMPK/`snd-aloop` groundwork (task 1.1, already done ad hoc this session).
- Out of scope: a hosted CI pipeline (GitHub Actions, etc.) - a typical CI runner has no `/dev/snd`, no `audio` group membership, and no X11 socket to pass through, so this stays a local/manual-trigger script, not an automatic on-push gate.
