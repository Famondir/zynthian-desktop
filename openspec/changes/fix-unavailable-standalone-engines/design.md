## Context

- `zynthian_lv2.mark_unavailable_engines()` (added by `enable-lv2-reverb-effects`) sets `AVAILABLE`/`INSTALL_HINT` only for `JV/*` entries. The engine screen greys out and refuses anything with `AVAILABLE=False`, and `add_processor()` refuses it up front - so standalone entries just need the flag.
- Standalone engines are listed in `zynthian_lv2.standalone_engine_info`; their engine classes start a program (`self.command`): `zynaddsubfx`, `fluidsynth`, `sfizz_jack`, `linuxsampler`, `setBfreeUI`, `aeolus`, `sooperlooper`, `vlc`, `pd`. MOD-UI instead runs `systemctl start mod-ui` (root services `mod-ui`, `mod-host`, `browsepy`). AudioPlayer, SysEx, MIDI Control, Clippy are in-process (zynlibs/Python).
- Audit 2026-10-04 (native): all 141 enabled+installed LV2 plugins reach jalv's prompt with `jalv -s -n <name> <url>` against a private `jackd -n audit -d dummy`; missing programs: `sooperlooper`, `aeolus`, `vlc`, `pd`, `mod-ui`/`mod-host`. Pianoteq is already disabled by `chain_manager.get_engine_info()` when its binary is absent; LinuxSampler is disabled in the catalog.
- Upstream installs (zynthian-sys `setup_system_raspioslite_64bit_trixie.sh` + recipes): `apt-get install sooperlooper`; `install_vlc.sh` = `vlc vlc-plugin-jack` plus a `geteuid` patch only needed when running vlc as root (the desktop port never runs as root); PureData = `puredata puredata-core puredata-utils puredata-import python3-yaml` + ~45 `pd-*` externals; Aeolus = `install_aeolus.sh` builds `zynthian/aeolus` branch `zynthian`, copies `stops` to `/usr/local/share/aeolus`, writes `/etc/aeolus.conf`.

## Goals / Non-Goals

**Goals:** no engine is shown selectable unless it can start; install every standalone engine upstream enables that works without root services.

**Non-Goals:** MOD-UI on the desktop (root systemd services, own fork, Python-3.11 path patches); LinuxSampler (no apt package, already disabled); auditing *disabled* catalog entries.

## Decisions

### D1: Required-program map next to `standalone_engine_info`
A dict `standalone_engine_requires = {code: (check, install_hint)}` in `zynthian_lv2.py`; `check` is a program name tested with `shutil.which()`, or for MOD-UI a systemd unit name tested via the unit file's existence. `mark_unavailable_engines()` applies it to non-`JV/` keys. Hints: `SL` → `sooperlooper`, `IR` → `vlc vlc-plugin-jack`, `PD` → `puredata`, `AE`/`MD`/`LS` → none (no plain apt package that works). *Alternative*: instantiate each engine class to read its `command` - rejected: constructors have side effects (start OSC servers, read configs). *Alternative*: try-start and catch - that's what already happens on click; the point is to grey it out *before*.

setBfree: its engine runs `setBfreeUI` or `setBfree` depending on config - check `setBfree` (both ship in the same package).

### D2: PureData with the externals upstream installs
Install the same `pd-*` list as upstream, so its bundled patches work; packages that don't exist on Ubuntu 24.04 are dropped (checked with `apt-cache policy` during implementation) and listed in tasks.

### D3: Aeolus from Zynthian's fork, not Debian's
Zynthian's engine relies on its fork's CLI/OSC behaviour, so replicate `install_aeolus.sh` (build, `make install` to `/usr/local`, stops to `/usr/local/share/aeolus`, `/etc/aeolus.conf`) - as a Dockerfile step and as a documented native step (needs sudo). Check its build deps on Ubuntu (zita-alsa-pcmi, clthreads, clxclient, libreadline) during implementation; `install_aeolus_kokki.sh` builds the kokkinizita libs if apt's are unsuitable.

### D4: Verification by workflow, per engine
One workflow per installed engine (add to a chain, no new errors, engine present in saved snapshot), native + Docker. Plus re-running the LV2 audit script in Docker once, since its plugin set differs (full guitarix build).

## Risks / Trade-offs

- [PureData externals list partly missing on Ubuntu] → install what exists, note the rest.
- [Aeolus build fails with Ubuntu's libs] → fall back to `install_aeolus_kokki.sh`; worst case Aeolus stays greyed out (still a correct state).
- [vlc pulls many deps into the image] → accepted; Internet Radio is an upstream default engine.
- [Grey check runs on every catalog load] → a handful of `shutil.which` calls, negligible.

## Migration Plan

Fork change pushed to `fork/vangelis`; user runs the apt/Aeolus install natively; Docker rebuild with `CACHEBUST`. Rollback: revert fork commit; packages can stay.

## Open Questions

- Does SooperLooper's GUI-less mode (`sooperlooper -q`) need anything else on the desktop (e.g. its own MIDI bindings file path)? Verified by the workflow.

## Findings during implementation

- **Aeolus segfault on x86_64 (fixed by patch):** the engine's `start()` sends `/retune` (freq `f`, temperament `i`); Aeolus crashed in `Model::proc_rank` at `scales[_itemp]`. gdb showed `retune(freq=0, temp=1138556928)` - 1138556928 is `0x43DD0000`, the bit pattern of 442.0f. Cause in `zynthian/aeolus` (`source/osc.cc`): `new M_ifc_retune(tosc_getNextFloat(msg), tosc_getNextInt32(msg))` - the evaluation order of function arguments is unspecified, GCC on x86_64 evaluates right-to-left, so the int is read from the float's slot (ARM happens to read left-to-right, hence fine on real hardware). Same pattern in `/recall_preset` and `/store_preset` (bank/preset swapped). `docker/patches/aeolus-osc-arg-order.patch` reads the arguments into locals first, like the fork's other handlers already do; applied in the Dockerfile and `install_native.sh`. Upstream PR candidate for `zynthian/aeolus`.
- **Aeolus: saving before configuring crashes the save (not fixed here):** after adding Aeolus, its bank screen asks for a keyboard configuration, then a temperament; only then does `start()` give each processor a `division`. Saving a snapshot in between raises `AttributeError: 'zynthian_processor' object has no attribute 'division'` in `get_extended_config()` and the save fails. Upstream zynthian-ui bug, independent of the desktop port; the workflow follows the real user path (pick both) instead. Follow-up candidate.
- **Slow engine starts vs. the workflow runner:** SooperLooper and Internet Radio switch to their preset/bank screen seconds after the log first goes quiet, so the runner's final snapshot save raced them. `assert: screen_is` now waits (bounded, 20 s) for the expected screen instead of checking once.
- **Native results:** all four engine workflows PASS natively with the patched Aeolus (Aeolus needed a third bank-screen step - after start() it re-shows the bank screen with the real bank list - and a new `screen_shown` assertion that waits for a screen to be shown *anew*, since `screen_is: bank` was already true before the slow start). Full native suite: 10/10 PASS.
- **Docker results:** suite 9/10; `add_aeolus` failed once (bank screen not shown within 20 s when it ran first against a freshly started container), PASS re-run alone - timing flakiness on a cold start, not a functional failure. LV2 load audit inside the image: 163/163 enabled LV2 plugins load.
- **Known weakness (raised by the user):** every engine workflow selects list entries *by index*. Installing or enabling another plugin shifts those indices; a test then picks a different entry. Engine-code asserts catch most of that, but not all (e.g. `select_unavailable_effect` only asserts the FluidSynth chain). Follow-up change: select by name.
