"""CUIA injection primitive for workflow-smoke-testing, via OSC.

See openspec/changes/add-workflow-smoke-testing/design.md's "CUIA/switch/
screen steps via direct OSC" decision. zyngui/zynthian_gui.py runs a real
OSC server (zynconf.ServerPort["cuia_osc"], port 1370 by default) whose
catch-all handler dispatches "/CUIA/<name> <args...>" straight into the
same cuia_queue the MIDI-note-to-CUIA path uses - confirmed by reading
cuia_zynswitch() and the queue consumer directly: ZYNSWITCH press ('P')
records a monotonic timestamp, release ('R') computes the real elapsed
time and classifies it into short/bold/long via zynswitch_timing(), using
zynthian_gui_config.zynswitch_bold_us/zynswitch_long_us either way. This
module reproduces that push/release timing over OSC - no VMPK, no Xvfb,
no pixel-coordinate calibration needed for switch/screen steps.

Musical-note injection (to verify audio output, not UI navigation) is a
separate concern - CUIA has no generic "play this note on this engine"
message - and stays on the VMPK mouse-click technique test_zynthian_docker.sh
already proved; that lives elsewhere (see design.md task 2.4), not here.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

import liblo

from workflow_testing.allowlist import check_cuia, check_zynswitch

PressDuration = Literal["short", "bold", "long"]

# Fallback thresholds, matching zynthian_gui_config.py's own defaults
# (ZYNTHIAN_UI_SWITCH_BOLD_MS / ZYNTHIAN_UI_SWITCH_LONG_MS). Callers that
# know the target session's actual configured thresholds (e.g. read from
# its zynthian_envars_custom.sh or container env) should pass them
# explicitly instead of relying on these - see PressTimings.
DEFAULT_BOLD_MS = 300
DEFAULT_LONG_MS = 2000

# Margin added above/below a threshold so a timed hold reliably lands on
# the intended side of it rather than racing the exact boundary.
_MARGIN_MS = 80
_SHORT_HOLD_MS = 50  # well under any realistic bold threshold


@dataclass(frozen=True)
class PressTimings:
    """Press-duration thresholds for one target session.

    Construct with the target's actual configured values when known
    (read from its environment - zynthian_gui_config.py's
    ZYNTHIAN_UI_SWITCH_BOLD_MS / ZYNTHIAN_UI_SWITCH_LONG_MS, falling back
    to zynthian_gui_config.py's own 300/2000 defaults if unset there
    too), so this module never hardcodes them independently of the
    session it's actually driving.
    """

    bold_ms: int = DEFAULT_BOLD_MS
    long_ms: int = DEFAULT_LONG_MS

    def hold_seconds(self, duration: PressDuration) -> float:
        if duration == "short":
            return _SHORT_HOLD_MS / 1000
        if duration == "bold":
            return (self.bold_ms + _MARGIN_MS) / 1000
        if duration == "long":
            return (self.long_ms + _MARGIN_MS) / 1000
        raise ValueError(f"Unknown press duration: {duration!r}")


class CuiaInjector:
    """Sends CUIA actions to one target zynthian_main.py session over OSC."""

    def __init__(self, host: str, port: int = 1370, timings: PressTimings | None = None):
        self.target = liblo.Address(host, port)
        self.timings = timings or PressTimings()

    def _send(self, cuia: str, *args) -> None:
        liblo.send(self.target, f"/CUIA/{cuia}", *args)

    def zynswitch_press(self, index: int, duration: PressDuration) -> None:
        """Press-and-release ZYNSWITCH `index` for the given duration class."""
        check_zynswitch(index)
        hold_seconds = self.timings.hold_seconds(duration)
        self._send("ZYNSWITCH", index, "P")
        time.sleep(hold_seconds)
        self._send("ZYNSWITCH", index, "R")

    def screen_jump(self, screen_cuia: str) -> None:
        """Jump directly to a screen via its SCREEN_* CUIA name."""
        check_cuia(screen_cuia)
        self._send(screen_cuia)

    def cuia(self, cuia: str) -> None:
        """Fire a simple, parameterless CUIA (e.g. ALL_NOTES_OFF)."""
        check_cuia(cuia)
        self._send(cuia)

    def select_list_item(self, index: int) -> None:
        """Move the current screen's list selection to `index` (no confirm).

        Maps to zynthian_gui's cuia_select -> screen.select(index) - moves
        the highlight only, doesn't trigger the item's action. See
        confirm_selection() for that.
        """
        check_cuia("SELECT")
        self._send("SELECT", index)

    def confirm_selection(self, press: PressDuration = "short") -> None:
        """Confirm ('select_action') whatever's currently highlighted on
        the current screen - the OSC equivalent of a physical SELECT/YES
        switch press. Maps to cuia_select_action -> screen.switch_select().
        """
        press_code = {"short": "S", "bold": "B", "long": "L"}[press]
        check_cuia("SELECT_ACTION")
        self._send("SELECT_ACTION", press_code)

    def add_chain(self) -> None:
        """Jump to the "Add Chain..." type-selector grid. Maps to cuia_add_chain."""
        check_cuia("ADD_CHAIN")
        self._send("ADD_CHAIN")

    def arrow(self, direction: Literal["right", "left"]) -> None:
        """Cycle the current screen's category/tab (e.g. the engine
        screen's Synth/Sampler/Piano/... categories) - the OSC equivalent
        of the front-panel arrow buttons. Maps to cuia_arrow_right/left ->
        screen.arrow_right()/arrow_left().
        """
        cuia = "ARROW_RIGHT" if direction == "right" else "ARROW_LEFT"
        check_cuia(cuia)
        self._send(cuia)
