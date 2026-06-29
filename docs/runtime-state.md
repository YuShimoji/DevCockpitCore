# DevCockpitCore Runtime State

updated_at: 2026-06-30
active_artifact: c4-scoped-runner-design-review-v1
artifact_current: c4-scoped-runner-design-review-v1
artifact_next: common-foundation-c4-scoped-runner-design-hardening-v1
next: Supervisor decision for C4 design hardening, C4 probe decision packet, controlled-runner stop, or C4 design fix
user_work: none
render_gate: not_applicable
handoff: docs/design/C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md

## Current State

DevCockpitCore has completed observer and foundation automation slices, the
bounded C3 probe/hardening path, C3 second-command design and help-probe
evidence, the C3 second-command acceptance review, option-B candidate
acceptance, and the production C3 help-only probe for `adapters_validate_help`.
The current working slice records a C4 scoped runner design-only boundary while
preserving C3 as the executable ceiling, and the follow-up review accepts that
boundary as design-only evidence.

The latest reviewed remote commit before this C4 design review slice is:

```text
7964c31 docs: design c4 scoped runner boundary
```

`main` tracks `origin/main`.

## Verified Capabilities

- Load read-only adapter manifests.
- Inspect a target git repository with read-only git commands.
- Emit `status_snapshot.v1` JSON.
- Handle missing target repositories and missing upstreams as structured
  warnings.
- Report validation commands without running them in the target repository.
- Normalize AGENT_REPORT-like text into `report_normalization.v1`.
- Classify normalized reports and status snapshots into
  `gate_classification.v1`.
- Run the fixed DevCockpitCore-local validation pack and emit
  `validation_pack_result.v1`.
- Run read-only cross-project smoke observations with structured skipped or
  warning states for absent optional sibling repositories.
- Preserve controlled runner design boundaries without unlocking automation.
- Execute and review the single fixed C3 `status_snapshot_help` probe.
- Record the canonical C3 hardening package with C4, C5, and C6 still locked.
- Evaluate C3 second-command candidates in design-only form.
- Recommend `adapters_validate_help` only as a future Supervisor-approved probe
  candidate; no second command key is implemented in this slice.
- Record bounded help/readback evidence for `adapters_validate_help` without
  adding it to the production controlled runner allowlist.
- Review the second-command evidence and recommend option B: accept
  `adapters_validate_help` as a help-only second C3 command candidate, not as a
  production command implementation.
- Record option B as the selected continuation state: `adapters_validate_help`
  is a help-only accepted candidate, while production C3 command execution still
  accepts only `status_snapshot_help`.
- Execute the production C3 help-only probe for `adapters_validate_help`, mapped
  only to `python -m dev_cockpit.adapters --help`, with hardcoded argv and
  before/after repo-state evidence.
- Review and accept the production C3 help-only probe evidence for
  `adapters_validate_help`; exactly two production C3 command keys are accepted.
- Canonicalize the accepted two-command C3 production state as
  `c3_second_command_hardening.v1`, preserving the exact command set, no-third
  rule, help-only boundary, and C4-C6 locks.
- Record the C3 command set as freeze-ready and recommend
  `common-foundation-c4-scoped-runner-design-v1` only as a separate design-only
  route. C4 implementation remains forbidden.
- Define the C4 scoped runner boundary as design-only. The recommended next
  route is `common-foundation-c4-scoped-runner-design-review-v1`; implementation
  remains forbidden.
- Review and accept the C4 scoped runner design boundary as design-only
  evidence. C4 implementation remains unauthorized, C3 remains the executable
  ceiling, and the recommended next route is
  `common-foundation-c4-scoped-runner-design-hardening-v1`.

## Safety Boundary

This project still has no general execution loop, arbitrary command runner,
scheduler, external notification integration, auto-render workflow, web server,
database, credential handling, or target-repository writeback system.

C3 production execution is limited to exactly two help-only command keys:
`status_snapshot_help` and `adapters_validate_help`. The second key maps only to
`python -m dev_cockpit.adapters --help`. Broad adapter validation, adapter
`default_validation`, target repo writeback, a generalized runner, and C4-C6
remain locked until a separate prompt authorizes a new slice. The current
decision state accepts C4 design as design-only evidence and recommends C4
design hardening as the next useful route. C4 implementation and any further
command expansion remain forbidden.

The current C4 design review accepts the design boundary only. It does not add
execution behavior. C3 remains the executable ceiling until a later Supervisor
prompt authorizes and reviews a separate C4 probe slice.
