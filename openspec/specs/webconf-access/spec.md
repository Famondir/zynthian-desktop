## Purpose

Make `zynthian-webconf` - the browser-based configuration UI real Zynthian hardware ships alongside `zynthian-ui` - reachable from a browser for both this project's Docker image and its native `/zynthian` install, neither of which provision or run it today. Both environments use a forked/patched version (`Famondir/zynthian-webconf`, branch `vangelis`) with password-based auth in place of upstream's PAM/root login, since neither environment runs as root.

## Requirements

### Requirement: Docker image provisions zynthian-webconf at build time
`docker/Dockerfile` SHALL clone the `zynthian-webconf` repository into `$ZYNTHIAN_DIR/zynthian-webconf` and install its Python dependencies into the same venv used by `zynthian-ui`, so a built image contains a runnable webconf without any manual setup step.

#### Scenario: Building the image produces a runnable webconf checkout
- **WHEN** `docker build` completes against `docker/Dockerfile`
- **THEN** `$ZYNTHIAN_DIR/zynthian-webconf` exists in the resulting image with its startup script present, and the image's venv has `tornado`, `tornadostreamform`, `websocket-client`, `tornado_xstatic`, `terminado`, `xstatic`, and `XStatic_term.js` installed

### Requirement: Docker container starts webconf alongside the main UI
`docker/entrypoint.sh` SHALL start `zynthian-webconf` as a background process before starting the Zynthian UI, and SHALL terminate it on container shutdown using the same cleanup path already used for jackd/a2jmidid.

#### Scenario: Container start brings up webconf
- **WHEN** the container starts via `docker/entrypoint.sh`
- **THEN** the webconf process is running in the background before `zynthian_main.py` starts, with its output logged to a file

#### Scenario: Container shutdown stops webconf
- **WHEN** the container receives a shutdown signal (e.g. `docker stop`, or the entrypoint's `exec`'d UI process exits)
- **THEN** the webconf background process is also terminated, not left running or orphaned

### Requirement: Docker webconf is reachable from the host browser
`run_zynthian_docker.sh` SHALL publish the container's webconf port to the host and grant the container whatever capability it needs to bind that port as its non-root user, so a user can open webconf in a browser on the host without the container running as root.

#### Scenario: Webconf reachable after `run_zynthian_docker.sh`
- **WHEN** a user runs `run_zynthian_docker.sh` and the container has finished starting
- **THEN** the host can reach the webconf UI at the published host port in a browser, and the container process serving it runs as the non-root user `run_zynthian_docker.sh` already sets via `--user`

### Requirement: Native install can provision and start zynthian-webconf on demand
A new repo-local script SHALL clone `zynthian-webconf` into `/zynthian/zynthian-webconf` if it isn't already present, install its dependencies into `/zynthian/venv`, and start it, independently of `/zynthian/run_zynthian.sh` and `run_zynthian_vnc.sh`.

#### Scenario: First run on a machine without zynthian-webconf checked out
- **WHEN** the new native script is run and `/zynthian/zynthian-webconf` does not yet exist
- **THEN** the script clones it, installs its dependencies into the existing `/zynthian/venv`, and then starts it

#### Scenario: Subsequent run with zynthian-webconf already present
- **WHEN** the new native script is run and `/zynthian/zynthian-webconf` already exists
- **THEN** the script skips re-cloning and starts webconf directly using the existing checkout

#### Scenario: Runs independently of the main UI
- **WHEN** the new native script is run without `run_zynthian_vnc.sh` or `/zynthian/run_zynthian.sh` also running
- **THEN** webconf still starts and stays up on its own, since it does not depend on the main UI process being active

### Requirement: Native webconf is reachable from a browser without modifying `/zynthian/run_zynthian.sh`
The native provisioning/startup script SHALL be a standalone file in this repo (not edits to the non-version-controlled `/zynthian/run_zynthian.sh`), and starting it SHALL make webconf reachable from a browser on the host.

#### Scenario: Webconf reachable after running the native script
- **WHEN** a user runs the new native script directly
- **THEN** the host can reach the webconf UI at a documented URL/port in a browser, without `/zynthian/run_zynthian.sh` having been modified by this change
