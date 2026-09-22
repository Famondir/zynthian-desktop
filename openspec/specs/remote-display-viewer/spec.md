## Purpose

Provide browser-based (noVNC) viewing of the native desktop install's UI on a virtual display, so the running Zynthian UI can be viewed and scaled to the browser window without installing or configuring a separate VNC client application.

## Requirements

### Requirement: Browser-based viewing of the native desktop install
Running `run_zynthian_vnc.sh` SHALL make the virtual display viewable from a web browser via a printed URL, without requiring a separate VNC client application to be installed or configured.

#### Scenario: Starting the script prints a working browser URL
- **WHEN** `run_zynthian_vnc.sh` is run
- **THEN** it starts `Xvfb`, `x11vnc`, and a `websockify`-served `noVNC` front end, and prints a `http://localhost:<port>/vnc.html?...resize=scale` URL that, when opened in a browser, shows the running Zynthian UI

#### Scenario: View scales to the browser window
- **WHEN** the printed URL is opened and the browser window is resized
- **THEN** the displayed UI scales responsively to fit the window, with no manual VNC-client configuration (scale mode, window size) required

### Requirement: noVNC fetched on demand, not vendored
The `noVNC` static web client SHALL be fetched automatically if not already present, rather than committed to this repository.

#### Scenario: First run with no local noVNC checkout
- **WHEN** `run_zynthian_vnc.sh` is run and its expected `noVNC` directory does not exist
- **THEN** it clones `noVNC` from its upstream repository to that path before starting `websockify`

#### Scenario: Subsequent runs reuse the existing checkout
- **WHEN** `run_zynthian_vnc.sh` is run and its expected `noVNC` directory already exists
- **THEN** it reuses that checkout without re-cloning

### Requirement: Existing raw-VNC workflow keeps working
Direct VNC client access (e.g. Remmina) to the same session SHALL continue to work unchanged, so this change is additive rather than a removal of the prior workflow.

#### Scenario: Connecting a VNC client directly
- **WHEN** a VNC client connects to the same host/port `x11vnc` listens on
- **THEN** it can view/control the session exactly as it could before this change
