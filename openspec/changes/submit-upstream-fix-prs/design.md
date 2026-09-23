## Context

Five fix changes each have identical final task: open a PR from an already-pushed `Famondir/zynthian-ui` topic branch, so the fix reaches the wider upstream project rather than staying fork-only. All five branches already exist and are already picked up by this project's own builds via `fork/vangelis` - nothing here affects this project's own functioning. This change exists purely to hold that tracking in one place instead of across five otherwise-complete changes, plus one optional sixth candidate (the VMPK whitelist entry, not yet on its own topic branch).

## Goals / Non-Goals

**Goals:**
- Track the six pending PR-submission tasks (five ready, one - VMPK - needs its own topic branch first) in one place.
- Let the five originating fix changes be archived without losing track of this remaining step.

**Non-Goals:**
- Actually opening any PR as part of applying this change. Opening a PR is a visible, external action on a public repository under the user's own GitHub identity - each one needs its own explicit go-ahead at the time it's actually submitted, not a blanket one here.
- Deciding whether to also PR the two touchkeypad/knob fixes from this session - already decided against (see proposal.md): they only affect this fork's own `device`/`device_cables` GUI styles, which don't exist in - or matter to - the upstream project.

## Decisions

- **One consolidated change, not five individually re-opened ones.** The underlying code work in each original fix change is done and verified; only the PR-submission step remains, and it's mechanically identical across all five (push already done, just needs `gh pr create` or the GitHub UI against the same target). Tracking five near-duplicate tasks in one place is clearer than five open changes that are otherwise 100% complete.
- **Explicit per-PR confirmation before submission, not a batch action.** Each task in tasks.md stays unchecked until the PR is actually opened, and opening one happens only when the user asks for that specific PR (or explicitly says "open all of them") - never inferred from this change simply existing or being applied.
- **VMPK entry kept separate from the knob fixes it was committed alongside.** `722d8e7` (VMPK whitelist) and `bfe70a9` (knob colour feedback) were both pushed directly to `fork/vangelis` in the same session, but only the former is a plausible upstream contribution (extends an existing, already-general whitelist mechanism upstream already maintains for other virtual MIDI tools) - the latter is scoped entirely to this fork's own desktop-port-specific GUI styles.

## Risks / Trade-offs

- [A PR against `zynthian/zynthian-ui` may sit unreviewed or get rejected/asked for changes - normal open-source contribution risk, not something to design around here] → No mitigation needed beyond being prepared to respond to review feedback when/if a PR is actually opened.
- [The VMPK topic branch doesn't exist yet - task 6 needs that done first before a PR is possible] → Noted as a sub-step of its own task rather than assumed already done.
