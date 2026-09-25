"""Native environment adapter: launches an isolated, headless zynthian-ui
session directly on this machine for workflow-script testing.

See openspec/changes/add-workflow-smoke-testing/design.md and tasks.md
group 4. Deliberately does NOT call run_zynthian.sh (run_zynthian_vnc.sh's
own technique) - that script stops the host's real PipeWire and binds
jackd to real hardware (JACKD_OPTIONS from zynthian_envars_custom.sh),
appropriate for an interactive session but overkill and disruptive for a
scripted background test that mostly only needs structural/log
assertions. Instead this launches zynthian_main.py directly against:

- a private Xvfb display (own DISPLAY, never the host's real one)
- a dummy-driver JACK server under its own server name (`-n`/`-j`/
  JACK_DEFAULT_SERVER, never the default server name) - never touches
  /dev/snd or PipeWire at all, so a workflow test can run even while
  something else (a real interactive Zynthian session, an unrelated
  recording) is using the host's real audio hardware. No PipeWire stop/
  start dance is needed either, unlike run_zynthian.sh/
  run_zynthian_vnc.sh - confirmed live, see teardown()'s docstring.
- a2jmidid scoped to that same isolated server via its own `-j` flag -
  confirmed live during development that a2jmidid does NOT honor the
  JACK_DEFAULT_SERVER env var, only `-j`; using just the env var silently
  attached it to the host's real default JACK server instead (caught via
  `jack_lsp -A` showing the bridged ports on the wrong server, before any
  real harm was done).

Verified live: jackd's dummy driver requires forcing the real system
jackd2 (LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:...") ahead of
PipeWire's own jackd-compatible shim, which doesn't support the dummy
driver at all ("Driver 'dummy' is not a master") - the same REAL_LIB_DIR
technique run_zynthian.sh itself uses, for the same reason. jack_lsp's
`-s`/`-S` server-name flag also crashes on this machine's build
("buffer overflow detected", exit 134) - use the JACK_DEFAULT_SERVER env
var instead, never that flag.

zynthian_envars_custom.sh is still sourced before launching
zynthian_main.py (RBPI_VERSION, BLINKA_FORCEBOARD, LV2_PATH, etc. that
zyngine imports need at module load time - confirmed live: without it,
zynthian_main.py crashes at import time with `TypeError: argument of
type 'NoneType' is not iterable` from zynthian_engine_jalv.py reading
RBPI_VERSION), but its JACKD_OPTIONS is never used - jackd is started
here directly against the dummy driver, not by run_zynthian.sh.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field

REAL_LIB_DIR = "/usr/lib/x86_64-linux-gnu"
ENVARS_CUSTOM_SH = "/zynthian/config/zynthian_envars_custom.sh"
VENV_ACTIVATE_SH = "/zynthian/venv/bin/activate"
ZYNTHIAN_UI_DIR = "/zynthian/zynthian-ui"
DEFAULT_JACK_SERVER_NAME = "zynworkflow"
DEFAULT_DISPLAY = ":95"
DEFAULT_DOCKER_IMAGE = "zynthian-desktop:latest"

# zynmixer_bus:output_00a/00b - the main JACK mixbus output, one hop
# upstream of system:playback (itself unrecordable - an input-direction
# port). Same ports test_zynthian_docker.sh's own audio_output check
# taps, confirmed live there to carry the full MIDI-to-audio signal path.
MIXBUS_OUTPUT_PORTS = ("zynmixer_bus:output_00a", "zynmixer_bus:output_00b")


class ContentionError(Exception):
    """Raised when a conflicting native or Docker Zynthian session is already running."""


def _real_lib_env(extra: dict | None = None) -> dict:
    env = {
        **os.environ,
        "LD_LIBRARY_PATH": f"{REAL_LIB_DIR}:{os.environ.get('LD_LIBRARY_PATH', '')}",
    }
    if extra:
        env.update(extra)
    return env


def check_no_contention(docker_image: str = DEFAULT_DOCKER_IMAGE) -> None:
    """Refuse to start if a real (or another test) session is already up.

    Ports test_zynthian_docker.sh's own pgrep/docker-ps contention checks
    (task 4.4) - a second concurrent session would fight the first for
    the same real audio hardware (an interactive native/Docker session)
    or the same isolated JACK server name (a second workflow-test run
    left running by mistake).
    """
    pgrep = subprocess.run(
        ["pgrep", "-f", r"run_zynthian(_vnc)?\.sh|zynthian_main\.py"],
        capture_output=True,
        text=True,
    )
    if pgrep.returncode == 0 and pgrep.stdout.strip():
        raise ContentionError(
            "A native Zynthian session (run_zynthian.sh/run_zynthian_vnc.sh/"
            "zynthian_main.py) appears to already be running - refusing to "
            "start a competing one."
        )

    docker_ps = subprocess.run(
        ["docker", "ps", "--filter", f"ancestor={docker_image}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    if docker_ps.returncode == 0 and docker_ps.stdout.strip():
        raise ContentionError(
            f"A Docker container from image '{docker_image}' is already running - "
            "refusing to start a competing native session (same underlying "
            "zynthian-ui code, would race on shared state like zynthian-my-data)."
        )


def _wait_for_display(display: str, timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if subprocess.run(["xdpyinfo", "-display", display], capture_output=True).returncode == 0:
            return
        time.sleep(0.2)
    raise RuntimeError(f"Xvfb on {display} never became ready within {timeout_s}s")


def _wait_for_jack_server(server_name: str, timeout_s: float = 10.0) -> None:
    env = _real_lib_env({"JACK_DEFAULT_SERVER": server_name})
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if subprocess.run(["jack_lsp"], env=env, capture_output=True).returncode == 0:
            return
        time.sleep(0.2)
    raise RuntimeError(f"JACK server '{server_name}' never became ready within {timeout_s}s")


def wait_for_ui_ready(ui_log_path: str, is_alive, timeout_s: float = 30.0) -> None:
    """Block until zynthian_main.py has finished booting, not just started.

    Shared by both environment adapters (native: a local Popen's
    `.poll() is None`; Docker: `docker ps` reachability) - the boot-
    completion signal itself is identical either way, only "is the
    process still alive" differs.

    The OSC server ("ZYNTHIAN-UI OSC server running") comes up well before
    boot actually finishes - snapshot loading, engine startup and
    soundfont loading all continue afterwards on the same thread. Found
    live: injecting/marking a log-diff window right after the OSC line
    catches that trailing boot activity (bank-load/soundfont-load INFO
    lines, plus a harmless "Bad controller address" ERROR from Bluetooth
    init) as false-positive "new errors", not a real regression. The
    "SHOW SCREEN '<initial screen>'" line (see show_screen()'s
    logging.info patch on the zynthian-ui fork) is reliably the *last*
    line of a normal boot, so wait for that instead.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not is_alive():
            raise RuntimeError(f"zynthian_main.py exited during boot - see {ui_log_path}")
        try:
            if "SHOW SCREEN" in open(ui_log_path).read():
                return
        except FileNotFoundError:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"zynthian_main.py did not finish booting within {timeout_s}s - see {ui_log_path}")


@dataclass
class NativeSession:
    display: str
    jack_server_name: str
    ui_log_path: str
    _xvfb_proc: subprocess.Popen = field(repr=False)
    _jackd_proc: subprocess.Popen = field(repr=False)
    _a2jmidid_proc: subprocess.Popen = field(repr=False)
    _ui_proc: subprocess.Popen = field(repr=False)
    _ui_log_file: object = field(repr=False)

    def is_ui_alive(self) -> bool:
        return self._ui_proc.poll() is None

    def capture_audio(self, output_wav_path: str, duration_s: float = 3.0) -> None:
        """Record `duration_s` seconds from the mixbus output via jack_rec.

        Blocks for `duration_s` - callers inject the note to capture
        (musical_note.play_note) after starting this, same ordering
        test_zynthian_docker.sh uses (jack_rec started first, in the
        background, then the note injected shortly after).
        """
        env = _real_lib_env({"JACK_DEFAULT_SERVER": self.jack_server_name})
        subprocess.run(
            ["jack_rec", "-f", output_wav_path, "-d", str(duration_s), *MIXBUS_OUTPUT_PORTS],
            env=env,
            check=True,
        )

    def teardown(self) -> None:
        """Stop every process this session started, in reverse start order.

        No PipeWire restore step is needed here, unlike run_zynthian.sh/
        run_zynthian_vnc.sh/test_zynthian_docker.sh - this adapter never
        stops the host's PipeWire in the first place (the dummy JACK
        driver never touches /dev/snd), so there's nothing to hand back.
        """
        procs = (self._ui_proc, self._a2jmidid_proc, self._jackd_proc, self._xvfb_proc)
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        deadline = time.monotonic() + 5.0
        for proc in procs:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
        self._ui_log_file.close()


def launch(
    *,
    display: str = DEFAULT_DISPLAY,
    jack_server_name: str = DEFAULT_JACK_SERVER_NAME,
    ui_log_path: str | None = None,
    xvfb_size: str = "1600x960x24",
) -> NativeSession:
    """Start an isolated native session: Xvfb, dummy JACK, a2jmidid, zynthian_main.py.

    Call check_no_contention() first - this doesn't call it itself, so
    callers control exactly when that check runs relative to their own
    setup/locking.
    """
    ui_log_path = ui_log_path or f"/tmp/workflow_test_native_ui_{os.getpid()}.log"

    xvfb_proc = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", xvfb_size, "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_display(display)

    jackd_proc = subprocess.Popen(
        ["jackd", "-n", jack_server_name, "-d", "dummy", "-r", "48000", "-p", "512"],
        env=_real_lib_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_jack_server(jack_server_name)

    a2jmidid_proc = subprocess.Popen(
        ["a2jmidid", "-j", jack_server_name, "-e"],
        env=_real_lib_env(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # a2jmidid has no readiness signal worth polling for (no matching
    # jack_lsp port to wait on until a MIDI device actually shows up) -
    # a short fixed wait matches what manual validation already confirmed
    # is enough for it to attach to the target server.
    time.sleep(1.0)

    # PYTHONUNBUFFERED: without it, zynthian_main.py's stdout/stderr are
    # block-buffered (not a TTY) - log lines can be *generated* well
    # before they're actually *flushed to the file*. Found live: this
    # broke the log-diff assertion (workflow_testing/log_diff.py), which
    # assumes byte-offset order matches generation order - a harmless
    # boot-time line (Bluetooth's "Bad controller address") showed up
    # flushed late, inside a workflow step's diff window that started
    # well after that line was actually logged, misattributing it as a
    # regression introduced by that step.
    ui_env = _real_lib_env(
        {"JACK_DEFAULT_SERVER": jack_server_name, "DISPLAY": display, "PYTHONUNBUFFERED": "1"}
    )
    launch_script = (
        f"source {ENVARS_CUSTOM_SH} && "
        f"source {VENV_ACTIVATE_SH} && "
        f"cd {ZYNTHIAN_UI_DIR} && "
        f"exec python3 zynthian_main.py"
    )
    ui_log_file = open(ui_log_path, "wb")
    ui_proc = subprocess.Popen(
        ["bash", "-c", launch_script],
        env=ui_env,
        stdout=ui_log_file,
        stderr=subprocess.STDOUT,
    )

    wait_for_ui_ready(ui_log_path, lambda: ui_proc.poll() is None)

    return NativeSession(
        display=display,
        jack_server_name=jack_server_name,
        ui_log_path=ui_log_path,
        _xvfb_proc=xvfb_proc,
        _jackd_proc=jackd_proc,
        _a2jmidid_proc=a2jmidid_proc,
        _ui_proc=ui_proc,
        _ui_log_file=ui_log_file,
    )
