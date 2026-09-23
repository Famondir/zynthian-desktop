## Context

`_get_preset_list()` has two branches: one for presets inside a subdirectory (which correctly checks `filext[1:].lower() in cls.preset_fexts`), and one for files placed directly at the bank's top level (which hardcoded `filext.lower() == ".sfz"`). Both branches should honour the same `preset_fexts = ["sfz", "dspreset"]` list.

## Goals / Non-Goals

**Goals:**
- Bank-root `.dspreset` files are discovered exactly like bank-root `.sfz` files.

**Non-Goals:**
- Adding support for further preset formats - `preset_fexts` already defines the supported set; this fix only makes both code paths respect it consistently.

## Decisions

- Change the top-level check from `filext.lower() == ".sfz"` to `filext[1:].lower() in cls.preset_fexts`, mirroring the subdirectory branch exactly.

## Risks / Trade-offs

- None - this only adds recognition for files that were previously silently ignored; no existing behaviour changes for `.sfz` files.
