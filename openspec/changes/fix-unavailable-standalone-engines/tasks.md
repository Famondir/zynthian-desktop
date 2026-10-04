## 1. Availability for standalone engines (`/zynthian/zynthian-ui`, `zyngine/zynthian_lv2.py`)

- [x] 1.1 Add `standalone_engine_requires` (program or systemd unit + install hint per engine code) and apply it in `mark_unavailable_engines()` (design D1)
- [x] 1.2 Verify natively before installing anything: SL, AE, IR, PD, MD greyed out with the right hint; FS/ZY/SF/BF unchanged; selecting SL only shows the toast, no `Can't start engine` error (native: add_sooperlooper refuses SL before install - no `Can't start engine` logged, no traceback)

## 2. Install the engines (native - needs the user's sudo)

- [x] 2.1 `apt install sooperlooper vlc vlc-plugin-jack` and PureData (`puredata puredata-core puredata-utils puredata-import python3-yaml` + the upstream `pd-*` externals that exist on Ubuntu 24.04 - none dropped, all exist on 24.04) (design D2)
- [x] 2.2 Build and install Aeolus from `zynthian/aeolus` branch `zynthian` like `install_aeolus.sh` (deps, `/usr/local/share/aeolus/stops`, `/etc/aeolus.conf`) (design D3)
- [ ] 2.2b Apply `docker/patches/aeolus-osc-arg-order.patch` (x86_64 `/retune` segfault, see design findings) to the native Aeolus build and reinstall
- [ ] 2.3 Restart Zynthian; SL, AE, IR, PD shown normally; MD still greyed

## 3. Docker

- [x] 3.1 Add the same apt packages and an Aeolus build step to `docker/Dockerfile`
- [ ] 3.2 Rebuild with `CACHEBUST`; re-run the LV2 load audit inside the container

## 4. Verification

- [ ] 4.1 Add workflows that add SooperLooper, Aeolus, Internet Radio and PureData to a chain (assert engine code in the saved snapshot); run native + Docker
- [ ] 4.2 Commit and **push** the fork change; commit this repo
