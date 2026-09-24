# zynthian-desktop

Run the real [Zynthian](https://zynthian.org/) software stack — UI, audio engines, JACK — on a generic x86_64 Ubuntu desktop instead of Raspberry Pi hardware, as a pre-purchase test rig or a dev environment for working on Zynthian itself, without breaking the host's normal desktop audio (PipeWire).

Two ways to run it, both fully supported:

- **Docker** — an image that builds the whole stack (`docker/Dockerfile`) and runs it in a container, using JACK bound to your real audio hardware and a private virtual X11 display viewable in a browser via noVNC.
- **Native** — the same stack installed directly at `/zynthian` on this machine, with PipeWire paused for the session's duration (JACK needs exclusive access) and restored on exit.

## This repo is not the whole project

This repo holds the orchestration/dev-tooling layer only — Docker build, launcher scripts, dev/test tooling, and OpenSpec planning docs. The actual application code (`zynthian-ui`, `zynthian-webconf`) lives in their own forked repos, and the native install's runtime state lives outside any git repo. **See [CLAUDE.md](CLAUDE.md) for the full map** before touching application behavior — a desktop-port bug fix almost always belongs in one of those other repos, not here.

## Quick start

### Docker (recommended if you just want to try it)

```
./run_zynthian_docker.sh [classic|standard|device|device_cables]
```

Builds/pulls nothing automatically — build the image first (`cd docker && docker build -t zynthian-desktop:latest .`, or with `--build-arg CACHEBUST=$(date +%s)` to force a fresh clone of the actively-developed `zynthian-ui`/`zynthian-webconf` forks). The container needs `/dev/snd` passthrough and stops your host's PipeWire for the session (restored on exit).

By default you get a private headless display, viewable at the printed noVNC URL in any browser — no VNC client needed. Set `DOCKER_DISPLAY_MODE=host` to pass the container straight through to your own real X11 display instead.

### Native

```
./run_zynthian_vnc.sh [classic|standard|device|device_cables]
```

Runs the native `/zynthian/run_zynthian.sh` install on a private headless X display, same noVNC browser-viewing technique as the Docker path. Requires `/zynthian` already set up (native install, config, venv — see [CLAUDE.md](CLAUDE.md)).

Both accept the same GUI keypad style argument:
| Style | What it looks like |
|---|---|
| `classic` | Verbatim original upstream layout |
| `standard` | Same idea, button grid matches the real V5 panel |
| `device` | Chassis background matching real V5 proportions |
| `device_cables` | `device` + live audio-connection cable graphics |

## Webconf (browser config UI)

Both the Docker image and the native install also run [`zynthian-webconf`](https://github.com/Famondir/zynthian-webconf) (a patched fork — see [openspec/specs/webconf-access](openspec/specs/webconf-access/spec.md) for why).

- **Docker**: started automatically by `run_zynthian_docker.sh`, reachable at `http://localhost:8080` / `https://localhost:8443` (self-signed cert, your browser will warn — that's expected).
- **Native**: run separately, `./run_zynthian_webconf.sh` (needs a one-time `authbind` setup — see the script's own header comment). Reachable at `http://localhost` / `https://localhost`.

Default login password is `zynthian` — change it via `ZYNTHIAN_WEBCONF_PASSWORD` (webconf's own in-app password-change page is disabled for this desktop port; PAM/root login doesn't apply here since neither environment runs as root).

## Adding your own soundfonts

FluidSynth looks in two places for `.sf2`/`.sf3` files, shown in the UI's bank list as separate sources: **System** (the factory set baked into the image/native install, read-only) and **User** — `$ZYNTHIAN_MY_DATA_DIR/soundfonts/sf2`. Drop your own files there (subdirectories become banks in the UI); no rescan command needed, they show up next time you open the Bank screen for a FluidSynth chain. SFZ instruments go in the sibling `soundfonts/sfz` directory the same way.

- **Docker**: `run_zynthian_docker.sh` bind-mounts `$ZYNTHIAN_MY_DATA_DIR` (default `~/zynthian-my-data`) straight into the container at `/zynthian/zynthian-my-data` — it's the same filesystem, not a copy, so just copy your `.sf2`/`.sf3` files into `~/zynthian-my-data/soundfonts/sf2/` on the host. Works with the container already running, no restart needed.
- **Native**: same idea, directly at `/zynthian/zynthian-my-data/soundfonts/sf2`.

Want the whole `zynthian-my-data` tree (soundfonts, presets, snapshots, everything) somewhere other than `~/zynthian-my-data` — a different drive, an existing soundfont library's parent folder, etc.? Set `ZYNTHIAN_MY_DATA_DIR` before running (Docker only; the native path is fixed at `/zynthian/zynthian-my-data`):

```
ZYNTHIAN_MY_DATA_DIR=/path/to/your/data ./run_zynthian_docker.sh
```

`run_zynthian_docker.sh` creates that top-level directory if it doesn't exist yet; the container itself then scaffolds the `soundfonts/sf2`/`soundfonts/sfz`/`presets`/... layout inside it on every start (idempotent, safe to reuse a directory from a previous run).

## Dev/testing tooling

- **`setup_virtual_devices.sh`** — sets up VMPK (virtual MIDI keyboard) + `snd-aloop` (virtual audio loopback) so you can develop/test without the physical Korg Fisa Suprema. See [openspec/specs/virtual-test-devices](openspec/specs/virtual-test-devices/spec.md).
- **`test_zynthian_docker.sh`** — automated headless smoke test for the Docker image (boots it, injects a MIDI note via VMPK, confirms audio came out) — no human needed. Being superseded by `workflow_testing/` (below); see [openspec/changes/add-workflow-smoke-testing](openspec/changes/add-workflow-smoke-testing/).
- **`workflow_testing/`** — in-progress workflow-script test engine driving native *and* Docker sessions through the same scripted steps (CUIA actions injected over Zynthian's own OSC control port, not screen-clicking), with log-diff, snapshot-structure, and audio round-trip assertions. Not yet wired into a runnable CLI — see that change's `tasks.md` for status.

## Repo layout

| Path | What it is |
|---|---|
| `docker/Dockerfile` | Builds the containerized stack from source |
| `docker/entrypoint.sh` | Container's startup sequence (jackd, a2jmidid, webconf, UI) |
| `run_zynthian_docker.sh` | Launch the Docker image |
| `run_zynthian_vnc.sh` | Launch the native install on a headless display |
| `run_zynthian_webconf.sh` | Launch webconf natively |
| `novnc_viewer.sh` | Shared Xvfb+x11vnc+noVNC helper used by both `run_zynthian_*.sh` scripts |
| `setup_virtual_devices.sh` | One-time setup for VMPK/`snd-aloop` dev testing |
| `test_zynthian_docker.sh` | Automated Docker smoke test (being superseded) |
| `workflow_testing/` | New native+Docker workflow-test engine (in progress) |
| `config/zynthian_envars_custom.sh.example` | Reference copy of this machine's native runtime config |
| `openspec/` | Design/planning docs — proposals, specs, and their history |

## Design decisions and history

Every non-obvious decision in this repo (why jackd instead of PipeWire's JACK shim, why a forked webconf, why OSC instead of clicking a virtual piano, ALSA quirks found the hard way, ...) is written down in `openspec/`:

- `openspec/specs/` — the current, accepted behavior of each capability.
- `openspec/changes/` — in-progress work; each has a `proposal.md` (why), `design.md` (how, with alternatives considered and rejected), and `tasks.md` (status).
- `openspec/changes/archive/` — completed changes, kept for their design rationale even after being folded into `specs/`.

Start with a spec's `design.md`/the relevant archived change before assuming a piece of behavior is arbitrary — most of it isn't.
