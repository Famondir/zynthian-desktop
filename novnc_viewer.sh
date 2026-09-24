#!/bin/bash
# Shared Xvfb + x11vnc + noVNC (browser-based VNC) orchestration, sourced
# by both run_zynthian_vnc.sh (native install) and run_zynthian_docker.sh
# (Docker desktop image) - see openspec/changes/docker-novnc-browser-viewer
# for why this is a shared function rather than a second hand-maintained
# copy of the same setup.
#
# Not meant to be run directly - `source` this file, set the variables
# below, then call start_novnc_viewer. It sets XVFB_PID/X11VNC_PID/
# WEBSOCKIFY_PID as plain variables for the caller's own cleanup() trap to
# kill; it does not install its own trap.
#
# Callers should also call track_app_window after start_novnc_viewer and
# before launching the app itself (see that function's own comment) - sets
# WINDOW_TRACKER_PID the same way.
#
# Variables the caller must set before calling start_novnc_viewer:
#   VNC_DISPLAY   - X display number for Xvfb, e.g. ":97"
#   VNC_PORT      - port x11vnc listens on
#   NOVNC_PORT    - port websockify listens on
#   NOVNC_BIND    - address websockify binds to (localhost or 0.0.0.0)
#   NOVNC_DIR     - path to the noVNC checkout (cloned on demand if absent)
#   XVFB_SIZE     - e.g. "1910x1120x24"

start_novnc_viewer() {
    if ! command -v websockify > /dev/null; then
        echo "websockify not found - install it with: sudo apt install websockify" >&2
        exit 1
    fi

    if [ ! -d "$NOVNC_DIR" ]; then
        echo "--- Cloning noVNC to $NOVNC_DIR (one-time, not committed to this repo) ---"
        git clone https://github.com/novnc/noVNC.git "$NOVNC_DIR"
    fi

    echo "--- Starting Xvfb on $VNC_DISPLAY ($XVFB_SIZE) ---"
    Xvfb "$VNC_DISPLAY" -screen 0 "$XVFB_SIZE" > /tmp/zynthian_xvfb.log 2>&1 &
    XVFB_PID=$!
    sleep 1

    echo "--- Starting x11vnc on port $VNC_PORT, log: /tmp/zynthian_x11vnc.log ---"
    # x11vnc bails out with "Wayland display server detected" if it sees
    # WAYLAND_DISPLAY/XDG_SESSION_TYPE=wayland in its environment -
    # inherited from the host's Wayland desktop session - even though
    # -display here correctly points at Xvfb's own X11 socket, not the
    # host session. Strip those two vars for x11vnc specifically so its
    # (over-eager) check doesn't fire.
    env -u WAYLAND_DISPLAY -u XDG_SESSION_TYPE \
        x11vnc -display "$VNC_DISPLAY" -rfbport "$VNC_PORT" -forever -shared -nopw \
        > /tmp/zynthian_x11vnc.log 2>&1 &
    X11VNC_PID=$!
    sleep 1

    echo "--- Starting websockify (noVNC) on $NOVNC_BIND:$NOVNC_PORT, log: /tmp/zynthian_websockify.log ---"
    websockify --web="$NOVNC_DIR" "$NOVNC_BIND:$NOVNC_PORT" "localhost:$VNC_PORT" \
        > /tmp/zynthian_websockify.log 2>&1 &
    WEBSOCKIFY_PID=$!
    sleep 1

    echo "--- Open in a browser: http://$NOVNC_BIND:$NOVNC_PORT/vnc.html?host=$NOVNC_BIND&port=$NOVNC_PORT&resize=scale ---"
    echo "--- (or connect a raw VNC client to localhost:$VNC_PORT instead) ---"
}

# Xvfb is always sized for the largest GUI style (device_cables); classic/
# standard/device all render smaller windows within that same canvas, and
# x11vnc otherwise exports the *whole* canvas regardless of how much of it
# the app's window actually fills - found live as a large black margin
# around classic's much smaller window in the browser (see
# openspec/changes/novnc-fit-to-window). Fix: once the app's window
# appears, tell the already-running x11vnc (via its runtime remote-control
# channel) to export just that window instead - confirmed live to resize
# x11vnc's framebuffer to the window's exact size with no server restart.
#
# Runs as its own background loop (not by backgrounding the app launch
# itself) so neither caller's foreground-app / Ctrl+C / trap-based-cleanup
# behavior changes at all - see design.md's Decisions for why that
# mattered enough to avoid touching.
#
# Matches by WM_CLASS "Tk" (Zynthian's own Tk root window), not "any
# window" - a developer may have vmpk (support-virtual-test-devices)
# running on the same display for MIDI testing, and its Qt window
# ("vmpk"/"VMPK") must not be mistaken for Zynthian's.
#
# Best-effort: if the window never appears within the timeout, this just
# exits quietly and x11vnc keeps exporting the full canvas (today's
# behavior) - a viewing-quality enhancement, not something that should be
# able to break the session if it fails.
track_app_window() {
    (
        local elapsed=0
        local timeout=60
        local winid=""
        while [ "$elapsed" -lt "$timeout" ]; do
            winid="$(DISPLAY="$VNC_DISPLAY" xdotool search --class "Tk" 2>/dev/null | head -1)"
            if [ -n "$winid" ]; then
                break
            fi
            sleep 1
            elapsed=$((elapsed + 1))
        done

        if [ -n "$winid" ]; then
            # Brief settle delay - DISPLAY_WIDTH/HEIGHT are set very early
            # in zynthian_gui.py's init, but give the window manager-less
            # Tk root a moment to finish mapping at its final geometry
            # before reading it.
            sleep 1
            env -u WAYLAND_DISPLAY -u XDG_SESSION_TYPE \
                x11vnc -display "$VNC_DISPLAY" -R "id:$winid" > /dev/null 2>&1 || true
        fi
    ) &
    WINDOW_TRACKER_PID=$!
}
