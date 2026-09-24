## Context

`novnc_viewer.sh`'s `start_novnc_viewer` (shared by `run_zynthian_vnc.sh` and `run_zynthian_docker.sh`) starts `Xvfb` at a fixed `1910x1120` - sized for `device_cables`, the largest of the four GUI styles - and `x11vnc -display "$VNC_DISPLAY" ...` immediately after, exporting that entire virtual screen. `classic`/`standard` render noticeably smaller windows within that same canvas (`run_zynthian.sh`'s `DISPLAY_WIDTH`/`DISPLAY_HEIGHT` logic - `classic` keeps whatever the configured baseline is, e.g. `1600x960`; `standard` derives a different, also-smaller-than-1910x1120 size from it), and even `device` itself (`1910x960`) is 160px short of the full `1910x1120` height. Found live: viewing `classic` through the browser showed the real content confined to the upper-left, with a large black margin to the right and below - `x11vnc` has no idea how big the *app's own window* is, only the full display it was told to export.

## Goals / Non-Goals

**Goals:**
- The noVNC view fits whichever GUI style is actually running, for both launchers, with no manual configuration per style.
- No change to either script's existing foreground-app / trap-based-cleanup shutdown behavior (established carefully across `novnc-browser-viewer` and `docker-novnc-browser-viewer` - not worth risking a regression here).
- Fails soft: if window-tracking can't find the window for any reason, the session still works exactly as it does today (full-canvas export), just with the margin.

**Non-Goals:**
- Re-tracking if the app's window is destroyed and recreated mid-session - `zynthian_main.py` keeps one long-lived root Tk window for the life of the process, so a one-time track-at-startup covers the whole session.
- Cropping to sub-regions of a window, resizing Xvfb itself, or any other approach to the same visual problem - see Decisions for why window-tracking was chosen over those.

## Decisions

### Reconfigure `x11vnc` at runtime via `-R id:<windowid>`, not a per-style Xvfb size
Confirmed live: sending `x11vnc -display <disp> -R id:<windowid>` to an already-running `x11vnc` instance (matching `-display`) makes it immediately re-announce a new framebuffer sized exactly to that window (`rfbNewFramebuffer(..., 1009, 196, ...)` observed for a 1009x196 test window) - no server restart needed, and the *same* running instance keeps serving the *same* `websockify`/noVNC connection throughout.
- **Alternative considered and rejected: compute the right `XVFB_SIZE` per style up front.** Would require duplicating `run_zynthian.sh`'s `CLASSIC_PANEL`/`CLASSIC_SCREEN_WIDTH`/`CLASSIC_SCREEN_HEIGHT` arithmetic (and sourcing its baseline `DISPLAY_WIDTH`/`DISPLAY_HEIGHT` from `zynthian_envars_custom.sh` first) in a second place, for both launchers - fragile (a future tweak to that formula would need to be mirrored, and previously drift silently), and it still wouldn't handle `device`'s own 1910x960-vs-1910x1120 shortfall without being style-aware in the first place. Runtime window-tracking needs none of that - it asks the X server directly for the real, current geometry instead of predicting it.

### A background watcher polls for the window, not a foreground/backgrounded app launch
Both launchers currently run the app itself as the last, foreground, blocking command (`DISPLAY=... /zynthian/run_zynthian.sh "$GUI_STYLE"` / `docker run --rm -it ...`) - this is what makes `Ctrl+C` deliver `SIGINT` directly to that process (and, for the native case, is what the already-solved "Tk swallows SIGINT" `kill -9` handling in `run_zynthian.sh` itself depends on). Backgrounding the app launch to poll for its window in the same script would risk breaking that. Instead, `novnc_viewer.sh` gets a new function that forks its *own* small background loop (poll for the window, send the one remote command, exit) - the app launch line in each caller script stays completely untouched, foreground and blocking exactly as before. The watcher's PID is exposed the same way `XVFB_PID`/`X11VNC_PID`/`WEBSOCKIFY_PID` already are, for each caller's own `cleanup()` to kill defensively (harmless if it already exited).

### Match the window by `WM_CLASS` ("Tk"), not "any visible window"
`docker-automated-smoke-test` used a generic `xdotool search --onlyvisible '.*'` for its own readiness check, safe there because nothing else ran on that private display yet. Here, a developer may well have `vmpk` (`support-virtual-test-devices`) running on the *same* display at the same time for MIDI testing - a generic match could latch onto VMPK's window instead of Zynthian's. `xdotool search --class "Tk"` targets Zynthian's own Tk root window specifically (confirmed class `"tk"`/`"Tk"` in earlier live probes), which VMPK's Qt window (`"vmpk"`/`"VMPK"`) never matches.

### Best-effort, not required
If the window never appears within the poll timeout (something already failed elsewhere, or start-up is unusually slow), the watcher just exits without sending anything - `x11vnc` keeps exporting the full canvas, i.e. today's behavior, not a broken session. No error surfaced to the user beyond that (this is a viewing-quality enhancement, not a correctness requirement).

## Risks / Trade-offs

- [The `-R id:` remote-control channel communicates via an X property on the target display - if a future `x11vnc` invocation ever adds `-novncconnect` (which disables it, per `x11vnc -help`) this would silently stop working] → Neither script uses that flag; noted here so a future edit doesn't add it without noticing this dependency.
- [If `zynthian_main.py` ever creates a secondary `"Tk"`-classed toplevel *before* its main window (unlikely - the main window is created very early in `zynthian_gui.py`'s `__init__`), the watcher could track the wrong window] → Low risk given current startup ordering; not defended against further since the fix is best-effort by design (see Decisions).
- [The observed `x11vnc` warning "New width (1009) is not a multiple of 4" for odd-width windows] → Cosmetic (encoding efficiency only, not a correctness issue); Zynthian's actual `DISPLAY_WIDTH` values in practice are round numbers unlikely to trigger this, and even if one does, the view still works.

## Migration Plan

N/A - purely additive behavior change to existing scripts, no data/state migration. Rollback is deleting the new function/calls.

### `XVFB_SIZE` widened, now that cropping makes over-sizing free
**Found during task 3.2 validation**: `standard`'s computed window width (`CLASSIC_SCREEN_WIDTH * 10 / 6`, derived from whatever baseline `DISPLAY_WIDTH` `zynthian_envars_custom.sh` sets - `2133` with this repo's reference `1600` baseline) is *wider* than the `1910` `XVFB_SIZE` both launchers hardcode - wider than even `device_cables`, the style that constant was originally sized for. The window gets literally clipped by the Xvfb screen boundary: real content (the second mixer channel strip) was missing entirely from the screenshot, not just padded with black. Window-tracking (this change's main fix) can't recover content that was never rendered inside the virtual screen in the first place.

Now that `track_app_window` crops the noVNC view to the actual window regardless of how large the underlying Xvfb canvas is, oversizing `XVFB_SIZE` is free (no visible margin cost - see above), so both launchers' `XVFB_SIZE` width is bumped from `1910` to `2400` to comfortably clear `standard`'s `2133` (with this repo's reference config) plus headroom for a somewhat larger configured baseline `DISPLAY_WIDTH`. This remains a static, config-dependent assumption, not a computed guarantee - the alternative (deriving the exact figure by sourcing `zynthian_envars_custom.sh` and replicating `run_zynthian.sh`'s formula) was already rejected above for the same fragility reasons. Height (`1120`) was already sufficient across all four styles' observed heights and doesn't need changing.

## Open Questions

None - the core mechanism was validated live before writing this design, closing the main uncertainty. The `XVFB_SIZE` widening above was itself found and resolved during validation, not left open.
