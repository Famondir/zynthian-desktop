# Zynthian desktop port, containerized. See openspec/changes/docker-desktop-image
# (design.md) for why each decision below was made; this mirrors the exact
# package list and build steps already proven working on the reference
# Ubuntu 24.04 desktop install.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Package list grounded in the reference machine's actual apt history
# (/var/log/apt/history.log) for the equivalent native install, plus
# meson/ninja-build here (as real apt packages) instead of relying on pip
# packages of the same name pulled in later by requirements.txt - the
# native install got meson from pip, but jalv/lilv need it *before* the
# Python venv exists, so apt is the simpler dependency order for a build.
#
# python3-rdflib: on the reference machine this came in automatically as a
# dependency of the stock `jalv` apt package. We don't install stock jalv
# (build our own from source instead - see the jalv build step below), so
# it has to be listed explicitly; zynthian_lv2.py imports it directly and
# it's pulled in unconditionally via zyngine/__init__.py at startup.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git pkg-config meson ninja-build \
    libasound2-dev liblo-dev liblo7 libjack-jackd2-dev jackd2 a2jmidid \
    libboost-python-dev libboost-thread-dev libboost-system-dev \
    librubberband-dev rubberband-cli \
    python3-venv python3-dev python3-pip python3-tk python3-evdev python3-lilv python3-pil.imagetk python3-rdflib \
    liblilv-dev lv2-dev \
    libsndfile1-dev sox \
    fluidsynth libfluidsynth-dev fluid-soundfont-gm \
    zynaddsubfx setbfree carla \
    nlohmann-json3-dev \
    libmimalloc-dev \
    liblrdf0-dev libzita-convolver-dev libzita-resampler-dev fonts-roboto \
    gperf libsigc++-2.0-dev libeigen3-dev \
    ca-certificates wget curl unzip openssl \
    x11-apps xauth \
    && rm -rf /var/lib/apt/lists/*
# Notably NOT installed: pipewire-jack, or any PipeWire package. There is
# no PipeWire running inside the container to conflict with jackd.

ENV ZYNTHIAN_DIR=/zynthian
ENV ZYNTHIAN_CONFIG_DIR=$ZYNTHIAN_DIR/config
ENV ZYNTHIAN_SW_DIR=$ZYNTHIAN_DIR/zynthian-sw
ENV ZYNTHIAN_UI_DIR=$ZYNTHIAN_DIR/zynthian-ui
ENV ZYNTHIAN_SYS_DIR=$ZYNTHIAN_DIR/zynthian-sys
ENV ZYNTHIAN_DATA_DIR=$ZYNTHIAN_DIR/zynthian-data
ENV ZYNTHIAN_MY_DATA_DIR=$ZYNTHIAN_DIR/zynthian-my-data
ENV ZYNTHIAN_PLUGINS_DIR=$ZYNTHIAN_DIR/zynthian-plugins
ENV ZYNTHIAN_PLUGINS_SRC_DIR=$ZYNTHIAN_SW_DIR/plugins
ENV ZYNTHIAN_RECIPE_DIR=$ZYNTHIAN_SYS_DIR/scripts/recipes
ENV LV2_PATH=/usr/lib/lv2:/usr/local/lib/lv2:$ZYNTHIAN_PLUGINS_DIR/lv2:$ZYNTHIAN_DATA_DIR/presets/lv2:$ZYNTHIAN_MY_DATA_DIR/presets/lv2
ENV PATH=$ZYNTHIAN_SYS_DIR/sbin:$PATH

# No dedicated encoder/GPIO hardware in a container: dummy encoders, touch/mouse UI.
ENV ZYNTHIAN_WIRING_LAYOUT=TOUCH_ONLY
# Zynthian imports board/neopixel_spi unconditionally even with no WS281x LED
# strip attached; Blinka's generic-Linux stub satisfies the import.
ENV BLINKA_FORCEBOARD=GENERIC_LINUX_PC
ENV BLINKA_FORCECHIP=GENERIC_X86
# Several engines branch on Pi model number; 0 selects the most conservative
# (non-Pi) settings instead of crashing on missing /proc hardware info.
ENV RBPI_VERSION="PC (UNSUPPORTED!)"
ENV RBPI_VERSION_NUMBER=0
ENV ZYNTHIAN_UI_ENABLE_CURSOR=1
ENV ZYNTHIAN_LOG_LEVEL=20
# Without this, zynthian_gui_config.py's touch_shown defaults to 0 and the
# main content area fills the whole window - the touch keypad panel/chassis
# graphics (classic/standard/device/device_cables) never get shown at all,
# only the plain display area. There's no physical encoder/button hardware
# in a container (same reasoning as ZYNTHIAN_WIRING_LAYOUT=TOUCH_ONLY above),
# so this is always wanted here, not host-specific.
ENV ZYNTHIAN_TOUCH_SHOWN=1
# Baseline window size entrypoint.sh's GUI-style logic adjusts from (the
# real V5 touchscreen's resolution). Without an explicit size, the UI
# auto-sizes to the full host display and opens as a borderless window.
# Override via zynthian_envars_custom.sh if your display needs different
# numbers to work from.
ENV DISPLAY_WIDTH=1600
ENV DISPLAY_HEIGHT=960
# jackd's ALSA driver tries to reserve the audio device via a D-Bus session
# bus (rtkit-style device reservation) before opening it; there's no D-Bus
# session in this container, and it just fails the reservation check without
# this - the device itself opens fine once that check is skipped.
ENV JACK_NO_AUDIO_RESERVATION=1

WORKDIR $ZYNTHIAN_DIR

# --- 2. Source repos ---
# zynthian-ui: Famondir/zynthian-ui, branch vangelis - has every fix-* change
# plus touchkeypad-visual-styles. NOT the upstream zynthian/zynthian-ui repo,
# which is missing all of that.
#
# CACHEBUST: the vangelis branch moves (actively developed UI/styling work),
# but this RUN line itself never changes, so Docker would otherwise cache a
# stale clone forever. Pass --build-arg CACHEBUST=$(date +%s) to force a
# fresh clone without invalidating the slow apt-get layer above it.
#
# zynthian-webconf: also Famondir/zynthian-webconf, branch vangelis - NOT
# upstream zynthian/zynthian-webconf, which gates every page behind a PAM
# login against the system root account (assumes webconf runs as root, as
# it does via systemd on real hardware). This container runs non-root (see
# run_zynthian_docker.sh's --user), so the fork's login instead checks
# ZYNTHIAN_WEBCONF_PASSWORD - see openspec/changes/enable-webconf-access/
# design.md for the full rationale.
ARG CACHEBUST=1
RUN git clone --depth 1 -b vangelis https://github.com/Famondir/zynthian-ui.git zynthian-ui \
    && git clone --depth 1 https://github.com/zynthian/zyncoder.git zyncoder \
    && git clone --depth 1 https://github.com/zynthian/zynthian-sys.git zynthian-sys \
    && git clone --depth 1 https://github.com/zynthian/zynthian-data.git zynthian-data \
    && git clone --depth 1 -b vangelis https://github.com/Famondir/zynthian-webconf.git zynthian-webconf \
    && ln -s ../zyncoder zynthian-ui/zyncoder \
    && mkdir -p "$ZYNTHIAN_SW_DIR" "$ZYNTHIAN_PLUGINS_SRC_DIR" "$ZYNTHIAN_PLUGINS_DIR/lv2"

# zynthian-webconf unconditionally listens on 443 with a self-signed cert
# (zynthian_webconf.py: app.listen(443, ssl_options={"certfile": "cert/
# cert.pem", "keyfile": "cert/key.pem"})) - it crashes at startup without
# these files, and the repo itself doesn't ship them (cert/ is gitignored
# there). Same command real hardware uses to (re)generate its own
# (zynthian-sys/sbin/regenerate_keys.sh), baked in at build time here
# instead of first-run, since there's no per-device identity to keep
# unique in a container image.
RUN mkdir -p "$ZYNTHIAN_DIR/zynthian-webconf/cert" \
    && openssl req -x509 -newkey rsa:4096 \
        -keyout "$ZYNTHIAN_DIR/zynthian-webconf/cert/key.pem" \
        -out "$ZYNTHIAN_DIR/zynthian-webconf/cert/cert.pem" \
        -days 36500 -nodes -subj "/CN=zynthian-desktop.local"

# zynthian-ui bundles its own fonts (fonts/*), none of which are apt
# packages - the default UI font (zynthian_gui_config.font_family, default
# "Audiowide") and the "forkawesome" icon font the touch keypad uses for
# arrow/transport glyphs (labels >= ) both come from here. Without
# this, Tk silently falls back to a generic font: wrong-looking text and
# missing-glyph boxes for icons instead of arrows.
RUN mkdir -p /usr/local/share/fonts/zynthian-ui \
    && cp -r "$ZYNTHIAN_UI_DIR/fonts/." /usr/local/share/fonts/zynthian-ui/ \
    && fc-cache -f

# --- 2.3 zyncoder, dummy-encoders/TOUCH_ONLY mode (ZYNTHIAN_WIRING_LAYOUT above) ---
RUN cd zyncoder && mkdir build && cd build && cmake .. && make -j"$(nproc)"

# --- 3. Native library / plugin builds ---
# Follow zynthian-sys's own recipes rather than re-inventing the build
# commands. `bash -e` because the recipe scripts don't `set -e` themselves.
#
# 3.1 lilv: apt's liblilv-dev/python3-lilv (installed above) are recent
# enough on Ubuntu 24.04 - confirmed against the reference machine, which
# never ran install_lv2_lilv.sh. Skipped here for the same reason.
#
# 3.2 jalv: the custom zynthian/jalv fork (branch asyncli). The recipe also
# builds suil from source, but confirmed on the reference machine that only
# jalv itself needs to be custom-built - it links fine against apt's
# liblilv-0. The stock distro jalv package uses a different stdin/stdout
# protocol and does not work with zynthian-ui's LV2 engine.
RUN bash -e "$ZYNTHIAN_RECIPE_DIR/install_lv2_jalv.sh"

# 3.3 sfizz: not packaged for Ubuntu, build from source.
RUN bash -e "$ZYNTHIAN_RECIPE_DIR/install_sfizz.sh"

# 3.4 GxPlugins.lv2 (Guitarix effects, brummer10/GxPlugins.lv2), installed
# into $ZYNTHIAN_PLUGINS_DIR/lv2.
RUN bash -e "$ZYNTHIAN_RECIPE_DIR/install_gxplugins.sh"

# 3.4b The full Guitarix project itself (brummer10/guitarix, install_
# guitarix.sh) - a separate, much bigger repo from GxPlugins.lv2 above and
# not mentioned in design.md, but it's what actually provides the gx_amp/
# gx_amp_stereo amp-sim LV2 plugins (http://guitarix.sourceforge.net/
# plugins/...) - GxPlugins.lv2 alone doesn't have them, and without this
# adding an "Audio Generator" > amp-sim chain fails with a lilv
# "Plugin not found" KeyError. Its recipe's declared deps (liblrdf-dev,
# libboost-system-dev, libzita-convolver-dev, libzita-resampler-dev,
# fonts-roboto) are already in section 1's package list.
#
# Not run via the recipe script as-is: waf's shebang is `#!/usr/bin/env
# python`, and this image (like the reference machine) has no `python`
# binary, only `python3` - invoke waf via `python3` explicitly instead.
RUN cd "$ZYNTHIAN_PLUGINS_SRC_DIR" \
    && git clone --depth 1 https://github.com/brummer10/guitarix.git guitarix \
    && cd guitarix/trunk \
    && python3 ./waf configure --no-standalone --no-lv2-gui --disable-sse \
        --lv2dir="$ZYNTHIAN_PLUGINS_DIR/lv2" --no-avahi --no-bluez --no-faust --mod-lv2 \
    && python3 ./waf build -j"$(nproc)" \
    && python3 ./waf install \
    && python3 ./waf clean \
    && cd "$ZYNTHIAN_PLUGINS_SRC_DIR" && rm -rf guitarix

# 3.4c Neural Amp Modeler LV2 (mikeoliphant/neural-amp-modeler-lv2) - same
# "Plugin not found" KeyError pattern as guitarix above, not mentioned in
# design.md. zynthian-sys's own install_nam.sh recipe has a real bug
# (`if [-d "..."]` - missing space, not valid bash) that makes it fail
# immediately if run as-is, so this replicates its intent by hand instead
# of invoking it. DSP-only build (skips install_nam.sh's second half, the
# brummer10/neural-amp-modeler-ui modgui) - already produces a complete,
# valid LV2 bundle (manifest.ttl + neural_amp_modeler.ttl + .so); the UI
# repo just adds a nicer on-screen graphical control panel on top.
RUN cd "$ZYNTHIAN_PLUGINS_SRC_DIR" \
    && git clone --recurse-submodules -j"$(nproc)" https://github.com/mikeoliphant/neural-amp-modeler-lv2.git \
    && cd neural-amp-modeler-lv2/build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release \
    && make -j"$(nproc)" \
    && mv neural_amp_modeler.lv2 "$ZYNTHIAN_PLUGINS_DIR/lv2/Neural_Amp_Modeler.lv2" \
    && cd "$ZYNTHIAN_PLUGINS_SRC_DIR" && rm -rf neural-amp-modeler-lv2

# 3.5 zynthian-ui's own zynlibs (zynaudioplayer, zynmixer, zynseq, zynsmf,
# zynclippy). The vangelis fork branch already has the GCC-13 -Werror
# relaxations and mimalloc support baked in - just build, don't re-patch.
RUN cd "$ZYNTHIAN_UI_DIR/zynlibs" && ./build.sh

# --- 4. Python environment ---
# --system-site-packages: python3-lilv/python3-evdev/python3-pil.imagetk
# are apt packages with no pip equivalent, so the venv needs to see them.
#
# Beyond pexpect/numpy/scipy/wavio/psutil (already known missing from
# requirements.txt - see design.md), zyngine/__init__.py and zynthian_gui.py
# unconditionally import every engine/gui module at startup, which pulls in
# further undeclared imports found by statically scanning every import in
# the codebase against what's actually installed (not just reacting to each
# crash one at a time): pyliblo3 (OSC - zynthian_controller.py/zynthian_
# engine.py, core, not optional), websocket-client (zynthian_engine_modui.py),
# pyalsaaudio (alsaaudio module; zynthian_autoconnect.py/zynthian_engine_
# alsa_mixer.py), pyudev (zynthian_engine_inet_radio.py), beautifulsoup4
# (zynthian_gui_help.py), and cairosvg/moderngl/moderngl-window (the V5
# touch-keypad chassis rendering and the audio-file waveform widget - both
# directly relevant since this image runs ZYNTHIAN_WIRING_LAYOUT=TOUCH_ONLY).
# None of pyliblo3/websocket-client/pyalsaaudio/pyudev are apt packages
# under these names on Ubuntu 24.04 (apt's python3-liblo provides a `liblo`
# module, not `pyliblo3`, and does not satisfy that import).
#
# zynthian-webconf's own deps, on top of the above (it imports zyncoder/
# zynconf/zyngine/zyngui directly, so it needs zynthian-ui's dependencies
# too - already covered by the two installs below): tornado/tornadostreamform/
# tornado_xstatic/terminado/xstatic/XStatic_term.js (its Tornado web app +
# in-browser terminal), jsonpickle/mido/mutagen/py7zr/rarfile/requests (found
# by statically scanning zynthian_webconf.py + lib/*.py the same way, see
# design.md). Not installed: PAM/python-pam, bcrypt - both were only used by
# the upstream PAM/root login this project's zynthian-webconf fork (Famondir/
# zynthian-webconf, branch vangelis, cloned above) replaces; pyliblo3/
# websocket-client/beautifulsoup4 above already cover webconf's own imports
# of those same modules.
RUN python3 -m venv "$ZYNTHIAN_DIR/venv" --system-site-packages \
    && "$ZYNTHIAN_DIR/venv/bin/pip" install --no-cache-dir -r "$ZYNTHIAN_UI_DIR/requirements.txt" \
    && "$ZYNTHIAN_DIR/venv/bin/pip" install --no-cache-dir \
        pexpect numpy scipy wavio psutil \
        pyliblo3 pyalsaaudio websocket-client pyudev \
        beautifulsoup4 cairosvg moderngl moderngl-window \
        tornado tornadostreamform tornado_xstatic terminado xstatic XStatic_term.js \
        jsonpickle mido mutagen py7zr rarfile requests

# --- 5. Directory scaffolding ---
# A plain checkout doesn't provide these, and the app errors without them.
# zynthian_gui_config.py unconditionally reads $ZYNTHIAN_CONFIG_DIR/wiring-
# profiles/v5 at import time for the TOUCH_ONLY layout's touch-keypad
# codepath, and other modules read keybinding/, engine_config.json, etc.
# from the same directory - so $ZYNTHIAN_CONFIG_DIR needs zynthian-sys's
# config/ content seeded in, not just the couple of extra subdirectories
# below that a plain checkout is missing.
RUN mkdir -p "$ZYNTHIAN_CONFIG_DIR" \
    && cp -r "$ZYNTHIAN_SYS_DIR/config/." "$ZYNTHIAN_CONFIG_DIR/" \
    && mkdir -p \
    "$ZYNTHIAN_MY_DATA_DIR/presets/lv2" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/zynaddsubfx" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/fluidsynth" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/sfz" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/sf2" \
    "$ZYNTHIAN_MY_DATA_DIR/presets/gig" \
    "$ZYNTHIAN_MY_DATA_DIR/soundfonts/sf2" \
    "$ZYNTHIAN_MY_DATA_DIR/soundfonts/sfz" \
    "$ZYNTHIAN_MY_DATA_DIR/files/Neural Models" \
    "$ZYNTHIAN_DATA_DIR/collections" \
    "$ZYNTHIAN_CONFIG_DIR/jalv" \
    && chmod -R a+rwX "$ZYNTHIAN_MY_DATA_DIR" "$ZYNTHIAN_CONFIG_DIR"

# --- 6. Container entrypoint ---
COPY entrypoint.sh /usr/local/bin/zynthian-entrypoint.sh
RUN chmod +x /usr/local/bin/zynthian-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/zynthian-entrypoint.sh"]
