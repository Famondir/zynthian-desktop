## Why

`run_zynthian_vnc.sh` (added for viewing `device_cables`' fixed 1910x1120 render on a smaller laptop screen) currently requires a separate VNC client app (Remmina) plus manual per-viewer scale-mode/window-size configuration to shrink the view - fiddly, and the configured window size only approximates the actual on-screen result once the host's display scaling factor is accounted for (discovered the hard way this session: a 955x560 profile setting rendered at ~1432x840 physical pixels under 150% display scaling). Real Zynthian hardware already solves this exact problem with noVNC (a browser-based VNC client) sitting in front of its own VNC servers, and its `resize=scale` mode scales responsively to the browser window with no manual pixel math. Manually testing `websockify` + a `noVNC` checkout alongside the existing script this session confirmed it works well and resolves the scaling awkwardness cleanly.

## What Changes

- `run_zynthian_vnc.sh` starts `websockify` (serving the vendored `noVNC` static web client, proxying to the existing `x11vnc` port) alongside the `Xvfb`/`x11vnc` it already starts, and prints the ready-to-use browser URL (with `resize=scale`) instead of (or in addition to) the current "connect via Remmina" instructions.
- `noVNC` itself is fetched on demand (git-cloned to a fixed path next to the script) if not already present, matching how `vmpk`/`snd-aloop` are treated as on-demand dev tooling rather than vendored - not committed to this repo (added to `.gitignore`).
- No change to the underlying `Xvfb`/`x11vnc` setup or to `/zynthian/run_zynthian.sh` itself - purely adds a browser-facing front end to what's already there.

## Capabilities

### New Capabilities
- `remote-display-viewer`: browser-based (noVNC) viewing of the native desktop install's UI on a virtual display, replacing the external-VNC-client (Remmina) workflow.

### Modified Capabilities
(none)

## Impact

- `run_zynthian_vnc.sh`: add the `websockify` startup step, on-demand `noVNC` fetch, and updated printed instructions.
- `.gitignore` (new or appended): exclude the on-demand `noVNC` checkout.
- New dependency: `websockify` (apt package, already confirmed lightweight - `python3-jwcrypto`/`python3-numpy`/`python3-websockify` only, not the heavier OpenStack-flavored `novnc` apt package).
- Native desktop install only (`/zynthian/run_zynthian.sh` via `run_zynthian_vnc.sh`) - the Docker desktop image currently passes the container's UI straight through to the host's own X11 display (no private display to attach a VNC server to), so this doesn't apply there without a separate, larger change to how the container renders. Explicitly out of scope here.
