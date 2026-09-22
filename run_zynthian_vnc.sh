#!/bin/bash
# Run the native /zynthian/run_zynthian.sh on a virtual (headless) X
# display, exported over noVNC (browser-based VNC client - just open the
# printed URL, no separate app needed) so a laptop screen too small for
# the device/device_cables style's fixed 1910-wide render can view it
# scaled down instead. zynthian-ui's V5 keypad styles use absolute pixel
# constants tied to that one native size (see
# zyngui/zynthian_gui_touchkeypad_v5.py's V5_* constants) - the window
# itself can't be resized (Tk locks min/maxsize to DISPLAY_WIDTH/HEIGHT),
# so scaling has to happen on the viewing side, not by asking the app for
# a smaller size. noVNC's resize=scale mode handles that responsively in
# the browser - no manual VNC-client scale-mode/window-size configuration
# needed (see openspec/changes/novnc-browser-viewer).
#
# A raw VNC client (e.g. Remmina) can still connect directly to
# localhost:$VNC_PORT if preferred - this only adds a browser front end,
# it doesn't replace the underlying x11vnc server.
#
# Usage: ./run_zynthian_vnc.sh [classic|standard|device|device_cables]
set -e

GUI_STYLE="${1:-device_cables}"

VNC_DISPLAY="${VNC_DISPLAY:-:97}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
# localhost-only by default - deliberately not exposing an unauthenticated
# VNC-over-websocket service to the LAN unless explicitly asked for (see
# design.md's Decisions). Set NOVNC_BIND=0.0.0.0 to view from another
# device on the same network instead.
NOVNC_BIND="${NOVNC_BIND:-localhost}"
NOVNC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/noVNC"

# Matches device_cables' fixed native size (see run_zynthian.sh); classic/
# standard/device all fit within this too since run_zynthian.sh adjusts
# DISPLAY_WIDTH/HEIGHT itself for those styles.
XVFB_SIZE="1910x1120x24"

if ! command -v websockify > /dev/null; then
    echo "websockify not found - install it with: sudo apt install websockify" >&2
    exit 1
fi

if [ ! -d "$NOVNC_DIR" ]; then
    echo "--- Cloning noVNC to $NOVNC_DIR (one-time, not committed to this repo) ---"
    git clone https://github.com/novnc/noVNC.git "$NOVNC_DIR"
fi

cleanup() {
    echo "--- Stopping websockify/x11vnc/Xvfb ---"
    kill "$WEBSOCKIFY_PID" "$X11VNC_PID" "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "--- Starting Xvfb on $VNC_DISPLAY ($XVFB_SIZE) ---"
Xvfb "$VNC_DISPLAY" -screen 0 "$XVFB_SIZE" > /tmp/zynthian_xvfb.log 2>&1 &
XVFB_PID=$!
sleep 1

echo "--- Starting x11vnc on port $VNC_PORT, log: /tmp/zynthian_x11vnc.log ---"
# x11vnc bails out with "Wayland display server detected" if it sees
# WAYLAND_DISPLAY/XDG_SESSION_TYPE=wayland in its environment - inherited
# from the host's Wayland desktop session - even though -display here
# correctly points at Xvfb's own X11 socket, not the host session. Strip
# those two vars for x11vnc specifically so its (over-eager) check doesn't
# fire.
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
echo "--- Starting Zynthian ($GUI_STYLE) on the virtual display ---"
DISPLAY="$VNC_DISPLAY" /zynthian/run_zynthian.sh "$GUI_STYLE"
