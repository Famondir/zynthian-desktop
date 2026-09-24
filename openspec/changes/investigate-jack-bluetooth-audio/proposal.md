## Why

`fix-audio-hotplug-support` (archived) fixed hotplug for USB audio interfaces - ALSA-card-level add/remove events bridged live via `zynautoconnect`'s `start_alsa_in`/`start_alsa_out`. Validating that change with real hardware also surfaced two input/output sources that still don't work at all: plugging a headset into the laptop's onboard 3.5mm jack, and pairing Bluetooth audio devices (tested live: AirPods, both mic and speaker). Neither was in that change's scope, but both are real gaps a desktop user would hit, and the root causes are different enough from ALSA-card hotplug (and from each other) that they need their own investigation before deciding whether either is worth fixing.

## What Changes

- Investigate the 3.5mm jack's actual behavior: confirm whether it's a kernel/codec jack-sensing issue (e.g. missing ALSA jack-detection kcontrol / UCM profile for this codec) as suspected, and whether the capture port could be made to activate on insertion without becoming full ALSA-card hotplug.
- Investigate Bluetooth audio's actual behavior: confirm whether it's fundamentally incompatible with the PipeWire-stopped JACK session (this project's `run_zynthian.sh` already stops the host's PipeWire for the session's duration, and BlueZ/PipeWire is the normal BT audio path), or whether a bridge (e.g. `bluealsa-aplay` writing into a dedicated ALSA loopback card the same way `alsa_in`/`alsa_out` already bridge USB devices) could make it work without reintroducing the PipeWire/jackd conflict the prior change avoided.
- Based on those findings, decide per-source whether to implement a fix now or document it as a permanent limitation of this architecture - this proposal covers the investigation and that decision, not a committed implementation of both fixes.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `zynthian-desktop-runtime`: outcome depends on the investigation - either a new hotplug requirement for one or both sources (if a fix is found), or an explicit documented limitation (if not). Either way this capability's spec is where the resulting decision is recorded.

## Impact

- Native desktop install only (`/zynthian/run_zynthian.sh`, `zynautoconnect.py`) - not the Docker image, which has no host PipeWire to fight and no onboard jack passthrough concern in the same way.
- Depends on `fix-audio-hotplug-support`'s bridging machinery (`start_alsa_in`/`start_alsa_out`) as the mechanism a Bluetooth bridge would plug into, if that route is chosen.
- **Status: proposed, investigation not yet started.**
