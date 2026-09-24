"""Musical-note injection via VMPK, for audio-output verification only.

See openspec/changes/add-workflow-smoke-testing/design.md's "CUIA/switch/
screen steps via direct OSC" decision: CUIA/UI-navigation steps go over
OSC (injection.py) now, not VMPK - but CUIA has no generic "play this
note on this engine" message, so a real *musical* note (to confirm audio
actually comes out of a chain, e.g. in reload_and_check_audio) still needs
real MIDI, and VMPK is the already-proven way to produce it headlessly.

This ports test_zynthian_docker.sh's exact technique unchanged (same repo,
see that script for the original, still-used-there version):
`xdotool key` targeted at VMPK's window does NOT produce a MIDI event at
all (confirmed live there with aseqdump - zero events, regardless of key
or hold duration). VMPK's on-screen piano responds reliably to an actual
mouse click, though, so this clicks a key derived from the window's own
geometry (a fixed percentage across/down, not hardcoded pixels) rather
than the specific-note-by-coordinate problem switch/screen steps would
have needed (avoided entirely by using OSC for those instead - see
design.md). This module only ever needs to hit *some* audible note in
whatever chain is active, not a *specific* MIDI note number, so the
existing single-point click technique applies unchanged.

Requires: xdotool, a running `vmpk` process already visible on the target
X11 DISPLAY (launching/tearing down vmpk is the calling adapter's job -
see design.md's native/Docker adapter tasks - not this module's).
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

VMPK_WINDOW_TITLE = "Virtual MIDI Piano Keyboard"


class VmpkWindowNotFoundError(Exception):
    """Raised when no VMPK main window is visible on the target display."""


@dataclass(frozen=True)
class WindowGeometry:
    x: int
    y: int
    width: int
    height: int


def _run(cmd: list[str], display: str) -> str:
    return subprocess.run(
        cmd, env={"DISPLAY": display}, capture_output=True, text=True, check=True
    ).stdout


def find_vmpk_window(display: str) -> str:
    """Return VMPK's main window id, or raise if it isn't up yet.

    Matches the exact window title, not just "VMPK" - VMPK also creates
    unrelated 1x1 helper windows (a selection owner, etc.) that match a
    looser pattern but have no real geometry to click into.
    """
    out = subprocess.run(
        ["xdotool", "search", "--name", VMPK_WINDOW_TITLE],
        env={"DISPLAY": display},
        capture_output=True,
        text=True,
    )
    window_ids = [w for w in out.stdout.splitlines() if w.strip()]
    if not window_ids:
        raise VmpkWindowNotFoundError(
            f"No window titled '{VMPK_WINDOW_TITLE}' on display {display} - is vmpk running yet?"
        )
    return window_ids[0]


def wait_for_vmpk_window(display: str, timeout_s: float = 20.0, poll_interval_s: float = 0.5) -> str:
    """Poll for VMPK's window to appear, same bounded-timeout style as
    the rest of this project's dev tooling (no fixed sleep guesses)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            return find_vmpk_window(display)
        except VmpkWindowNotFoundError:
            time.sleep(poll_interval_s)
    raise VmpkWindowNotFoundError(
        f"VMPK window did not appear on display {display} within {timeout_s}s"
    )


def get_window_geometry(window_id: str, display: str) -> WindowGeometry:
    out = _run(["xdotool", "getwindowgeometry", "--shell", window_id], display)
    values = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    return WindowGeometry(
        x=int(values["X"]), y=int(values["Y"]), width=int(values["WIDTH"]), height=int(values["HEIGHT"])
    )


def play_note(display: str, hold_seconds: float = 1.5, *, x_pct: int = 30, y_pct: int = 90) -> None:
    """Click-and-hold a key on VMPK's on-screen piano for `hold_seconds`.

    x_pct/y_pct locate the click point as a percentage of the window's
    own geometry (default: 30% across, 90% down - low on a white key,
    clear of the black-key strip along the top), matching
    test_zynthian_docker.sh's proven default exactly. Which specific note
    that lands on depends on VMPK's current octave/view, which is fine
    for this module's only use case (confirm *some* audible note reaches
    an active chain) - callers needing a specific note number should use
    injection.py's OSC-based CUIA path instead, not this module.
    """
    window_id = find_vmpk_window(display)
    geom = get_window_geometry(window_id, display)
    click_x = geom.x + geom.width * x_pct // 100
    click_y = geom.y + geom.height * y_pct // 100

    subprocess.run(
        ["xdotool", "mousemove", str(click_x), str(click_y), "mousedown", "1"],
        env={"DISPLAY": display},
        check=True,
    )
    time.sleep(hold_seconds)
    subprocess.run(["xdotool", "mouseup", "1"], env={"DISPLAY": display}, check=True)
    # Move off the piano so nothing lingers pressed, matching
    # test_zynthian_docker.sh.
    subprocess.run(["xdotool", "mousemove", "0", "0"], env={"DISPLAY": display}, check=True)
