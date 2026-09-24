## Context

`device_cables` is a `zynthian_gui_touchkeypad_v5.py` keypad style that draws a labelled "cable" line down from the top edge for every live audio/MIDI port, grouped into 4 x-anchored columns (audio-in, MIDI-in, MIDI-out, audio-out) plus a static LAN indicator. The space for this sits in a `cable_margin` strip above the V5 chassis render, currently a constant 160px (`zynthian_gui_touchkeypad_v5.py:168`). That constant isn't just a drawing detail - it's baked into three places that all have to agree:

- `zynthian_gui_touchkeypad_v5.py`'s own `cable_margin`, `top_margin`, chassis-image placement, and the knob hit-area vertical offset (`cable_margin + V5_KNOB_ROWS[index]`, line 548).
- `run_zynthian.sh`'s `device_cables` branch, which sets `DISPLAY_HEIGHT=1120` (`V5_IMAGE_SIZE[1]` 960 + margin 160) *before* the Python process starts - this is what actually determines the Tk canvas/window's height, since `zynthian_gui_touchkeypad_v5.py:141-146` creates the canvas with `height=zynthian_gui_config.display_height` and the Tk root's `minsize`/`maxsize` locks to it (per `run_zynthian_vnc.sh`'s own comment).
- `run_zynthian_vnc.sh`'s `XVFB_SIZE` (`2400x1120x24`), whose height was chosen specifically because it "already covers all four styles' observed heights" - i.e. it's a ceiling on top of the ceiling above.

Live testing with a Fisa Suprema (USB, MIDI+audio) and Yamaha AG03MK2 (USB-C) connected together showed the label stacks in the MIDI-in/MIDI-out columns overflowing 160px: `draw_connections()`'s vertical placement (`y = (self.cable_margin - block_h) // 2`, line 440) centers each column's label block independently, with no clamp - a column whose `block_h` exceeds `cable_margin` gets a negative `y` and its top rows render above the visible canvas, and because different columns can each compute their own (independently negative or small) `y`, two unrelated columns' content can end up overlapping (observed: the LAN group's "network" chip landing on top of a MIDI-out row).

## Goals / Non-Goals

**Goals:**
- All connected devices' cable labels stay fully visible (no clipping against the canvas edge) for realistic simultaneous device counts (e.g. 2 audio interfaces, each also contributing a MIDI port, plus the existing `zynsmf`/`zynseq`/`CV-Gate`/`ZynMaster`/`ZynMidiRouter` internal MIDI routing entries already seen in normal operation).
- No visual overlap between different port-category columns, even if one column is much taller than another.
- Keep the 3-way constant agreement (`zynthian_gui_touchkeypad_v5.py`'s `cable_margin`, `run_zynthian.sh`'s `DISPLAY_HEIGHT`, `run_zynthian_vnc.sh`'s `XVFB_SIZE` height) intact rather than letting any one of them silently become the new bottleneck.
- Keep `touchkeypad-encoder-controls`' knob-to-graphic alignment correct at the new margin size (it already reads `cable_margin`, so this falls out of keeping that one source of truth authoritative - just needs verifying, not new code).

**Non-Goals:**
- True runtime window resizing (canvas/window growing or shrinking live as devices come and go). The Tk window's height is fixed for the process's lifetime by `run_zynthian.sh` before Python starts; changing that would mean lifting the `minsize`/`maxsize` lock `run_zynthian_vnc.sh` documents, a materially bigger change than this overflow fix needs.
- Scrollable per-column lists. Unnecessary interaction complexity (touch-scroll gesture + indicator) for a diagnostic overlay that already redraws every 3s (`refresh_connections()`); a big-enough fixed budget plus graceful degradation covers realistic use.
- Handling truly unbounded device counts perfectly (e.g. 20 simultaneous MIDI devices). The truncation/"+N more" fallback (see Decisions) exists so that case degrades safely, not so it displays perfectly.

## Decisions

### Pick a new fixed `cable_margin` empirically, not computed from a theoretical maximum
Real port lists include entries beyond just physically-plugged devices (`zynsmf:midi_out`, `zynseq:output`, `CV/Gate`, `ZynMaster:midi_in`, `ZynMidiRouter:seq_in` all show up alongside actual hardware in the observed screenshot), so a "theoretical max" is unbounded in principle. Rather than trying to derive a provably-sufficient number, pick a new constant sized to comfortably fit what's actually been observed with 2 real USB audio/MIDI interfaces connected at once (the realistic ceiling for this project's hardware), with headroom - then rely on the graceful-degradation fix below for anything beyond that, rather than chasing a perfect bound.

### Clamp/top-align instead of naive full centering
Change `y = (self.cable_margin - block_h) // 2` to clamp at a small fixed top inset (e.g. `y = max(2, (self.cable_margin - block_h) // 2)`) per column. This keeps the current centered look for columns that fit comfortably (the common case), while a column that doesn't fit renders starting from the top instead of starting above the canvas - so it's still readable (bottom rows may run close to/under the chassis image edge in the worst case) rather than having its *top* rows silently vanish. Combined with the larger margin, this should be enough that the visually broken case (invisible top rows, cross-column overlap) doesn't happen in practice; a column that still doesn't fit at all is truncated with a final "+N more" chip rather than being left to overlap a neighboring column's cable, since overlap (data from two unrelated devices rendered on top of each other) is more misleading than a clearly-marked "there's more, not shown here."

### Update all three size constants together, verified live
`zynthian_gui_touchkeypad_v5.py`'s `cable_margin`, `run_zynthian.sh`'s `device_cables` `DISPLAY_HEIGHT`, and `run_zynthian_vnc.sh`'s `XVFB_SIZE` height all move together by the same delta. Verify via the same live noVNC session used to discover this bug (Fisa Suprema + AG03MK2 connected) that: the Tk window is actually taller now, `track_app_window`'s window-ID-based crop follows it with no visible black margin or clipping, and the knob hit-areas (`touchkeypad-encoder-controls`) still line up with their graphics at the new offset.

## Risks / Trade-offs

- Picking the new constant empirically (not from a hard bound) means a sufficiently unusual future setup (many more simultaneous devices) could still hit the truncation fallback - accepted per Non-Goals; the fallback exists precisely for that case and degrades safely rather than silently.
- The three-constants-in-sync approach is the same kind of implicit-coupling fragility the codebase already has here (nothing enforces agreement between them today either) - not solved by this change, just carried forward at a new value. Worth a one-line comment cross-referencing all three locations so a future change to any one of them doesn't quietly break the others.
