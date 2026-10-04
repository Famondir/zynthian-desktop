## 1. Diagnose (gates the rest - see design D1)

- [x] 1.1 Back up `/zynthian/config/engine_config.json` and the current last-state snapshot from `zynthian-my-data/snapshots/`
- [x] 1.2 Recover from the user's hung chains: start Zynthian once with the last-state snapshot moved aside, confirm the UI comes up clean (design D6)
- [ ] 1.3 Reproduce: add `GxReverb-Stereo` (installed + enabled) after a synth chain, play a note - record whether it loads and is audible. If it fails, capture the traceback and revisit design.md before continuing
- [x] 1.4 Reproduce: add a not-installed reverb (e.g. Dragonfly Hall Reverb) - capture the exact `KeyError: Plugin not found` traceback and what leaves the chain hung/unremovable

## 2. Install LV2 effect packages (native)

- [x] 2.1 `apt install dragonfly-reverb-lv2 calf-plugins x42-plugins zam-plugins mda-lv2 swh-lv2 lsp-plugins-lv2` on the native host
- [x] 2.2 Verify with `lilv` (venv python, runtime env sourced) that the new reverb URIs are found

## 3. Regenerate and curate the engine catalog

- [x] 3.1 Run `python3 zyngine/zynthian_lv2.py engines` from `/zynthian/zynthian-ui` with the runtime env sourced (design D3)
- [x] 3.2 Verify every `JV/*` entry's `URL` is in the `lilv` world; diff against the backup (count dropped/added entries, check user-set enabled flags survived, check MDA URI handling)
- [x] 3.3 Enable the default reverb set (design D7) with `EDIT=1`, restart Zynthian, confirm the "Reverb" category lists them

## 4. zynthian-ui fork fixes (`/zynthian/zynthian-ui`, branch `vangelis`)

- [x] 4.1 In `zynthian_lv2.load_engines()`, set `AVAILABLE` per `JV/*` entry from the `lilv` world, and add upstream-default entries that are enabled there but not installed, in memory only, with `AVAILABLE=False`; make sure `save_engines()` never writes them (design D4)
- [x] 4.1b In `zynthian_gui_engine.fill_list()`, sort unavailable entries to the end of each category and render them greyed out (new `color_unavailable`, see design findings); `select_action()` ignores them
- [x] 4.1c Info pane for greyed entries: "Not installed" plus apt package hint from a URI-prefix → package map for the curated families
- [x] 4.2 Make the processor-add path roll back cleanly on a missing plugin: no half-added processor, logged error, GUI message, chain still removable (location from 1.4) (design D5)
- [ ] 4.3 Make state/snapshot loading skip a processor whose plugin is missing, with a warning, and load the rest
- [ ] 4.4 Verify against a deliberately stale catalog entry (shows grey, not selectable) and a forced add of a missing plugin (clean rollback), then commit and **push** to `fork/vangelis`

## 5. Docker parity

- [x] 5.1 Add the same apt package list to `docker/Dockerfile`
- [x] 5.2 Add a catalog regeneration step after plugin installation in the Dockerfile (or rely on 4.1 at runtime - decide and document)
- [ ] 5.3 Rebuild the image with `CACHEBUST`, confirm a reverb can be added in the container

## 6. Verification

- [ ] 6.1 Add a workflow test (`workflow_testing/workflows/add_reverb_effect.yaml`, modelled on `add_amp_effect.yaml`) that adds a reverb to a synth chain; run it native + Docker
- [ ] 6.2 Live test with the user: FISA right hand → MIDI ch. 1 → FluidSynth distorted-guitar preset → reverb (no extra distortion effect); check for xruns at the real `JACKD_OPTIONS`. Mark done only after the user confirms by ear
- [ ] 6.3 Record follow-ups as separate changes: MIDI channel filter not isolating ch. 1, lost MIDI notes
