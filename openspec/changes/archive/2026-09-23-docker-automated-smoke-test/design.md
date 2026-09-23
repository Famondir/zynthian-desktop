## Context

Three things already exist independently from this session's work:
- `run_zynthian_vnc.sh` proves a fully headless X display (Xvfb) is enough to run the real Tk GUI and interact with it programmatically (screenshots, synthetic input) with no physical monitor.
- `support-virtual-test-devices` proved VMPK (bridged via a2jmidid, recognized as virtual hardware by the `zynautoconnect.py` regex fix) and `snd-aloop` (a real kernel loopback card, genuine hotplug-equivalent add/remove events) stand in for the physical Suprema for MIDI and audio respectively.
- `run_zynthian_docker.sh` proves the Docker image boots and passes audio/MIDI/X11 through correctly on this machine, but only interactively (task 8.2 still open) - nobody has scripted a check against it.

This change wires the first two together against the third: run the Docker image against a private Xvfb display instead of the host's real one, drive it with the same virtual MIDI/audio devices, and assert on the result instead of a human watching the window.

## Goals / Non-Goals

**Goals:**
- One command that boots the Docker image headlessly, exercises the same MIDI→audio signal path validated manually this session, and exits 0/non-zero based on whether GUI render, MIDI routing, and audio output all actually happened.
- Reuse already-validated tooling (Xvfb, VMPK, `snd-aloop`, a2jmidid) rather than introducing a new simulated-device mechanism.
- Leave the interactive scripts (`run_zynthian_docker.sh`, `run_zynthian_vnc.sh`) untouched - this is a new, separate script, not a mode flag bolted onto either.

**Non-Goals:**
- Hosted CI integration (see proposal's Impact) - no `/dev/snd`/X11/`audio`-group on a typical CI runner; this stays a locally-triggered dev script.
- Testing real-hardware-specific hotplug behavior (USB add/remove) - that's `fix-audio-hotplug-support`'s real-hardware validation tasks, out of scope here.
- Pixel-perfect visual regression testing of the GUI - the screenshot check only confirms *something* rendered (non-blank), not that it looks correct; that's still a human job (`touchkeypad-*` changes' manual visual passes).

## Decisions

### Own `docker run` invocation, not a reuse of `run_zynthian_docker.sh`
`run_zynthian_docker.sh` runs `docker run --rm -it ...` in the foreground, attached to whatever terminal invokes it - correct for interactive use, awkward for a script that also needs to `docker exec` into the same container to poll `jack_lsp`/`jack_connect` state while it's running. Rather than adding test-only concerns (detached mode, `--name` for exec targeting, non-tty) to the production interactive script, the new script builds its own `docker run -d --name zynthian-smoke-test ...` invocation mirroring the same flags (`--device /dev/snd`, `--group-add audio`, the `SYS_NICE`/`rtprio`/`memlock` trio, the `zynthian-my-data` bind mount) documented in `docker-desktop-image/design.md`. Both scripts stay independently readable; flag drift between them is a small, acceptable cost versus tangling the two use cases.

### Private Xvfb display, not the host's real X server
Matches `run_zynthian_vnc.sh`'s approach exactly: start `Xvfb :98 ...`, export `DISPLAY=:98` for both VMPK and the `docker run` command's `-e DISPLAY`/X11 socket mount, run `xhost +local:docker` against that display (not the host's real one). This makes the whole test self-contained and safe to run alongside a real interactive session on the same machine without fighting over the visible display.

### Real VMPK + `xdotool` key injection, not a new MIDI library
VMPK maps its on-screen piano to the QWERTY row. Rather than adding a new dependency (e.g. `python-rtmidi`/`mido`) to synthesize raw ALSA MIDI events, launch the real `vmpk` binary on the private Xvfb display (headless - nothing needs to *see* it) and use `xdotool key` to send the same keypress VMPK's own UI would receive. This reproduces the exact signal path already validated manually (VMPK → a2jmidid → `zynautoconnect`'s regex whitelist → `ZynMidiRouter`) instead of a synthetic approximation of it, which also means it naturally re-verifies `support-virtual-test-devices` task 1.2 (does the MIDI whitelist fix survive a restart) as a side effect on every run.

### A committed fixture snapshot gives the container an active chain to route MIDI into
**Gap found during implementation**: nothing in the original design accounts for the fact that a freshly-booted Zynthian has no chains at all - injecting a MIDI note into an empty session has nowhere to go, so the audio-output check would fail regardless of whether MIDI routing itself is correct. `zyngui/zynthian_gui.py`'s startup path (confirmed in source) calls `state_manager.load_default_snapshot()` whenever `ZYNTHIAN_UI_RESTORE_LAST_STATE=0` (the default) and `<snapshot_dir>/default.zss` exists - `snapshot_dir` resolves under `$ZYNTHIAN_MY_DATA_DIR/snapshots`. So: commit a minimal, hand-verified snapshot (single FluidSynth chain, MIDI channel 0 - VMPK's default output channel - connected straight to the main mix bus, no effects) at `docker/fixtures/smoke-test-default.zss` in this repo, and have the smoke-test script copy it to `<scratch-my-data-dir>/snapshots/default.zss` before starting the container. Existing demo snapshots under `/zynthian/zynthian-data/snapshots/` were considered and rejected as a shortcut - they're an older, differently-shaped schema (`index`/`mixer`/`layers` top-level keys) than what this fork's `zynthian_state_manager.py` currently produces/expects (`schema_version`/`chains`/`zs3`), so reusing one directly risks a silent partial load instead of a real fixture; the committed fixture must be generated by actually saving a snapshot from a running instance of this exact fork, not adapted from an old file.
- Also implies the smoke-test script needs its own **scratch** `zynthian-my-data` directory (not the user's real `$HOME/zynthian-my-data`, unlike `run_zynthian_docker.sh`'s default) - both so the fixture snapshot can be dropped into `snapshots/default.zss` without touching the user's own snapshots, and so a smoke-test run can't collide with or corrupt real user data.

### Audio captured via `jack_rec` inside the container, not `arecord` against `snd-aloop`'s capture side
**Revised during implementation**: the original plan (capture the loopback's capture side with `arecord`, mirroring the manual `snd-aloop` technique) was tried first and abandoned - the paired capture substream returned `EIO` on every read attempt regardless of format/channel-count tuning (`SNDRV_PCM_IOCTL_READI_FRAMES` failing immediately after a clean `PREPARE`, confirmed with `strace`). This is the same class of `snd-aloop` cross-coupling flakiness `support-virtual-test-devices` already hit and worked around (by connecting fluidsynth's JACK output directly to the target chain) rather than fixed - it recurs here for the same underlying reason. Fix: run `jack_rec` *inside* the container via `docker exec` (sharing the container's own JACK server, no ALSA loopback involved at all), tapping `zynmixer_bus:output_00a`/`00b` - the main mixbus output, one hop upstream of `system:playback_*` (itself not recordable: it's an input-direction JACK port, confirmed live via `jack_rec`'s own "cannot connect input port ... to system:playback_1" error) - then `docker cp` the resulting WAV out to the host for the `sox <file> -n stat` non-silence check (RMS amplitude above a small threshold, tuned empirically - see Open Questions). `snd-aloop` is still loaded and still what the container's `jackd` binds its ALSA backend to (`JACKD_OPTIONS`'s `-d hw:<card>,0`, pinned to `-i 2 -o 2` rather than the hardware-max 32 channels `snd-aloop` reports, which jackd opens by default without an explicit count) - only the *capture-side verification* moved off of it, not the audio-output binding itself.
- A related gap surfaced by the same debugging pass: the committed fixture snapshot's FluidSynth chain references a soundfont path from the native machine it was saved on (`Roland Fantom X/00 Ac.Piano.sf2`), which doesn't exist in the container - FluidSynth logged a "can't be loaded" warning and produced no audio at all, independent of the capture-mechanism bug above. Fixed by symlinking the one soundfont both the host and the image actually have (the `fluid-soundfont-gm` apt package, identical path on both - see `docker/Dockerfile`'s package list) into place at the exact path the fixture expects, rather than regenerating the fixture.

### Screenshot non-blank check via ImageMagick, not a golden-image diff
`import -display :98 -window root shot.png` (already available via the `x11-apps`-adjacent tooling this project already depends on) captures the framebuffer; `identify -format "%[fx:standard_deviation]" shot.png` near zero means a blank/black window (crash, failed X connection, GUI never painted) - not a full golden-image comparison, which would be brittle across style/resolution changes and is explicitly a Non-Goal.

### The script owns loading/unloading `snd-aloop`, but only if it loaded it itself
Mirrors the idempotency requirement already written into `support-virtual-test-devices` task 2.2 for the planned dev script: check `lsmod | grep snd_aloop` before `modprobe`, and only `modprobe -r` on cleanup if this run was the one that loaded it - never unload a module something else (a real dev session) is relying on.

## Risks / Trade-offs

- **Timing-dependent boot sequencing** (Xvfb ready → VMPK window exists → container's JACK/GUI ready → key injection lands) → poll for concrete readiness signals (`xdotool search` for the VMPK window, `jack_lsp` inside the container via `docker exec` for expected ports) with a bounded timeout and a clear timeout error, not fixed `sleep` durations guessed from one observed run.
- **Competing for `/dev/snd`** if a real interactive session (native or another Docker run) is already using the same physical/loopback device → the script should detect an existing `zynthian-smoke-test` container or a running native session before starting, and fail fast with a clear message rather than silently producing a false failure from device contention.
- **Stale container from a previous crashed run** reusing the fixed `--name zynthian-smoke-test` → `docker rm -f zynthian-smoke-test` (ignoring "not found") at the start of every run, before `docker run -d`.
- **Flag drift** between this script's own `docker run` invocation and `run_zynthian_docker.sh`'s → both reference `docker-desktop-image/design.md`'s flag list as the source of truth; a future change to one should prompt checking the other, noted as a comment in both scripts.

## Migration Plan

N/A - purely additive, opt-in script; nothing else changes behavior. No rollback needed beyond deleting the script.

## Open Questions

- Exact non-blank (`standard_deviation`) and non-silence (`sox stat` RMS) thresholds - tune empirically against the real container output during implementation/validation rather than guessing numbers here.
- Whether `xdotool`-driven VMPK key injection reproduces the same "MIDI Out" vs. "VMPK Output" ALSA-client-name variability noted in `support-virtual-test-devices` task 1.1 (dependent on whether `~/.config/vmpk.sourceforge.net/VMPK.conf` already exists inside whatever HOME the script gives VMPK) - worth confirming during implementation; if it does vary, the existing regex fix already covers both names, so this is a confirmation, not a new fix.
