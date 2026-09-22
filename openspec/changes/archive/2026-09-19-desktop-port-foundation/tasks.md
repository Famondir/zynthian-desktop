## 1. Audio server

- [x] 1.1 Write `run_zynthian.sh`: stop PipeWire, start real `jackd` + `a2jmidid` with `LD_LIBRARY_PATH` forcing the real `libjack.so`, launch `zynthian_main.py`, restore PipeWire on exit
- [x] 1.2 Force-kill (`SIGKILL`) jackd/a2jmidid on exit instead of graceful shutdown, to avoid the ~20s-per-dead-client hang
- [x] 1.3 Tune `JACKD_OPTIONS` for the actual audio interface(s) in use (AG03MK2, then Fisa Suprema capture + HDMI playback)

## 2. Hardware stubs

- [x] 2.1 Set `BLINKA_FORCEBOARD`/`BLINKA_FORCECHIP` so Adafruit Blinka's `board`/`neopixel_spi` import succeeds without a WS281x LED strip
- [x] 2.2 Set `RBPI_VERSION`/`RBPI_VERSION_NUMBER` to safe non-Pi defaults
- [x] 2.3 Set `ZYNTHIAN_WIRING_LAYOUT=TOUCH_ONLY` (dummy encoders, mouse/touch navigation)

## 3. Native library builds

- [x] 3.1 Relax `-Werror` to `-Wno-error=format`/`-Wno-error=unused-result` in `zynaudioplayer`, `zynsmf`, `zynclippy` CMakeLists for GCC 13
- [x] 3.2 Install `libmimalloc-dev` and rebuild `zynseq` against it to fix the free()-corruption crash on exit

## 4. Directory structure & config

- [x] 4.1 Create missing `zynthian-my-data` subdirectories the app expects but a plain checkout doesn't provide (presets/*, soundfonts/*, files/Neural Models/)
- [x] 4.2 Create `zynthian-data/collections/` and `config/jalv/`
- [x] 4.3 Keep `zynthian_envars.sh` (the hardcoded config path) in sync with the working `zynthian_envars_custom.sh`
