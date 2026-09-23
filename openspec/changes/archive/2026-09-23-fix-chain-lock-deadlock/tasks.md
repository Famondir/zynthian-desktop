## 1. Fix

- [x] 1.1 Wrap `rebuild_audio_graph()` body in `try:`/`finally: zynautoconnect.release_lock()`
- [x] 1.2 Wrap `rebuild_midi_graph()` body in `try:`/`finally: zynautoconnect.release_lock()`
- [x] 1.3 Commit on the `vangelis` branch in the local fork
- [x] 1.4 Cherry-pick onto a clean topic branch off `origin/vangelis` and push to `Famondir/zynthian-ui` as `fix/chain-lock-try-finally`
- [ ] 1.5 Open PR against `zynthian/zynthian-ui:vangelis` (link prepared, submission pending)
