## 1. 3.5mm jack investigation

- [ ] 1.1 Confirm the jack-detection kcontrols (`Mic Jack`, `Headphone Jack`, `Speaker Phantom Jack` on `hw:sofhdadsp`) actually change value on insertion/removal - watch with `alsactl monitor` (or repeated `amixer -c sofhdadsp cget ...`) while plugging/unplugging.
- [ ] 1.2 Check whether `pyalsa`/`alsaaudio` (whichever ALSA Python binding `zynautoconnect.py` already uses) exposes a way to subscribe to control-change notifications, or whether it would need polling.
- [ ] 1.3 Prototype (throwaway script, not wired into `zynautoconnect` yet): react to a jack-insertion event and confirm it's reliably distinguishable from other control-change noise on this card.
- [ ] 1.4 Decide: worth wiring into `zynautoconnect`'s hotplug path (estimate effort/risk from 1.1-1.3), or document as a permanent limitation. Record the decision and reasoning in design.md's "Decisions" section.

## 2. Bluetooth audio investigation

- [ ] 2.1 Confirm directly (not just inferred from `run_zynthian.sh` stopping PipeWire): with a Zynthian session running, is there *any* ALSA/JACK-visible trace of a connected Bluetooth device (check `aplay -l`, `pactl`/`wpctl` if anything's still listening, `jack_lsp`)?
- [ ] 2.2 Install `bluealsa` and test standalone (Zynthian session stopped) whether `bluealsa-aplay`/`bluealsa-rec` can move audio for the already-paired AirPods, independent of PipeWire.
- [ ] 2.3 If 2.2 works, prototype routing `bluealsa-aplay`'s output into a dedicated `snd-aloop` card the same way `setup_virtual_devices.sh`'s `--with-fluidsynth` mode already does for dev testing - then check whether `zynautoconnect`'s existing bridging picks it up as a normal ALSA capture/playback source.
- [ ] 2.4 Assess latency/quality of the bridged path - Bluetooth audio (A2DP especially) has inherent latency that may be unacceptable for live playing, independent of whether the bridge technically works.
- [ ] 2.5 Decide: worth implementing the `bluealsa` bridge (estimate effort/risk and note the latency finding from 2.4), or document as a permanent limitation. Record the decision and reasoning in design.md's "Decisions" section.

## 3. Wrap up

- [ ] 3.1 Update this change's `specs/zynthian-desktop-runtime/spec.md` delta if either investigation concludes "fix it" rather than "document the gap" - the ADDED requirement here assumes both stay gaps; a decision to fix one needs the delta (or a follow-up change) updated to match before archiving.
- [ ] 3.2 If either fix is decided worth doing, note that it needs its own follow-up change (new proposal or continuation) rather than being implemented inside this investigation change.
