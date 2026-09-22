#!/bin/bash
# Run the native /zynthian/run_zynthian.sh on a virtual (headless) X
# display, exported over VNC so a laptop screen too small for the
# device/device_cables style's fixed 1910-wide render can view it scaled
# down instead. zynthian-ui's V5 keypad styles use absolute pixel
# constants tied to that one native size (see
# zyngui/zynthian_gui_touchkeypad_v5.py's V5_* constants) - the window
# itself can't be resized (Tk locks min/maxsize to DISPLAY_WIDTH/HEIGHT),
# so scaling has to happen on the viewing side, not by asking the app for
# a smaller size.
#
# Usage: ./run_zynthian_vnc.sh [classic|standard|device|device_cables]
# Then connect a VNC client (e.g. Remmina) to localhost:5900 and enable
# "Scale to window" there to view it at any size, including half.
set -e

GUI_STYLE="${1:-device_cables}"

VNC_DISPLAY="${VNC_DISPLAY:-:97}"
VNC_PORT="${VNC_PORT:-5900}"

# Matches device_cables' fixed native size (see run_zynthian.sh); classic/
# standard/device all fit within this too since run_zynthian.sh adjusts
# DISPLAY_WIDTH/HEIGHT itself for those styles.
XVFB_SIZE="1910x1120x24"

cleanup() {
    echo "--- Stopping x11vnc/Xvfb ---"
    kill "$X11VNC_PID" "$XVFB_PID" 2>/dev/null || true
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

echo "--- Connect a VNC client to localhost:$VNC_PORT and enable 'Scale to window' ---"
echo "--- Starting Zynthian ($GUI_STYLE) on the virtual display ---"
DISPLAY="$VNC_DISPLAY" /zynthian/run_zynthian.sh "$GUI_STYLE"
