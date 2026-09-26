#!/usr/bin/env python3
"""Regression check for the mixer topbar's tempo/time-signature status text
getting clipped by the status canvas's left edge under the desktop
touchkeypad's `device_cables` style - see
openspec/changes/fix-mixer-bpm-display-clipping.

Root cause was `zynthian_gui_config.py`'s `topbar_height` (and everything
sized from it, including the mixer's status text font/budget) being computed
from the *outer* display's dimensions before the touch keypad style corrected
`screen_width`/`screen_height` down to the mocked screen's own, much smaller
size - oversizing the topbar status text relative to the room reserved for
it. `device_cables` is the worst case (its screen size is a fixed constant,
800x480, entirely decoupled from the outer display), so that's what this
check reproduces, at the same 1910x1200 outer size the bug was first found
at live.

Rather than screenshotting and pixel-scanning the rendered text (fragile,
and can't actually distinguish "the correct text, in full" from "some other
text that happens to fill the same pixels" without OCR), this reads the
ground-truth measurement `zynthian_gui_mixer.py`'s `layout_status_tempo()`
already logs on every layout pass - the real Tk font measurement the app
itself uses to position the text, not a reimplementation of the formula
that could drift from it.

Usage:
    python3 -m workflow_testing.check_topbar_status_fit

Requires a native zynthian-ui checkout at /zynthian/zynthian-ui, same as
run_all.py's native environment - see that module's docstring.
"""

from __future__ import annotations

import re
import sys

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
    r"layout_status_tempo: status_l=(\d+) timesig_left_edge=(-?\d+) fits=(True|False)"
)


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
    finally:
        session.teardown()

    matches = LAYOUT_LINE_RE.findall(log_text)
    if not matches:
        print(f"FAIL: no 'layout_status_tempo:' line found in {session.ui_log_path} - "
              "did zynthian_gui_mixer.py's logging change get reverted?")
        return 1

    failures = [(status_l, edge) for status_l, edge, fits in matches if fits != "True"]
    print(f"Found {len(matches)} layout_status_tempo measurement(s) under device_cables "
          f"(DISPLAY_WIDTH=1910, DISPLAY_HEIGHT=1200).")
    if failures:
        for status_l, edge in failures:
            print(f"  FAIL: status_l={status_l} timesig_left_edge={edge} (negative -> clipped)")
        return 1

    print("PASS: topbar status text stays within the status canvas (no clipping).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
