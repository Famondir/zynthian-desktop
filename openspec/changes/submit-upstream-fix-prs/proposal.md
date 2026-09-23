## Why

Five small bug-fix changes (`fix-fluidsynth-prompt-detection`, `fix-sfizz-dspreset-bank-root`, `fix-audio-in-stale-index`, `fix-chain-lock-deadlock`, `fix-autoconnect-empty-alias`) are each fully implemented, committed, and already pushed as topic branches to `Famondir/zynthian-ui` (the `fork` remote) - this project's own native/Docker builds already have every one of these fixes via `fork/vangelis`, with nothing further needed for that. The only task left open in each is identical and unrelated to this project's own functioning: opening a pull request against the wider project so the fix reaches other Zynthian users, not just this fork. That's a distinct, external, optional action (visible on a public repo, under the user's own identity) rather than more implementation work, so it doesn't belong holding those otherwise-complete changes open - collecting it here lets the five originals be archived now.

## What Changes

- Track the five pending "open PR" tasks (one per already-pushed topic branch) in a single place, so they can still be picked up later without blocking archival of the changes whose actual code work is done.
- Add one optional task for a sixth, not-yet-branched candidate: the VMPK entry added to `zynautoconnect.py`'s existing virtual-MIDI-hardware whitelist (part of `support-virtual-test-devices`, already on `fork/vangelis` directly, no topic branch yet) - unlike the knob-related fixes from the same session (which only affect this fork's own `device`/`device_cables` GUI styles, not present in - or relevant to - the upstream project at all), this whitelist mechanism already exists upstream and already recognizes several other virtual MIDI tools (`QmidiNet`, `jackrtpmidid`, `TouchOSC Bridge`), so adding VMPK to it is a plausible small upstream contribution.
- No PRs are actually opened by this change itself - each remains a tracked, pending task requiring explicit go-ahead when actually submitted (see design.md).

## Capabilities

### New Capabilities
(none - this tracks external process/contribution work, not a requirement or behavior of this project's own software)

### Modified Capabilities
(none)

## Impact

- No code changes in this repo or in `/zynthian/zynthian-ui`.
- Five existing topic branches on `Famondir/zynthian-ui` (`fix/fluidsynth-prompt-detection`, `fix/sfizz-dspreset-bank-root`, `fix/audio-in-stale-index`, `fix/chain-lock-try-finally`, `fix/autoconnect-empty-alias`) are the PR sources for five of the six tasks.
- The sixth (VMPK whitelist entry) has no topic branch yet - it was pushed directly to `fork/vangelis` as part of `722d8e7`, alongside an unrelated knob-feedback commit (`bfe70a9`) that stays out of scope here (see What Changes).
