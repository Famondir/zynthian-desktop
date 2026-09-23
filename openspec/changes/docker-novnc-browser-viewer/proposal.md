## Why

`run_zynthian_docker.sh` passes the container's UI straight through to the host's real X11 display today - `novnc-browser-viewer` explicitly scoped this out as "a materially bigger, separate change" since Docker has no private virtual display to attach a VNC server to, unlike the native install's own `Xvfb`. That gap is now a real problem in practice: the container's default window (`device_cables` in particular, a fixed 1910x1120px render) opened too large for the screen actually being used, with no way to scale it down short of installing/configuring an external VNC client by hand - the exact pain point `run_zynthian_vnc.sh` already solved for the native install.

## What Changes

- Give the container its own private headless display (`Xvfb`) instead of passing through the host's real one, and serve it over noVNC (browser-based VNC) by default, the same viewing experience `run_zynthian_vnc.sh` already provides natively.
- Extract the `Xvfb`/`x11vnc`/`websockify` orchestration (currently only in `run_zynthian_vnc.sh`) into a shared, sourced helper script, and have both `run_zynthian_vnc.sh` and `run_zynthian_docker.sh` use it - avoids a second hand-maintained copy of the same non-trivial setup (including the `WAYLAND_DISPLAY`/`XDG_SESSION_TYPE` fix `x11vnc` needs) drifting out of sync.
- Keep a raw-VNC/direct-X11 escape hatch: a VNC client can still connect directly, matching `novnc-browser-viewer`'s existing "additive, not a replacement" precedent. Direct host-X11 passthrough (today's only mode) becomes opt-in for anyone who prefers it over noVNC, rather than the default.

## Capabilities

### Modified Capabilities
- `remote-display-viewer`: broadens from "the native desktop install" to also cover the Docker desktop image (`run_zynthian_docker.sh`), using the same underlying mechanism.

## Impact

- `run_zynthian_docker.sh`: no longer binds the container to the host's `$DISPLAY`/X11 socket by default; starts its own `Xvfb` and points the container at that instead.
- `run_zynthian_vnc.sh`: refactored to source the new shared helper instead of its own inline `Xvfb`/`x11vnc`/`websockify` block - behavior unchanged, implementation de-duplicated.
- New shared file (name decided in design.md) alongside the two launcher scripts.
- No changes to `docker/Dockerfile` or `docker/entrypoint.sh` - this is entirely a host-side launch-script concern, same as the native equivalent was.
