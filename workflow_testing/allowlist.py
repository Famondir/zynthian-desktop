"""CUIA safety allow-list for workflow-smoke-testing.

See openspec/changes/add-workflow-smoke-testing/design.md's "CUIA safety
allow-list" decision: the engine injects CUIA actions directly over OSC
(injection.py), bypassing zynthian-ui's MIDI-note-to-CUIA translation
table entirely - so this allow-list is keyed by CUIA name, not MIDI note
number, and does not need zynconf/zynthian_config.py's NoteCuiaDefault at
runtime (referenced only as documentation of what CUIA names exist).

Fails closed: a CUIA/ZYNSWITCH index not explicitly listed here is
refused, never silently injected. Grow this list deliberately as new
workflow scripts need specific actions - never add POWER, RESTART_UI, or
anything only reachable via SCREEN_ADMIN's further switch presses (see
design.md's rationale).
"""

from __future__ import annotations

# Direct CUIA jumps/actions a workflow step may use (no parameters beyond
# the CUIA name itself).
ALLOWED_CUIAS = frozenset({
    "SCREEN_CHAIN_MANAGER",
    "SCREEN_MIXER",
    "SCREEN_MIDI_RECORDER",
    "ALL_NOTES_OFF",
    # For save_snapshot (task 6.1b): navigate to the snapshot screen, then
    # SELECT <index> to move the list highlight (no confirm) and
    # SELECT_ACTION <press> to confirm whatever's currently highlighted.
    # SELECT/SELECT_ACTION are generic "confirm the current screen's
    # highlighted list item" actions, not scoped to snapshot alone - safe
    # here specifically because every screen a workflow can reach is
    # already on this same allow-list (SCREEN_ADMIN is in _NEVER_ALLOW and
    # unreachable), none of which expose a destructive action behind a
    # single list confirm.
    "SCREEN_SNAPSHOT",
    "SELECT",
    "SELECT_ACTION",
    # For building a chain from scratch (task 7.1): ADD_CHAIN jumps to the
    # "Add Chain..." type-selector grid; ARROW_RIGHT/ARROW_LEFT cycle the
    # engine screen's category tabs (e.g. "Synth" -> "Sampler" to reach
    # FluidSynth) - same "generic navigation action, safe because every
    # screen reachable this way is already allow-listed" reasoning as
    # SELECT/SELECT_ACTION above.
    "ADD_CHAIN",
    "ARROW_RIGHT",
    "ARROW_LEFT",
    # For adding a processor to an existing chain (task 7.2): CHAIN_OPTIONS
    # opens the active chain's option list (Add MIDI-FX/Add Audio-FX/
    # rename/move/remove chain/...) - nothing reachable from it exceeds
    # what a workflow can already do to its own chains by construction
    # (create/modify/remove), and none of it reaches SCREEN_ADMIN or
    # anything system-level.
    "CHAIN_OPTIONS",
})

# ZYNSWITCH indices a workflow step may press. Index range on TOUCH_ONLY
# wiring (this project's desktop port) is small - see design.md task 1.3.
ALLOWED_ZYNSWITCH_INDICES = frozenset({0, 1, 2, 3})

# CUIAs that must never be reachable from this engine, documented for
# clarity even though anything not in ALLOWED_CUIAS is already refused by
# default. Kept here so the reasoning is visible next to the allow-list,
# not just in design.md.
_NEVER_ALLOW = frozenset({
    "POWER",
    "RESTART_UI",
    "RELOAD_MIDI_CONFIG",
    "RELOAD_KEY_BINDING",
    "RELOAD_WIRING_LAYOUT",
    "LAST_STATE_ACTION",
    "SCREEN_ADMIN",
})


class DisallowedCuiaError(Exception):
    """Raised when a workflow step requests a CUIA not on the allow-list."""


def check_cuia(cuia: str) -> None:
    """Raise DisallowedCuiaError unless `cuia` is on the allow-list."""
    cuia = cuia.upper()
    if cuia in _NEVER_ALLOW:
        raise DisallowedCuiaError(
            f"CUIA '{cuia}' is explicitly denied (never allowed) - see workflow_testing/allowlist.py"
        )
    if cuia not in ALLOWED_CUIAS:
        raise DisallowedCuiaError(
            f"CUIA '{cuia}' is not on the allow-list - add it deliberately to "
            "workflow_testing/allowlist.py if a workflow genuinely needs it"
        )


def check_zynswitch(index: int) -> None:
    """Raise DisallowedCuiaError unless `index` is an allowed ZYNSWITCH."""
    if index not in ALLOWED_ZYNSWITCH_INDICES:
        raise DisallowedCuiaError(
            f"ZYNSWITCH {index} is not on the allow-list "
            f"(allowed: {sorted(ALLOWED_ZYNSWITCH_INDICES)}) - add it deliberately "
            "to workflow_testing/allowlist.py if a workflow genuinely needs it"
        )
