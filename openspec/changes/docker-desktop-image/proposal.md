## Why

`desktop-port-foundation` got Zynthian running on this specific Ubuntu 24.04 machine, but most of the effort was fighting distro-specific build friction (GCC 13 `-Werror` failures, exact apt package names/versions, native library builds) that would have to be repeated on any other distro (Fedora, Arch, Debian, older Ubuntu, etc.). A Docker image eliminates that friction entirely for anyone who isn't on Ubuntu 24.04, which the pure documentation/patch-set approach (`desktop-port-foundation`) doesn't reach. This was deliberately sequenced *after* upstreaming the generic bugfixes (see `fix-*` changes) and *after* the desktop patch set was proven working, since building a container around a still-unstable base would just move the debugging target.

## What Changes

- A `Dockerfile` (in this repo, this project's own home - not inside the vendored `zynthian-ui` fork) that builds a complete, runnable Zynthian desktop image: OS packages, native library builds (zynthian-ui's own `zynlibs/*`, zyncoder, the custom `zynthian/jalv` fork, sfizz, GxPlugins.lv2), Python venv, and directory scaffolding - all grounded in the exact package list and build steps already proven working on this machine (see design.md).
- A host-side run script (`run_zynthian_docker.sh` or similar) that plays the same role `run_zynthian.sh` does for the native install: pause the host's PipeWire session, run the container with the right device/X11/audio flags, restore PipeWire on exit.
- Data (soundfonts, presets, config) stays on the host as bind-mounted volumes - never baked into the image, both because of size (hundreds of GB of soundfonts) and so users can customize without rebuilding.

## Capabilities

### New Capabilities
- `docker-desktop-image`: build and run Zynthian's desktop port as a Docker container on any Linux host with Docker, JACK-capable audio hardware, and X11.

### Modified Capabilities
(none)

## Impact

- New files only; does not modify anything in the `zynthian-ui` fork itself.
- Depends on `zynthian-desktop-runtime` (the same audio/hardware-stub decisions apply, adapted for a container) and pulls `zynthian-ui` from the `Famondir/zynthian-ui` fork's `vangelis` branch (which already has every `fix-*` and `touchkeypad-visual-styles` commit).
- **Status: proposed, not yet implemented.** This proposal is written to be picked up and executed independently (e.g. by a different agent/session) - see design.md for the full context a fresh implementer needs, and tasks.md for concrete, ordered steps.
