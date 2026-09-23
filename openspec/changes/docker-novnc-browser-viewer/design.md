## Context

`run_zynthian_docker.sh` today bind-mounts the host's own `/tmp/.X11-unix` and passes through the host's `$DISPLAY`, so the container's window is just another window on the host's real desktop - full native size, no scaling, exactly the "opened too large for the screen" problem `run_zynthian_vnc.sh` already solved for the native install by giving it a private `Xvfb` + noVNC front end instead. `novnc-browser-viewer` deliberately left Docker out of that fix (see its design.md's Non-Goals) because the container has no private virtual display to attach a VNC server to under host-X11 passthrough - it needs its own `Xvfb`, the same way the native install already has one.

## Goals / Non-Goals

**Goals:**
- `run_zynthian_docker.sh` gets its own private `Xvfb`, viewable by default over noVNC in a browser, with no manual VNC-client setup - matching `run_zynthian_vnc.sh`'s existing UX exactly.
- Both launcher scripts run from the same non-duplicated `Xvfb`/`x11vnc`/`websockify` logic, so a fix to one (e.g. the `WAYLAND_DISPLAY` workaround) can't silently miss the other.
- Keep today's host-X11-passthrough mode available as an explicit opt-out for anyone who prefers it.

**Non-Goals:**
- Changing `docker/Dockerfile`/`docker/entrypoint.sh` - the container itself doesn't know or care whether `$DISPLAY` points at a real host display or a private `Xvfb`; this is purely a host-side launch-script concern.
- LAN/TLS exposure, multi-viewer, or anything `novnc-browser-viewer` already scoped out for the native case - unchanged here.
- Changing the default GUI style Docker launches with (`standard`) - the "window too big" problem applies to any style on a small enough screen, and noVNC's `resize=scale` fixes it generically rather than by picking a smaller default style.

## Decisions

### Extract a shared `novnc_viewer.sh`, sourced by both scripts
`run_zynthian_vnc.sh`'s existing `Xvfb`/`x11vnc`/`websockify` block (including the non-obvious `WAYLAND_DISPLAY`/`XDG_SESSION_TYPE` strip that `x11vnc` needs - see its own comment) becomes a function, `start_novnc_viewer`, in a new `novnc_viewer.sh` at the repo root. Both launcher scripts `source novnc_viewer.sh` and call that function after setting their own `VNC_DISPLAY`/`VNC_PORT`/`NOVNC_PORT`/`NOVNC_BIND`/`NOVNC_DIR`/`XVFB_SIZE` variables (same names already used in `run_zynthian_vnc.sh` today, so its own refactor is close to "cut this block into the new file, source it, call the function"). The function sets `XVFB_PID`/`X11VNC_PID`/`WEBSOCKIFY_PID` as plain (unprefixed) variables, exactly as the inline code does today, so each caller's own `cleanup()` trap keeps killing them the same way it already does - no change to either script's trap logic beyond where those PIDs come from.
- Alternative considered: duplicate the block into `run_zynthian_docker.sh` (the approach `docker-automated-smoke-test` took for its own one-off `docker run` invocation, accepting flag drift as a documented trade-off there). Rejected here because this block is materially larger and includes a non-obvious platform workaround (`WAYLAND_DISPLAY`) that has already needed one bug-driven fix once - duplicating it doubles the chance a future fix only lands in one copy.

### Distinct default ports/display per script, so both can run at once
Docker's launcher gets its own defaults, separate from the native script's, so a developer can run a native `run_zynthian_vnc.sh` session and a `run_zynthian_docker.sh` session side by side without a port clash: `VNC_DISPLAY=:96` (native: `:97`), `VNC_PORT=5901` (native: `5900`), `NOVNC_PORT=6081` (native: `6080`). Both remain overridable via the same env vars as before.

### `XVFB_SIZE` matches the native script's, for the same reason
`1910x1120x24` - covers `device_cables`'s fixed 1910x1120 render (the largest of the four styles); `classic`/`standard`/`device` all fit within it since `docker/entrypoint.sh` adjusts `DISPLAY_WIDTH`/`DISPLAY_HEIGHT` itself per style, same as the native launcher already relies on.

### Host-X11 passthrough kept as an opt-out, not removed
A new `DOCKER_DISPLAY_MODE` env var (`novnc` default, `host` opt-out) selects between the new private-`Xvfb`-plus-noVNC path and today's exact host-`$DISPLAY`-passthrough behavior. `host` mode's code path is unchanged from what exists today (same `-e DISPLAY="$DISPLAY"`, same `/tmp/.X11-unix` mount, same `xhost +local:docker` against the host's real display) - this is purely additive, matching `novnc-browser-viewer`'s own "additive, not a replacement" precedent for the native raw-VNC fallback.

### `xhost` targets the private display, called from `run_zynthian_docker.sh` itself
Granting the container X access (`xhost +local:docker`) only matters for Docker (the native process is a direct child of the same user session, no `xhost` needed - which is why today's `run_zynthian_vnc.sh` never calls it). This stays in `run_zynthian_docker.sh`, called against `$VNC_DISPLAY` (the private display) once `start_novnc_viewer` has started `Xvfb`, rather than being folded into the shared helper - the helper stays display-technology-agnostic (it doesn't know or care that one of its callers is about to run Docker containers against the display it set up).

## Risks / Trade-offs

- [Refactoring `run_zynthian_vnc.sh` to source the new shared file touches already-shipped, archived (`novnc-browser-viewer`) code] → Behavior-preserving by design (same variables, same function body, same trap pattern); re-verify with the same manual checks that change's tasks.md already used (fresh clone, reuse, `resize=scale`, Ctrl+C cascade, raw VNC still works) before considering this done.
- [Two independent noVNC viewers (native + Docker) running at once means two browser tabs to juggle, not a unified view] → Acceptable - they're two genuinely different runtimes (native install vs. container), not expected to run simultaneously in normal use; the distinct-defaults decision above just prevents them from *breaking* each other if a developer does happen to run both.
- [**Found live during validation**: running a native `run_zynthian_vnc.sh` session and a Docker `run_zynthian_docker.sh` session at the same time - the specific scenario the distinct-ports decision above targets - the *display/port* isolation works exactly as designed (both noVNC endpoints reachable on their own ports, no clash), but the Docker session's own `jackd`/`ZynMidiRouter` failed to initialize, because both scripts independently stop/start the *same* host PipeWire session and expect exclusive access to the same physical audio hardware while running. This is not a regression this change introduces - neither script has ever supported two concurrent Zynthian sessions (native+native, Docker+Docker, or native+Docker) sharing one machine's audio hardware, and `docker-desktop-image`'s own design never assumed otherwise] → Documented as a pre-existing limitation, not a bug to fix here: the display/noVNC layer is genuinely dual-session-safe now, the audio layer never was and remains out of scope.

## Open Questions

None - this follows the same shape `novnc-browser-viewer` already validated for the native case; the only new territory is the shared-helper extraction and Docker's own port/display defaults, both resolved above.
