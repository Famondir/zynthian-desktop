## Context

Workflow steps reach the UI through OSC CUIAs (`/CUIA/SELECT <i>`, `/CUIA/ARROW_RIGHT`, …), sent by `workflow_testing/injection.py`. The runner gets no reply. Its only feedback is the UI log, which it reads after each step through `log_diff` (no new ERROR lines) and through the `SHOW SCREEN '<name>'` lines.

Today's `cuia_select` and `cuia_select_action` swallow `AttributeError`/`TypeError`. While the UI is busy, `osc_cb_all` drops CUIAs and only logs that at debug level. An out-of-range or shifted index therefore never produces a visible failure.

Positions are unstable for several reasons:
- the engine list is sorted by title and puts unavailable entries last;
- Audio-FX and MIDI-Tool lists add a "None" row at index 0;
- `cat_index` carries over between engine-screen visits;
- the native host and Docker have different package sets.

The selector base class already has `select_listbox_by_name(name)`. Nothing calls it from a CUIA, it fails silently, and it doesn't work for grid screens (`zynthian_gui_selector_grid` has no listbox and keeps its entries in `self.config[i]["title"]`).

## Goals / Non-Goals

**Goals:**
- Select engines, categories and named menu entries by visible label, with a positive confirmation and a loud failure.
- Make every engine workflow independent of package set and sort order.
- Turn `select_unavailable_effect` into a real negative test.

**Non-Goals:**
- Name selection for non-list screens (mixer, control screens, touchkeypad).
- Fuzzy, substring or case-insensitive matching. An exact label (with whitespace normalised) is what we want to pin down.
- Fixing upstream's silent `cuia_select` behaviour. Positional `select:` stays as it is.
- Asserting which entry is highlighted after a plain positional `select:`.

## Decisions

### 1. Two new fork CUIAs, matching on what the user sees
`cuia_select_name(params)` and `cuia_select_category(params)` live in `zyngui/zynthian_gui.py`. They delegate to a new `find_index_by_name(name)` on the current screen object:
- `zynthian_gui_selector`: searches `list_data[i][2]` (the label shown in the listbox, which is exactly what `fill_listbox` inserts) and skips separators (`list_data[i][0] is None`);
- `zynthian_gui_selector_grid`: searches `config[i]["title"]`;
- engine screen category: searches `engine_cats` and calls the existing `set_cat()`.

Labels are compared after `" ".join(label.split())`, so the grid's `"MIDI\n+\nAudio"` is addressable as `MIDI + Audio`.

Alternatives considered:
- Reusing `select_listbox_by_name`: it reads the Tk listbox, doesn't exist on grids and swallows errors.
- Selecting by engine key (`JV/GxAmplifier-X`) instead of title: more stable against title renames, but doesn't work for menu entries or categories. Keeping one concept for all screens is simpler, and a renamed title failing loudly is fine.

### 2. Feedback through the log, not a reply channel
- On success the CUIA logs at INFO: `SELECT_NAME '<text>' => <index>` (or `SELECT_CATEGORY …`).
- On a missing or ambiguous label it logs at ERROR: `SELECT_NAME '<text>' not found` / `… ambiguous: [i, j]`.

The runner waits up to `_SCREEN_WAIT_S` for either line in the new log lines of this step. It fails on the error line (the existing `no_new_errors` check would catch it anyway), and it also fails on timeout, which covers a CUIA dropped while busy.

Alternative considered: an OSC reply to the sender. This needs a server socket in the runner and a protocol change to zynthian-ui. The log channel already exists and is exactly how `screen_is`/`screen_shown` work.

### 3. Strict ambiguity
Two identical labels on one screen make the step fail instead of choosing the first. Silently choosing is exactly the bug class this change removes. If a real screen has legitimate duplicates, the workflow has to be written differently.

### 4. Positional `select:` stays for intrinsically positional choices
Examples are "first free MIDI channel" and "first bank/preset" of an engine, where any entry is valid and the label depends on the environment. This rule goes into the runner docstring and the spec. `arrow:` steps are dropped from the engine workflows entirely, because `category:` replaces them.

### 5. The negative test needs a name that is greyed in *both* environments
The greyed Reverb entry differs between the two environments (DuskVerb natively, MVerb in Docker). The workflow names one engine that the Docker image does not install and that is also absent on the native host. That engine is picked from both catalogs during implementation. If no common engine exists, `select_name` accepts a per-environment mapping (`{native: …, docker: …}`), resolved by the runner from `--env`. The assertion is `chain_lacks_engine: <key>` plus the existing `chain_has_engine: FS`.

## Risks / Trade-offs

- [Upstream renames a title or category] → The workflow fails loudly with the missing label. That is intended: a one-line YAML fix instead of a silently wrong test.
- [Same title in two categories] → Matching is only within the current category, so this can't happen there. Across the whole list the strict-ambiguity rule catches it.
- [The fork diverges further from upstream] → Two small additive handlers with no change to existing behaviour. This is a good PR candidate to remove the divergence later.
- [Log line formats become an implicit protocol] → The success/error formats are pinned in one place in the runner (a regex constant) and documented in the CUIA docstrings.

## Migration Plan

1. Implement the fork CUIAs, commit and **push** (Docker clones the pushed fork).
2. Add the runner steps and assertion; convert the workflows one by one, running each natively (with snapshot backup/restore as usual).
3. Run the native suite and the Docker suite after a rebuild.

Rollback: revert the workflow YAMLs. The CUIAs are harmless when unused.

## Open Questions

- Which greyed Reverb (or other) engine is unavailable in both environments? This is resolved during implementation (decision 5).
