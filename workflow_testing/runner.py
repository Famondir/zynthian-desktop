"""Shared workflow-script execution core (design.md's "Shared step-execution
core, thin per-environment adapters" decision, tasks.md group 7's runner).

A workflow is a YAML file (task 1.2's resolved format) describing an
ordered list of steps against a *running* session (either
native_adapter.NativeSession or docker_adapter.DockerSession - this module
only needs `.ui_log_path`, `.snapshots_dir` and `.capture_audio()`, so both
adapters satisfy it without a common base class):

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
below (tasks 6.1b/6.2) for the exact CUIA sequence/audio-check mechanics.
`reload_and_check_audio` needs the `adapter` module (native_adapter or
docker_adapter) passed to `run_workflow()` too, since it starts a second,
fresh session of the same kind.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import injection, log_diff, musical_note, zss_assert

# RMS threshold above which captured audio counts as "not silence" - same
# value test_zynthian_docker.sh already validated against a real recording.
_SILENCE_RMS_THRESHOLD = 0.001

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


_SAVING_SNAPSHOT_RE = re.compile(r"Saving snapshot (.+) \.\.\.")
# The container-internal (or, for native, host-identical) snapshots
# directory every "Saving snapshot <path> ..." log line's path is
# rooted at - stripped and rejoined onto session.snapshots_dir so the
# result is always a host-visible path, regardless of which environment
# logged it.
_INTERNAL_SNAPSHOTS_DIR = "/zynthian/zynthian-my-data/snapshots"


def save_snapshot(session, injector: injection.CuiaInjector) -> str:
    """Trigger a snapshot save and return the resulting, host-visible .zss path.

    Confirmed live (task 6.1b): the "SAVE" action on the `snapshot`
    screen is a list entry (`zyngui/zynthian_gui_snapshot.py`'s
    `select_action`), not a global save CUIA. Selecting it opens an
    on-screen keyboard pre-filled with "New Snapshot"
    (`show_keyboard(save_snapshot_by_name, "New Snapshot")`), which
    defaults its selection to the "Enter" key
    (`zynthian_gui_keyboard.show()` sets `selected_button = btn_enter`) -
    so confirming immediately accepts that default text without needing
    to type anything.

    The exact list position this lands on - and therefore the exact
    resulting filename - depends on what's *already* in the target
    session's snapshot banks: a session with pre-existing snapshots (found
    live: this project's own long-reused native install) can land on a
    different list entry than a genuinely fresh one (found live: a Docker
    session's empty scratch my-data), producing a different save path
    each time (`last_state.zss` vs `000/001-New Snapshot.zss`, both seen
    live). Rather than assume either, this parses the actual path from
    zynthian_state_manager.save_snapshot()'s own
    `"Saving snapshot <path> ..."` INFO log line - correct regardless of
    which internal path the confirm sequence happened to trigger.
    """
    mark = log_diff.mark_tail(session.ui_log_path)
    injector.screen_jump("SCREEN_SNAPSHOT")
    injector.select_list_item(0)
    injector.confirm_selection("short")
    injector.confirm_selection("short")
    new_lines = log_diff.wait_for_stable_tail(mark)

    for line in new_lines:
        m = _SAVING_SNAPSHOT_RE.search(line)
        if m:
            internal_path = m.group(1)
            relative = os.path.relpath(internal_path, _INTERNAL_SNAPSHOTS_DIR)
            return os.path.join(session.snapshots_dir, relative)

    raise RuntimeError(
        "save_snapshot: no 'Saving snapshot <path> ...' log line seen after the confirm sequence - "
        f"log tail was: {new_lines}"
    )


class AudioCheckError(Exception):
    """Raised when reload_and_check_audio's captured audio is silent."""


def _start_vmpk(display: str) -> tuple[subprocess.Popen, str]:
    """Start VMPK headlessly on `display`, pre-seeded to the ALSA driver.

    Same technique test_zynthian_docker.sh already proved: a fresh HOME
    has no VMPK.conf, so VMPK defaults to its own built-in synth output
    driver, which tries (and fails) to reach PulseAudio - pre-seed ALSA
    instead. `-u WAYLAND_DISPLAY -u XDG_SESSION_TYPE` avoids Qt grabbing
    the host's real Wayland session instead of this private X11 display
    (same fix run_zynthian_vnc.sh needed for x11vnc).
    """
    vmpk_home = tempfile.mkdtemp(prefix="workflow-test-vmpk-home.")
    conf_dir = os.path.join(vmpk_home, ".config", "vmpk.sourceforge.net")
    os.makedirs(conf_dir, exist_ok=True)
    with open(os.path.join(conf_dir, "VMPK.conf"), "w") as f:
        f.write(
            "[Connections]\nAdvancedEnabled=false\nInEnabled=false\n"
            "InputDriver=None\nOutputDriver=ALSA\nThruEnabled=false\n"
        )
    env = {**os.environ, "HOME": vmpk_home, "DISPLAY": display}
    env.pop("WAYLAND_DISPLAY", None)
    env.pop("XDG_SESSION_TYPE", None)
    proc = subprocess.Popen(["vmpk"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc, vmpk_home


# ZynMidiRouter:dev0_in is the first physical/virtual MIDI input slot -
# whatever a2jmidid bridges in first (VMPK, here) lands on it, confirmed
# live. Used only as a "has *something* been auto-connected yet" signal,
# not to identify VMPK specifically.
_FIRST_MIDI_INPUT_PORT = "ZynMidiRouter:dev0_in"


def _wait_for_vmpk_autoconnect(session, timeout_s: float = 10.0, poll_interval_s: float = 0.5) -> None:
    """Block until zynautoconnect's hotplug thread has wired VMPK's
    bridged port into the signal path.

    Found live (task 6.2): zynautoconnect's auto_connect_thread polls for
    hardware/virtual MIDI port changes on a ~2s cycle
    (zynautoconnect.py's `deferred_timeout`), not instantly on VMPK
    appearing - injecting a note right after VMPK's window shows up (no
    wait) reliably produced silent audio, confirmed via jack_lsp showing
    zero connections on VMPK's bridged port at that point. Polling
    list_port_connections() instead of a fixed sleep matches this
    project's established "bounded timeout, not a guessed sleep"
    convention (see e.g. log_diff.wait_for_stable_tail).
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if session.list_port_connections(_FIRST_MIDI_INPUT_PORT):
            return
        time.sleep(poll_interval_s)
    raise RuntimeError(
        f"VMPK never got auto-connected to {_FIRST_MIDI_INPUT_PORT} within {timeout_s}s"
    )


def reload_and_check_audio(zss_path: str, adapter, *, my_data_dir: str | None = None) -> None:
    """Start a fresh session loading `zss_path` as its default snapshot,
    inject a musical note, confirm non-silent audio via jack_rec+sox.

    `adapter` is native_adapter or docker_adapter (duck-typed: needs
    `check_no_contention()` and `launch()`). `my_data_dir` is required for
    docker_adapter (point the fresh container at the same scratch tree the
    original session saved into - see docker_adapter.launch()'s own
    docstring); native_adapter ignores it, since its zynthian-my-data is a
    single fixed path shared by every session already.

    Raises AudioCheckError if the captured audio is silent.
    """
    default_zss_path = os.path.join(os.path.dirname(zss_path), "default.zss")
    shutil.copyfile(zss_path, default_zss_path)

    adapter.check_no_contention()
    session = adapter.launch(my_data_dir=my_data_dir)
    vmpk_proc = None
    vmpk_home = None
    try:
        vmpk_proc, vmpk_home = _start_vmpk(session.display)
        musical_note.wait_for_vmpk_window(session.display)
        _wait_for_vmpk_autoconnect(session)

        capture_path = tempfile.mktemp(suffix=".wav", prefix="workflow-test-capture.")
        capture_thread = threading.Thread(
            target=session.capture_audio, args=(capture_path,), kwargs={"duration_s": 3.0}
        )
        capture_thread.start()
        time.sleep(0.3)  # let jack_rec actually start recording before the note plays
        musical_note.play_note(session.display, hold_seconds=1.5)
        capture_thread.join(timeout=10.0)

        result = subprocess.run(
            ["sox", capture_path, "-n", "stat"], capture_output=True, text=True
        )
        rms = None
        for line in result.stderr.splitlines():
            if "RMS" in line and "amplitude" in line:
                rms = float(line.split()[-1])
                break
        if rms is None:
            raise AudioCheckError(f"reload_and_check_audio: couldn't parse sox RMS output: {result.stderr}")
        if rms <= _SILENCE_RMS_THRESHOLD:
            raise AudioCheckError(f"reload_and_check_audio: captured audio is silent (RMS={rms})")
    finally:
        if vmpk_proc is not None:
            vmpk_proc.terminate()
            vmpk_proc.wait(timeout=5.0)
        if vmpk_home is not None:
            shutil.rmtree(vmpk_home, ignore_errors=True)
        session.teardown()


def run_workflow(workflow: Workflow, session, injector: injection.CuiaInjector, adapter=None) -> WorkflowResult:
    """`adapter` (native_adapter or docker_adapter, whichever created
    `session`) is only required when `workflow.reload_and_check_audio` is
    set - it needs to start a *second*, fresh session of the same kind.
    """
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
                my_data_dir = os.path.dirname(session.snapshots_dir)
                # reload_and_check_audio needs a *fresh* boot, and the
                # adapter's own contention check would otherwise refuse
                # to start it while this session is still up (same
                # single-native-session-at-a-time model as a real
                # interactive session) - tear this one down first. Safe
                # for the caller's own teardown() to run again afterward
                # (both adapters guard already-dead processes/containers).
                session.teardown()
                reload_and_check_audio(zss_path, adapter, my_data_dir=my_data_dir)
    except (zss_assert.ZssAssertionError, AudioCheckError) as e:
        workflow_level_error = str(e)

    return WorkflowResult(workflow_name=workflow.name, step_results=step_results, workflow_level_error=workflow_level_error)
