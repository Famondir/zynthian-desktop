## 1. Ready to submit (topic branch already pushed to `fork`)

- [ ] 1.1 Open PR: `Famondir/zynthian-ui:fix/fluidsynth-prompt-detection` → `zynthian/zynthian-ui:vangelis` (from `fix-fluidsynth-prompt-detection`)
- [ ] 1.2 Open PR: `Famondir/zynthian-ui:fix/sfizz-dspreset-bank-root` → `zynthian/zynthian-ui:vangelis` (from `fix-sfizz-dspreset-bank-root`)
- [ ] 1.3 Open PR: `Famondir/zynthian-ui:fix/audio-in-stale-index` → `zynthian/zynthian-ui:vangelis` (from `fix-audio-in-stale-index`)
- [ ] 1.4 Open PR: `Famondir/zynthian-ui:fix/chain-lock-try-finally` → `zynthian/zynthian-ui:vangelis` (from `fix-chain-lock-deadlock`)
- [ ] 1.5 Open PR: `Famondir/zynthian-ui:fix/autoconnect-empty-alias` → `zynthian/zynthian-ui:vangelis` (from `fix-autoconnect-empty-alias`)

## 2. Optional (needs its own topic branch first)

- [ ] 2.1 Cherry-pick the VMPK whitelist entry (part of commit `722d8e7`, alongside the unrelated knob-colour commit `bfe70a9` - separate just this one) onto a clean topic branch off `origin/vangelis`, e.g. `fix/vmpk-midi-whitelist`, and push it to `Famondir/zynthian-ui`
- [ ] 2.2 Open PR: `Famondir/zynthian-ui:fix/vmpk-midi-whitelist` → `zynthian/zynthian-ui:vangelis`

Each task above requires explicit go-ahead at the time it's actually done - see design.md's Non-Goals. Nothing here is submitted automatically by this change existing.
