## Context

Use case (corrected by the user during implementation): FISA Suprema right hand → MIDI ch. 1 → FluidSynth chain with an already-distorted guitar preset → reverb. The distortion comes from the FluidSynth preset itself - no Guitarix/NAM distortion is in the signal path (a NAM chain existed but was muted). The left-hand accompaniment is a separate audio-input chain without effects. What's missing is only the reverb after FluidSynth.

Exploration findings (2026-10-04, native host, Ubuntu 24.04):

- `/zynthian/config/engine_config.json` has 1128 entries / 886 `Audio Effect`s - a verbatim copy of upstream's RPi catalog (`zynthian-sys/config/engine_config.json`), never regenerated on this host.
- `lilv` (via `LV2_PATH` from `zynthian_envars_custom.sh`) finds 98 plugins: Guitarix (in `~/.lv2`), NAM, TONE3000, x42 b_synth/b_whirl, Carla utilities. Only **75** catalog effects are installed.
- Reverbs installed: `GxReverb-Stereo` (enabled), `GxMultiBandReverb`, `Gxroom_simulator`, `Gxshimmizita`, `GxZita_rev1-Stereo` (all disabled). Every other enabled reverb in the list (Dragonfly ×4, Calf Reverb, MVerb, MaGigaverb, TAL ×3, Roomy, Shiroverb, DuskVerb, GVerb, MDA Ambience, x42 IR Convolver, …) is **not installed**.
- `zynthian_lv2.load_engines()` reads the catalog file as-is; `get_engines_by_type()` doesn't filter by installation. Selecting a missing plugin → `KeyError: Plugin not found` (already observed for synths in `add-workflow-smoke-testing`'s design.md, left out of scope there).
- `generate_engines_config_file()` builds the catalog **only** from `world.get_all_plugins()`, reusing metadata of existing keys - so regeneration naturally drops not-installed entries.
- The autoconnect-lock `try/finally` fix (`fix-chain-lock-deadlock`) is present and pushed in the fork, so the user's "hung, unremovable chains" is not that bug - cause still to be diagnosed.
- apt candidates exist for `dragonfly-reverb-lv2`, `calf-plugins`, `x42-plugins`, `zam-plugins`, `mda-lv2`, `lsp-plugins-lv2`, `swh-lv2`.

Open contradiction: `GxReverb-Stereo` *is* installed and enabled, yet the user reports "no reverb works". Either they only tried missing ones, or there is a second, jalv-level problem. Must be reproduced first.

## Goals / Non-Goals

**Goals:**
- Several working reverbs selectable in the UI, natively and in Docker.
- Catalog reflects reality - no more selectable-but-missing plugins; missing upstream plugins stay visible, greyed out, as an install hint.
- A failed plugin add never leaves a hung/unremovable chain.

**Non-Goals:**
- MIDI channel filtering (left hand reaching the guitar chain), lost MIDI notes - separate change(s).
- Building upstream's full RPi plugin set from source (TAL, DuskVerb, Aether, …).
- Reverb send/return bus architecture - a reverb processor at the end of the FluidSynth guitar chain is enough for now.

## Decisions

### D1: Diagnose first with an already-installed reverb
Reproduce with `GxReverb-Stereo` before installing anything. If it fails too, the problem is in the jalv/engine layer (custom-built jalv, port setup, presets cache) and package installation alone won't help - the design must be revisited. *Alternative*: install packages first and see - rejected, it would hide a second bug behind a changed plugin set.

### D2: apt packages, not source builds
Ubuntu 24.04 ships the main LV2 reverb families. apt is reproducible, cheap to put into the Dockerfile, and matches how the rest of the desktop port picks dependencies. Curated set: `dragonfly-reverb-lv2` (Hall/Room/Plate/Early - best fit for guitar), `calf-plugins`, `x42-plugins`, `zam-plugins` (ZamVerb), `mda-lv2`, `swh-lv2` (GVerb, Plate), `lsp-plugins-lv2`. *Alternative*: zynthian-sys's per-plugin source recipes - rejected for now: slow builds, and some recipes are known broken (`install_nam.sh`).

`lsp-plugins-lv2` is large and adds many new catalog entries; they come in disabled (`is_engine_enabled(key, False)`), so they don't clutter the UI. Can be dropped if disk/scan time hurts.

### D3: Regenerate the catalog via upstream's own entry point
Run `python3 zyngine/zynthian_lv2.py engines` (→ `update_engine_defaults()` → `generate_engines_config_file()`) with the runtime env sourced. It merges in upstream defaults (good titles/categories/enabled flags for plugins upstream knows), keeps user edits (`EDIT` flag), drops everything not in the `lilv` world, and builds presets caches for new plugins. Back up the old file first. *Alternative*: hand-filter the JSON - rejected, duplicates logic that already exists.

URI caveat: Debian's `mda-lv2` uses `drobilla.net` URIs, upstream's catalog the `moddevices.com` ones. Keys are `JV/<plugin name>`, so if names match, metadata carries over with the new URL; if not, they show up as new, disabled entries. Either way it's correct - just check the result.

### D4: Mark unavailable plugins instead of hiding them (fork)
User request: the user wants to see what could be installed, so missing plugins stay visible. Two sources, kept separate:

- **Catalog file** (`$ZYNTHIAN_CONFIG_DIR/engine_config.json`): installed only, exactly as upstream's `generate_engines_config_file()` produces it (D3). Not polluted with phantom entries, so regeneration stays upstream-compatible.
- **Upstream default catalog** (`$ZYNTHIAN_SYS_DIR/config/engine_config.json`, already read by `update_engine_defaults()`): the "known universe".

In `load_engines()`, after `init_lilv()`: every `JV/*` entry gets `AVAILABLE = URL in lilv world`. Entries from the upstream default catalog that are `ENABLED` there but missing locally are added in memory (never saved: `save_engines()` drops them) with `AVAILABLE=False`. Upstream's *disabled* entries are left out, otherwise every category gets hundreds of grey rows (LSP alone has ~200).

`zynthian_gui_engine.fill_list()` sorts unavailable entries after the available ones in each category and renders them with `color_tx_off` (the colour the selector already uses for inactive rows). `select_action()` ignores them: no processor, no error. The info pane shows the description plus "Not installed" and an apt package hint from a small URI-prefix → package map covering the curated families (e.g. `urn:dragonfly:` → `dragonfly-reverb-lv2`, `http://calf.sourceforge.net/` → `calf-plugins`); no hint for the others.

This also makes a stale catalog copied in later harmless (e.g. Docker): stale entries just turn grey. *Alternatives*: (a) hide missing entries completely - rejected per the user's request; (b) keep phantom entries in the catalog file - rejected, regeneration would delete them again and they'd spread into backups/Docker; (c) a config toggle to hide grey entries - not now, can be added if the lists get too long.

### D5: Graceful failure on missing plugin (fork)
Find where `KeyError: Plugin not found` surfaces when a processor is added (jalv engine `__init__`/`start`, plugin port lookup) and make the add path roll back: remove the half-added processor, log, show a GUI message. Same handling during state/snapshot load (skip that processor). Exact location to be found by reproducing - not guessed here.

### D6: Recovery for the user's current broken state
Before the fix lands, document how to get out: start once with a clean state (move the last-state snapshot in `zynthian-my-data/snapshots/` aside) after backing it up.

### D7: Default enabled reverbs
After regeneration, enable (via webconf Engines page or a small scripted `ENABLED` edit with `EDIT=1`, so later regenerations keep it) at least: Dragonfly Hall, Dragonfly Room, Dragonfly Plate, Calf Reverb, ZamVerb, GxReverb-Stereo, GxZita_rev1-Stereo. Final list = whatever actually passes the live test.

## Risks / Trade-offs

- [GxReverb-Stereo also fails → second root cause in jalv layer] → D1 gates everything; revise design if so.
- [Calf/LSP pull GTK UI libs, bigger image] → acceptable on desktop; jalv runs headless, UIs aren't used.
- [Regeneration resets an enabled flag the user set] → back up catalog; use `EDIT=1` for our own enables; diff before/after.
- [High-CPU reverbs (LSP Room Builder, convolution) cause xruns at the current JACK buffer] → test with the real `JACKD_OPTIONS`; prefer algorithmic reverbs for the default set.
- [Docker catalog drift: image ships its own catalog copy] → regenerate in the Dockerfile after apt install; D4 marks stale entries grey at runtime.
- [Grey entries make long lists (e.g. "Synth") harder to scroll on the small screen] → only upstream-*enabled* entries, always sorted to the end; config toggle as a follow-up if needed.
- [Webconf's engine page still shows only the catalog file] → acceptable; webconf greying is a possible follow-up.

## Migration Plan

1. Back up `/zynthian/config/engine_config.json` and the last-state snapshot.
2. apt install → regenerate catalog → enable defaults → restart Zynthian.
3. Fork fixes (D4, D5) committed and **pushed** to `Famondir/zynthian-ui` `vangelis`.
4. Dockerfile updated, image rebuilt with `CACHEBUST`.
Rollback: restore the catalog backup; `apt remove` the packages.

## Open Questions

- Does `GxReverb-Stereo` work right now? (decides D1)
- Exact error/traceback when a chain "hangs" - is it the `KeyError` path or something else?
- Is `lsp-plugins-lv2` worth its size, or is Dragonfly + Calf + Zam + Gx enough?

## Findings during implementation

- **Why the user's chain hung (task 1.4, from code + the saved state):** the user's `last_state.zss` chain 3 (FluidSynth, MIDI ch. 1) held `JV/Tal-Reverb-II`, `JV/DuskVerb`, `JV/GVerb` - none installed then. Two upstream bugs combine: `chain_manager.start_engine()` doesn't catch the jalv constructor's `KeyError: Plugin not found`, so it escapes `add_processor()` past its `end_busy()` (UI stuck busy); and `add_processor()` inserts the processor into the chain *before* starting the engine, and on failure only drops it from `self.processors`, never from the chain - an engine-less slot that then gets saved into the state. Fixed in `add_processor()`: try/except around `start_engine()`, and on failure `chain.remove_processor()` + `end_busy()`. Both callers (GUI "Failed to create processor", state restore skipping the slot) already handle a `None` return, which covers the "saved state with an unavailable plugin still loads" requirement too. Recovery for the user's existing state (D6) was done by removing just those three slots (+ their `zs3` entries) from `last_state.zss`, keeping the FluidSynth chain, instead of moving the whole state aside.
- **Catalog regeneration result (task 3.2):** 1128 → 616 entries (601 LV2, all resolvable), 535 stale entries dropped, 23 new (Carla utilities), no enabled flag changed. Debian's `mda-lv2` (drobilla.net URIs) mapped onto upstream's `JV/MDA *` keys by name as hoped. 175 upstream-enabled plugins remain not installed and show greyed out.
- **Install hints only where they're right:** after installing the packages, the still-missing plugins of those families mostly come from elsewhere (LSP chorus/matcher = newer LSP than Ubuntu's, `ZamNoise`, x42 `avldrums` = separate `avldrums.lv2` package). `get_install_hint()` therefore names a package only if *no* plugin of that URI family is installed yet; otherwise the info pane just says "Not installed".
- **Greyed colour:** `color_tx_off` (#e0e0e0) is indistinguishable from normal text (#fff) and `color_off` is unreadable on the list background, so a new `color_unavailable` (#8a929d, overridable via `ZYNTHIAN_UI_COLOR_UNAVAILABLE`) was added.
- **`add_amp_effect.yaml` never tested an amp:** it selected chain-options index 1 = "Add MIDI-FX" (index 0 is the "> PROCESSORS" header row), so it added the SysEx MIDI tool - which is exactly why its `chain_has_engine: SX` assert passed. GxPlexi, its intended target, isn't even installed natively (likely also the real cause of its "silent in Docker, no Starting Engine line" note). Fixed to index 2 + `GxAmplifier-X` + a real assert; the new reverb workflows use the same corrected index.
- **Docker:** the image seeds `engine_config.json` from zynthian-sys exactly like the native install did, so it gets the same apt packages plus a build-time `zynthian_lv2.py engines` regeneration. Runtime greying alone wouldn't be enough there - upstream's MDA entries carry `moddevices.com` URIs and would show greyed although `mda-lv2` is installed. ZamVerb/GxZita are only enabled natively (D7 used `EDIT=1` on the host catalog); Docker gets upstream's enabled set, which already has 11 working reverbs.
