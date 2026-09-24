## Purpose

Run the real Zynthian software stack (UI, engines, JACK audio) on a generic x86_64 Ubuntu desktop instead of Raspberry Pi hardware, as a pre-purchase test rig, without breaking the host's normal desktop audio.

## Requirements

### Requirement: Real JACK server for audio I/O
The runtime SHALL use a real standalone `jackd` process for audio I/O instead of PipeWire's JACK-compatibility layer, because Zynthian's autoconnect logic calls `jack_port_set_alias()` on ports it does not own, which PipeWire's `pipewire-jack` rejects.

#### Scenario: Starting a session
- **WHEN** `run_zynthian.sh` is launched
- **THEN** the host's PipeWire audio services are stopped, a real `jackd` process is started with the configured device/sample-rate options, and `zynthian_main.py` runs with `LD_LIBRARY_PATH` set so it links against the real `libjack.so` rather than PipeWire's shim

#### Scenario: Ending a session
- **WHEN** the Zynthian process exits, for any reason (clean exit, crash, or Ctrl+C)
- **THEN** `jackd` and `a2jmidid` are terminated and the host's normal PipeWire audio services are restarted, so desktop audio (browser, media players, etc.) works again afterward

### Requirement: Audio hardware hotplug without restarting the app
Reconnecting or newly plugging in a USB audio interface SHALL make it selectable as an audio source without requiring the whole app (and its jackd process) to be restarted, matching how MIDI hotplug already behaves.

#### Scenario: Reconnecting the same audio interface
- **WHEN** a previously-connected USB audio interface is unplugged and plugged back in while the app is running
- **THEN** its capture/playback ports become selectable again (e.g. in the Audio Input screen or `device_cables`' live cable display) without restarting the app

#### Scenario: Plugging in a different audio interface
- **WHEN** a USB audio interface that wasn't connected at app startup is plugged in while the app is running
- **THEN** its capture/playback ports become selectable without restarting the app

### Requirement: Hardware-independent startup on non-Raspberry-Pi Linux
The runtime SHALL start and reach a usable UI on a generic x86_64 Ubuntu desktop with no Raspberry-Pi GPIO, LED, or sensor hardware present, by substituting safe stand-ins for those subsystems instead of failing.

#### Scenario: No WS281x LED strip attached
- **WHEN** Zynthian imports `board`/`neopixel_spi` (Adafruit Blinka) during startup
- **THEN** the import succeeds using Blinka's generic-Linux-PC stub (`BLINKA_FORCEBOARD=GENERIC_LINUX_PC`, `BLINKA_FORCECHIP=GENERIC_X86`) instead of raising an error

#### Scenario: No Raspberry Pi temperature/undervoltage sensors
- **WHEN** the state manager checks CPU temperature or undervoltage status at startup
- **THEN** the check fails gracefully (logged error/warning) and startup continues, rather than crashing the whole process

### Requirement: Native libraries build on GCC 13
The zynthian-ui native libraries (`zynaudioplayer`, `zynsmf`, `zynclippy`, `zynseq`, `zynmixer`) SHALL build successfully with the GCC version shipped in Ubuntu 24.04 (GCC 13), even where that compiler emits warnings the Raspberry Pi OS Bookworm toolchain does not.

#### Scenario: Building zynaudioplayer/zynsmf/zynclippy
- **WHEN** the CMake build for these libraries runs on Ubuntu 24.04
- **THEN** the build succeeds; `-Wformat` and `-Wunused-result` are treated as non-fatal warnings instead of `-Werror` build failures

### Requirement: Clean process exit without native crashes
The runtime SHALL exit without a native-level crash (double-free/heap corruption) when the UI process is closed.

#### Scenario: Closing the UI window
- **WHEN** the user closes the Zynthian UI window or selects Admin > Exit
- **THEN** the process tears down its native libraries (including `zynseq`, built against mimalloc) without a "free(): corrupted unsorted chunks"-style crash
