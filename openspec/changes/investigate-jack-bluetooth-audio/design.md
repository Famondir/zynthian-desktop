## Context

`fix-audio-hotplug-support` (archived) solved ALSA-card-level hotplug: a USB audio interface appearing/disappearing from `/proc/asound/` triggers `zynautoconnect`'s `start_alsa_in`/`start_alsa_out` bridging. The two gaps this change investigates are different signal paths entirely, not smaller versions of the same problem - initial checks on the reference machine already narrow both down further than the original "note, don't fix" task assumed:

**3.5mm jack** - `amixer -c sofhdadsp controls` shows the onboard codec already exposes ALSA jack-detection kcontrols: `Mic Jack`, `Headphone Jack`, `Speaker Phantom Jack` (plus 3 HDMI/DP jack controls). So the earlier assumption written into `fix-audio-hotplug-support/design.md` - "the onboard codec doesn't disappear/reappear from ALSA when a cable is plugged into its jack" - is true but incomplete: there's no *card*-level hotplug event, but there *is* a kernel/ALSA-level jack-sense signal available (a control-value-changed notification on these kcontrols, the same mechanism `alsamixer`/`amixer` would show updating live on insertion). `zynautoconnect.py` currently only reacts to card add/remove (via its existing hotplug polling) - it doesn't listen for ALSA control-change events at all, for any card. This is a real, own investigation track: whether `zynautoconnect`'s hotplug detection can also listen for control-change notifications (e.g. via `pyalsa`/`alsaaudio`'s control-notify APIs, or `alsactl monitor`-style polling) and treat a jack-insertion event on these kcontrols similarly to a card hotplug event for the purpose of prompting/activating the capture port.

**Bluetooth** - `run_zynthian.sh` stops `wireplumber`, `pipewire-pulse`, and `pipewire` themselves for the whole session (`systemctl --user stop ...`, restarted on exit) - this is the *only* audio-routing stack present on this machine capable of carrying BlueZ's Bluetooth audio profiles (A2DP/HFP) into anything else. `bluealsa` (the lower-level BlueZ-to-ALSA bridge that doesn't depend on PipeWire) is not installed on the reference machine. So a paired Bluetooth device's audio has no path to ALSA or JACK at all while Zynthian is running - not a bug in the hotplug bridging, but the direct, expected consequence of a design decision `zynthian-desktop-runtime` already made (stop PipeWire so jackd has exclusive access to the hardware). This matches what was observed live (AirPods mic+speaker registered nothing).

## Goals / Non-Goals

**Goals:**
- Determine, concretely, whether the 3.5mm jack's kcontrol-based jack-sensing can be wired into `zynautoconnect`'s existing hotplug-triggered port-activation path, and estimate the effort/risk of doing so.
- Determine, concretely, whether Bluetooth audio can be bridged into JACK without reintroducing the PipeWire/jackd device conflict `zynthian-desktop-runtime` already solved by stopping PipeWire (the `bluealsa-aplay`-into-a-loopback-card idea is the leading candidate, not yet verified) - or confirm it can't be done cleanly and should be documented as a permanent limitation instead.
- Produce a clear per-source decision (fix now / fix later / permanent limitation) with the reasoning recorded, so this isn't re-investigated from scratch next time it comes up.

**Non-Goals:**
- Implementing either fix as part of this change - that's a follow-up `/opsx:apply` (or a fresh proposal) once the investigation lands on "worth fixing".
- Changing anything about the Docker image - it has no host PipeWire to stop and no onboard-jack passthrough path in the same sense (no `/dev/snd` jack-sensing across a container boundary has been explored at all).
- Re-litigating the PipeWire-stop decision itself (`zynthian-desktop-runtime`'s existing, working trade-off) - any Bluetooth bridge has to work *around* that decision, not replace it.

## Decisions

Not yet made - this change's own tasks.md is the investigation plan. Both tracks above have a plausible mechanism (ALSA control-notify for the jack; `bluealsa-aplay` + loopback card for Bluetooth) but neither has been prototyped yet. Record the actual decision here once each track's investigation task completes, rather than committing to an approach upfront.

## Risks / Trade-offs

- The jack-sensing kcontrol approach adds a second, different "something changed" signal type to `zynautoconnect` (control-notify, not card add/remove) - worth checking whether this fits its existing polling loop cleanly or needs a genuinely separate code path, since that affects how much this is really "extending" vs. "duplicating" the hotplug mechanism.
- A `bluealsa`-based Bluetooth bridge would be a new runtime dependency and a new moving part (BlueZ pairing state, `bluealsa` service, the loopback card, latency of the extra hop) on top of an already iteration-heavy audio stack (`zynthian-desktop-runtime`'s own history) - even if technically possible, worth weighing against just documenting the limitation, especially if Bluetooth audio quality/latency through such a bridge turns out to be poor for live playing.
- Both investigations depend on state specific to this reference machine (this exact codec's kcontrol names, this exact absence of `bluealsa`) - findings should be treated as "true on this machine" unless cross-checked against other hardware, matching the same caution `fix-audio-hotplug-support` applied to `JACKD_OPTIONS`.
