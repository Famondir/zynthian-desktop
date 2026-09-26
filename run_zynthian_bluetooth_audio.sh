#!/bin/bash
# Bridge a connected Bluetooth device's audio output into the Zynthian
# audio graph, via bluealsa and a snd-aloop ("Loopback") card. Opt-in,
# manually-started companion script, independent of run_zynthian.sh /
# run_zynthian_vnc.sh - see openspec/changes/support-bluetooth-audio-output
# for the full rationale, and openspec/changes/investigate-jack-bluetooth-audio
# (archived) for how this path was de-risked.
#
# *** LATENCY WARNING: ~150-190ms round-trip (A2DP/SBC's ~150ms transport
# *** delay is a hard protocol floor, plus ~40ms of tuned ALSA buffering
# *** on this bridge). NOT suitable for live/real-time monitoring while
# *** playing - use only for background/non-critical audio output,
# *** testing, or casual listening. This is a deliberate, accepted
# *** tradeoff, not a bug.
#
# What this does NOT do:
#  - Stop/restart PipeWire itself. Run this alongside an already-running
#    Zynthian session (run_zynthian.sh/run_zynthian_vnc.sh), which already
#    stopped PipeWire for its own jackd needs. bluealsa and PipeWire both
#    try to claim the same BlueZ A2DP media endpoint - only one can hold
#    it at a time - so this script fails fast if PipeWire is still active
#    rather than silently producing no audio.
#  - Auto-detect a Bluetooth device connecting/disconnecting. Unlike a USB
#    device (unconditionally reported by the kernel via
#    /proc/asound/cards the moment it's plugged in), Bluetooth requires an
#    explicit prior pairing/connection step by the user anyway
#    (bluetoothctl connect) - it was never going to be truly
#    hotplug-transparent the way USB is.
#  - Use the alsa_out/alsa_in bridge binaries fix-audio-hotplug-support
#    uses for USB devices - those are confirmed to crash outright
#    ("buffer overflow detected") on a bluealsa device string. This script
#    uses plain arecord/aplay instead.
#
# This script only gets a Bluetooth device's audio *out* of the Loopback
# card's capture side (hw:Loopback,1) and onto the Bluetooth device - it
# doesn't touch routing on the Zynthian side. zynautoconnect.py already
# treats "Loopback" as a normal hotplug-discoverable ALSA device (same
# mechanism support-virtual-test-devices/setup_virtual_devices.sh already
# exercises for dev testing), so once this script is running, use
# device_cables to connect a chain's audio output to the Loopback card's
# playback side (hw:Loopback,0) - that's what this script's arecord reads
# from.
#
# Usage: ./run_zynthian_bluetooth_audio.sh [--yes] [MAC-or-name-substring]
#   --yes                  Skip the interactive latency-warning confirmation
#                          (for repeat/scripted runs - the warning is still
#                          printed either way).
#   MAC-or-name-substring  Which connected Bluetooth device to bridge to.
#                          A MAC address (AA:BB:CC:DD:EE:FF) is matched
#                          exactly; anything else is matched as a
#                          case-insensitive substring against `bluetoothctl
#                          devices Connected` names. If omitted and exactly
#                          one device is connected, that one is used.
#
# Prerequisite: bluez-alsa-utils (sudo apt install bluez-alsa-utils), with
# bluealsa.service running (usually enabled by default after install).
set -e

LOG="/tmp/zynthian_bluetooth_audio.log"
: > "$LOG"

CONFIRM=1
DEVICE_ARG=""
for arg in "$@"; do
    if [ "$arg" = "--yes" ]; then
        CONFIRM=0
    else
        DEVICE_ARG="$arg"
    fi
done

# --- 2.2: bluez-alsa-utils / bluealsa.service ---
if ! command -v bluealsa-aplay >/dev/null; then
    echo "bluez-alsa-utils is required: sudo apt install bluez-alsa-utils" >&2
    exit 1
fi
if ! systemctl is-active --quiet bluealsa.service; then
    echo "bluealsa.service isn't running: sudo systemctl start bluealsa.service" >&2
    exit 1
fi

# --- 2.4 / 1.3: PipeWire must already be stopped (this script doesn't manage
# that dance itself - see header comment). Same unit list run_zynthian.sh's
# own "Stopping PipeWire for this session" step stops.
if systemctl --user is-active --quiet pipewire.service; then
    echo "PipeWire is still running - bluealsa can't claim the Bluetooth" >&2
    echo "device's audio transport while it does. Start a Zynthian session" >&2
    echo "first (run_zynthian.sh or run_zynthian_vnc.sh), which already" >&2
    echo "stops PipeWire for its own jackd needs, then run this script" >&2
    echo "alongside it." >&2
    exit 1
fi

# --- 2.3: snd-aloop, reusing setup_virtual_devices.sh's own check ---
if lsmod | grep -q "^snd_aloop"; then
    echo "--- snd-aloop already loaded ---"
else
    echo "--- Loading snd-aloop (may prompt for your password) ---"
    sudo modprobe snd-aloop
fi
LOOPBACK_CARD="$(aplay -l | awk '/Loopback/{print $2; exit}' | tr -d ':')"
if [ -z "$LOOPBACK_CARD" ]; then
    echo "snd-aloop loaded but no Loopback card found in 'aplay -l'" >&2
    exit 1
fi
echo "--- snd-aloop card: $LOOPBACK_CARD ---"

# --- 2.5: device selection ---
MAC_RE='^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
CONNECTED="$(bluetoothctl devices Connected)"

if [ -n "$DEVICE_ARG" ] && [[ "$DEVICE_ARG" =~ $MAC_RE ]]; then
    MAC="$(echo "$DEVICE_ARG" | tr 'a-f' 'A-F')"
    if ! echo "$CONNECTED" | grep -qi "^Device $MAC "; then
        echo "$DEVICE_ARG is not currently connected (bluetoothctl devices Connected):" >&2
        echo "$CONNECTED" >&2
        exit 1
    fi
elif [ -n "$DEVICE_ARG" ]; then
    MATCHES="$(echo "$CONNECTED" | grep -i "$DEVICE_ARG" || true)"
    MATCH_COUNT="$(echo "$MATCHES" | grep -c . || true)"
    if [ "$MATCH_COUNT" -eq 0 ]; then
        echo "No connected Bluetooth device matches '$DEVICE_ARG'. Connected devices:" >&2
        echo "$CONNECTED" >&2
        exit 1
    elif [ "$MATCH_COUNT" -gt 1 ]; then
        echo "'$DEVICE_ARG' matches more than one connected device - be more specific:" >&2
        echo "$MATCHES" >&2
        exit 1
    fi
    MAC="$(echo "$MATCHES" | awk '{print $2}')"
else
    MATCH_COUNT="$(echo "$CONNECTED" | grep -c . || true)"
    if [ "$MATCH_COUNT" -eq 0 ]; then
        echo "No connected Bluetooth device found. Pair/connect one first, e.g.:" >&2
        echo "  bluetoothctl" >&2
        echo "  > connect AA:BB:CC:DD:EE:FF" >&2
        exit 1
    elif [ "$MATCH_COUNT" -gt 1 ]; then
        echo "Multiple connected Bluetooth devices - pass one as an argument (MAC or name):" >&2
        echo "$CONNECTED" >&2
        exit 1
    fi
    MAC="$(echo "$CONNECTED" | awk '{print $2}')"
fi
DEVICE_NAME="$(echo "$CONNECTED" | grep -i "^Device $MAC " | cut -d' ' -f3-)"
echo "--- Bridging to: $DEVICE_NAME ($MAC) ---"

# --- 1.2 / 2.7: latency warning, printed as runtime output (not just the
# header comment above), with an interactive confirmation by default.
echo
echo "########################################################################"
echo "# LATENCY WARNING: this Bluetooth audio bridge has ~150-190ms of"
echo "# round-trip latency (A2DP/SBC's ~150ms transport delay is a hard"
echo "# protocol floor - it cannot be tuned away). NOT suitable for"
echo "# live/real-time monitoring while playing. Use only for"
echo "# background/non-critical audio output, testing, or casual listening."
echo "########################################################################"
echo
if [ "$CONFIRM" = "1" ]; then
    read -r -p "Type 'yes' to continue: " ANSWER
    if [ "$ANSWER" != "yes" ]; then
        echo "Aborted." >&2
        exit 1
    fi
fi

# --- 2.5 (continued): ensure bluealsa (not PipeWire) holds the A2DP
# transport. If PipeWire held it before this session's PipeWire stop, a
# stale transport can linger - a disconnect/reconnect cycle after PipeWire
# is stopped (already confirmed above) reliably hands it to bluealsa.
if ! bluealsa-aplay -L 2>/dev/null | grep -qi "DEV=$MAC"; then
    echo "--- bluealsa doesn't see a PCM for $MAC yet - reconnecting ---"
    bluetoothctl disconnect "$MAC" >/dev/null
    sleep 1
    bluetoothctl connect "$MAC" >/dev/null
    for _ in $(seq 1 10); do
        if bluealsa-aplay -L 2>/dev/null | grep -qi "DEV=$MAC"; then
            break
        fi
        sleep 1
    done
    if ! bluealsa-aplay -L 2>/dev/null | grep -qi "DEV=$MAC"; then
        echo "bluealsa still doesn't see a PCM for $MAC after reconnecting." >&2
        echo "Check 'bluealsa-aplay -L' and 'journalctl -u bluealsa.service' for detail." >&2
        exit 1
    fi
fi

# --- 2.6: start the bridge ---
FIFO="$(mktemp -u /tmp/zynthian_bluetooth_audio.fifo.XXXXXX)"
mkfifo "$FIFO"

ARECORD_PID=""
APLAY_PID=""
cleanup() {
    echo "--- Stopping Bluetooth audio bridge ---"
    [ -n "$APLAY_PID" ] && kill "$APLAY_PID" 2>/dev/null
    [ -n "$ARECORD_PID" ] && kill "$ARECORD_PID" 2>/dev/null
    rm -f "$FIFO"
}
trap cleanup EXIT INT TERM

arecord -D "hw:Loopback,1,0" -F 20000 -B 40000 > "$FIFO" 2>>"$LOG" &
ARECORD_PID=$!
aplay -D "bluealsa:DEV=$MAC,PROFILE=a2dp" -F 20000 -B 40000 < "$FIFO" 2>>"$LOG" &
APLAY_PID=$!

echo "--- Bridge running (arecord PID $ARECORD_PID, aplay PID $APLAY_PID), log: $LOG ---"
echo "--- Route a chain's audio output to the Loopback card (device_cables) to hear it here ---"
echo "--- Press Ctrl-C to stop ---"
wait "$ARECORD_PID" "$APLAY_PID"
