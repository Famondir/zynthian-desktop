## Why

Newer readline/libedit emit bracketed-paste-mode ANSI escapes (`ESC[?2004h`/`ESC[?2004l`) around FluidSynth's interactive `"> "` prompt, which broke the exact regex `pexpect` used to detect it, and the anchored `.match()` used to check for "loaded SoundFont has ID N" failed when that line had a leading escape/CR. Together these made `load_soundfont()` report failure - and silently retry the *entire* load - even though the soundfont had already loaded successfully, making large soundfonts look like they take minutes and then fail. Submitted upstream as a standalone PR.

## What Changes

- Prompt detection now matches plain `"> "` text instead of modeling the exact bracketed-paste escape sequence.
- The "loaded SoundFont has ID" check uses `re.search()` instead of `re.match()`, since anchored matching fails when a line has a leading escape/CR before the text.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `desktop-engine-reliability`: adds the requirement that FluidSynth's interactive-CLI prompt/output detection is robust to bracketed-paste-mode ANSI escapes.

## Impact

- `zyngine/zynthian_engine_fluidsynth.py` (`command_prompt`, `load_soundfont`).
- Submitted upstream as `fix/fluidsynth-prompt-detection` against `zynthian/zynthian-ui`.
