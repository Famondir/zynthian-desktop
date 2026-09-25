"""Docker environment adapter: launches an isolated, headless zynthian-ui
container for workflow-script testing.

See openspec/changes/add-workflow-smoke-testing/design.md and tasks.md
group 5. Own `docker run` invocation, not a call into
run_zynthian_docker.sh (same "dedicated invocation is cleaner than
reusing the interactive script" reasoning as native_adapter.py and
test_zynthian_docker.sh before it - the interactive script's PipeWire
stop/start dance and real-hardware `/dev/snd` passthrough serve a human
listening to real audio, not a scripted structural/log test).

Unlike run_zynthian_docker.sh, this adapter overrides JACKD_OPTIONS to
the `dummy` driver (same technique as native_adapter.py) instead of
requesting `--device /dev/snd`/`--group-add audio` - there's no PipeWire
process inside the container to fight with jackd either way (see
docker/entrypoint.sh's own header comment), so the *only* reason to touch
real hardware here at all would be genuine audio-output verification,
and even that only needs jackd's dummy driver plus a JACK-level capture
tap (`jack_rec` against `zynmixer_bus:output_00a/00b`, same ports the
native adapter and test_zynthian_docker.sh already use) - not real
speakers. This sidesteps the whole host-side PipeWire stop/start dance
run_zynthian_docker.sh needs for an interactive session.

The container's `zynthian_main.py` runs as PID 1 (entrypoint.sh's own
`exec`), so its stdout/stderr is exactly `docker logs <container>`'s
output - this adapter tails that continuously into a local file
(`docker logs -f ... > path`) so `workflow_testing.log_diff` can treat it
identically to the native adapter's log file, no adapter-specific
diffing logic needed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field

from . import native_adapter

DEFAULT_IMAGE = native_adapter.DEFAULT_DOCKER_IMAGE
DEFAULT_CONTAINER_NAME = "zynthian-workflow-test"
DEFAULT_DISPLAY = ":98"
DEFAULT_OSC_HOST_PORT = 11370


def check_no_contention(docker_image: str = DEFAULT_IMAGE) -> None:
    """Same check as native_adapter - a real interactive session (native
    or Docker) or a leftover test container from either adapter all
    conflict the same way (shared JACK/X11 assumptions, or just noise in
    `docker ps`)."""
    native_adapter.check_no_contention(docker_image=docker_image)


def _wait_for_container_running(container_name: str, timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        out = subprocess.run(
            ["docker", "ps", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if out.stdout.strip() == container_name:
            return
        time.sleep(0.2)
    raise RuntimeError(
        f"Container '{container_name}' never reached running state within {timeout_s}s"
    )


def _is_container_running(container_name: str) -> bool:
    out = subprocess.run(
        ["docker", "ps", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    return out.stdout.strip() == container_name


@dataclass
class DockerSession:
    display: str
    container_name: str
    osc_port: int
    ui_log_path: str
    snapshots_dir: str
    _xvfb_proc: subprocess.Popen = field(repr=False)
    _logs_tail_proc: subprocess.Popen = field(repr=False)
    _ui_log_file: object = field(repr=False)
    _scratch_dir: str = field(repr=False)
    _my_data_dir: str = field(repr=False)
    _owns_my_data_dir: bool = field(repr=False)

    def is_ui_alive(self) -> bool:
        return _is_container_running(self.container_name)

    def capture_audio(self, output_wav_path: str, duration_s: float = 3.0) -> None:
        """Record `duration_s` seconds from the container's own mixbus via
        `docker exec ... jack_rec`, then copy the result out to the host.

        Same ports as native_adapter.NativeSession.capture_audio() and
        test_zynthian_docker.sh's proven audio_output check.
        """
        container_capture = "/tmp/workflow_test_capture.wav"
        subprocess.run(
            [
                "docker", "exec", self.container_name,
                "jack_rec", "-f", container_capture, "-d", str(duration_s),
                *native_adapter.MIXBUS_OUTPUT_PORTS,
            ],
            check=True,
        )
        subprocess.run(
            ["docker", "cp", f"{self.container_name}:{container_capture}", output_wav_path],
            check=True,
        )

    def list_port_connections(self, port_name: str) -> list[str]:
        """Return the JACK ports `port_name` is currently connected to."""
        result = subprocess.run(
            ["docker", "exec", self.container_name, "jack_lsp", "-c", port_name],
            capture_output=True,
            text=True,
        )
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return lines[1:] if lines else []

    def teardown(self) -> None:
        """Stop the container and every host-side helper process this
        session started."""
        subprocess.run(["docker", "stop", self.container_name], capture_output=True)
        subprocess.run(["docker", "rm", "-f", self.container_name], capture_output=True)
        for proc in (self._logs_tail_proc, self._xvfb_proc):
            if proc.poll() is None:
                proc.terminate()
        deadline = time.monotonic() + 5.0
        for proc in (self._logs_tail_proc, self._xvfb_proc):
            remaining = max(0.0, deadline - time.monotonic())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
        self._ui_log_file.close()
        # Always this session's own scratch dir (just the config file).
        shutil.rmtree(self._scratch_dir, ignore_errors=True)
        # my_data_dir only if this session created it itself - an
        # externally-provided one (see launch()'s my_data_dir docstring,
        # task 6.2's reload_and_check_audio) outlives this session on
        # purpose, since a second session needs to boot from it next.
        if self._owns_my_data_dir:
            shutil.rmtree(self._my_data_dir, ignore_errors=True)


def launch(
    *,
    image: str = DEFAULT_IMAGE,
    display: str = DEFAULT_DISPLAY,
    container_name: str = DEFAULT_CONTAINER_NAME,
    osc_host_port: int = DEFAULT_OSC_HOST_PORT,
    ui_log_path: str | None = None,
    xvfb_size: str = "1600x960x24",
    my_data_dir: str | None = None,
) -> DockerSession:
    """Start an isolated Docker session: Xvfb, the container (dummy JACK
    driver, no real audio hardware), and a `docker logs -f` tail.

    Call check_no_contention() first - same convention as native_adapter,
    callers control exactly when that check runs.

    `my_data_dir`: reuse an existing zynthian-my-data tree (e.g. another
    session's, to reload a snapshot it just saved - see runner.py's
    reload_and_check_audio, task 6.2) instead of creating a fresh, empty
    one. A freshly-created one is this session's own (deleted by
    teardown()); a passed-in one is not (outlives this session - the
    whole point of passing it in is for something else to use it next).
    """
    ui_log_path = ui_log_path or f"/tmp/workflow_test_docker_ui_{os.getpid()}.log"
    scratch_dir = tempfile.mkdtemp(prefix="zynthian-workflow-test.")
    owns_my_data_dir = my_data_dir is None
    if my_data_dir is None:
        my_data_dir = tempfile.mkdtemp(prefix="zynthian-workflow-test-my-data.")

    # entrypoint.sh only creates /zynthian/config/zynthian_envars.sh (which
    # zynconf/zynthian_config.py reads directly, unconditionally, at
    # startup) by copying it from a bind-mounted zynthian_envars_custom.sh
    # - found live: without this mount at all, boot crashes with
    # FileNotFoundError on zynthian_envars.sh. run_zynthian_docker.sh always
    # provides this mount (auto-creating a default if none exists), so this
    # gap never shows up there - only in an adapter that (like this one)
    # skips it. An empty file is enough to satisfy the cp step.
    config_file = os.path.join(scratch_dir, "zynthian_envars_custom.sh")
    with open(config_file, "w") as f:
        f.write(
            "#!/bin/bash\n"
            # This container has no systemd at all - zynthian_state_manager's
            # default_bluetooth() (called once during boot) calls
            # `systemctl start bluetooth` unless told Bluetooth is already
            # off, which fails loudly (found live: logged at ERROR,
            # breaking a workflow step's zero-tolerance log-diff). The
            # native install's own zynthian_envars_custom.sh sets this to
            # "1" instead (real systemd/bluetooth present there, so
            # is_service_active() short-circuits before ever reaching that
            # failing command) - this headless test adapter has no real
            # Bluetooth hardware either way, so just disable it outright.
            'export ZYNTHIAN_MIDI_BLE_ENABLED="0"\n'
        )

    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    xvfb_proc = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", xvfb_size, "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        if subprocess.run(["xdpyinfo", "-display", display], capture_output=True).returncode == 0:
            break
        time.sleep(0.2)

    subprocess.run(["env", f"DISPLAY={display}", "xhost", "+local:docker"], capture_output=True)

    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", container_name,
            # Not for the dummy JACK driver (which never touches it) -
            # a2jmidid needs the host's real /dev/snd/seq to bridge a
            # host-side VMPK process into the container's JACK graph for
            # reload_and_check_audio (task 6.2). Same flag
            # test_zynthian_docker.sh already validated for this exact
            # purpose. --group-add audio for device permission, matching
            # that script too.
            "--device", "/dev/snd",
            "--group-add", "audio",
            "--cap-add=SYS_NICE",
            "--ulimit", "rtprio=95",
            "--ulimit", "memlock=-1",
            "--shm-size=256m",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-e", "HOME=/tmp",
            "-e", f"DISPLAY={display}",
            # dummy driver: no real audio hardware needed, matches
            # native_adapter's isolation approach (see module docstring).
            "-e", "JACKD_OPTIONS=-d dummy -r 48000 -p 512",
            # See native_adapter.launch()'s own PYTHONUNBUFFERED comment -
            # same block-buffering hazard applies here (docker logs -f
            # reading a piped, non-TTY stdout/stderr).
            "-e", "PYTHONUNBUFFERED=1",
            "-v", "/tmp/.X11-unix:/tmp/.X11-unix:ro",
            "-v", f"{my_data_dir}:/zynthian/zynthian-my-data",
            "-v", f"{config_file}:/zynthian/config/zynthian_envars_custom.sh:ro",
            "-p", f"{osc_host_port}:1370/udp",
            image,
        ],
        check=True,
        capture_output=True,
    )
    _wait_for_container_running(container_name)

    ui_log_file = open(ui_log_path, "wb")
    logs_tail_proc = subprocess.Popen(
        ["docker", "logs", "-f", container_name],
        stdout=ui_log_file,
        stderr=subprocess.STDOUT,
    )

    native_adapter.wait_for_ui_ready(ui_log_path, lambda: _is_container_running(container_name))

    return DockerSession(
        display=display,
        container_name=container_name,
        osc_port=osc_host_port,
        ui_log_path=ui_log_path,
        snapshots_dir=os.path.join(my_data_dir, "snapshots"),
        _xvfb_proc=xvfb_proc,
        _logs_tail_proc=logs_tail_proc,
        _ui_log_file=ui_log_file,
        _scratch_dir=scratch_dir,
        _my_data_dir=my_data_dir,
        _owns_my_data_dir=owns_my_data_dir,
    )
