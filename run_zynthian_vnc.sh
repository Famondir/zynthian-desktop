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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/novnc_viewer.sh"

GUI_STYLE="${1:-device_cables}"

VNC_DISPLAY="${VNC_DISPLAY:-:97}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
# localhost-only by default - deliberately not exposing an unauthenticated
# VNC-over-websocket service to the LAN unless explicitly asked for (see
# design.md's Decisions). Set NOVNC_BIND=0.0.0.0 to view from another
# device on the same network instead.
NOVNC_BIND="${NOVNC_BIND:-localhost}"
NOVNC_DIR="$SCRIPT_DIR/noVNC"

# Wider than device_cables' own 1910px fixed size: standard's computed
# width (run_zynthian.sh's CLASSIC_PANEL arithmetic, scaled off whatever
# DISPLAY_WIDTH zynthian_envars_custom.sh sets) can exceed even that - with
# this repo's reference 1600 baseline it comes out to 2133, found live to
# get clipped by a narrower Xvfb screen (real content missing, not just
# padding). track_app_window (see novnc_viewer.sh) crops the noVNC view to
# whatever the actual window turns out to be, so oversizing this is free -
# no visible margin cost for the narrower styles. Height (1120) already
# covers all four styles' observed heights.
XVFB_SIZE="2400x1120x24"

cleanup() {
    echo "--- Stopping websockify/x11vnc/Xvfb ---"
    kill "$WINDOW_TRACKER_PID" "$WEBSOCKIFY_PID" "$X11VNC_PID" "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT

start_novnc_viewer
# See novnc_viewer.sh's own comment: crops the noVNC view to the app's
# actual window once it appears, instead of the full (device_cables-sized)
# Xvfb canvas - matters for classic/standard, which render much smaller.
track_app_window

echo "--- Starting Zynthian ($GUI_STYLE) on the virtual display ---"
DISPLAY="$VNC_DISPLAY" /zynthian/run_zynthian.sh "$GUI_STYLE"
