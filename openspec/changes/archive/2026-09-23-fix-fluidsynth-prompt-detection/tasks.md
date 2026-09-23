## 1. Fix

- [x] 1.1 Set `command_prompt = "> "` (plain text match) instead of a bracketed-paste-aware regex
- [x] 1.2 Change the "loaded SoundFont has ID" check from `re.match()` to `re.search()`
- [x] 1.3 Revert the earlier `proc_timeout = 120` band-aid now that detection is fixed (kept in `desktop-port-foundation`'s history, not part of this diff)
- [x] 1.4 Commit on the `vangelis` branch in the local fork
- [x] 1.5 Cherry-pick onto a clean topic branch off `origin/vangelis` and push to `Famondir/zynthian-ui` as `fix/fluidsynth-prompt-detection`
- [ ] 1.6 Open PR against `zynthian/zynthian-ui:vangelis` (link prepared, submission pending)
