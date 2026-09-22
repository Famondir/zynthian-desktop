## Context

`run_zynthian_vnc.sh` currently starts `Xvfb` (virtual X display) + `x11vnc` (VNC server bound to it) and tells the user to connect an external VNC client (Remmina) to view/interact with it, since `device`/`device_cables`'s render is a fixed 1910x1120px window that can't be resized from inside the app (see the script's own header comment). This worked, but two problems showed up in practice this session:

- Remmina's "scale to window" only approximates the intended size, since the profile's `window_width`/`window_height` are logical (GTK) pixels that the host's display scale factor (150% on this laptop, not the "125% or so" initially guessed - confirmed via `gdbus`/Mutter's `DisplayConfig`) then multiplies again before anything hits the screen - required manual back-calculation (955x560 -> 636x373) to land close to the intended physical size.
- It requires an external app (Remmina) to be installed and manually configured (a saved `.remmina` profile) rather than "just open a link."

Real Zynthian hardware already solves the identical problem (viewing/controlling its touchscreen UI remotely) with `noVNC` - a pure browser-based VNC client - sitting in front of the same kind of `x11vnc`/`vncserver` setup (see `zynthian-sys`'s `novnc0.service`/`novnc1.service`, `vncserver0.service`/`vncserver1.service`). Manually running `websockify --web=<noVNC dir> 6080 localhost:5900` alongside the existing `run_zynthian_vnc.sh` this session confirmed it works and that noVNC's `resize=scale` URL parameter scales responsively to the browser window with no manual pixel math at all.

## Goals / Non-Goals

**Goals:**
- Replace the Remmina-based viewing workflow with a browser-based one (noVNC), reachable via a plain URL printed by the script.
- No manual multi-terminal juggling - `run_zynthian_vnc.sh` alone should start everything needed (Xvfb, x11vnc, noVNC/websockify, Zynthian itself).
- Keep the change additive/reversible - don't remove the ability to still connect a regular VNC client to the same `x11vnc` port if someone prefers that.

**Non-Goals:**
- TLS/certificates. Real hardware's `novnc0.service` uses `--cert`/`--key` because it may be reachable over a LAN/untrusted network; this stays `localhost`-only (or LAN-reachable over plain `ws://` at most, see Open Questions) - not a public-facing service, so the added complexity of generating/managing certs isn't justified here.
- The Docker desktop image. `run_zynthian_docker.sh` passes the container's UI straight through to the *host's* X11 display (bind-mounted `/tmp/.X11-unix`, inherited `$DISPLAY`) - there's no private virtual display inside the container to attach a VNC server to, unlike the native install's own `Xvfb`. Giving Docker an equivalent browser-viewer would mean reworking its display strategy to run its own internal `Xvfb`/`x11vnc` instead of (or as an option alongside) host-X11 passthrough - a materially bigger, separate change, not assumed or scoped here.
- Multi-user/concurrent-viewer support, authentication, or anything beyond "one developer views their own dev instance."

## Decisions

- **`websockify` (apt package) + a git-cloned `noVNC` static client, not the Ubuntu `novnc` apt package.** Checked `apt-cache show novnc`: it's the OpenStack Nova console proxy packaging (pulls in `python3-oslo.*`, `nodejs`, `net-tools` - a dozen+ irrelevant transitive deps). `apt-cache depends websockify` alone is lean (`python3-jwcrypto`/`python3-numpy`/`python3-websockify`/`python3`/`libc6`). This also matches upstream Zynthian's own approach (`zynthian-sys/scripts/recipes/install_noVNC.sh` git-clones `noVNC` directly rather than using a distro package).
- **`noVNC` fetched on demand, not vendored into this repo.** ~15MB, pure static JS/HTML (no build step). Matches the precedent set for `vmpk`/`snd-aloop` in `support-virtual-test-devices` (dev tooling fetched/installed as needed, not committed) and upstream Zynthian's own convention (git-cloned into `$ZYNTHIAN_SW_DIR` by an install script, not vendored into `zynthian-sys`'s own repo). `run_zynthian_vnc.sh` clones it to a fixed path next to itself (`$(dirname "$0")/noVNC`) if missing - the exact path the user already has it at from this session's manual testing, so no relocation needed. Added to `.gitignore`.
- **One combined script, no separate "start noVNC" step.** `run_zynthian_vnc.sh` already orchestrates `Xvfb`/`x11vnc`/`run_zynthian.sh` with a shared `cleanup()` trap; `websockify` is a fourth process of the same shape (background, PID tracked, killed on exit) - no reason to split it into a second script the user has to remember to also run.
- **Print the noVNC URL, keep the raw VNC port available too.** The script's final echo changes from "connect a VNC client to localhost:$VNC_PORT" to the noVNC URL (`http://localhost:$NOVNC_PORT/vnc.html?host=localhost&port=$NOVNC_PORT&resize=scale`), but `x11vnc` keeps listening on `$VNC_PORT` unchanged - Remmina (or any VNC client) still works exactly as before for anyone who prefers it; this is additive, not a replacement of the underlying server.
- **Bind websockify to `localhost` by default, not `0.0.0.0`.** Keeps the default behavior matching today's `x11vnc` binding (also effectively localhost-only in practice, since nothing publishes the port elsewhere) and avoids quietly exposing an unauthenticated VNC-over-websocket service to the LAN. LAN access (e.g. from a phone) is left as an opt-in via an env var rather than the default - see Open Questions.

## Risks / Trade-offs

- [`websockify` is a new system dependency (`apt install`), and `noVNC` a new on-demand git-clone (network access required on first run)] → Both are one-line, low-friction installs already verified working this session; the script can check for both and print a clear one-line instruction if either is missing, same pattern `run_zynthian_vnc.sh` could use for any other missing tool.
- [No TLS means VNC credentials/framebuffer data cross the network in the clear if `NOVNC_BIND`/equivalent is ever changed to something LAN-reachable] → Documented as an explicit non-goal/opt-in; default stays `localhost`-only where this doesn't matter.
- [A second background process (`websockify`) is one more thing `cleanup()` must reliably kill on exit, alongside `Xvfb`/`x11vnc`] → Same trap/PID-tracking pattern already used for the other two; no new mechanism needed.

## Open Questions

- Should there be an easy opt-in for LAN access (e.g. `NOVNC_BIND=0.0.0.0 ./run_zynthian_vnc.sh`) for viewing from a phone/tablet on the same network, or is `localhost`-only sufficient for now? Left as a tasks.md item to decide during implementation rather than blocking the proposal - default is `localhost`-only either way.
