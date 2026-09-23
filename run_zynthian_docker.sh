#!/bin/bash
# Run the Zynthian desktop Docker image. Plays the same role
# run_zynthian.sh plays for the native install: pause the host's PipeWire
# session, run the app with the right device/X11/audio flags, restore
# PipeWire on exit. See docker/Dockerfile and openspec/changes/
# docker-desktop-image/design.md for how the image itself is built.
#
# By default the container gets its own private headless display (Xvfb),
# viewable in a browser via noVNC - same technique and reasoning as
# run_zynthian_vnc.sh uses for the native install (a laptop screen too
# small for device_cables' fixed 1910x1120 render can view it scaled down
# instead of full-size). See openspec/changes/docker-novnc-browser-viewer.
# Set DOCKER_DISPLAY_MODE=host to instead pass the container straight
# through to your own real X11 display (this script's only behavior
# before that change).
#
# Prerequisites this script assumes and does not try to work around:
#  - Docker, with your user in the `docker` group.
#  - X11 (or XWayland on a Wayland host) - a Wayland-native passthrough is
#    out of scope.
#  - `xhost +local:docker` (run automatically below) so the container can
#    connect to the X display it's given; if your setup is more locked
#    down, you may want a narrower `xhost +si:localuser:$(whoami)` instead.
#  - The container runs with --user matching your host UID/GID (below), so
#    typical Xauthority setups and the bind-mounted data directories (owned
#    by you on the host) work without permission fights.
#  - DOCKER_DISPLAY_MODE=novnc (the default) additionally needs websockify
#    (sudo apt install websockify) - see novnc_viewer.sh.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# GUI keypad style: classic (verbatim original upstream layout) |
# standard (same idea, but grid matches the real V5 panel) | device
# (chassis background matching real V5 proportions) | device_cables
# (device + live cable graphics). Same styles as run_zynthian.sh; actually
# applied by docker/entrypoint.sh inside the container.
GUI_STYLE="${1:-standard}"
case "$GUI_STYLE" in
    classic|standard|device|device_cables) ;;
    *)
        echo "Unknown GUI style '$GUI_STYLE' (expected: classic, standard, device, device_cables)" >&2
        exit 1
        ;;
esac

# novnc (default): private Xvfb + noVNC, viewable/scalable in a browser.
# host: today's original behavior, straight through to the host's own
# real X11 display - no Xvfb, no noVNC.
DOCKER_DISPLAY_MODE="${DOCKER_DISPLAY_MODE:-novnc}"
case "$DOCKER_DISPLAY_MODE" in
    novnc|host) ;;
    *)
        echo "Unknown DOCKER_DISPLAY_MODE '$DOCKER_DISPLAY_MODE' (expected: novnc, host)" >&2
        exit 1
        ;;
esac

IMAGE="${ZYNTHIAN_DOCKER_IMAGE:-zynthian-desktop:latest}"
ZYNTHIAN_MY_DATA_DIR="${ZYNTHIAN_MY_DATA_DIR:-$HOME/zynthian-my-data}"
ZYNTHIAN_DOCKER_CONFIG="${ZYNTHIAN_DOCKER_CONFIG:-$HOME/.config/zynthian-docker/zynthian_envars_custom.sh}"

if [ ! -d "$ZYNTHIAN_MY_DATA_DIR" ]; then
    echo "--- Creating $ZYNTHIAN_MY_DATA_DIR (bind-mounted soundfonts/presets/snapshots) ---"
    mkdir -p "$ZYNTHIAN_MY_DATA_DIR"
fi

if [ ! -f "$ZYNTHIAN_DOCKER_CONFIG" ]; then
    echo "--- Writing default config: $ZYNTHIAN_DOCKER_CONFIG ---"
    mkdir -p "$(dirname "$ZYNTHIAN_DOCKER_CONFIG")"
    cat > "$ZYNTHIAN_DOCKER_CONFIG" <<'EOF'
# Host-specific overrides for the Zynthian Docker container. Bind-mounted
# into the container and sourced by docker/entrypoint.sh before jackd
# starts. The image's built-in JACKD_OPTIONS default (hw:0) is almost
# certainly wrong for your hardware - check `aplay -l` and uncomment/edit.
#
# -i 0: without an explicit capture-channel count, jackd opens your
# device in full duplex, which zynautoconnect then auto-wires into any
# audio-accepting chain (e.g. Guitarix's pregain) as if it were an
# instrument - picking up your built-in mic's noise with no real source
# connected. Leave capture off unless you actually want the onboard mic
# as an input; external interfaces are still bridged in dynamically at
# runtime by zynautoconnect's existing hotplug machinery when plugged in.
#export JACKD_OPTIONS="-P 70 -t 2000 -d alsa -d hw:0 -i 0 -o 2 -p 512 -n 3 -r 48000"
EOF
fi

cleanup() {
    echo "--- Cleaning up ---"
    kill "$WEBSOCKIFY_PID" "$X11VNC_PID" "$XVFB_PID" 2>/dev/null || true
    echo "--- Restarting PipeWire ---"
    systemctl --user start pipewire.socket pipewire.service \
        pipewire-pulse.socket pipewire-pulse.service \
        wireplumber.service 2>/dev/null || true
}
trap cleanup EXIT

if [ "$DOCKER_DISPLAY_MODE" = "novnc" ]; then
    source "$SCRIPT_DIR/novnc_viewer.sh"
    # Distinct from run_zynthian_vnc.sh's :97/5900/6080 defaults, so a
    # native and a Docker session can run side by side without a clash.
    VNC_DISPLAY="${VNC_DISPLAY:-:96}"
    VNC_PORT="${VNC_PORT:-5901}"
    NOVNC_PORT="${NOVNC_PORT:-6081}"
    NOVNC_BIND="${NOVNC_BIND:-localhost}"
    NOVNC_DIR="$SCRIPT_DIR/noVNC"
    XVFB_SIZE="1910x1120x24"
    start_novnc_viewer
    CONTAINER_DISPLAY="$VNC_DISPLAY"
else
    CONTAINER_DISPLAY="$DISPLAY"
fi

echo "--- Authorizing local Docker containers to use this X11 display ---"
DISPLAY="$CONTAINER_DISPLAY" xhost +local:docker > /dev/null

echo "--- Stopping PipeWire for this session ---"
systemctl --user stop wireplumber.service pipewire-pulse.socket pipewire-pulse.service pipewire.socket pipewire.service 2>/dev/null || true
sleep 1

echo "--- Starting Zynthian container ($IMAGE) ---"
# --shm-size: Docker's 64MB default /dev/shm is too small for jackd's
# shared-memory ring buffers (~100MB+ at typical buffer/period settings) -
# exceeding it doesn't fail cleanly, it SIGBUSes jackd on first access past
# the tmpfs quota. Found by strace'ing the crash; 256m covers this with
# headroom. Not a security-related flag, just a size limit.
docker run --rm -it \
    --device /dev/snd \
    --group-add audio \
    --cap-add=SYS_NICE \
    --ulimit rtprio=95 \
    --ulimit memlock=-1 \
    --shm-size=256m \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e DISPLAY="$CONTAINER_DISPLAY" \
    -e ZYNTHIAN_GUI_STYLE="$GUI_STYLE" \
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
    -v "$ZYNTHIAN_MY_DATA_DIR:/zynthian/zynthian-my-data" \
    -v "$ZYNTHIAN_DOCKER_CONFIG:/zynthian/config/zynthian_envars_custom.sh:ro" \
    "$IMAGE"
