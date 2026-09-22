## Context

This design captures everything learned building the *native* desktop port (`zynthian-desktop-runtime`, `desktop-engine-reliability`, `touchkeypad-visual-styles`) that a container build needs to know, so whoever implements this doesn't have to rediscover it. If you're implementing this on the same machine this was written on, `/zynthian/` is a complete, working, natively-built reference install - when in doubt about an exact build command/flag, check what actually worked there (`/zynthian/zynthian-sys/scripts/recipes/*.sh` for the official build recipes, shell history, `dpkg -l` for exact installed package versions) rather than re-deriving from scratch.

## Goals / Non-Goals

**Goals:**
- A single `docker build` produces a runnable Zynthian desktop image on any Docker host.
- Match the native install's proven-working configuration (same packages, same custom forks, same fixes) rather than re-solving already-solved problems.
- Keep the container's own audio setup simpler than the native install's, where possible (see Decisions - no PipeWire fighting needed *inside* the container).

**Non-Goals:**
- Baking soundfont/preset data into the image (hundreds of GB; use bind mounts).
- Solving audio/GUI passthrough perfectly on every possible host config (Wayland-only hosts, rootless Docker, podman, etc.) - target the same kind of host this was developed on (X11 or XWayland, Docker with a `docker` group member, PipeWire as the host audio server) and document the assumption.
- GPU acceleration / anything beyond what the native Tk GUI already needs.

## Decisions

### Base image and package list
Use `ubuntu:24.04` as the base, matching the machine this was proven on. Install (grounded in this machine's actual `apt` history for the native build - see `/var/log/apt/history.log` on the reference machine, or just this list):

```
build-essential cmake git pkg-config meson ninja-build
libasound2-dev liblo-dev liblo7 libjack-jackd2-dev jackd2 a2jmidid
libboost-python-dev libboost-thread-dev libboost-system-dev
librubberband-dev rubberband-cli
python3-venv python3-dev python3-pip python3-tk python3-evdev python3-lilv python3-pil.imagetk
liblilv-dev lv2-dev
libsndfile1-dev sox
fluidsynth libfluidsynth-dev fluid-soundfont-gm
zynaddsubfx setbfree carla
nlohmann-json3-dev
libmimalloc-dev
liblrdf0-dev libzita-convolver-dev libzita-resampler-dev fonts-roboto
gperf libsigc++-2.0-dev libeigen3-dev
ca-certificates wget curl unzip
x11-apps xauth
```

Notably **not installed**: `pipewire-jack` or any PipeWire package at all. Unlike the native install, there is no PipeWire running *inside* the container to conflict with jackd - see the audio decision below.

### Source repos
- `zynthian-ui`: clone `https://github.com/Famondir/zynthian-ui.git`, branch `vangelis` (this fork already has every `fix-*` change's commit plus `touchkeypad-visual-styles` - do NOT clone `zynthian/zynthian-ui` upstream directly, it's missing all of that).
- `zyncoder`, `zynthian-sys`, `zynthian-data`: clone from the official `zynthian/*` GitHub repos (upstream, unforked - no patches were made to these during the desktop port).
- Build `zyncoder` in its `TOUCH_ONLY`/dummy-encoders mode (no real GPIO). Check the reference machine's actual build invocation/CMake flags for `zyncoder` before guessing - it wasn't documented in detail during the native port's own change (`desktop-port-foundation`) and needs to be captured accurately here.

### Native library / plugin builds
Follow `zynthian-sys`'s own recipes (`zynthian-sys/scripts/recipes/*.sh`) rather than re-inventing:
- `install_lv2_lilv.sh` - lilv (may be skippable if `liblilv-dev`/`python3-lilv` from apt are recent enough, as they were on the reference machine; verify).
- `install_lv2_jalv.sh` - **must** build `zynthian/jalv` branch `asyncli` from source. The stock Debian/Ubuntu `jalv` package uses a different interactive stdin/stdout protocol and does not work with zynthian-ui's LV2 engine.
- `install_sfizz.sh` - sfizz isn't packaged for Ubuntu; build from `sfztools/sfizz` source.
- `install_gxplugins.sh` - builds `GxPlugins.lv2` (Guitarix effects/amp sims) from source into `zynthian-plugins/lv2`.
- `zynthian-ui`'s own `zynlibs/{zynaudioplayer,zynmixer,zynseq,zynsmf,zynclippy}` via their CMakeLists - these already have the GCC-13 `-Werror` relaxations from `desktop-port-foundation` baked in on the `vangelis` fork branch, and `zynseq` should be built with `libmimalloc-dev` available (also already handled by that change).

### Python environment
`python3 -m venv venv --system-site-packages` (matches the official `setup_system_debian_amd64_bookworm.sh` recipe's approach - `python3-lilv`/`python3-evdev`/`python3-pil.imagetk` are apt packages with no pip equivalent, so the venv needs to see system site-packages). Install `zynthian-ui/requirements.txt`, plus these packages the requirements file is missing but the code actually imports (verified on the reference machine): `pexpect`, `numpy`, `scipy`, `wavio`, `psutil`.

### Directory scaffolding
Create the same `zynthian-my-data`/`zynthian-data` subdirectories `desktop-port-foundation` needed (`presets/{lv2,zynaddsubfx,fluidsynth,sfz,sf2,gig}`, `soundfonts/{sf2,sfz}`, `files/Neural Models/`, `zynthian-data/collections/`, `config/jalv/`) - a plain git checkout doesn't provide them and the app errors without them.

### Audio: real jackd with direct hardware access, no host PipeWire wrangling needed inside the container
Unlike the native install, there's no PipeWire process *inside* the container to fight with jackd - the container just needs `jackd2`/`a2jmidid` installed and direct access to the host's ALSA device via `--device /dev/snd` on `docker run`. This removes the entire "stop PipeWire, run jackd, restart PipeWire" dance *from inside* the entrypoint.

However, the **host's** PipeWire may still be holding the same physical ALSA device the container wants exclusive access to. The host-side run script (not the Dockerfile/entrypoint) still needs to do what `run_zynthian.sh` does today: stop the host's PipeWire audio services before `docker run`, restart them after the container exits. This logic can be lifted close to verbatim from `run_zynthian.sh`.

`docker run` needs, at minimum:
- `--device /dev/snd` (ALSA hardware access)
- `--group-add audio` (or run the container's default user in a group matching the host's `audio` GID)
- `--cap-add=SYS_NICE --ulimit rtprio=95 --ulimit memlock=-1` (jackd's `-P 70` realtime-priority request; without these the container's jackd falls back to non-realtime scheduling)

### GUI: X11 socket passthrough
`docker run` needs:
- `-e DISPLAY=$DISPLAY`
- `-v /tmp/.X11-unix:/tmp/.X11-unix:ro`
- The host needs to run `xhost +local:docker` (or a more scoped `xhost +si:localuser:$(whoami)`) before `docker run`, and the container should run as a non-root user whose UID matches the host user for this to work cleanly with typical Xauthority setups. Document this as a host prerequisite; don't try to work around it silently.
- This targets X11 (or XWayland on a Wayland host); a Wayland-native passthrough is out of scope (see Non-Goals).

### Data as bind mounts, not baked into the image
Bind-mount at minimum:
- `zynthian-my-data` (soundfonts, presets, user config) - this is where hundreds of GB of soundfonts live; must never be copied into the image.
- The env-var config file (`zynthian_envars_custom.sh`-equivalent) so users can change `JACKD_OPTIONS`/audio device without rebuilding.

## Risks / Trade-offs

- Audio/GUI passthrough is inherently host-config-dependent (X11 vs Wayland, rootless vs rootful Docker, which user is in the `audio`/`docker` groups). Expect a debugging pass on a genuinely different host before this is solid - don't assume the design above is bug-free on first try, the same way the native port needed several iterations.
- Two audio-serving stacks (host PipeWire, container's jackd) time-sharing the same physical device via start/stop is inherently a bit fragile, same trade-off `zynthian-desktop-runtime` already accepted for the native install.
- Image size: native library builds pull in a lot of `-dev` packages. Consider a multi-stage build (builder stage with build tools, final stage without them) once the single-stage build is proven working - don't optimize this before it works at all.
