## Why

Before spending money on a Zynthian V5.1 hardware unit, get the real Zynthian software stack (not a mockup) running on an existing Ubuntu 24.04 laptop with a Yamaha AG03(MK2)/Korg Fisa Suprema, using genuine synth engines and JACK audio, so the actual workflow (accordion MIDI + audio in, amp sims, soundfont libraries) can be evaluated hands-on first.

## What Changes

- Build zynthian-ui, zyncoder, zynthian-sys and zynthian-data from source on x86_64/Ubuntu 24.04 instead of Raspberry Pi OS.
- Run a real standalone `jackd` instance instead of PipeWire's JACK-compat layer, because PipeWire rejects `jack_port_set_alias()` on ports it doesn't own, which Zynthian's autoconnect logic depends on.
- Stub out Raspberry-Pi-only hardware assumptions (GPIO encoders/buttons, WS281x LED strip via Adafruit Blinka, temperature/undervoltage sensors) so the app runs with mouse/touch input only.
- Provide a single `run_zynthian.sh` launch script that stops/restarts the desktop's normal PipeWire session around each run, and handles jackd/a2jmidid lifecycle including a fast/forced shutdown (real jackd's graceful shutdown can take ~20s per dead client).
- Fix native-library build failures against GCC 13 (Ubuntu 24.04) that don't occur on the GCC used for Raspberry Pi OS images (`-Werror` on new format/unused-result warnings).
- Fix a native-library crash-on-exit ("free(): corrupted unsorted chunks") by building zynseq with mimalloc.

## Capabilities

### New Capabilities
- `zynthian-desktop-runtime`: running the Zynthian software stack (UI + engines + JACK audio) on a standard x86_64 Ubuntu desktop instead of Raspberry Pi hardware, including audio device configuration, process lifecycle, and the RPi-hardware stubs needed for the app to start and exit cleanly.

### Modified Capabilities
(none - this is the first documented change for this project)

## Impact

- New/changed files live entirely outside the vendored `zynthian-ui` fork: `/zynthian/run_zynthian.sh`, `/zynthian/config/zynthian_envars_custom.sh` (synced to `/zynthian/config/zynthian_envars.sh`, which the app hardcodes as its config path).
- Native builds: `zynlibs/zynaudioplayer`, `zynlibs/zynsmf`, `zynlibs/zynclippy` (CMakeLists `-Werror` relaxation), `zynlibs/zynseq` (mimalloc).
- New directory structure under `zynthian-my-data/` that the app expects but isn't created by a plain git checkout (`presets/{lv2,zynaddsubfx,fluidsynth,sfz,sf2,gig}`, `soundfonts/{sf2,sfz}`, `files/Neural Models/`) plus `zynthian-data/collections/` and `config/jalv/`.
- Environment: `BLINKA_FORCEBOARD`/`BLINKA_FORCECHIP`, `RBPI_VERSION`/`RBPI_VERSION_NUMBER`, `ZYNTHIAN_WIRING_LAYOUT=TOUCH_ONLY`, `DISPLAY_WIDTH`/`DISPLAY_HEIGHT`.
