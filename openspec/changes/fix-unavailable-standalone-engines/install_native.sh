#!/bin/bash
# Native install for fix-unavailable-standalone-engines (tasks 2.1, 2.2).
# Run as the normal user; it calls sudo where root is needed.
#
# - SooperLooper, Internet Radio (vlc + JACK output), PureData with the
#   same pd-* externals zynthian-sys's setup script installs (all exist on
#   Ubuntu 24.04).
# - Aeolus from Zynthian's own fork (branch "zynthian"), replicating
#   zynthian-sys's recipes/install_aeolus.sh - Debian's aeolus lacks
#   Zynthian's patches. Its build deps come from apt instead of building
#   the kokkinizita libs by hand (install_aeolus_kokki.sh).
set -euo pipefail

sudo apt-get install -y \
    sooperlooper vlc vlc-plugin-jack \
    puredata puredata-core puredata-utils puredata-import python3-yaml \
    pd-lua pd-moonlib pd-pdstring pd-markex pd-iemnet pd-plugin pd-ekext pd-bassemu pd-readanysf pd-pddp \
    pd-zexy pd-list-abs pd-flite pd-windowing pd-fftease pd-bsaylor pd-osc pd-sigpack pd-hcs pd-pdogg pd-purepd \
    pd-beatpipe pd-freeverb pd-iemlib pd-smlib pd-hid pd-csound pd-earplug pd-wiimote pd-pmpd pd-motex \
    pd-arraysize pd-ggee pd-chaos pd-iemmatrix pd-comport pd-libdir pd-vbap pd-cxc pd-lyonpotpourri pd-iemambi \
    pd-pdp pd-mjlib pd-cyclone pd-jmmmp pd-3dp pd-boids pd-mapping pd-maxlib \
    libclthreads-dev libclxclient-dev libzita-alsa-pcmi-dev libreadline-dev libxft-dev

src_dir="${ZYNTHIAN_SW_DIR:-/zynthian/zynthian-sw}"
mkdir -p "$src_dir"
cd "$src_dir"
rm -rf aeolus
git clone -b zynthian https://github.com/zynthian/aeolus.git
cd aeolus/source
make -j"$(nproc)"
sudo make install
cd ..
sudo mkdir -p /usr/local/share/aeolus
sudo cp -a stops /usr/local/share/aeolus
echo "-u -S /usr/local/share/aeolus/stops" | sudo tee /etc/aeolus.conf

echo "--- Done. Check: ---"
for p in sooperlooper vlc pd aeolus; do printf "%-14s %s\n" "$p" "$(command -v "$p" || echo MISSING)"; done
