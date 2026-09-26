#!/usr/bin/env python3
"""Run workflow_testing/workflows/*.yaml against native and/or Docker
sessions, with clear pass/fail reporting per workflow and per step.

The single entry point for this engine (task 7.4) - supersedes
test_zynthian_docker.sh (task 8), the same "run this before/after a
change to confirm the desktop port still works" role, now covering both
environments from one workflow definition instead of one Docker-only
fixture-loaded scenario. Not a hosted CI job (same Non-Goal as the
capability this replaces) - a typical CI runner has no /dev/snd, no X11
socket, no `docker` access without privilege. Run manually.

Usage:
    python3 -m workflow_testing.run_all [--env native|docker|both] [--workflow NAME]

Requires a native zynthian-ui checkout at /zynthian/zynthian-ui (or a
built zynthian-desktop:latest image for --env docker) plus the same
VMPK/snd-aloop setup as setup_virtual_devices.sh - see openspec/specs
/virtual-test-devices. Only one real or test Zynthian session (native or
Docker) can be up at a time; check_no_contention() refuses to start
otherwise rather than fight over /dev/snd or the OSC port.

Adding a new workflow: drop a `<name>.yaml` file into workflows/ - it is
picked up automatically by this module's `WORKFLOWS_DIR.glob("*.yaml")`,
no registration needed. A workflow file is:

    name: my-workflow
    steps:
      - screen: SCREEN_MIXER          # direct screen jump
        assert: {screen_is: mixer}    # optional per-step assertion
      - zynswitch: 0
        press: short                  # short|bold|long
      - cuia: ADD_CHAIN                # any other allow-listed CUIA
      - select: 0                      # move list highlight, no confirm
      - confirm: short                 # confirm highlighted item
      - arrow: right                   # cycle category/tab
      - play_note: true                # real MIDI note via VMPK
    save_snapshot: true                # trigger a save at the end
    assert_zss:
      chain_has_engine: FS             # structural check on the saved .zss
      chain_count: 1
    reload_and_check_audio: true       # reload the saved .zss fresh,
                                        # confirm non-silent audio
    assert_new_capture_file: mid       # assert a new file with this
                                        # extension appeared under capture/

Every step gets an unconditional `no_new_errors` log-diff check - see
runner.py's module docstring and `Step`/`Workflow` dataclasses for the
full field-by-field rationale, and workflows/*.yaml for worked examples.
A step's CUIA (or ZYNSWITCH index) must already be on allowlist.py's
allow-list, or the run fails before injecting anything - add a new entry
there deliberately when a new workflow needs one (see design.md's "CUIA
safety allow-list" decision for why this fails closed, not open).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import docker_adapter, injection, native_adapter, runner

WORKFLOWS_DIR = Path(__file__).parent / "workflows"

ADAPTERS = {
    "native": native_adapter,
    "docker": docker_adapter,
}


def _run_one(workflow_path: Path, env_name: str, adapter, docker_image: str | None) -> bool | None:
    """Returns True/False (pass/fail), or None if skipped (contention)."""
    print(f"\n--- {workflow_path.stem} / {env_name} ---")
    launch_kwargs = {}
    if env_name == "docker" and docker_image:
        launch_kwargs["image"] = docker_image
        contention_kwargs = {"docker_image": docker_image}
    else:
        contention_kwargs = {}
    try:
        adapter.check_no_contention(**contention_kwargs)
    except adapter.ContentionError as e:
        print(f"  SKIP: {e}")
        return None

    workflow = runner.load_workflow(workflow_path)
    session = adapter.launch(**launch_kwargs)
    injector = injection.CuiaInjector(host="localhost", port=getattr(session, "osc_port", 1370))
    try:
        result = runner.run_workflow(workflow, session, injector, adapter=adapter)
    finally:
        # Safe even if run_workflow() already tore this session down
        # itself (reload_and_check_audio does, to free it up for the
        # fresh reload session - see runner.py) - both adapters guard
        # already-dead processes/containers.
        session.teardown()

    for step_result in result.step_results:
        status = "PASS" if step_result.passed else "FAIL"
        detail = f" - {step_result.error}" if step_result.error else ""
        print(f"  [{status}] {step_result.step.describe()}{detail}")
    if result.workflow_level_error:
        print(f"  [FAIL] (workflow-level) {result.workflow_level_error}")

    print(f"  => {'PASS' if result.passed else 'FAIL'}")
    return result.passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", choices=["native", "docker", "both"], default="both")
    parser.add_argument("--workflow", help="Run only the workflow with this filename stem (e.g. build_fluidsynth_chain)")
    parser.add_argument(
        "--docker-image",
        default=None,
        help="Docker image tag to use (default: docker_adapter.DEFAULT_IMAGE) - "
        "matches ZYNTHIAN_DOCKER_IMAGE's role elsewhere in this project",
    )
    args = parser.parse_args()

    envs = ["native", "docker"] if args.env == "both" else [args.env]
    workflow_paths = sorted(WORKFLOWS_DIR.glob("*.yaml"))
    if args.workflow:
        workflow_paths = [p for p in workflow_paths if p.stem == args.workflow]
        if not workflow_paths:
            print(f"No workflow named '{args.workflow}' in {WORKFLOWS_DIR}", file=sys.stderr)
            return 2

    results: dict[tuple[str, str], bool | None] = {}
    for workflow_path in workflow_paths:
        for env_name in envs:
            results[(workflow_path.stem, env_name)] = _run_one(
                workflow_path, env_name, ADAPTERS[env_name], args.docker_image
            )

    print("\n=== Summary ===")
    any_failed = False
    for (name, env_name), passed in results.items():
        if passed is None:
            print(f"  SKIP {name} / {env_name}")
            continue
        if not passed:
            any_failed = True
        print(f"  {'PASS' if passed else 'FAIL'} {name} / {env_name}")

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
