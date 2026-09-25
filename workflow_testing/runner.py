"""Shared workflow-script execution core (design.md's "Shared step-execution
core, thin per-environment adapters" decision, tasks.md group 7's runner).

A workflow is a YAML file (task 1.2's resolved format) describing an
ordered list of steps against a *running* session (either
native_adapter.NativeSession or docker_adapter.DockerSession - this module
only needs `.ui_log_path` and `.capture_audio()`, so both adapters satisfy
it without a common base class):

    name: build-fluidsynth-chain
    steps:
      - screen: SCREEN_CHAIN_MANAGER
        assert: {screen_is: chain_manager}
      - zynswitch: 0
        press: short
    save_snapshot: true
    assert_zss:
      chain_count: 1
      chain_has_engine: FS
    reload_and_check_audio: true

Each step is either a `screen: <CUIA_SCREEN_NAME>` jump or a
`zynswitch: <index>` press (`press: short|bold|long`, default short).
`no_new_errors` (design.md's per-step log-diff decision) runs after every
step unconditionally, not opt-in - a workflow step is never allowed to
silently introduce a regression. `screen_is: <name>` is optional per step
and checks for the fork's `SHOW SCREEN '<name>'` log line (the *internal*
screen name zynthian-ui logs, e.g. "chain_manager" - not the CUIA name
used to request it, e.g. "SCREEN_CHAIN_MANAGER").

`save_snapshot`/`assert_zss`/`reload_and_check_audio` are workflow-level,
run once at the end - see `save_snapshot()`/`reload_and_check_audio()`
below for their current status (tasks 6.1b/6.2, deferred pending live
investigation of exactly which CUIA sequence triggers a save).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import injection, log_diff, zss_assert

_SHOW_SCREEN_RE = re.compile(r"SHOW SCREEN '([^']+)'")


@dataclass
class Step:
    screen: str | None = None
    zynswitch: int | None = None
    press: injection.PressDuration = "short"
    assert_screen_is: str | None = None

    def __post_init__(self) -> None:
        if (self.screen is None) == (self.zynswitch is None):
            raise ValueError("Step needs exactly one of 'screen' or 'zynswitch'")

    def describe(self) -> str:
        if self.screen is not None:
            return f"screen:{self.screen}"
        return f"zynswitch:{self.zynswitch}:{self.press}"


@dataclass
class Workflow:
    name: str
    steps: list[Step]
    save_snapshot: bool = False
    assert_zss: dict = field(default_factory=dict)
    reload_and_check_audio: bool = False


@dataclass
class StepResult:
    step: Step
    passed: bool
    error: str | None = None


@dataclass
class WorkflowResult:
    workflow_name: str
    step_results: list[StepResult]
    workflow_level_error: str | None = None

    @property
    def passed(self) -> bool:
        return self.workflow_level_error is None and all(r.passed for r in self.step_results)


def load_workflow(path: str | Path) -> Workflow:
    with open(path) as f:
        data = yaml.safe_load(f)

    steps = []
    for raw_step in data.get("steps", []):
        assert_block = raw_step.get("assert") or {}
        steps.append(
            Step(
                screen=raw_step.get("screen"),
                zynswitch=raw_step.get("zynswitch"),
                press=raw_step.get("press", "short"),
                assert_screen_is=assert_block.get("screen_is"),
            )
        )

    return Workflow(
        name=data.get("name", Path(path).stem),
        steps=steps,
        save_snapshot=data.get("save_snapshot", False),
        assert_zss=data.get("assert_zss", {}),
        reload_and_check_audio=data.get("reload_and_check_audio", False),
    )


@dataclass
class _ScreenTracker:
    """Tracks the last-known current screen from the fork's `SHOW SCREEN
    '<name>'` log line.

    `show_screen()` only logs when the screen actually *changes*
    (`if self.current_screen != screen:` guard in the fork) - a step whose
    target screen is already current (e.g. SCREEN_MIXER right after boot,
    which already defaults to mixer) is a legitimate no-op and produces no
    fresh log line at all. Found live: asserting "a fresh SHOW SCREEN line
    must appear this step" therefore false-fails on no-op transitions.
    Tracking the last-seen value instead (seeded once from the log
    already captured by the time the session is ready, then updated by
    whichever step last produced a fresh line) fixes this without needing
    a live "what screen are we on" query that doesn't exist.
    """

    current: str | None = None

    def seed(self, log_path: str) -> None:
        with open(log_path) as f:
            matches = _SHOW_SCREEN_RE.findall(f.read())
        if matches:
            self.current = matches[-1]

    def update(self, new_lines: list[str]) -> None:
        for line in new_lines:
            m = _SHOW_SCREEN_RE.search(line)
            if m:
                self.current = m.group(1)


def _run_step(step: Step, session, injector: injection.CuiaInjector, screen_tracker: _ScreenTracker) -> StepResult:
    mark = log_diff.mark_tail(session.ui_log_path)

    if step.screen is not None:
        injector.screen_jump(step.screen)
    else:
        injector.zynswitch_press(step.zynswitch, step.press)

    new_lines = log_diff.wait_for_stable_tail(mark)

    try:
        log_diff.assert_no_new_errors(
            log_diff.LogTailMark(path=session.ui_log_path, byte_offset=mark.byte_offset),
            step_description=step.describe(),
        )
    except log_diff.LogRegressionError as e:
        return StepResult(step=step, passed=False, error=str(e))

    screen_tracker.update(new_lines)

    if step.assert_screen_is is not None and screen_tracker.current != step.assert_screen_is:
        return StepResult(
            step=step,
            passed=False,
            error=(
                f"Expected screen '{step.assert_screen_is}' after {step.describe()}, "
                f"actual current screen is '{screen_tracker.current}'"
            ),
        )

    return StepResult(step=step, passed=True)


def save_snapshot(session, injector: injection.CuiaInjector) -> str:
    """Trigger a snapshot save and return the resulting .zss path.

    NOT YET IMPLEMENTED (task 6.1b, deferred): saving isn't a single CUIA
    - `zyngui/zynthian_gui_snapshot.py`'s "SAVE" action is a list entry on
    the `snapshot` screen (selected like any other list item), not a
    global save command. Needs a live session to confirm the exact
    zynswitch sequence (navigate to SCREEN_SNAPSHOT, move to the "SAVE"
    entry, confirm) and where the resulting file lands.
    """
    raise NotImplementedError("save_snapshot: see task 6.1b in tasks.md - needs live investigation")


def reload_and_check_audio(zss_path: str, environment: str) -> None:
    """Start a fresh session loading `zss_path` as its default snapshot,
    inject a musical note, confirm non-silent audio via jack_rec+sox.

    NOT YET IMPLEMENTED (task 6.2, deferred) - depends on save_snapshot
    (task 6.1b) landing first to have a real .zss to reload.
    """
    raise NotImplementedError("reload_and_check_audio: see task 6.2 in tasks.md")


def run_workflow(workflow: Workflow, session, injector: injection.CuiaInjector) -> WorkflowResult:
    screen_tracker = _ScreenTracker()
    screen_tracker.seed(session.ui_log_path)

    step_results = []
    for step in workflow.steps:
        result = _run_step(step, session, injector, screen_tracker)
        step_results.append(result)
        if not result.passed:
            # Fail fast: a failed step leaves state that later steps
            # weren't written to handle (same reasoning as tasks.md's
            # "fail-fast on contention" requirement for session setup).
            return WorkflowResult(workflow_name=workflow.name, step_results=step_results)

    workflow_level_error = None
    try:
        if workflow.save_snapshot:
            zss_path = save_snapshot(session, injector)
            if workflow.assert_zss:
                snapshot = zss_assert.load_zss(zss_path)
                if "chain_count" in workflow.assert_zss:
                    zss_assert.assert_chain_count(snapshot, workflow.assert_zss["chain_count"])
                if "chain_has_engine" in workflow.assert_zss:
                    zss_assert.assert_chain_has_engine(snapshot, workflow.assert_zss["chain_has_engine"])
            if workflow.reload_and_check_audio:
                reload_and_check_audio(zss_path, environment="native")
    except (zss_assert.ZssAssertionError, NotImplementedError) as e:
        workflow_level_error = str(e)

    return WorkflowResult(workflow_name=workflow.name, step_results=step_results, workflow_level_error=workflow_level_error)
