## Context

This is the second of two lock-orphaning bugs found in the same area (see `fix-autoconnect-empty-alias`): a hand-rolled lock (`zynautoconnect.acquire_lock()`/`release_lock()`) gets permanently stuck whenever an unrelated exception fires between acquire and release, because the release call only happens at the natural end of the function.

## Goals / Non-Goals

**Goals:**
- Guarantee the autoconnect lock is released no matter how the function body exits (normal return or exception).

**Non-Goals:**
- Replacing the hand-rolled lock with a context manager/`with` statement across the whole codebase - out of scope for a minimal, upstreamable fix; noted as a possible future cleanup.

## Decisions

- Use `try/finally` rather than a context manager, to keep the diff minimal and match the existing code style (the surrounding code doesn't use context managers for this lock elsewhere).

## Risks / Trade-offs

- `finally` runs even if the lock was never actually acquired (e.g. `acquire_lock()` returned False and the function already returned early) - not a concern here since `release_lock()` on an already-released lock is a no-op in this codebase.
