## MODIFIED Requirements

### Requirement: Browser-based viewing of the native desktop install and the Docker desktop image
Running `run_zynthian_vnc.sh` (native install) or `run_zynthian_docker.sh` (Docker desktop image) SHALL make the running Zynthian UI viewable from a web browser via a printed URL, without requiring a separate VNC client application to be installed or configured.

#### Scenario: Starting either script prints a working browser URL
- **WHEN** `run_zynthian_vnc.sh` or `run_zynthian_docker.sh` is run in its default mode
- **THEN** it starts `Xvfb`, `x11vnc`, and a `websockify`-served `noVNC` front end, and prints a `http://localhost:<port>/vnc.html?...resize=scale` URL that, when opened in a browser, shows the running Zynthian UI

#### Scenario: View scales to the browser window
- **WHEN** the printed URL is opened and the browser window is resized
- **THEN** the displayed UI scales responsively to fit the window, with no manual VNC-client configuration (scale mode, window size) required

#### Scenario: Both launchers can run at once without a port clash
- **WHEN** a `run_zynthian_vnc.sh` session and a `run_zynthian_docker.sh` session are started at the same time on the same machine, both using their default settings
- **THEN** each starts its own `Xvfb`/`x11vnc`/`websockify` on its own distinct display and ports, and both are viewable independently with no conflict

## ADDED Requirements

### Requirement: Host-X11-passthrough opt-out for the Docker launcher
`run_zynthian_docker.sh` SHALL support an opt-out mode that passes the container's display straight through to the host's own X11 display (its behavior prior to this capability), for anyone who prefers that over the default noVNC viewer.

#### Scenario: Opting out of noVNC
- **WHEN** `run_zynthian_docker.sh` is run with the opt-out mode selected
- **THEN** it does not start `Xvfb`/`x11vnc`/`websockify`, and instead binds the container to the host's own `$DISPLAY` and X11 socket exactly as before this capability existed
