## Why

Zynthian's web configuration UI (`zynthian-webconf`) is never present today: it's not cloned into the native `/zynthian` install and not built into the Docker image, so there's no browser-based way to manage engine/MIDI/audio settings for this desktop port - only the touchscreen UI. Both the native install and the Docker image need it reachable from a browser on the host.

## What Changes

- Clone and provision `zynthian-webconf` (the `zynthian/zynthian-webconf` repo) into both environments' `$ZYNTHIAN_DIR`, alongside the existing `zynthian-ui`/`zyncoder`/etc. checkouts.
- **Docker image** (`docker/Dockerfile`): clone `zynthian-webconf` and install its Python dependencies (`tornado`, `tornadostreamform`, `websocket-client`, `tornado_xstatic`, `terminado`, `xstatic`, `XStatic_term.js`) into the same venv used by `zynthian-ui`.
- **Docker entrypoint** (`docker/entrypoint.sh`): start the webconf service as a background process alongside jackd/a2jmidid/the UI, and shut it down on container exit via the existing `cleanup` trap.
- **Docker run script** (`run_zynthian_docker.sh`): publish the webconf HTTP port to the host (`-p`) and add whatever `--cap-add`/port configuration is needed for it to bind while running as the non-root container user (the container currently runs as `--user "$(id -u):$(id -g)"`, so binding webconf's default privileged port needs either a capability grant or reconfiguring webconf to a high port).
- **Native install**: a new repo-local script (mirroring `run_zynthian_vnc.sh`'s role for VNC) that clones `zynthian-webconf` into `/zynthian` if missing, installs its deps into `/zynthian/venv`, and starts/stops it for local use - without touching `/zynthian/run_zynthian.sh` itself (not version-controlled, per `CLAUDE.md`) or requiring the real-hardware systemd unit.
- Document the webconf URL/port and any host firewall/port implications in this change's design and in follow-up README/usage notes.

## Capabilities

### New Capabilities
- `webconf-access`: provisioning, starting, stopping, and reaching the Zynthian web configuration UI from a browser, for both the native desktop install and the Docker image.

### Modified Capabilities
(none - no existing spec's requirements change; this only adds new capability)

## Impact

- Affected files: `docker/Dockerfile`, `docker/entrypoint.sh`, `run_zynthian_docker.sh`, a new native-side helper script in this repo, `config/zynthian_envars_custom.sh.example` (if webconf needs a configurable port/host override), and `openspec/specs/` (new `webconf-access` capability).
- New dependency: the `zynthian/zynthian-webconf` git repo (cloned at build/setup time, like `zynthian-ui`/`zyncoder`/`zynthian-sys`), plus its pip packages.
- Host-visible change: a new port is published from the Docker container and opened on the native install's loopback/LAN interface - worth calling out explicitly since it's a new network-facing surface, not just a local process.
- No changes to `zynthian-ui` application code itself; this is purely provisioning/orchestration, matching this repo's stated scope in `CLAUDE.md`.
