#!/bin/bash
# Container entrypoint: start jackd + a2jmidid, then the Zynthian UI.
#
# Unlike the native install's run_zynthian.sh, there's no PipeWire process
# *inside* the container to fight with jackd, so none of that stop/start
# dance is needed here - just direct ALSA hardware access via --device
# /dev/snd on `docker run`. The host-side PipeWire handoff still happens,
# but in run_zynthian_docker.sh, on the host, not in here.
set -e

# The Dockerfile scaffolds $ZYNTHIAN_MY_DATA_DIR's required subdirectories
# at build time (see design.md's "Directory scaffolding"), but
# run_zynthian_docker.sh bind-mounts a host directory over that same path -
# a bind mount replaces the mount point's whole contents, so that build-time
# scaffolding is invisible once mounted. Redo it here, against whatever's
# actually mounted, every start (idempotent - safe on an already-populated
# directory from a previous run). Mirrors the reference native install's
# full zynthian-my-data layout, not just what a plain checkout is missing.
mkdir -p \
    "$ZYNTHIAN_MY_DATA_DIR/presets/lv2" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/zynaddsubfx" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/fluidsynth" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/sfz" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/sf2" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/gig" \
    "$ZYNTHIAN_MY_DATA_DIR/soundfonts/sf2" \
    "$ZYNTHIAN_MY_DATA_DIR/soundfonts/sfz" \
    "$ZYNTHIAN_MY_DATA_DIR/files/Neural Models" \
    "$ZYNTHIAN_MY_DATA_DIR/midi-profiles" \
    "$ZYNTHIAN_MY_DATA_DIR/snapshots" \
    "$ZYNTHIAN_MY_DATA_DIR/capture" \
    "$ZYNTHIAN_MY_DATA_DIR/sounds" \
    "$ZYNTHIAN_MY_DATA_DIR/uploads"

# Host-specific overrides (JACKD_OPTIONS, DISPLAY_WIDTH, SOUNDCARD_NAME, ...)
# bind-mounted by run_zynthian_docker.sh; safe to skip if not mounted.
if [ -f "$ZYNTHIAN_CONFIG_DIR/zynthian_envars_custom.sh" ]; then
    source "$ZYNTHIAN_CONFIG_DIR/zynthian_envars_custom.sh"
    # Some UI code (zynconf/zynthian_config.py) reads $ZYNTHIAN_CONFIG_DIR/
    # zynthian_envars.sh directly at runtime instead of via the shell
    # environment (e.g. the admin "envars" editor); keep it in sync with
    # what we actually sourced above.
    cp "$ZYNTHIAN_CONFIG_DIR/zynthian_envars_custom.sh" "$ZYNTHIAN_CONFIG_DIR/zynthian_envars.sh" 2>/dev/null || true
fi

# GUI keypad style, ported from run_zynthian.sh: classic (verbatim original
# upstream layout) | standard (same idea, but grid matches the real V5
# panel) | device (chassis background matching real V5 proportions) |
# device_cables (device + live cable graphics). Without this, DISPLAY_WIDTH/
# DISPLAY_HEIGHT stay whatever zynthian_envars_custom.sh set (or the
# Dockerfile's 1600x960 default), and the window doesn't get the per-style
# panel-width/screen-height adjustment - it just renders oversized/
# borderless. Set via `run_zynthian_docker.sh <style>`.
GUI_STYLE="${ZYNTHIAN_GUI_STYLE:-standard}"
case "$GUI_STYLE" in
    classic|standard|device|device_cables) ;;
    *)
        echo "Unknown GUI style '$GUI_STYLE' (expected: classic, standard, device, device_cables)" >&2
        exit 1
        ;;
esac
export ZYNTHIAN_GUI_KEYPAD_STYLE="$GUI_STYLE"
echo "--- GUI keypad style: $GUI_STYLE ---"

# standard/device/device_cables reserve a wider button panel than classic
# and let their button grid fill the full window height with no gap - see
# run_zynthian.sh for the full rationale. standard is a drop-in-safe
# upgrade over classic (same screen box, better button layout), so both
# DISPLAY_WIDTH and DISPLAY_HEIGHT are pre-adjusted so its screen ends up
# pixel-identical to classic's. device/device_cables use fixed, absolute
# geometry lifted from the real V5 mockup render.
if [ "$GUI_STYLE" != "classic" ] && [ "$GUI_STYLE" != "device" ] && [ "$GUI_STYLE" != "device_cables" ]; then
    CLASSIC_PANEL=$(( (DISPLAY_WIDTH / 10) * 2 ))
    CLASSIC_SCREEN_WIDTH=$(( DISPLAY_WIDTH - CLASSIC_PANEL ))
    CLASSIC_SCREEN_HEIGHT=$(( 5 * DISPLAY_HEIGHT / 6 ))
    export DISPLAY_WIDTH=$(( CLASSIC_SCREEN_WIDTH * 10 / 6 ))
    export DISPLAY_HEIGHT="$CLASSIC_SCREEN_HEIGHT"
    echo "--- Adjusted window to ${DISPLAY_WIDTH}x${DISPLAY_HEIGHT} (target screen area ${CLASSIC_SCREEN_WIDTH}x${CLASSIC_SCREEN_HEIGHT}) ---"
elif [ "$GUI_STYLE" = "device" ]; then
    export DISPLAY_WIDTH=1910
    export DISPLAY_HEIGHT=960
    echo "--- Set window to the real V5 render's native size: ${DISPLAY_WIDTH}x${DISPLAY_HEIGHT} ---"
elif [ "$GUI_STYLE" = "device_cables" ]; then
    export DISPLAY_WIDTH=1910
    export DISPLAY_HEIGHT=1120
    echo "--- Set window to the real V5 render's native size plus a cable-graphics strip: ${DISPLAY_WIDTH}x${DISPLAY_HEIGHT} ---"
fi

# Device names vary per host (see `aplay -l`); this default is almost
# certainly wrong for any given machine. Override via the mounted
# zynthian_envars_custom.sh above, or -e JACKD_OPTIONS=... on `docker run`.
export JACKD_OPTIONS="${JACKD_OPTIONS:--P 70 -t 2000 -d alsa -d hw:0 -p 512 -n 3 -r 48000}"

# Login password for zynthian-webconf (Famondir/zynthian-webconf, branch
# vangelis - not upstream, which gates login behind a PAM check against the
# system root account; this container runs non-root, so that fork's login
# checks this env var instead - see openspec/changes/enable-webconf-access/
# design.md). Same "documented default, change it" convention as
# JACKD_OPTIONS above; override via zynthian_envars_custom.sh or
# `docker run -e ZYNTHIAN_WEBCONF_PASSWORD=...`.
export ZYNTHIAN_WEBCONF_PASSWORD="${ZYNTHIAN_WEBCONF_PASSWORD:-zynthian}"

# All the /zynthian/* repos were git-cloned as root at image build time,
# but this container runs as the host's non-root UID (see the --user flag
# in run_zynthian_docker.sh). git's "dubious ownership" safe-directory
# check refuses to run any command (branch/rev-parse/etc.) against a repo
# it doesn't own as the current user - zynthian-webconf's dashboard shells
# out to `git branch`/`git rev-parse` on six of these repos to show
# version info, and 500'd on every load until this is set. HOME=/tmp
# (already exported above/in run_zynthian_docker.sh) is where this lands.
git config --global --add safe.directory '*'

cleanup() {
    echo "--- Shutting down jackd/a2jmidid/webconf ---"
    # See run_zynthian.sh: SIGKILL, not a graceful shutdown - Zynthian can
    # leave dead clients registered in jackd, and a graceful SIGTERM makes
    # jackd wait up to ~20s per dead client trying to notify them.
    kill -9 "$WEBCONF_PID" "$A2J_PID" "$JACKD_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "--- Starting jackd ($JACKD_OPTIONS), log: /tmp/zynthian_jackd.log ---"
jackd $JACKD_OPTIONS > /tmp/zynthian_jackd.log 2>&1 &
JACKD_PID=$!
sleep 2

echo "--- Starting a2jmidid, log: /tmp/zynthian_a2jmidid.log ---"
a2jmidid -e > /tmp/zynthian_a2jmidid.log 2>&1 &
A2J_PID=$!
sleep 1

# zynthian_webconf.sh (its own script, not this one) expects to run with
# the venv's python3 first on PATH and its own directory as CWD (it execs
# `./zynthian_webconf.py` and reads `cert/{cert,key}.pem` as relative
# paths) - both handled inside this subshell so they don't leak into the
# rest of this script (which still needs to `cd "$ZYNTHIAN_UI_DIR"` below).
echo "--- Starting zynthian-webconf, log: /tmp/zynthian_webconf.log ---"
(
    source "$ZYNTHIAN_DIR/venv/bin/activate"
    cd "$ZYNTHIAN_DIR/zynthian-webconf"
    exec ./zynthian_webconf.sh
) > /tmp/zynthian_webconf.log 2>&1 &
WEBCONF_PID=$!

echo "--- Starting Zynthian UI ---"
source "$ZYNTHIAN_DIR/venv/bin/activate"
cd "$ZYNTHIAN_UI_DIR"
exec python3 zynthian_main.py
