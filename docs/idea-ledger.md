# DevCockpitCore Idea Ledger

This file parks future directions and rejected paths so they do not get mixed
into the current slice.

## Active Seeds

### C4 Design Hardening

Purpose: make the accepted C4 design-only boundary canonical and easier to
review later.

Effect: should tighten docs/tests/samples only; it must not create C4 runtime
behavior.

Requirements: preserve C3 as the executable ceiling, keep exact two production
C3 keys, keep C4/C5/C6 locked, and keep adapter validation outside
`controlled_runner_probe`.

State: recommended next route after `c4-scoped-runner-design-review-v1`.

Owner: Supervisor must authorize; Agent may implement only after a matching
prompt.

Next move: generate and execute
`common-foundation-c4-scoped-runner-design-hardening-v1` if selected.

### C4 Probe Decision Packet

Purpose: decide whether a future C4 probe is worth proposing.

Effect: should remain a decision artifact, not implementation.

Requirements: no direct C4 implementation, no command registry from config, no
third C3 command, and no target repository writeback.

State: allowed alternative route, not selected as the default.

Owner: Supervisor decision.

Next move: use only if hardening is not the best next step.

## Parked Or Forbidden Paths

### Direct C4 Implementation

Purpose: would create new runnable behavior.

Effect: expands capability beyond accepted evidence.

Requirements: forbidden until a later prompt authorizes a scoped probe route and
the evidence is reviewed.

State: parked as forbidden.

Owner: User/Supervisor approval required before any reconsideration.

Next move: do not implement from the current state.

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

Next move: do not pursue from current common-foundation C4 design-review state.
