## 1. Fix

- [x] 1.1 Change the bank-root extension check in `_get_preset_list()` from `filext.lower() == ".sfz"` to `filext[1:].lower() in cls.preset_fexts`
- [x] 1.2 Commit on the `vangelis` branch in the local fork
- [x] 1.3 Cherry-pick onto a clean topic branch off `origin/vangelis` and push to `Famondir/zynthian-ui` as `fix/sfizz-dspreset-bank-root`
- [ ] 1.4 Open PR against `zynthian/zynthian-ui:vangelis` (link prepared, submission pending)
