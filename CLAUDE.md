# CLAUDE.md

## This project spans multiple locations, not just this repo

This repo (`Akkordeon/Zynthian`) holds the orchestration/dev-tooling layer: `docker/`, `run_zynthian_docker.sh`, `run_zynthian_vnc.sh`, `run_zynthian_webconf.sh`, `openspec/` planning docs, `.claude/` tooling. The actual Zynthian application and its native install live elsewhere, in their own separate git repos:

- **`/zynthian/zynthian-ui`** — the real application code (Python UI, `zynautoconnect`, touchkeypad, etc.). A git clone of the `Famondir/zynthian-ui` fork (remotes `fork`/`origin`), branch `vangelis`. **Code fixes for the desktop port go here, not into this repo** — e.g. `zynautoconnect/zynthian_autoconnect.py`, `zyngui/zynthian_gui_touchkeypad_v5.py`. Commit changes there directly; this repo's `openspec/changes/*` only document/plan them.
- **`/zynthian/zynthian-webconf`** — the browser config UI (Tornado app; imports `zyngine`/`zynconf`/`zyngui` from `zynthian-ui` directly, so it always runs alongside a working `zynthian-ui` checkout). A git clone of the `Famondir/zynthian-webconf` fork, branch `vangelis`, patched to authenticate against `ZYNTHIAN_WEBCONF_PASSWORD` instead of upstream's PAM-against-system-root-account login (this desktop port never runs as root; see `openspec/changes/enable-webconf-access/design.md`). Code fixes go there directly, same as `zynthian-ui`. Started via `run_zynthian_webconf.sh` for the native install.
- **`/zynthian/config/zynthian_envars_custom.sh`** — host-local runtime config (`JACKD_OPTIONS`, hotplug settings, etc.) for the native install on this machine. **Not version controlled anywhere** (matches real Zynthian hardware's own convention - it's runtime state, not source). A reference copy is kept at `config/zynthian_envars_custom.sh.example` in this repo so the tuning behind it isn't only findable on one machine, but that copy is not auto-sourced from here.
- **`/zynthian/run_zynthian.sh`** — the native launcher script, not version controlled. Mirrors `docker/entrypoint.sh`'s role for the native install.
- **`/zynthian/zynthian-sys`**, **`/zynthian/zyncoder`**, **`/zynthian/zynthian-data`** — upstream `zynthian/*` repos, unmodified reference material (e.g. `zynthian-sys`'s systemd units and per-hardware `zynthian_envars_*.sh` files are useful reference for how real hardware configures things, like the `-d hw:sndrpihifiberry` pattern that motivated `fix-audio-hotplug-support`).
- **`/zynthian/venv`, `zynthian-my-data`, `zynthian-plugins`, `zynthian-sw`** — Python venv / data / build directories, not source, not version controlled.

The Docker image (`docker/Dockerfile`) clones its own fresh copy of `zynthian-ui` and `zynthian-webconf` (same forks/branches) at build time - it does **not** use `/zynthian/zynthian-ui` or `/zynthian/zynthian-webconf`, which are only relevant to the native install.

When implementing an `openspec` change that touches application behavior, check whether the actual edit belongs in `/zynthian/zynthian-ui` (or `/zynthian/config`) rather than in this repo.
