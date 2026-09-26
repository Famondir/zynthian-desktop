#!/usr/bin/env python3
"""Regression check for two related mixer-topbar bugs:

1. fix-mixer-bpm-display-clipping: the tempo/time-signature status text
   getting clipped by the status canvas's left edge under the desktop
   touchkeypad's `device_cables` style. Root cause was
   `zynthian_gui_config.py`'s `topbar_height` (and everything sized from it,
   including the mixer's status text font/budget) being computed from the
   *outer* display's dimensions before the touch keypad style corrected
   `screen_width`/`screen_height` down to the mocked screen's own, much
   smaller size - oversizing the topbar status text relative to the room
   reserved for it.

2. fix-topbar-resize-on-keypad-toggle: toggling the touch keypad view at
   runtime (a tap on the topbar's status area) left the topbar/status text
   frozen at its startup size, even though `zynthian_gui_config.py`'s
   `screen_width`/`screen_height` (and everything else that reads them at
   redraw time, e.g. the mixer's own strip labels) updated correctly.

`device_cables` is the worst case for both (its screen size is a fixed
constant, 800x480, entirely decoupled from the outer display), so that's
what this check reproduces, at the same 1910x1200 outer size the first bug
was found at live.

Rather than screenshotting and pixel-scanning the rendered text (fragile,
and can't actually distinguish "the correct text, in full" from "some other
text that happens to fill the same pixels" without OCR), this reads the
ground-truth measurement `zynthian_gui_mixer.py`'s `layout_status_tempo()`
already logs on every layout pass - the real Tk font measurement/geometry
the app itself uses to position the text, not a reimplementation that could
drift from it. Two things are checked from that log line:
- `fits`: the text's left edge never goes negative (bug 1 - overflow).
- `status_l` actually grows after a toggle to the larger view (bug 2 - a
  naive "fits" check alone can't catch this: text frozen at its old, small,
  self-consistent size still technically "fits" its own frozen budget, it's
  just wrong relative to the rest of the now-larger screen. Confirmed this
  gap live while writing this check - an earlier version of this script
  wrongly passed against code with bug 2 still present).

Toggling the keypad view at runtime is not reachable via CUIA/OSC injection
- it's a raw Tk mouse-click callback (zynthian_gui_base.py's
status_short_touch_action), with no CUIA equivalent anywhere in
zynthian_gui.py. So this drives it the only way available: an `xdotool`
click on the actual X11 window, at coordinates found by parsing
`xwininfo`'s tree for the mocked screen's known 800x480 sub-window (device_
cables' fixed size - see zynthian_gui_touchkeypad_v5.py's V5_SCREEN_RECT).

Usage:
    python3 -m workflow_testing.check_topbar_status_fit

Requires a native zynthian-ui checkout at /zynthian/zynthian-ui, same as
run_all.py's native environment - see that module's docstring. Also
requires `xdotool` and `xwininfo` (both already used by this project's
run_zynthian_vnc.sh/novnc_viewer.sh tooling).
"""

from __future__ import annotations

import re
import subprocess
import sys
import time

from . import native_adapter

DISPLAY = ":96"
XVFB_SIZE = "2400x1200x24"
EXTRA_ENV = {
    "ZYNTHIAN_WIRING_LAYOUT": "TOUCH_ONLY",
    "ZYNTHIAN_GUI_KEYPAD_STYLE": "device_cables",
    "ZYNTHIAN_TOUCH_SHOWN": "1",
    "DISPLAY_WIDTH": "1910",
    "DISPLAY_HEIGHT": "1200",
}

LAYOUT_LINE_RE = re.compile(
    r"layout_status_tempo: status_l=(\d+) status_fs=(\d+) "
    r"timesig_left_edge=(-?\d+) fits=(True|False)"
)

# device_cables' mocked screen is always exactly this size (V5_SCREEN_RECT) -
# xwininfo's "WxH+X+Y  +X+Y" line format, matched on the WxH part only.
SCREEN_WINDOW_SIZE = "800x480"

# Toggling shown->hidden takes screen_width from 800 to DISPLAY_WIDTH=1910
# (2.4x), so status_l (0.27*screen_width) should grow by roughly that much.
# 1.3x is a generous floor - well above noise, well below "didn't resize".
MIN_GROWTH_FACTOR = 1.3


def _parse_measurements(text: str) -> list[tuple[int, int, int, bool]]:
    return [
        (int(status_l), int(status_fs), int(edge), fits == "True")
        for status_l, status_fs, edge, fits in LAYOUT_LINE_RE.findall(text)
    ]


def _find_status_area_click_point(display: str) -> tuple[int, int] | None:
    """Locate the mocked screen's absolute (x, y) via xwininfo's window tree
    and return a click point safely inside its topbar's status area (the
    rightmost slice of the topbar's top-left corner - anywhere in it triggers
    the toggle), or None if the window can't be found."""
    result = subprocess.run(
        ["xwininfo", "-root", "-tree", "-display", display],
        capture_output=True, text=True,
    )
    for line in result.stdout.splitlines():
        if SCREEN_WINDOW_SIZE in line and "+" in line:
            # e.g. "   0xc00184 (has no name): ()  800x480+731+494  +731+494"
            try:
                geom = line.split()[-1]  # trailing "+X+Y" (absolute coords)
                _, x_str, y_str = geom.split("+")
                x, y = int(x_str), int(y_str)
            except (IndexError, ValueError):
                continue
            # A point well inside the topbar's status area: near the right
            # edge (status area is the rightmost ~27% of the 800px-wide
            # screen), a bit down from the top (avoids any edge/border pixel).
            return (x + 700, y + 20)
    return None


def _check_toggle(display: str, ui_log_path: str, status_l_before: int) -> list[str]:
    """Click the status area to toggle the keypad view, then confirm a fresh
    layout_status_tempo log line shows both fits=True AND a status_l that
    actually grew, not just one frozen at its old value. Returns a list of
    problem descriptions (empty if all good)."""
    # wait_for_ui_ready() only waits for the "SHOW SCREEN" log line, which can
    # land slightly before the window is fully mapped/settled - found live,
    # clicking immediately afterward intermittently missed the status canvas.
    time.sleep(2.0)
    point = _find_status_area_click_point(display)
    if point is None:
        msg = f"could not find the {SCREEN_WINDOW_SIZE} mocked-screen window via xwininfo"
        return [msg]

    log_size_before = len(open(ui_log_path).read())
    subprocess.run(
        ["xdotool", "mousemove", str(point[0]), str(point[1]), "click", "1"],
        env={"DISPLAY": display}, check=True,
    )
    time.sleep(1.0)
    new_text = open(ui_log_path).read()[log_size_before:]
    new_measurements = _parse_measurements(new_text)
    if not new_measurements:
        return ["clicked the status area but no new layout_status_tempo log line "
                "appeared - the click may not have landed on the status canvas"]

    problems = []
    for status_l, status_fs, edge, fits in new_measurements:
        if not fits:
            problems.append(
                f"after toggling: status_l={status_l} timesig_left_edge={edge} "
                "(negative -> clipped)")
        if status_l < status_l_before * MIN_GROWTH_FACTOR:
            problems.append(
                f"after toggling: status_l={status_l} (status_fs={status_fs}) is not "
                f"meaningfully larger than the pre-toggle status_l={status_l_before} - "
                "the topbar looks frozen at its old (small) size instead of resizing "
                "to the new (larger) screen")
    return problems


def main() -> int:
    native_adapter.check_no_contention()

    session = native_adapter.launch(
        display=DISPLAY,
        jack_server_name="zynworkflow_topbar_check",
        xvfb_size=XVFB_SIZE,
        extra_env=EXTRA_ENV,
    )
    try:
        log_text = open(session.ui_log_path).read()
        measurements = _parse_measurements(log_text)
        toggle_problems = (
            _check_toggle(DISPLAY, session.ui_log_path, measurements[-1][0])
            if measurements else ["no pre-toggle measurement to compare against"]
        )
    finally:
        session.teardown()

    if not measurements:
        print(f"FAIL: no 'layout_status_tempo:' line found in {session.ui_log_path} - "
              "did zynthian_gui_mixer.py's logging change get reverted?")
        return 1

    failures = [(status_l, edge) for status_l, _status_fs, edge, fits in measurements if not fits]
    print(f"Found {len(measurements)} layout_status_tempo measurement(s) under device_cables "
          f"(DISPLAY_WIDTH=1910, DISPLAY_HEIGHT=1200).")
    if failures:
        for status_l, edge in failures:
            print(f"  FAIL: status_l={status_l} timesig_left_edge={edge} (negative -> clipped)")
        return 1

    if toggle_problems:
        for problem in toggle_problems:
            print(f"  FAIL: {problem}")
        return 1

    print("PASS: topbar status text stays within the status canvas, at startup "
          "and after a runtime keypad-view toggle (which also resizes it).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
