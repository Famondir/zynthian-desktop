## 1. Dependencies

- [x] 1.1 Add a `websockify` presence check to `run_zynthian_vnc.sh` (e.g. `command -v websockify`), printing a one-line `sudo apt install websockify` hint and exiting if missing - matches how the script should fail clearly rather than silently misbehave.
- [x] 1.2 Add on-demand `noVNC` fetch: if `$(dirname "$0")/noVNC` doesn't exist, `git clone https://github.com/novnc/noVNC.git` to that path before starting `websockify`.
- [x] 1.3 Add `/noVNC/` to this repo's `.gitignore` (create the file if it doesn't exist yet).

## 2. Script changes

- [x] 2.1 Add a `NOVNC_PORT` variable (default `6080`, overridable like `VNC_DISPLAY`/`VNC_PORT` already are).
- [x] 2.2 Start `websockify --web=<noVNC dir> $NOVNC_PORT localhost:$VNC_PORT` in the background after `x11vnc` is up, log to `/tmp/zynthian_websockify.log` (matching the existing `/tmp/zynthian_*.log` convention), track its PID.
- [x] 2.3 Extend `cleanup()` to also kill the `websockify` PID alongside the existing `X11VNC_PID`/`XVFB_PID`.
- [x] 2.4 Update the printed instructions: replace/augment "Connect a VNC client to localhost:$VNC_PORT" with the noVNC URL (`http://localhost:$NOVNC_PORT/vnc.html?host=localhost&port=$NOVNC_PORT&resize=scale`), keep a note that a raw VNC client can still connect to `$VNC_PORT` directly.
- [x] 2.5 Update the script's header comment (currently says "connect a VNC client (e.g. Remmina)") to describe the new browser-based workflow as the primary path.

## 3. LAN-access decision (design.md open question)

- [x] 3.1 Decided per design.md's stated default: `websockify` binds `localhost`-only by default, with `NOVNC_BIND` (e.g. `NOVNC_BIND=0.0.0.0`) as an opt-in for LAN access. Implemented as a `NOVNC_BIND` env var (default `localhost`), used for both the `websockify` bind address and the printed URL's host.

## 4. Validate

- [x] 4.1 Fresh run from a clean state (no existing `noVNC` checkout): confirm it clones automatically and the printed URL works. Confirmed: log showed "Cloning noVNC to ..." only on this run, and `curl http://localhost:6080/vnc.html` returned HTTP 200 with the noVNC page.
- [x] 4.2 Re-run with `noVNC` already present: confirm it's reused, not re-cloned. Confirmed: second run's log has no "Cloning noVNC..." line.
- [x] 4.3 Confirm `resize=scale` behaves as expected when the browser window is resized. Confirmed by the user against the actual integrated `run_zynthian_vnc.sh` ("läuft alles passend").
- [x] 4.4 Confirm Ctrl+C cleanly stops `Xvfb`/`x11vnc`/`websockify` (check no orphaned processes via `ps aux` afterward). Confirmed via killing the foreground `python3 zynthian_main.py` process (the real-world equivalent of the app being closed/Ctrl+C reaching it) and observing the full trap cascade in the log: run_zynthian.sh's own cleanup (jackd/a2jmidid killed, PipeWire restarted) followed immediately by run_zynthian_vnc.sh's cleanup ("Stopping websockify/x11vnc/Xvfb") - `ps aux` afterward showed zero orphaned processes.
- [x] 4.5 Confirm a direct VNC client (e.g. Remmina) can still connect to `$VNC_PORT` unchanged, so the prior workflow isn't broken. Confirmed at the protocol level: a raw socket connect to `localhost:5900` received the standard `RFB 003.008\n` handshake banner, exactly what Remmina (or any VNC client) expects - `x11vnc`'s invocation is untouched by this change.
