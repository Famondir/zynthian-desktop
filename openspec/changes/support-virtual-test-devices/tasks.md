## 1. MIDI: recognize VMPK as a virtual hardware source

- [x] 1.1 Add a virtual-MIDI-treated-as-hardware whitelist entry for VMPK in `update_hw_midi_ports()` (`/zynthian/zynthian-ui/zynautoconnect/zynthian_autoconnect.py`). Note: the initial literal `"a2j:MIDI Out"` match broke on the very next session - VMPK's ALSA client name turned out to depend on whether `~/.config/vmpk.sourceforge.net/VMPK.conf` exists yet ("MIDI Out" pre-config default vs. "VMPK Output" once VMPK has written its own config). Fixed with the regex `"a2j:(MIDI Out|VMPK)"` to cover both/future VMPK-prefixed renames.
- [ ] 1.2 Confirm the fix survives a `zynthian_main.py` restart. NOT yet actually confirmed for the current regex-corrected version - the original literal-string version was tested across a restart and found broken (see 1.1's note), prompting the regex fix, but that corrected version has only been verified via manual `jack_connect` so far, not a fresh restart. Needs one more restart+observe cycle before this can be checked off.

## 2. Dev script

- [ ] 2.1 Write a repo-root script (matching `run_zynthian_docker.sh`/`run_zynthian_vnc.sh` style) that: installs/checks for `vmpk`, loads `snd-aloop`, optionally starts `fluidsynth` wired to the loopback playback side, and prints next steps (launch VMPK, play a note)
- [ ] 2.2 Script should be idempotent (safe to re-run if `vmpk`/`snd-aloop` already present/loaded)

## 3. Documentation

- [ ] 3.1 Document the `modprobe snd-aloop` / `modprobe -r snd-aloop` cycle as the way to simulate audio-interface hotplug for dev testing, including how it relates to (but doesn't replace) real-hardware validation
- [ ] 3.2 Document the VMPK MIDI setup (ALSA driver, a2jmidid bridging) and the current limitation it fixes (VMPK not auto-recognized without the task-1 patch)

## 4. Validate

- [ ] 4.1 Fresh run: launch VMPK + the dev script from a clean state, confirm MIDI reaches the active chain with no manual `jack_connect`
- [ ] 4.2 Confirm `snd-aloop` load/unload produces the expected ALSA card add/remove (cross-check against whatever `fix-audio-hotplug-support` validation observes)
- [ ] 4.3 Confirm the virtual-device workflow doesn't interfere with real-hardware use (Suprema still works normally when actually plugged in)

## 5. Open question follow-up

- [ ] 5.1 Quick test: does this workflow work unmodified against the Docker desktop image (`run_zynthian_docker.sh`), given `/dev/snd` is passed through? Note the answer in this change or a follow-up, don't leave it unverified
