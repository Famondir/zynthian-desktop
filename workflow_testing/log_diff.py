"""Per-step log-diff assertion.

See openspec/changes/add-workflow-smoke-testing/design.md's "Per-step
log-diff assertion" decision: compare a target session's log output
against the tail captured immediately before a step, and fail if any new
line at ERROR level or containing an unhandled traceback appears. Scoped
per-step (not a global allowlist) so pre-existing harmless log noise
(e.g. the "i2cdetect: not found"/"wlan0 not found" lines this project's
own enable-webconf-access change ran into) never needs allowlisting -
it's simply outside any step's diff window.

Works against any plain-text, append-only log file - the target session's
own log path is the caller's concern (native: wherever zynthian_main.py's
stdout/stderr is redirected; Docker: `docker logs`/a file inside the
container, read via `docker exec`/`docker cp`), not this module's.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

_ERROR_MARKERS = ("ERROR", "Traceback (most recent call last):")


@dataclass
class LogTailMark:
    """A remembered position in a log file, to diff new content against."""

    path: str
    byte_offset: int = field(default=0)


class LogRegressionError(Exception):
    """Raised when a step's diff window contains a new ERROR/traceback line."""


def mark_tail(path: str) -> LogTailMark:
    """Capture the current end-of-file position of `path`."""
    with open(path, "rb") as f:
        f.seek(0, 2)  # seek to end
        return LogTailMark(path=path, byte_offset=f.tell())


def read_new_lines(mark: LogTailMark) -> list[str]:
    """Return lines appended to `mark.path` since `mark` was captured."""
    with open(mark.path, "rb") as f:
        f.seek(mark.byte_offset)
        new_bytes = f.read()
    return new_bytes.decode(errors="replace").splitlines()


def _is_error_line(line: str) -> bool:
    return any(marker in line for marker in _ERROR_MARKERS)


def wait_for_stable_tail(
    mark: LogTailMark, *, quiet_period_s: float = 0.5, timeout_s: float = 10.0, poll_interval_s: float = 0.1
) -> list[str]:
    """Poll `mark.path` until no new bytes have appeared for `quiet_period_s`.

    Bounded timeout, not a fixed sleep - same style as the rest of this
    project's dev tooling (see e.g. test_zynthian_docker.sh's VMPK-window
    wait). Returns the new lines once the tail has stabilized, or once
    `timeout_s` elapses (whichever comes first - a step that never
    produces a stable-looking tail should still be diffed with whatever
    arrived, not hang forever).
    """
    deadline = time.monotonic() + timeout_s
    last_size = mark.byte_offset
    stable_since = time.monotonic()

    while time.monotonic() < deadline:
        with open(mark.path, "rb") as f:
            f.seek(0, 2)
            current_size = f.tell()
        if current_size != last_size:
            last_size = current_size
            stable_since = time.monotonic()
        elif time.monotonic() - stable_since >= quiet_period_s:
            break
        time.sleep(poll_interval_s)

    return read_new_lines(mark)


def assert_no_new_errors(mark: LogTailMark, *, step_description: str = "step") -> None:
    """Raise LogRegressionError if any new line since `mark` looks like an error."""
    new_lines = wait_for_stable_tail(mark)
    error_lines = [line for line in new_lines if _is_error_line(line)]
    if error_lines:
        raise LogRegressionError(
            f"New error output during {step_description}:\n" + "\n".join(error_lines)
        )
