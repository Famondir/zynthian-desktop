## Context

Zynthian ships as a Raspberry Pi OS image with dedicated GPIO hardware (encoders, buttons, WS281x LEDs) and jackd as the system's only pro-audio server. None of that exists on a stock Ubuntu 24.04 desktop, which instead runs PipeWire as its audio server and has no GPIO at all.

## Goals / Non-Goals

**Goals:**
- Run the real zynthian-ui/zyngine stack (not a mockup) with working audio in/out and MIDI.
- Keep the host's normal desktop audio (PipeWire/Bluetooth/etc.) working before and after a session.
- Make failures visible and debuggable (logs, clean process teardown) rather than silently degraded.

**Non-Goals:**
- Running Zynthian and normal desktop audio *simultaneously* (real jackd needs exclusive access to the ALSA device while active).
- Replacing PipeWire system-wide or changing default audio routing outside of a `run_zynthian.sh` session.
- GPIO/physical-encoder support - out of scope for a laptop test rig (see `touchkeypad-visual-styles` for the touch-based substitute).

## Decisions

- **Real jackd instead of PipeWire's JACK-compat layer.** PipeWire's `pipewire-jack` rejects `jack_port_set_alias()` on ports it doesn't own (errno -22). Zynthian's autoconnect logic calls this on hardware/MIDI-bridge ports it doesn't own, so under PipeWire this either raises an unhandled exception (see `desktop-engine-reliability`) or silently leaves the port without an alias. Real jackd allows it, matching actual Raspberry Pi hardware behaviour. `run_zynthian.sh` stops PipeWire's services for the session and restarts them on exit.
- **Force-kill jackd/a2jmidid on exit instead of a graceful shutdown.** Zynthian sometimes crashes on exit (see the mimalloc decision below), leaving dead clients registered in jackd. A graceful `SIGTERM` makes jackd wait up to ~20s *per dead client* trying to notify them. Since a clean JACK shutdown isn't needed here, `SIGKILL` is used instead.
- **`LD_LIBRARY_PATH` override, not a system-wide default change.** jackd/a2jmidid/zynthian_main.py are launched with `LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:...` to force the real `libjack.so` ahead of PipeWire's shim, scoped to these processes only, so the rest of the desktop keeps using PipeWire normally.
- **Adafruit Blinka RPi stub (`BLINKA_FORCEBOARD=GENERIC_LINUX_PC`, `BLINKA_FORCECHIP=GENERIC_X86`).** Zynthian imports `board`/`neopixel_spi` unconditionally even without a real LED strip; Blinka's generic-Linux stub satisfies the import without real hardware.
- **`RBPI_VERSION_NUMBER=0`.** Several engines (e.g. FluidSynth's voice/preload-size tuning) branch on Pi model number; `0` selects the most conservative (Pi 3-equivalent) settings rather than crashing on missing `/proc` hardware info.
- **mimalloc for zynseq.** A "free(): corrupted unsorted chunks" crash on exit was traced to zynseq's native allocator; rebuilding it against `libmimalloc` fixed it. Scoped to zynseq only, not applied process-wide.
- **`-Wno-error=format` / `-Wno-error=unused-result` for zynaudioplayer/zynsmf/zynclippy.** GCC 13 (Ubuntu 24.04) is stricter about these warnings than the GCC used for Raspberry Pi OS Bookworm images; the underlying code isn't desktop-specific, only the compiler is. (Upstream has since explicitly rejected similar fixes during their pre-release feature freeze - see `desktop-engine-reliability`'s design notes - so this stays a local-only patch, not something to re-propose upstream.)

## Risks / Trade-offs

- Pausing the host's PipeWire session means normal desktop audio (browser, Spotify, etc.) is unavailable for the duration of a Zynthian session and needs a manual restart of some apps afterward (PipeWire itself restarts automatically via `run_zynthian.sh`'s exit trap).
- `SIGKILL`-ing jackd/a2jmidid skips graceful client notification; acceptable here since the session is ending anyway, but would be wrong for a long-lived production JACK setup.
- The GCC-13 warning relaxations and RPi-hardware stubs are desktop-only patches that intentionally diverge from upstream and must be re-applied/rebased if this fork is refreshed from `zynthian/zynthian-ui` again.
