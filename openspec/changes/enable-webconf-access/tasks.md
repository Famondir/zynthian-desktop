## 1. Research zynthian-webconf's actual startup/config

- [x] 1.1 Clone `zynthian/zynthian-webconf` to a scratch location and read `zynthian_webconf.sh` plus its config/port handling to confirm: entry point command, default port/bind address, and whether the port is overridable via env var or config file.
- [x] 1.2 Confirm the pip dependency list (`tornado`, `tornadostreamform`, `websocket-client`, `tornado_xstatic`, `terminado`, `xstatic`, `XStatic_term.js`) against the repo's actual `requirements.txt`/setup docs, and note any missing/extra packages.
- [x] 1.3 Record findings in design.md's Open Questions section (update or resolve them) before proceeding if reality differs from the port-80/`NET_BIND_SERVICE` assumption.

## 2. Patch zynthian-webconf's login for the desktop port

- [x] 2.1 Confirm the fork `https://github.com/Famondir/zynthian-webconf` (branch `vangelis`) exists and is clean (matched upstream HEAD before patching).
- [x] 2.2 Patch `lib/login_handler.py`: replace PAM/root authentication with a check against `ZYNTHIAN_WEBCONF_PASSWORD` (constant-time compare), keeping the same `set_secure_cookie("user", "root", ...)` session so downstream `@tornado.web.authenticated` handlers are unaffected.
- [x] 2.3 Patch `lib/security_config_handler.py`: remove the now-unused `PAM`/`bcrypt` imports (module-level `import PAM` would otherwise crash webconf at startup) and disable the password-change sub-flow (VNC/WIFI-hotspot/filebrowser password rewrites - none applicable here) with a message pointing at `ZYNTHIAN_WEBCONF_PASSWORD`.
- [x] 2.4 Commit and push the patch to `Famondir/zynthian-webconf`'s `vangelis` branch.
- [x] 2.5 (found during task 6.5's live test) Patch `lib/dashboard_handler.py`'s `get_i2c_chips()` to tolerate a missing `i2cdetect`/I2C bus - it's called at module import time via `wiring_config_handler.py` and crashed webconf at startup on a machine with no GPIO expansion hardware. Committed as `a6addce`, pushed to `vangelis`.
- [x] 2.6 (found during task 6.6's live test) Patch `templates/dashboard_block.html`: two separate spots checked `'value' in info`/`'value' in i` (dict key presence) instead of whether the value itself is `None` - true for env-var-derived dashboard fields like `DISPLAY_NAME` on a desktop install, crashing the authenticated dashboard page (`GET /` -> 500) both via `escape()` and via the "Report Issue" link's `urllib.parse.quote()`. Fixed both call sites to check `info.get('value') is not None` (matching `config_block.html`'s existing correct pattern elsewhere in the same repo). Committed as `f9effdf` and `820fccd`, pushed to `vangelis`.

## 3. Docker image provisioning

- [x] 3.1 Add a `git clone -b vangelis https://github.com/Famondir/zynthian-webconf.git` step to `docker/Dockerfile`, alongside the existing `zynthian-ui`/`zyncoder`/`zynthian-sys`/`zynthian-data` clones, into `$ZYNTHIAN_DIR/zynthian-webconf`.
- [x] 3.2 Add its pip dependencies to the existing venv install step in `docker/Dockerfile`: `tornado`, `tornadostreamform`, `websocket-client`, `tornado_xstatic`, `terminado`, `xstatic`, `XStatic_term.js`, plus the extra ones found in task 1.2 (`jsonpickle`, `mido`, `mutagen`, `py7zr`, `rarfile`, `requests`). Do **not** add `PAM`/`python-pam` or `bcrypt` - no longer imported anywhere after task 2's patch.
- [x] 3.3 Generate the self-signed TLS cert webconf requires at `$ZYNTHIAN_DIR/zynthian-webconf/cert/{key.pem,cert.pem}` during the image build (`openssl req -x509 -newkey rsa:4096 ... -days 36500 -nodes`, mirroring `zynthian-sys/sbin/regenerate_keys.sh`'s own command) - `zynthian_webconf.py`'s unconditional `app.listen(443, ...)` crashes the whole process at startup without these files.
- [x] 3.4 Build the image and verify `$ZYNTHIAN_DIR/zynthian-webconf` (+ `cert/`) and its deps are present (`docker run --rm <image> ls /zynthian/zynthian-webconf/cert`, `docker run --rm <image> /zynthian/venv/bin/pip show tornado`). Verified across 3 rebuilds (first two picked up stale fork commits mid-flight as tasks 2.5/2.6 landed; final rebuild confirmed `820fccd`, cert, and all pip deps present).
- [x] 3.5 (found while verifying the built image directly, before task 4.3/5.5) `lib/upload_handler.py` unconditionally `os.mkdir()`s a `tmp/` dir inside the webconf checkout at *import* time - crashed with `PermissionError` under the container's non-root user, since the checkout is owned by `root` from the build. Extended the existing `chmod -R a+rwX` scaffolding step in `docker/Dockerfile` (previously just `$ZYNTHIAN_MY_DATA_DIR`/`$ZYNTHIAN_CONFIG_DIR`) to also cover `$ZYNTHIAN_DIR/zynthian-webconf`.

## 4. Docker container startup and lifecycle

- [x] 4.1 In `docker/entrypoint.sh`, export `ZYNTHIAN_WEBCONF_PASSWORD` (default if unset, e.g. `zynthian`, documented as change-me) and start webconf (`$ZYNTHIAN_DIR/zynthian-webconf/zynthian_webconf.sh`) as a background process, logging to `/tmp/zynthian_webconf.log` and capturing its PID, before `exec python3 zynthian_main.py`.
- [x] 4.2 Add the webconf PID to the existing `cleanup()` trap's `kill -9` list.
- [ ] 4.3 Verify webconf's process comes up on container start and is cleanly killed on container stop (check `/tmp/zynthian_webconf.log`, check no orphaned process after `docker stop`). Partially checked via ad-hoc `docker run` reproductions (confirmed webconf's own login+dashboard flow works once given the same config mount/scaffolding `run_zynthian_docker.sh` always provides - two of those ad-hoc attempts hit unrelated `FileNotFoundError`/`AttributeError` crashes caused by *omitting* that mount or `DISPLAY`, not by webconf itself). Needs a real `run_zynthian_docker.sh` run (proper X11/noVNC) for full confirmation, same as task 5.5.

## 5. Docker host reachability

- [x] 5.1 In `run_zynthian_docker.sh`, add `-p <host_http_port>:80 -p <host_https_port>:443` to the `docker run` invocation (both listeners are unconditional in webconf - see design.md), with configurable host ports following the existing `VNC_PORT`/`NOVNC_PORT` env-var-with-default pattern.
- [x] 5.2 Add `--cap-add=NET_BIND_SERVICE` to the `docker run` invocation so the non-root container user (`--user "$(id -u):$(id -g)"`) can bind ports 80/443.
- [x] 5.3 Pass `ZYNTHIAN_WEBCONF_PASSWORD` through to the container (`-e`, defaulting/documented same as task 4.1) so the host operator knows the login credential.
- [x] 5.4 Document the webconf URL (host ports) and the default password/how to change it in `run_zynthian_docker.sh`'s header comment, matching how noVNC's URL/behavior is already documented there.
- [ ] 5.5 Manually verify: run `run_zynthian_docker.sh`, open `https://localhost:<host_https_port>` (or the HTTP port) in a host browser, log in with the password, confirm the dashboard loads, and confirm the serving process is non-root inside the container (`docker exec <container> ps aux`).

## 6. Native install provisioning and startup script

- [x] 6.1 Create `run_zynthian_webconf.sh` in this repo (sibling to `run_zynthian_vnc.sh`), with a header comment explaining its role, that it runs independently of `run_zynthian_vnc.sh`/`/zynthian/run_zynthian.sh`, the network-exposure implications, and the default password (matching `run_zynthian_docker.sh`'s comment style).
- [x] 6.2 Implement idempotent provisioning: clone `Famondir/zynthian-webconf` (`vangelis`) into `/zynthian/zynthian-webconf` only if missing, then `pip install` its dependencies (same list as task 3.2) into `/zynthian/venv`.
- [x] 6.3 Generate the self-signed cert at `/zynthian/zynthian-webconf/cert/{key.pem,cert.pem}` if missing (same `openssl` command as task 3.3).
- [x] 6.4 Implement startup: require `authbind` (native has no `--cap-add` equivalent for binding ports 80/443 as non-root - see design.md's follow-on decision; `setcap` on the venv's `python3` was rejected since it's a symlink to the system interpreter), activate `/zynthian/venv`, export `ZYNTHIAN_WEBCONF_PASSWORD` (default/documented, overridable via env), and `exec authbind --deep ./zynthian_webconf.sh`.
- [x] 6.5 Manually verify: run the script on a machine without `/zynthian/zynthian-webconf` present, confirm it clones/installs/generates the cert/starts; run it again and confirm it skips provisioning and starts directly. Verified live on this machine - first run cloned/installed/generated the cert; found and fixed tasks 2.5/2.6 along the way; subsequent runs skip straight to starting.
- [x] 6.6 Manually verify webconf is reachable and logs in successfully from a host browser while the script is running, independent of whether `run_zynthian_vnc.sh` is also running. Verified live: authbind lets the non-root process bind 80/443, login with the default password works, and the dashboard renders correctly (screenshot confirmed by the user).

## 7. Documentation

- [x] 7.1 Note the new native script, the Docker webconf ports/URLs, and the default login password (+ how to change it, given `sys-security`'s password-change page is disabled per task 2.3) in this repo's top-level docs, including the LAN-reachability caveat from design.md.
- [x] 7.2 Document `ZYNTHIAN_WEBCONF_PASSWORD` (and ports, if made configurable) as an override in `config/zynthian_envars_custom.sh.example`.
