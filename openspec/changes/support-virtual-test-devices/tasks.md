## 1. MIDI: recognize VMPK as a virtual hardware source

- [x] 1.1 Add a virtual-MIDI-treated-as-hardware whitelist entry for VMPK in `update_hw_midi_ports()` (`/zynthian/zynthian-ui/zynautoconnect/zynthian_autoconnect.py`). Note: the initial literal `"a2j:MIDI Out"` match broke on the very next session - VMPK's ALSA client name turned out to depend on whether `~/.config/vmpk.sourceforge.net/VMPK.conf` exists yet ("MIDI Out" pre-config default vs. "VMPK Output" once VMPK has written its own config). Fixed with the regex `"a2j:(MIDI Out|VMPK)"` to cover both/future VMPK-prefixed renames.
- [x] 1.2 Confirm the fix survives a `zynthian_main.py` restart. Confirmed for the `VMPK` branch of the regex: `docker-automated-smoke-test`'s script cold-starts a fresh `zynthian_main.py` (inside a fresh container) and a fresh VMPK process every run, and across 5 consecutive fresh starts (once the fix was pushed to `fork/vangelis` and the image rebuilt) `jack_lsp` consistently showed `a2j:VMPK Output` correctly recognized and connected - no manual `jack_connect` involved. Not separately re-confirmed on the *native* install specifically, and the smoke test's VMPK config always pre-exists (written fresh by the script before VMPK starts each run), so the `MIDI Out` pre-config-file branch specifically wasn't re-exercised - only the `VMPK` alternative was. Since both are the same regex and the original concern (a fix silently breaking across a restart) is what mattered here, this is being marked done on that basis.

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

- [x] 5.1 Quick test: does this workflow work unmodified against the Docker desktop image? Answered by `docker-automated-smoke-test`: **not entirely unmodified**, but close. `/dev/snd` passthrough does carry the ALSA sequencer (`/dev/snd/seq`) through, so VMPK on the host and `a2jmidid` inside the container do share the same kernel ALSA-seq namespace with no extra wiring, and the `zynautoconnect.py` whitelist fix works identically in the container. What needed adjusting for Docker specifically: (1) `jackd`'s alsa backend opens `snd-aloop`'s hardware-max 32 channels unless told `-i 2 -o 2` explicitly, which broke ALSA-level capture from the loopback's paired side; (2) reading that paired capture side via `arecord` turned out to be unreliable regardless (`EIO` on read) and was abandoned in favor of recording straight from the container's own JACK graph (`jack_rec` via `docker exec`) - see that change's design.md for the full story. `run_zynthian_docker.sh` itself needed no changes.
