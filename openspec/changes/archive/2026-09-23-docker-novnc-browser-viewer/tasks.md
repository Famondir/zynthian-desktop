## 1. Shared helper extraction

- [x] 1.1 Create `novnc_viewer.sh` at the repo root with a `start_novnc_viewer` function, containing the `websockify` check, on-demand `noVNC` clone, `Xvfb` start, `x11vnc` start (with the `WAYLAND_DISPLAY`/`XDG_SESSION_TYPE` strip), and `websockify` start currently inline in `run_zynthian_vnc.sh` - reading `VNC_DISPLAY`/`VNC_PORT`/`NOVNC_PORT`/`NOVNC_BIND`/`NOVNC_DIR`/`XVFB_SIZE` from the caller's already-set variables and setting `XVFB_PID`/`X11VNC_PID`/`WEBSOCKIFY_PID` for the caller's own cleanup trap
- [x] 1.2 Refactor `run_zynthian_vnc.sh` to `source novnc_viewer.sh` and call `start_novnc_viewer` instead of its inline block; keep its own variable defaults, `cleanup()` trap, and final "Starting Zynthian" line unchanged
- [x] 1.3 Manually re-verify `run_zynthian_vnc.sh` still works exactly as before (fresh `noVNC` clone path, reuse path, `resize=scale`, Ctrl+C cascade, raw VNC client still connects) - this refactor must be behavior-preserving

## 2. Docker launcher: noVNC by default

- [x] 2.1 Add `DOCKER_DISPLAY_MODE` (default `novnc`, opt-out `host`) to `run_zynthian_docker.sh`
- [x] 2.2 In `novnc` mode: set `VNC_DISPLAY=:96`, `VNC_PORT=5901`, `NOVNC_PORT=6081` defaults (distinct from `run_zynthian_vnc.sh`'s `:97`/`5900`/`6080`), `XVFB_SIZE=1910x1120x24`, source `novnc_viewer.sh` and call `start_novnc_viewer`, then `xhost +local:docker` against `$VNC_DISPLAY`, then run the existing `docker run` with `-e DISPLAY="$VNC_DISPLAY"` instead of the host's `$DISPLAY`
- [x] 2.3 In `host` mode: keep exactly today's behavior (`-e DISPLAY="$DISPLAY"`, host `/tmp/.X11-unix`, `xhost +local:docker` against the host's real display) - no Xvfb/x11vnc/websockify started
- [x] 2.4 Extend `run_zynthian_docker.sh`'s `cleanup()` to also kill `XVFB_PID`/`X11VNC_PID`/`WEBSOCKIFY_PID` (when set, i.e. in `novnc` mode) alongside its existing PipeWire-restart logic
- [x] 2.5 Print the noVNC URL (mirroring `run_zynthian_vnc.sh`'s echo) before starting the container in `novnc` mode

## 3. Documentation

- [x] 3.1 Update `run_zynthian_docker.sh`'s header comment to describe the new default (private display + noVNC) and the `DOCKER_DISPLAY_MODE=host` opt-out
- [x] 3.2 Update `CLAUDE.md` if it references `run_zynthian_docker.sh`'s display behavior (check before assuming a change is needed). Checked - `CLAUDE.md` only mentions `run_zynthian_docker.sh` by name in the repo-layout list, no display-behavior claim to go stale. No change needed.

## 4. Validation

- [x] 4.1 Fresh run of `run_zynthian_docker.sh` in default (`novnc`) mode: confirm the printed URL opens in a browser and shows the container's GUI. Confirmed: `curl` against the printed URL returned 200, and a screenshot of the private `Xvfb` display (`import`/`identify`) showed the real "Add Chain..." screen rendering correctly (not blank) - `resize=scale` itself is noVNC's own unchanged client-side behavior, already proven for the native case and not specific to Docker, so not re-tested pixel-by-pixel here. (`docker run -it` needed a fake tty via `script -qc` to run non-interactively for this test - an artifact of this being driven from an automated shell, not a script change.)
- [x] 4.2 Confirm `DOCKER_DISPLAY_MODE=host ./run_zynthian_docker.sh` still behaves exactly as `run_zynthian_docker.sh` did before this change. Confirmed via a safe dry-run (real `$DISPLAY`, deliberately invalid image tag so `docker run` fails immediately without ever touching the host's real display): no `Xvfb`/`x11vnc`/`websockify` started, went straight to `xhost`+PipeWire-stop+`docker run` exactly as before, PipeWire correctly restored on exit.
- [x] 4.3 Run a native `run_zynthian_vnc.sh` session and a Docker `run_zynthian_docker.sh` (novnc mode) session at the same time. **Found a real, pre-existing limitation, not a regression** (see design.md's Risks): display/port isolation worked exactly as designed (native's noVNC on 6080 stayed reachable throughout), but the Docker session's `jackd`/`ZynMidiRouter` failed to initialize, because both scripts independently stop/start the *same* host PipeWire session and assume exclusive access to the same physical audio hardware - neither script has ever supported two concurrent Zynthian sessions sharing one machine's audio. Documented rather than fixed, since fixing shared-hardware audio arbitration between two independent launcher scripts is well outside this change's scope (display/viewing only).
- [x] 4.4 Confirm Ctrl+C on `run_zynthian_docker.sh` in `novnc` mode cleanly tears down the container, `Xvfb`/`x11vnc`/`websockify`, and restores host PipeWire, with no orphaned processes. Confirmed (via `docker kill` on the running container, equivalent to the Ctrl+C cascade): container removed, no orphaned `zynthian_main`/`Xvfb`/`x11vnc`/`websockify`/`run_zynthian_docker.sh` processes, PipeWire back to `active`.
