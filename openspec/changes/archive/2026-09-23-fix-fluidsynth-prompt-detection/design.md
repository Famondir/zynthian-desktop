## Context

Zynthian drives FluidSynth's interactive CLI via `pexpect`, matching its `"> "` prompt to know when a command has finished. This is the same interactive-subprocess technique already used successfully for sfizz/jalv. FluidSynth loading a soundfont looked reliably slow (minutes) and then time out - it was tempting to just raise the timeout, and that was tried first (`proc_timeout = 120`). It turned out to be a misdiagnosis: the load itself was fast, but a broken prompt-detection regex made the code think the load had failed, so it silently retried the *entire* load from scratch, repeatedly - `proc_timeout` was masking a detection bug, not compensating for genuinely slow I/O.

## Goals / Non-Goals

**Goals:**
- Detect FluidSynth's prompt/output reliably regardless of the exact bracketed-paste escape layout emitted by a given readline/libedit version.

**Non-Goals:**
- Re-introducing a longer `proc_timeout` - measured to be unnecessary once detection is fixed (a 382MB soundfont loads in well under a second cached, a few seconds cold), so the base engine's 30s default is kept.

## Decisions

- Match plain `"> "` text for the prompt instead of a regex modeling the exact escape sequence - the same pattern sfizz/jalv already use successfully. Earlier attempts tried to model the escape sequence precisely and kept breaking on different commands' slightly different escape/CR layouts.
- Use `re.search()` instead of `re.match()` for the "loaded SoundFont has ID" check, since `.match()` anchors at position 0 and fails when a line has a leading ANSI escape/CR before the text.
- Drop the `proc_timeout = 120` override added while this was still misdiagnosed as a slow-load problem (see `desktop-port-foundation`'s history) - kept out of this change's scope since it's a revert, not a new fix, but tracked as part of the same investigation.

## Risks / Trade-offs

- Matching plain `"> "` is less precise than a full escape-sequence-aware regex, but is proven robust in sfizz/jalv and avoids the maintenance burden of chasing every terminal/readline version's exact escape layout.
