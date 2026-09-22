## ADDED Requirements

### Requirement: Buildable Docker image
A `Dockerfile` SHALL build a complete Zynthian desktop image from a single `docker build` invocation, using the `Famondir/zynthian-ui` fork's `vangelis` branch (not vanilla upstream) so all desktop-port fixes are included.

#### Scenario: Building on a clean Docker host
- **WHEN** `docker build` is run against this project's Dockerfile
- **THEN** the build completes successfully and produces an image containing zynthian-ui, zyncoder, the custom `zynthian/jalv` fork, sfizz, GxPlugins.lv2, and a Python venv with all required packages

### Requirement: Runnable without baking in user data
The image SHALL NOT contain soundfont/preset/config data; that data SHALL be supplied via bind-mounted host volumes at run time.

#### Scenario: Running the container
- **WHEN** the container is started with the documented `docker run` flags (including a bind mount for `zynthian-my-data`)
- **THEN** the running app reads soundfonts/presets from the mounted host directory, and no soundfont data is part of the image itself

### Requirement: Real JACK audio via direct hardware access
The container SHALL use a real `jackd` process with direct access to the host's ALSA hardware (via `--device /dev/snd`), not a container-internal PipeWire instance.

#### Scenario: Starting the container
- **WHEN** the container starts with `--device /dev/snd`, `--group-add audio`, and the realtime-priority capability/ulimit flags
- **THEN** `jackd` starts successfully with realtime scheduling and can access the host's audio hardware

### Requirement: GUI visible on the host display
The container's Tk GUI SHALL render on the host's X11 (or XWayland) display when the host's X11 socket and `DISPLAY` are passed through.

#### Scenario: Launching the GUI
- **WHEN** the container is started with `-e DISPLAY` and the X11 socket bind-mounted, after the host has authorized the container to connect (e.g. `xhost`)
- **THEN** the Zynthian UI window appears on the host's display

### Requirement: Host audio handoff around a container session
A host-side run script SHALL pause the host's own audio server (PipeWire) before starting the container and restore it after the container exits, mirroring the native install's behaviour.

#### Scenario: Ending a container session
- **WHEN** the Zynthian container exits, for any reason
- **THEN** the host's PipeWire audio services are restarted, so normal desktop audio works again afterward
