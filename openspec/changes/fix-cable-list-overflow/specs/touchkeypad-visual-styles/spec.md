## ADDED Requirements

### Requirement: device_cables cable list stays visible under load
The `device_cables` style's cable/connection indicators SHALL remain fully visible within the cable-graphics margin - no label clipped off the top edge of the canvas, and no overlap between indicators belonging to different port categories (audio-in, MIDI-in, MIDI-out, audio-out, LAN) - for the realistic range of simultaneously connected devices this project's hardware produces.

#### Scenario: Several devices connected across multiple port categories
- **WHEN** enough audio/MIDI devices are connected at once that one or more port-category columns' label stacks would exceed the cable-graphics margin's available height
- **THEN** every label that fits within the enlarged margin renders fully visible and top-aligned within its column, with no label clipped above the canvas edge and no overlap with another column's labels

#### Scenario: A single column's content still exceeds the available margin
- **WHEN** one port-category column's label stack is taller than the cable-graphics margin even after accounting for the sizing this change introduces
- **THEN** that column renders as many labels as fit, followed by a final "+N more" indicator summarizing the rest, rather than clipping a label silently or overlapping a neighboring column
