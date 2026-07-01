# DevCockpitCore Idea Ledger

This file parks future directions and rejected paths so they do not get mixed
into the current slice.

## Active Seeds

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
