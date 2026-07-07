# DevCockpitCore Idea Ledger

This file parks future directions and rejected paths so they do not get mixed
into the current slice.

## Active Seeds

### Progress-Driven Report Evolution

Purpose: make the deterministic dashboard report wording react to blocker,
warning, freshness, and access-state mixes instead of staying as a fixed brief.

Effect: should improve the dashboard's first-scan usefulness as source
evidence changes. It must not add a reporting engine, server, telemetry,
scheduler, external service, or target-repository writeback.

Requirements: keep source paths and generated evidence visible, keep Review
Actions non-executable, preserve the report-first layout, and keep top-level
copy concise.

State: optional next review-surface route after visual acceptance of
`dashboard-report-first-frontpage-v1`.

Owner: Supervisor or user should choose this only after judging that the layout
is right but the report language needs evidence-aware variation.

Next move: use `progress-driven-report-evolution-v1` only from a matching
prompt.

### Japanese Display Polish

Purpose: refine the compact dark dashboard labels after human visual review,
especially for Japanese or machine-translated reading.

Effect: should improve dashboard readability only. It must not introduce a full
i18n system, external CSS/JS, a server, or any execution capability.

Requirements: keep Review Actions non-executable, keep source evidence
available, preserve keyboard/focus/print behavior, and avoid raw long enum
values in top-card headline text.

State: allowed next review-surface route after
`dashboard-compact-dark-overview-v1`.

Owner: Supervisor or user visual review should decide whether this is worth
doing before more C4 hardening.

Next move: use `japanese-display-polish-v1` only if the compact dark overview
still feels hard to scan after opening the generated local dashboard.

### C4 Probe Minimal Implementation Hardening

Purpose: make the accepted single C4 validation-pack probe review canonical and
easier to resume later.

Effect: should tighten docs/tests/samples and restart context only; it must not
add another C4 command or change the existing probe implementation.

Requirements: preserve the exact two-key C3 command set, keep exactly one
accepted C4 key, keep C5/C6 locked, and keep adapter validation outside
controlled runner behavior.

State: recommended next route after
`c4-probe-minimal-implementation-review-v1`.

Owner: Supervisor must authorize; Agent may implement only after a matching
prompt.

Next move: generate and execute
`common-foundation-c4-probe-minimal-implementation-hardening-v1` if selected.

### Validation Fixture Hygiene

Purpose: remove or reclassify the historical pseudo-git-tag fixture warning so
the validation pack can return pass instead of warn when no current issue is
present.

Effect: should improve validation signal quality without changing controlled
runner capability.

Requirements: keep report-normalizer and validation-pack semantics explicit;
do not hide real copy-transport residue or weaken hygiene gates.

State: allowed alternative route after the C4 probe review, not required before
acceptance.

Owner: Supervisor decision.

Next move: use only if clean validation signal is more valuable than hardening
the accepted C4 probe state.

## Parked Or Forbidden Paths

### Direct C4 Implementation

Purpose: would create new runnable behavior.

Effect: expands capability beyond accepted evidence.

Requirements: forbidden until a later prompt authorizes a scoped probe route and
the evidence is reviewed.

State: parked as forbidden except for the already reviewed single
`validation_pack_default_pretty` C4 probe.

Owner: User/Supervisor approval required before any reconsideration.

Next move: do not add any second C4 command or generalized runner from the
current state.

### Third C3 Command

Purpose: would expand the frozen C3 command set.

Effect: reopens C3 surface area instead of preserving the accepted two-key set.

Requirements: forbidden unless a later prompt explicitly reopens C3 command
design.

State: parked as forbidden.

Owner: Supervisor approval required.

Next move: do not add.

### C5/C6 Automation

Purpose: cross-project runner or scheduler/autonomy behavior.

Effect: creates a much broader execution-automation lane.

Requirements: separate design, user approval, monitoring and stop controls,
credential policy, and review/hardening path.

State: locked.

Owner: User/Supervisor approval required.

Next move: do not pursue from current common-foundation C4 probe-review state.
