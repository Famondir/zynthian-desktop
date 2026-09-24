## Why

`Xvfb` in both `run_zynthian_vnc.sh` (native) and `run_zynthian_docker.sh` (Docker) is always started at a fixed `1910x1120` - the size `device_cables` (the largest of the four GUI styles) needs. `classic` and `standard` render much smaller windows within that same canvas (e.g. `classic` at roughly `1600x960`, unchanged from the configured baseline), and since `x11vnc` exports the *entire* Xvfb screen regardless of how much of it the app's window actually fills, the noVNC view shows a large black margin around the real content for those two styles - found live while testing `classic` in the browser: the actual UI occupied only the upper-left portion, with a substantial black area to the right and below. `resize=scale` then scales that whole oversized canvas (content plus black margin) into the browser window, so the usable content ends up smaller than it needs to be.

## What Changes

- Once the app's window actually appears, dynamically reconfigure the already-running `x11vnc` to export just that window (cropped to its real size) instead of the full Xvfb canvas, using `x11vnc`'s runtime remote-control channel (`x11vnc -display <disp> -R id:<windowid>`) - confirmed live to work: `x11vnc` re-announces a new framebuffer sized exactly to the target window (`rfbNewFramebuffer(..., 1009, 196, ...)` for a 1009x196 test window), with no restart of the server needed.
- This runs as a small background watcher (poll for the window, then send the one remote command) alongside the existing foreground app launch, so neither script's existing foreground-blocking-with-trap-based-cleanup shutdown behavior changes.
- Applies to both launchers via the shared `novnc_viewer.sh` helper (`docker-novnc-browser-viewer`) - one fix, not two.

## Capabilities

### Modified Capabilities
- `remote-display-viewer`: the noVNC view now fits whichever GUI style is actually running, not just the largest one.

## Impact

- `novnc_viewer.sh`: new window-tracking function, called by both callers after `start_novnc_viewer`.
- `run_zynthian_vnc.sh` / `run_zynthian_docker.sh`: one additional call each, plus the tracker's PID added to each script's existing `cleanup()` kill list.
- No change to `docker/Dockerfile`, `docker/entrypoint.sh`, or `zynthian-ui` - purely a host-side viewer concern, same scope as `novnc-browser-viewer`/`docker-novnc-browser-viewer`.
