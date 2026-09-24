## 1. Shared helper

- [x] 1.1 Add a `track_app_window` function to `novnc_viewer.sh`: forks a background loop that polls `DISPLAY="$VNC_DISPLAY" xdotool search --class "Tk"` (bounded timeout, not indefinite) for the app's window, waits a short settle delay once found, then sends `x11vnc -display "$VNC_DISPLAY" -R "id:<windowid>"`; sets `WINDOW_TRACKER_PID` for the caller's own cleanup trap
- [x] 1.2 If the timeout elapses with no window found, the loop exits quietly (no error) - `x11vnc` keeps exporting the full canvas

## 2. Wire into both launchers

- [x] 2.1 `run_zynthian_vnc.sh`: call `track_app_window` after `start_novnc_viewer`, before the foreground `DISPLAY=... /zynthian/run_zynthian.sh "$GUI_STYLE"` line (unchanged)
- [x] 2.2 `run_zynthian_docker.sh` (`novnc` mode only): call `track_app_window` after `start_novnc_viewer`, before the foreground `docker run` line (unchanged)
- [x] 2.3 Both scripts' `cleanup()`: add `$WINDOW_TRACKER_PID` to the existing `kill` list alongside `XVFB_PID`/`X11VNC_PID`/`WEBSOCKIFY_PID`

## 3. Validation

- [x] 3.1 Native, `classic` style: confirm the noVNC view fills with no black margin. Confirmed: `x11vnc` log showed `rfbNewFramebuffer(..., 1600, 960, ...)` after the tracker fired - matches `classic`'s actual window exactly, down from the full `1910x1120` canvas the pre-fix screenshot showed padded with black.
- [x] 3.2 Native, `standard` style: same check. **Found and fixed an additional, related bug during this task**: `standard`'s computed width (`2133`, with this repo's reference `1600` baseline `DISPLAY_WIDTH`) exceeds `device_cables`' own `1910`, which both launchers' `XVFB_SIZE` was hardcoded to - the window was genuinely clipped (a screenshot showed the second mixer channel missing entirely, not just padded). Since `track_app_window` makes oversizing `XVFB_SIZE` free (no visible-margin cost), widened it to `2400` in both scripts - re-tested, `rfbNewFramebuffer(..., 2133, 800, ...)` now matches exactly, confirmed visually complete (both mixer channels present).
- [x] 3.3 Native, `device`/`device_cables`: confirm no regression. Confirmed no regression for `device_cables` (`rfbNewFramebuffer` still `1910x1120`, exact match) - and confirmed `device`'s own long-standing `1910x960`-vs-`1910x1120` shortfall (160px of previously-black bottom margin) is now also gone (`rfbNewFramebuffer(..., 1910, 960, ...)`, exact match).
- [x] 3.4 Docker, `novnc` mode, at least one smaller style: confirm the same fit behavior applies there too. Confirmed: Docker `classic` showed `rfbNewFramebuffer(..., 1600, 960, ...)`, same exact fit as the native case.
- [x] 3.5 Confirm `Ctrl+C`/teardown still works cleanly - no orphaned processes. Confirmed across every test run above (native `kill -9` cascade and Docker `docker kill` cascade): no orphaned `Xvfb`/`x11vnc`/`websockify`/`zynthian_main`/container processes, host PipeWire back to `active` every time.
- [x] 3.6 Confirm a VMPK window running on the same display does not get mistakenly tracked. Confirmed: with VMPK running alongside a `device`-style session on the same display, `xdotool search --class "Tk"` returned only Zynthian's window (VMPK's own window and sub-widgets all excluded) - `track_app_window`'s class-based matching correctly discriminates, and in practice never even raced with VMPK anyway since the tracker fires once at startup, before a developer would typically launch VMPK afterward.
