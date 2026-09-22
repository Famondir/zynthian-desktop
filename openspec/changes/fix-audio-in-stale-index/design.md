## Context

The Audio Input screen polls `zynautoconnect.get_audio_capture_ports()` periodically (`refresh_status()`) and rebuilds `list_data` whenever the capture port set changes, e.g. when a USB audio device is plugged in/out or JACK is still settling right after startup. A click already in flight references the row index from before the rebuild.

## Goals / Non-Goals

**Goals:**
- Never crash on a stale row index; simply ignore the click if the list has since changed shape.

**Non-Goals:**
- Preserving the "same" selection across a list rebuild (e.g. by matching on port name instead of index) - a nice-to-have, not needed to fix the crash.

## Decisions

- Add a simple `if i >= len(self.list_data): return` guard at the top of `select_action()`, rather than debouncing the background refresh - the race is rare and harmless to just ignore.

## Risks / Trade-offs

- A click on a now-invalid row is silently dropped instead of, say, showing a fresh list - acceptable since the underlying list is about to reflect the current port state anyway.
