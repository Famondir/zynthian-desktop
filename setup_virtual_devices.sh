#!/bin/bash
# Set up virtual stand-ins for the physical Korg Fisa Suprema, for dev
# testing on the native desktop install when the physical device isn't at
# hand. See openspec/changes/support-virtual-test-devices for the full
# rationale (and openspec/specs/virtual-test-devices for the resulting
# requirements).
#
# This is dev-only tooling - it does not run Zynthian itself. Run it
# alongside an already-running native session (./run_zynthian.sh or
# ./run_zynthian_vnc.sh), then launch VMPK and play a note.
#
# --- MIDI: VMPK ---
# VMPK (Virtual MIDI Piano Keyboard) sends over ALSA-seq (its default
# driver), which the native install's a2jmidid bridges into JACK exactly
# like real hardware. zynautoconnect.py's update_hw_midi_ports() has a
# whitelist of virtual-MIDI-treated-as-hardware ALSA client names
# (matches a2jmidid only sets JackPortIsPhysical for kernel-type ALSA
# clients - real/virtual-hardware drivers - not VMPK's type=user client,
# so without this whitelist entry VMPK's bridged port is invisible to the
# hardware scan and never auto-connects). This whitelist entry
# ("a2j:(MIDI Out|VMPK)", covering both VMPK's pre-config-file default
# ALSA client name "MIDI Out" and its post-config-file name "VMPK
# Output") already ships in this fork - nothing to set up here beyond
# installing/launching VMPK itself and setting its MIDI Output Driver to
# ALSA (Edit > MIDI Connections, first run only - VMPK otherwise defaults
# to its own built-in synth driver, which tries and fails to reach
# PulseAudio, itself paused for the Zynthian session).
#
# --- Audio: snd-aloop ---
# The snd-aloop kernel module creates a genuine ALSA card ("Loopback",
# with paired playback/capture subdevices) - modprobe/rmmod produce real
# udev card add/remove events, the same signal a USB audio interface's
# hotplug produces (unlike a PipeWire/PulseAudio virtual sink, which never
# touches ALSA's card list at all, and so wouldn't exercise the same
# get_alsa_audio_devices()/update_hw_audio_ports() code path
# fix-audio-hotplug-support's hotplug bridging relies on). Loading it here
# is the standard way to simulate an audio interface appearing for dev
# testing; `sudo modprobe -r snd-aloop` simulates it disappearing.
# snd-aloop's card is silent by default, though - simulating a device
# appearing/disappearing doesn't by itself confirm actual signal flow.
# Pass --with-fluidsynth to also start a small fluidsynth instance writing
# real audio into the loopback's playback side (hw:Loopback,0), so
# Zynthian's own Audio Input screen has something audible to pick up once
# it recognizes the Loopback card as a bridgeable input source.
#
# Usage: ./setup_virtual_devices.sh [--with-fluidsynth]
set -e

WITH_FLUIDSYNTH=0
if [ "${1:-}" = "--with-fluidsynth" ]; then
    WITH_FLUIDSYNTH=1
fi

if command -v vmpk > /dev/null; then
    echo "--- vmpk already installed ---"
else
    echo "--- Installing vmpk (may prompt for your password) ---"
    sudo apt-get install -y vmpk
fi

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

if [ "$WITH_FLUIDSYNTH" = "1" ]; then
    if pgrep -f "fluidsynth.*hw:$LOOPBACK_CARD" > /dev/null; then
        echo "--- fluidsynth already running against the loopback card ---"
    else
        echo "--- Starting fluidsynth against hw:$LOOPBACK_CARD,0, log: /tmp/zynthian_dev_fluidsynth.log ---"
        # Plain ALSA playback app, independent of the native install's own
        # jackd/JACK graph - it just writes into the loopback card, the
        # same way any other unrelated ALSA app would.
        LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH" \
            fluidsynth -a alsa -o audio.alsa.device="hw:$LOOPBACK_CARD,0" \
            -m alsa_seq -j -o midi.jack.id=fluidsynth-dev \
            /usr/share/sounds/sf2/FluidR3_GM.sf2 \
            > /tmp/zynthian_dev_fluidsynth.log 2>&1 &
        echo "--- fluidsynth PID: $! ---"
    fi
fi

echo
echo "--- Next steps ---"
echo "1. Make sure a native session is running: ./run_zynthian.sh or ./run_zynthian_vnc.sh"
echo "2. Launch VMPK: vmpk"
echo "   (first run only: Edit > MIDI Connections > MIDI Output Driver = ALSA)"
echo "3. Play a note - it should reach the active chain with no manual jack_connect"
if [ "$WITH_FLUIDSYNTH" = "1" ]; then
    echo "4. In Zynthian's Audio Input screen, the Loopback card is selectable as a source"
fi
echo "To simulate the interface disappearing: sudo modprobe -r snd-aloop"
