## REMOVED Requirements

### Requirement: Headless Docker boot verification
**Reason**: Superseded by `workflow-smoke-testing`, which drives both native and Docker sessions through the same shared engine instead of a Docker-only script, closing the maintenance-drift risk of keeping two independent test mechanisms.
**Migration**: Use `workflow-smoke-testing`'s Docker-targeted runs; GUI-render confirmation is covered by that capability's per-step assertions rather than a standalone boot check.

### Requirement: Automated MIDI-to-audio signal path verification
**Reason**: Superseded by `workflow-smoke-testing`'s round-trip reload verification and per-workflow audio checks, which build the active chain live via MIDI-injected CUIA actions instead of loading a single committed fixture.
**Migration**: The single fixture-based scenario this requirement covered is ported forward as the first workflow script in `workflow-smoke-testing`'s starting library.

### Requirement: Clean teardown on every exit path
**Reason**: Superseded by `workflow-smoke-testing`'s equivalent teardown requirement, which covers both native and Docker sessions instead of Docker containers only.
**Migration**: Use `workflow-smoke-testing`'s teardown behavior.

### Requirement: Fail-fast on device contention
**Reason**: Superseded by `workflow-smoke-testing`'s equivalent contention-detection requirement, which covers both native and Docker sessions instead of Docker containers only.
**Migration**: Use `workflow-smoke-testing`'s contention detection.
