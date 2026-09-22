#!/bin/bash
# Run the Zynthian desktop Docker image. Plays the same role
# run_zynthian.sh plays for the native install: pause the host's PipeWire
# session, run the app with the right device/X11/audio flags, restore
# PipeWire on exit. See docker/Dockerfile and openspec/changes/
# docker-desktop-image/design.md for how the image itself is built.
#
# Prerequisites this script assumes and does not try to work around:
#  - Docker, with your user in the `docker` group.
#  - X11 (or XWayland on a Wayland host) - a Wayland-native passthrough is
#    out of scope.
#  - `xhost +local:docker` (run automatically below) so the container can
#    connect to your X server; if your setup is more locked down, you may
#    want a narrower `xhost +si:localuser:$(whoami)` instead.
#  - The container runs with --user matching your host UID/GID (below), so
#    typical Xauthority setups and the bind-mounted data directories (owned
#    by you on the host) work without permission fights.
set -e

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
# certainly wrong for your hardware - check `aplay -l` and uncomment/edit:
#export JACKD_OPTIONS="-P 70 -t 2000 -d alsa -d hw:0 -p 512 -n 3 -r 48000"
EOF
fi

echo "--- Authorizing local Docker containers to use this X11 display ---"
xhost +local:docker > /dev/null

cleanup() {
    echo "--- Restarting PipeWire ---"
    systemctl --user start pipewire.socket pipewire.service \
        pipewire-pulse.socket pipewire-pulse.service \
        wireplumber.service 2>/dev/null || true
}
trap cleanup EXIT

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
    -e DISPLAY="$DISPLAY" \
    -e ZYNTHIAN_GUI_STYLE="$GUI_STYLE" \
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
    -v "$ZYNTHIAN_MY_DATA_DIR:/zynthian/zynthian-my-data" \
    -v "$ZYNTHIAN_DOCKER_CONFIG:/zynthian/config/zynthian_envars_custom.sh:ro" \
    "$IMAGE"
