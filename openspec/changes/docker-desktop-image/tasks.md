## 1. Base image and OS packages

- [x] 1.1 Create `docker/Dockerfile` in this repo (this project's own home, not inside a vendored fork) with `FROM ubuntu:24.04`
- [x] 1.2 Install the apt package list from design.md's "Base image and package list" section
- [x] 1.3 Confirm the exact package list against the reference machine (`/var/log/apt/history.log`, `dpkg -l`) if working on the same machine this proposal was written on - the list in design.md is grounded there but re-verify before trusting it blindly

## 2. Source repos

- [x] 2.1 Clone `zynthian-ui` from `https://github.com/Famondir/zynthian-ui.git`, branch `vangelis` (not upstream `zynthian/zynthian-ui` - see design.md for why)
- [x] 2.2 Clone `zyncoder`, `zynthian-sys`, `zynthian-data` from the official `zynthian/*` GitHub repos
- [x] 2.3 Build `zyncoder` in its dummy-encoders/`TOUCH_ONLY` mode - inspect the reference machine's actual build command/CMake flags first (not documented precisely elsewhere yet)

## 3. Native library / plugin builds

- [x] 3.1 Build/verify lilv (`install_lv2_lilv.sh` recipe, or confirm apt's `liblilv-dev`/`python3-lilv` are sufficient)
- [x] 3.2 Build the custom `zynthian/jalv` fork (branch `asyncli`) per `install_lv2_jalv.sh` - do not substitute the distro `jalv` package
- [x] 3.3 Build sfizz from source per `install_sfizz.sh`
- [x] 3.4 Build GxPlugins.lv2 per `install_gxplugins.sh`
- [x] 3.5 Build `zynthian-ui`'s own `zynlibs/{zynaudioplayer,zynmixer,zynseq,zynsmf,zynclippy}` via CMake (the `vangelis` fork branch already has the GCC-13 `-Werror` relaxations and mimalloc support needed - just build, don't re-patch)

## 4. Python environment

- [x] 4.1 Create venv with `python3 -m venv venv --system-site-packages`
- [x] 4.2 `pip install -r zynthian-ui/requirements.txt`
- [x] 4.3 `pip install pexpect numpy scipy wavio psutil` (used by the code but missing from requirements.txt - verified on the reference machine)

## 5. Directory scaffolding

- [x] 5.1 Create the `zynthian-my-data`/`zynthian-data` subdirectories listed in design.md ("Directory scaffolding") that a plain checkout doesn't provide

## 6. Container entrypoint

- [x] 6.1 Write an entrypoint script that starts `jackd`/`a2jmidid` (no PipeWire stop/start needed inside the container - see design.md) and then `zynthian_main.py`
- [x] 6.2 Decide and document default `JACKD_OPTIONS` (device names will vary per host; make this overridable via env var / mounted config, not hardcoded)

## 7. Host-side run script

- [x] 7.1 Write `run_zynthian_docker.sh` (or similar), adapting `run_zynthian.sh`'s PipeWire stop/start logic to wrap a `docker run` invocation instead of a direct process launch
- [x] 7.2 Include the `docker run` flags from design.md: `--device /dev/snd`, `--group-add audio`, `--cap-add=SYS_NICE --ulimit rtprio=95 --ulimit memlock=-1`, `-e DISPLAY`, `-v /tmp/.X11-unix:/tmp/.X11-unix:ro`, plus bind mounts for `zynthian-my-data` and the env-var config file
- [x] 7.3 Document the `xhost` prerequisite and the UID-matching consideration for X11/Xauthority to work cleanly

## 8. Validation

- [x] 8.1 Build the image end to end without errors
- [ ] 8.2 Run it on the same machine the native install already works on; compare behaviour against the native `run_zynthian.sh` session (audio in/out, MIDI, GUI, clean exit/PipeWire restore)
- [ ] 8.3 If possible, test on a genuinely different (non-Ubuntu) Linux host to validate the actual point of this change
- [ ] 8.4 Note any host-config-specific failures (Wayland-only, rootless Docker, etc.) as known limitations rather than silently working around them

## 9. Follow-ups (not blocking initial working image)

- [ ] 9.1 Multi-stage build to shrink final image size (drop `-dev`/build-tool packages from the runtime layer)
- [ ] 9.2 Consider publishing the image (registry choice, tagging/versioning strategy) - separate decision, out of scope for this change
