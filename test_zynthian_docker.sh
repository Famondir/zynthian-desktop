#!/bin/bash
# Automated headless smoke test for the Zynthian Docker image: boots it
# against a private Xvfb display (not the host's real one), drives it with
# the same virtual MIDI/audio devices validated for native dev testing
# (VMPK + snd-aloop, see openspec/changes/support-virtual-test-devices),
# and asserts the GUI rendered, MIDI reached an active chain, and audio was
# actually produced - instead of a human clicking through it and listening.
# See openspec/changes/docker-automated-smoke-test/design.md for the full
# rationale behind each check and decision below.
#
# This is a local dev script, not a hosted CI job - a typical CI runner has
# no /dev/snd, no X11 socket, and no `audio` group membership (see
# design.md's Non-Goals). Run it manually before/after changes to
# docker/Dockerfile or zynthian-ui.
#
# Prerequisites (on top of run_zynthian_docker.sh's own):
#  - xdotool, ImageMagick (import/identify), sox
#  - vmpk (see openspec/changes/support-virtual-test-devices)
#  - snd-aloop loadable (modprobe snd-aloop needs root; the script will
#    sudo-prompt if it isn't already loaded)
#  - docker/fixtures/smoke-test-default.zss (a minimal single-chain
#    FluidSynth snapshot - see design.md's "committed fixture snapshot"
#    decision for why this can't just be adapted from an existing demo
#    snapshot)
#
# Usage: ./test_zynthian_docker.sh [classic|standard|device|device_cables]
set -u
# Deliberately not `set -e`: every check below should run and report,
# not abort the whole script on the first failure.

GUI_STYLE="${1:-standard}"
case "$GUI_STYLE" in
    classic|standard|device|device_cables) ;;
    *)
        echo "Unknown GUI style '$GUI_STYLE' (expected: classic, standard, device, device_cables)" >&2
        exit 1
        ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${ZYNTHIAN_DOCKER_IMAGE:-zynthian-desktop:latest}"
CONTAINER_NAME="zynthian-smoke-test"
SMOKE_DISPLAY="${SMOKE_DISPLAY:-:98}"
# Big enough for every style, including device_cables' 1910x1120 (see
# run_zynthian_vnc.sh, which uses the same size for the same reason).
XVFB_SIZE="1920x1200x24"

FIXTURE="$SCRIPT_DIR/docker/fixtures/smoke-test-default.zss"
if [ ! -f "$FIXTURE" ]; then
    echo "Missing fixture snapshot: $FIXTURE (see design.md's 'committed fixture snapshot' decision) - nothing to route the test MIDI note into without it." >&2
    exit 1
fi

if ! command -v xdotool > /dev/null || ! command -v import > /dev/null || ! command -v identify > /dev/null; then
    echo "Missing xdotool and/or ImageMagick (import/identify) - install with: sudo apt install xdotool imagemagick" >&2
    exit 1
fi
if ! command -v sox > /dev/null; then
    echo "Missing sox - install with: sudo apt install sox" >&2
    exit 1
fi
if ! command -v vmpk > /dev/null; then
    echo "Missing vmpk - see openspec/changes/support-virtual-test-devices" >&2
    exit 1
fi

# --- 1.2 Pre-flight contention checks ---
if pgrep -f "run_zynthian(_vnc)?\.sh" > /dev/null; then
    echo "A native Zynthian session (run_zynthian.sh/run_zynthian_vnc.sh) appears to be running - refusing to start (would compete for the same audio device). Stop it first." >&2
    exit 1
fi
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    echo "A zynthian-smoke-test container is already running - refusing to start a second one. Stop it first: docker stop $CONTAINER_NAME" >&2
    exit 1
fi
docker rm -f "$CONTAINER_NAME" > /dev/null 2>&1 || true

SCRATCH_DIR="$(mktemp -d /tmp/zynthian-smoke-test.XXXXXX)"
MY_DATA_DIR="$SCRATCH_DIR/zynthian-my-data"
CONFIG_FILE="$SCRATCH_DIR/zynthian_envars_custom.sh"
VMPK_HOME="$SCRATCH_DIR/vmpk-home"
SCREENSHOT="$SCRATCH_DIR/screenshot.png"
CAPTURE_FILE="$SCRATCH_DIR/capture.wav"
echo "--- Scratch dir (diagnostics on failure): $SCRATCH_DIR ---"

declare -a PASSES=()
declare -a FAILURES=()
report() {
    # report <name> <pass|fail> [detail]
    local name="$1" result="$2" detail="${3:-}"
    if [ "$result" = "pass" ]; then
        PASSES+=("$name")
        echo "PASS: $name"
    else
        FAILURES+=("$name: $detail")
        echo "FAIL: $name - $detail"
    fi
}

SND_ALOOP_LOADED_BY_US=0
XVFB_PID=""
VMPK_PID=""

cleanup() {
    echo "--- Cleaning up ---"
    [ -n "$VMPK_PID" ] && kill "$VMPK_PID" 2>/dev/null || true
    # Capture container logs before removing it, if anything failed - the
    # container is gone after this, and it's the single most useful
    # diagnostic for a boot/GUI failure.
    if [ "${#FAILURES[@]}" -gt 0 ]; then
        docker logs "$CONTAINER_NAME" > "$SCRATCH_DIR/container.log" 2>&1 || true
    fi
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1 || true
    docker rm -f "$CONTAINER_NAME" > /dev/null 2>&1 || true
    [ -n "$XVFB_PID" ] && kill "$XVFB_PID" 2>/dev/null || true
    if [ "$SND_ALOOP_LOADED_BY_US" = "1" ]; then
        sudo modprobe -r snd-aloop 2>/dev/null || true
    fi
    echo "--- Restarting host PipeWire ---"
    systemctl --user start pipewire.socket pipewire.service \
        pipewire-pulse.socket pipewire-pulse.service \
        wireplumber.service 2>/dev/null || true
    # Only clean up the scratch dir (screenshot, captured audio, logs) on
    # a clean pass - on failure, task 3.3/spec's "save diagnostics on
    # failure" requirement needs them to survive past this trap.
    if [ "${#FAILURES[@]}" -eq 0 ]; then
        rm -rf "$SCRATCH_DIR"
    else
        echo "--- Diagnostics preserved at: $SCRATCH_DIR ---"
    fi
}
trap cleanup EXIT INT TERM

# --- 2.1 Headless display ---
echo "--- Starting Xvfb on $SMOKE_DISPLAY ($XVFB_SIZE) ---"
Xvfb "$SMOKE_DISPLAY" -screen 0 "$XVFB_SIZE" > "$SCRATCH_DIR/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 1
export DISPLAY="$SMOKE_DISPLAY"

echo "--- Authorizing local Docker containers to use this display ---"
xhost +local:docker > /dev/null

# --- 2.2 snd-aloop ---
if ! lsmod | grep -q "^snd_aloop"; then
    echo "--- Loading snd-aloop (may prompt for your password) ---"
    sudo modprobe snd-aloop
    SND_ALOOP_LOADED_BY_US=1
fi
LOOPBACK_CARD="$(aplay -l | awk '/Loopback/{print $2; exit}' | tr -d ':')"
if [ -z "$LOOPBACK_CARD" ]; then
    echo "snd-aloop loaded but no Loopback card found in 'aplay -l'" >&2
    exit 1
fi
echo "--- Using snd-aloop card: $LOOPBACK_CARD ---"

# --- 2.3 Scratch config: fixture snapshot + JACKD_OPTIONS pointed at the loopback card ---
mkdir -p "$MY_DATA_DIR/snapshots"
cp "$FIXTURE" "$MY_DATA_DIR/snapshots/default.zss"
# The fixture's FluidSynth chain references a soundfont path from the
# native machine it was saved on ("Roland Fantom X/00 Ac.Piano.sf2"),
# which doesn't exist in the container - FluidSynth logged a "can't be
# loaded" warning and produced no audio at all (found live during
# implementation). Symlink the one soundfont both the host and the image
# actually have (the fluid-soundfont-gm apt package, same path on both -
# see docker/Dockerfile's package list) into place at the exact path the
# fixture expects, rather than regenerating the fixture.
mkdir -p "$MY_DATA_DIR/soundfonts/sf2/Roland Fantom X"
ln -sf /usr/share/sounds/sf2/FluidR3_GM.sf2 "$MY_DATA_DIR/soundfonts/sf2/Roland Fantom X/00 Ac.Piano.sf2"
cat > "$CONFIG_FILE" <<EOF
# -i 2 -o 2: without an explicit channel count jackd's alsa backend opens
# the loopback card's hardware max (32 channels here), which then locks
# the paired capture side to 32-channel FLOAT_LE and made arecord fail
# with "Channels count non available" / I/O errors on read (found live
# during implementation) - pin it to a normal stereo pair instead.
export JACKD_OPTIONS="-P 70 -t 2000 -d alsa -d hw:$LOOPBACK_CARD,0 -i 2 -o 2 -p 512 -n 3 -r 48000"
EOF

echo "--- Stopping host PipeWire for this session ---"
systemctl --user stop wireplumber.service pipewire-pulse.socket pipewire-pulse.service pipewire.socket pipewire.service 2>/dev/null || true
sleep 1

# --- 2.4 Container launch (own docker run, not a reuse of run_zynthian_docker.sh - see design.md) ---
echo "--- Starting Zynthian container ($IMAGE, style=$GUI_STYLE) ---"
docker run -d --name "$CONTAINER_NAME" \
    --device /dev/snd \
    --group-add audio \
    --cap-add=SYS_NICE \
    --ulimit rtprio=95 \
    --ulimit memlock=-1 \
    --shm-size=256m \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e DISPLAY="$SMOKE_DISPLAY" \
    -e ZYNTHIAN_GUI_STYLE="$GUI_STYLE" \
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
    -v "$MY_DATA_DIR:/zynthian/zynthian-my-data" \
    -v "$CONFIG_FILE:/zynthian/config/zynthian_envars_custom.sh:ro" \
    "$IMAGE" > "$SCRATCH_DIR/docker_run.log" 2>&1
if [ $? -ne 0 ]; then
    report "gui_boot" fail "docker run failed, see $SCRATCH_DIR/docker_run.log"
    GUI_UP=0
else
    # --- 2.5 Poll for GUI readiness (bounded timeout, not a fixed sleep) ---
    BOOT_TIMEOUT=60
    elapsed=0
    GUI_UP=0
    while [ "$elapsed" -lt "$BOOT_TIMEOUT" ]; do
        # Not name-matching "Zynthian" specifically: Tk's root window title
        # defaults to sys.argv[0] ("zynthian_main.py") unless .title() is
        # called, which it isn't. Nothing else runs on this private
        # display yet at this point, so "any mapped window at all" is an
        # unambiguous readiness signal here.
        if [ -n "$(xdotool search --onlyvisible '.*' 2>/dev/null)" ]; then
            GUI_UP=1
            break
        fi
        if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
            break  # container exited early
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    if [ "$GUI_UP" = "1" ]; then
        report "gui_boot" pass
    else
        report "gui_boot" fail "GUI window not detected within ${BOOT_TIMEOUT}s - check: docker logs $CONTAINER_NAME"
    fi
fi

# --- 3. GUI render check ---
if [ "$GUI_UP" = "1" ]; then
    # A window existing (task 2.5) doesn't mean it's painted yet - Zynthian
    # keeps loading engines/snapshot/soundfonts for a while after the Tk
    # root window is first mapped (observed directly during
    # implementation). Poll for actual non-blank content instead of a
    # single fixed sleep, same "concrete readiness signal" reasoning as
    # task 2.5.
    RENDER_TIMEOUT=30
    elapsed=0
    STDDEV=0
    while [ "$elapsed" -lt "$RENDER_TIMEOUT" ]; do
        import -display "$SMOKE_DISPLAY" -window root "$SCREENSHOT" 2>/dev/null
        if [ -f "$SCREENSHOT" ]; then
            STDDEV="$(identify -format "%[fx:standard_deviation]" "$SCREENSHOT" 2>/dev/null)"
            # Threshold picked as "clearly not a solid-color blank window";
            # tune further if this proves too loose/tight (design.md's
            # Open Questions).
            if awk "BEGIN{exit !($STDDEV > 0.02)}" 2>/dev/null; then
                break
            fi
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    if awk "BEGIN{exit !($STDDEV > 0.02)}" 2>/dev/null; then
        report "gui_render" pass
    elif [ -f "$SCREENSHOT" ]; then
        report "gui_render" fail "screenshot still blank after ${RENDER_TIMEOUT}s (stddev=$STDDEV, saved at $SCREENSHOT)"
    else
        report "gui_render" fail "screenshot capture failed"
    fi
else
    report "gui_render" fail "skipped - GUI never booted"
fi

# --- 4. MIDI-to-audio signal path check ---
if [ "$GUI_UP" = "1" ]; then
    # A fresh HOME has no VMPK.conf, so VMPK defaults to its own built-in
    # synth output driver, which tries (and fails) to connect to
    # PulseAudio - same pitfall documented in support-virtual-test-devices
    # for the manual setup. Pre-seed the ALSA driver so this doesn't
    # depend on VMPK's shipped defaults.
    mkdir -p "$VMPK_HOME/.config/vmpk.sourceforge.net"
    cat > "$VMPK_HOME/.config/vmpk.sourceforge.net/VMPK.conf" <<'VMPKCONF'
[Connections]
AdvancedEnabled=false
InEnabled=false
InputDriver=None
OutputDriver=ALSA
ThruEnabled=false
VMPKCONF

    echo "--- Starting VMPK (headless) ---"
    # -u WAYLAND_DISPLAY -u XDG_SESSION_TYPE: same fix run_zynthian_vnc.sh
    # already needed for x11vnc - Qt otherwise tries the host's real
    # Wayland session instead of our private X11 display, and VMPK's
    # window never gets created (found live during implementation: the
    # vmpk process stayed running but mapped no window at all).
    env -u WAYLAND_DISPLAY -u XDG_SESSION_TYPE \
        HOME="$VMPK_HOME" DISPLAY="$SMOKE_DISPLAY" vmpk > "$SCRATCH_DIR/vmpk.log" 2>&1 &
    VMPK_PID=$!

    # Match the main window's exact title, not just "VMPK" - VMPK also
    # creates a couple of tiny 1x1 helper windows ("VMPK", a selection
    # owner) that match a looser pattern but have no real geometry to
    # click into (found live during implementation).
    vmpk_timeout=20
    elapsed=0
    VMPK_UP=0
    while [ "$elapsed" -lt "$vmpk_timeout" ]; do
        if xdotool search --name "Virtual MIDI Piano Keyboard" > /dev/null 2>&1; then
            VMPK_UP=1
            break
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    if [ "$VMPK_UP" != "1" ]; then
        report "midi_routing" fail "VMPK window never appeared, see $SCRATCH_DIR/vmpk.log"
        report "audio_output" fail "skipped - VMPK never started"
    else
        # Poll for the container's a2jmidid to expose VMPK's bridged port,
        # confirming support-virtual-test-devices task 1.2's regex
        # whitelist (a2j:(MIDI Out|VMPK)) is active in the pushed image.
        # If this never appears, first check whether /dev/snd/seq itself
        # reached the container at all (docker exec ... ls /dev/snd) -
        # ALSA-sequencer passthrough via a directory --device has not been
        # validated before this script existed.
        midi_timeout=15
        elapsed=0
        MIDI_PORT_SEEN=0
        while [ "$elapsed" -lt "$midi_timeout" ]; do
            if docker exec "$CONTAINER_NAME" jack_lsp 2>/dev/null | grep -qE "a2j:.*(MIDI Out|VMPK)"; then
                MIDI_PORT_SEEN=1
                break
            fi
            sleep 1
            elapsed=$((elapsed + 1))
        done

        if [ "$MIDI_PORT_SEEN" = "1" ]; then
            report "midi_routing" pass
        else
            report "midi_routing" fail "VMPK's a2j-bridged port never appeared in the container's jack_lsp output"
        fi

        echo "--- Capturing audio while injecting a held note ---"
        # Recording via arecord against the snd-aloop capture side was
        # tried first and abandoned: the paired capture substream
        # returned EIO on every read attempt regardless of format/channel
        # tuning (SNDRV_PCM_IOCTL_READI_FRAMES failing immediately after a
        # clean PREPARE, confirmed with strace) - the same class of
        # snd-aloop cross-coupling flakiness support-virtual-test-devices
        # already hit and worked around rather than fixed. Recording
        # directly from the container's own JACK graph via jack_rec
        # (started with docker exec, sharing the container's JACK server)
        # sidesteps the ALSA loopback entirely: it taps
        # zynmixer_bus:output_00a/00b, the main mixbus output one hop
        # upstream of system:playback (itself not recordable - it's an
        # input-direction JACK port, confirmed live: "cannot connect input
        # port jackrec:input1 to system:playback_1"), which still exercises
        # the full MIDI-to-audio signal path this check cares about.
        CONTAINER_CAPTURE="/tmp/smoke_test_capture.wav"
        docker exec -d "$CONTAINER_NAME" jack_rec -f "$CONTAINER_CAPTURE" -d 3 zynmixer_bus:output_00a zynmixer_bus:output_00b
        sleep 0.5
        # A keyboard keydown/keyup targeted at the window (xdotool
        # `--window`) was tried first and does NOT produce a MIDI event at
        # all - confirmed live with aseqdump watching VMPK's raw ALSA
        # output: zero events across several attempts, regardless of which
        # key or how long held. VMPK's on-screen piano responds reliably
        # to an actual mouse click, though, so click a key instead: derive
        # the click point from the window's own geometry (30% across,
        # 90% down - low on a white key, clear of the black-key strip
        # along the top) rather than hardcoding absolute screen pixels, so
        # this doesn't assume a fixed window position/size.
        VMPK_WINID="$(xdotool search --name "Virtual MIDI Piano Keyboard" | head -1)"
        VMPK_GEOM="$(xdotool getwindowgeometry --shell "$VMPK_WINID")"
        WIN_X="$(echo "$VMPK_GEOM" | grep '^X=' | cut -d= -f2)"
        WIN_Y="$(echo "$VMPK_GEOM" | grep '^Y=' | cut -d= -f2)"
        WIN_W="$(echo "$VMPK_GEOM" | grep '^WIDTH=' | cut -d= -f2)"
        WIN_H="$(echo "$VMPK_GEOM" | grep '^HEIGHT=' | cut -d= -f2)"
        CLICK_X=$((WIN_X + WIN_W * 30 / 100))
        CLICK_Y=$((WIN_Y + WIN_H * 90 / 100))
        xdotool mousemove "$CLICK_X" "$CLICK_Y" mousedown 1
        sleep 1.5
        xdotool mouseup 1
        xdotool mousemove 0 0  # move off the piano so nothing lingers pressed
        sleep 2  # let jack_rec's 3s recording finish

        docker cp "$CONTAINER_NAME:$CONTAINER_CAPTURE" "$CAPTURE_FILE" > "$SCRATCH_DIR/docker_cp.log" 2>&1
        if [ -f "$CAPTURE_FILE" ]; then
            RMS="$(sox "$CAPTURE_FILE" -n stat 2>&1 | grep "RMS.*amplitude" | awk '{print $NF}')"
            # Threshold picked as "clearly not silence"; tune against a
            # real successful run (design.md's Open Questions).
            if awk "BEGIN{exit !($RMS > 0.001)}" 2>/dev/null; then
                report "audio_output" pass
            else
                report "audio_output" fail "captured audio is silent (RMS=$RMS, file at $CAPTURE_FILE)"
            fi
        else
            report "audio_output" fail "jack_rec/docker cp capture failed, see $SCRATCH_DIR/docker_cp.log"
        fi
    fi
else
    report "midi_routing" fail "skipped - GUI never booted"
    report "audio_output" fail "skipped - GUI never booted"
fi

# --- 5. Summary ---
echo
echo "=== Smoke test summary (cleanup runs after this) ==="
for p in "${PASSES[@]}"; do echo "PASS: $p"; done
for f in "${FAILURES[@]}"; do echo "FAIL: $f"; done

if [ "${#FAILURES[@]}" -gt 0 ]; then
    echo "${#FAILURES[@]} check(s) failed."
    exit 1
else
    echo "All checks passed."
    exit 0
fi
