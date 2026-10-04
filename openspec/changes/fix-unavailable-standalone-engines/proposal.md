## Why

After `enable-lv2-reverb-effects`, the engine screens grey out LV2 plugins that aren't installed - but standalone engines (`SL`, `AE`, `IR`, `PD`, `MD`, …) are never checked. Found live on 2026-10-04: SooperLooper is listed as a normal, selectable Audio Effect, and adding it fails with `Can't start engine 'SL' => No such file or directory: 'sooperlooper'` (cleanly rolled back by that change's fix, but still a dead entry). An audit of everything currently shown as available on the native install found:

- **All 141 enabled, installed LV2 plugins load fine** with `jalv -s` (audited against a private dummy JACK server).
- **5 enabled standalone engines can't start** because their program is missing: SooperLooper (`sooperlooper`), Aeolus (`aeolus`), Internet Radio (`vlc`), PureData (`pd`), MOD-UI (`mod-ui`/`mod-host` systemd services).
- ZynAddSubFX, FluidSynth, Sfizz, setBfree have their programs; Pianoteq and LinuxSampler are already hidden/disabled.

## What Changes

- Extend the availability check to standalone engines: an engine whose required program/service is missing is shown greyed out, not selectable, with an install hint where one exists - same UI as for missing LV2 plugins.
- Install what's installable on Ubuntu 24.04, natively and in `docker/Dockerfile`: `sooperlooper` (apt), `vlc` + `vlc-plugin-jack` (apt), PureData (`puredata` + the `pd-*` externals upstream installs), Aeolus from Zynthian's own fork (`zynthian/aeolus`, branch `zynthian`, via zynthian-sys's `install_aeolus.sh` logic - the stock Debian `aeolus` lacks Zynthian's patches).
- MOD-UI stays greyed out: it needs root systemd services (`mod-ui`, `mod-host`, `browsepy`) and Zynthian's mod-ui fork - out of scope for the desktop port.
- Workflow tests that add each now-installed standalone engine.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `lv2-effect-availability`: availability marking and greying also cover standalone engines; the desktop install ships the standalone engines upstream enables, where installable.

## Impact

- **`/zynthian/zynthian-ui`** (fork): `zyngine/zynthian_lv2.py` (required-program map + check in `mark_unavailable_engines`); the engine screen's greying needs no change (it already keys on `AVAILABLE`).
- **Native host**: apt packages (needs the user's sudo), Aeolus build into `/usr/local`, `/etc/aeolus.conf`.
- **This repo**: `docker/Dockerfile` (same packages + Aeolus build), workflow tests.
