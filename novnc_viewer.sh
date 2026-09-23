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
