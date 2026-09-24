#!/bin/bash
# Run zynthian-webconf (the browser-based config UI) on the native
# desktop install, independently of run_zynthian_vnc.sh and
# /zynthian/run_zynthian.sh - mirrors how real Zynthian hardware runs
# webconf and the main UI as two independent systemd services rather than
# coupling their lifecycles. Run this in its own terminal, alongside (or
# instead of) run_zynthian_vnc.sh.
#
# On first run, clones Famondir/zynthian-webconf (branch vangelis - a fork
# with the login flow patched to check ZYNTHIAN_WEBCONF_PASSWORD instead
# of PAM auth against the system root account, since this isn't run as
# root; see openspec/changes/enable-webconf-access/design.md) into
# /zynthian/zynthian-webconf, installs its Python dependencies into the
# existing /zynthian/venv, and generates the self-signed TLS cert it
# requires (it crashes at startup without one - not optional). Subsequent
# runs skip straight to starting it.
#
# Reachable at http://localhost:${ZYNTHIAN_WEBCONF_PORT:-80} and
# https://localhost:443 (self-signed cert - your browser will warn,
# that's expected). Unlike run_zynthian_vnc.sh's noVNC (loopback-only by
# default), webconf listens on every network interface by default -
# webconf itself has no loopback-only mode, and that's also how real
# hardware exposes it (advertised over Avahi on the LAN). Default login
# password is "zynthian" - change it via ZYNTHIAN_WEBCONF_PASSWORD
# (webconf's own in-app password-change page is disabled for this
# desktop port, see design.md).
#
# Prerequisite: authbind (sudo apt install authbind), plus a one-time grant
# for ports 80/443 to your user:
#   sudo touch /etc/authbind/byport/80 /etc/authbind/byport/443
#   sudo chown "$(whoami)" /etc/authbind/byport/80 /etc/authbind/byport/443
#   sudo chmod 700 /etc/authbind/byport/80 /etc/authbind/byport/443
# Unlike the Docker image (which gets --cap-add=NET_BIND_SERVICE from
# run_zynthian_docker.sh), there's no per-container capability grant on a
# native install - authbind is the standard non-root way to bind ports
# <1024 without running the whole process as root or granting the
# capability to the shared system python3 binary (setcap on a venv's
# python3, which is just a symlink to /usr/bin/python3, would grant it
# system-wide to every python3 invocation - too broad).
set -e

source /zynthian/config/zynthian_envars_custom.sh

if ! command -v authbind >/dev/null; then
    echo "authbind is required (sudo apt install authbind) - see this script's header comment for the one-time port setup." >&2
    exit 1
fi
for p in 80 443; do
    if [ ! -x "/etc/authbind/byport/$p" ]; then
        echo "authbind isn't set up for port $p yet - see this script's header comment for the one-time 'sudo touch/chown/chmod /etc/authbind/byport/$p' setup." >&2
        exit 1
    fi
done

WEBCONF_DIR="$ZYNTHIAN_DIR/zynthian-webconf"
WEBCONF_REPO="https://github.com/Famondir/zynthian-webconf.git"
WEBCONF_BRANCH="vangelis"

if [ ! -d "$WEBCONF_DIR" ]; then
    echo "--- Cloning zynthian-webconf ($WEBCONF_BRANCH) into $WEBCONF_DIR ---"
    git clone --depth 1 -b "$WEBCONF_BRANCH" "$WEBCONF_REPO" "$WEBCONF_DIR"

    # Same list as docker/Dockerfile's venv install step - see
    # openspec/changes/enable-webconf-access/design.md for how this was
    # derived (tornado/etc. for the app itself; jsonpickle/mido/mutagen/
    # py7zr/rarfile/requests found by scanning its actual imports). Not
    # installed: PAM/python-pam/bcrypt - only used by upstream's PAM/root
    # login, which this fork's branch doesn't have.
    echo "--- Installing zynthian-webconf's Python dependencies ---"
    "$ZYNTHIAN_DIR/venv/bin/pip" install --no-cache-dir \
        tornado tornadostreamform tornado_xstatic terminado xstatic XStatic_term.js \
        jsonpickle mido mutagen py7zr rarfile requests
fi

# zynthian_webconf.py unconditionally listens on 443 with this cert
# (relative paths, read from its own CWD) - it crashes at startup without
# it. cert/ is gitignored in the webconf repo itself, so this always needs
# generating locally; same command zynthian-sys/sbin/regenerate_keys.sh
# uses for real hardware's own webconf cert.
if [ ! -f "$WEBCONF_DIR/cert/cert.pem" ] || [ ! -f "$WEBCONF_DIR/cert/key.pem" ]; then
    echo "--- Generating self-signed TLS cert for zynthian-webconf ---"
    mkdir -p "$WEBCONF_DIR/cert"
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$WEBCONF_DIR/cert/key.pem" \
        -out "$WEBCONF_DIR/cert/cert.pem" \
        -days 36500 -nodes -subj "/CN=$(hostname).local"
fi

# Same "documented default, change it" convention as JACKD_OPTIONS in
# zynthian_envars_custom.sh - override by exporting this before running
# the script, or adding it to zynthian_envars_custom.sh.
export ZYNTHIAN_WEBCONF_PASSWORD="${ZYNTHIAN_WEBCONF_PASSWORD:-zynthian}"

echo "--- Starting zynthian-webconf ---"
source "$ZYNTHIAN_DIR/venv/bin/activate"
cd "$WEBCONF_DIR"
# --deep: zynthian_webconf.sh execs python3 as a child process, not the
# bind() call itself - authbind's LD_PRELOAD shim has to follow through
# that exec, which --deep is for.
exec authbind --deep ./zynthian_webconf.sh
