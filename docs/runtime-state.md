# DevCockpitCore Runtime State

updated_at: 2026-06-30
active_artifact: c4-probe-minimal-implementation-v1
artifact_current: c4-probe-minimal-implementation-v1
artifact_next: common-foundation-c4-probe-minimal-implementation-review-v1
next: Review the single bounded C4 validation-pack probe, validation fixture hygiene, C4 design follow-up fix, or controlled-runner stop
user_work: none
render_gate: not_applicable
handoff: docs/handoffs/2026-06-30-c4-scoped-runner-design-review-handoff.md
latest_source_design_review_commit: 0598bee test: review c4 scoped runner design
latest_remote_handoff_refresh_commit: b99d8c6 docs: refresh c4 review handoff state
remote_sync_state_at_hardening_start: main == origin/main, parity 0 0
latest_hardening_commit: 763f9e9 test: harden c4 scoped runner design
latest_decision_packet_commit: 8f3312b docs: decide c4 probe authorization path
latest_authorization_review_commit: 53b3f45 test: review c4 probe authorization path

## Current State

DevCockpitCore has completed observer and foundation automation slices, the
bounded C3 probe/hardening path, C3 second-command design and help-probe
evidence, the C3 second-command acceptance review, option-B candidate
acceptance, and the production C3 help-only probe for `adapters_validate_help`.
The current state records a C4 scoped runner design-only boundary, accepts that
boundary as design-only evidence, and hardens it as the canonical policy state
without authorizing implementation. The current decision packet recommends
reviewing whether a future single fixed safe C4 probe should be authorized
later, the authorization review accepts eligibility for a future separate
minimal C4 probe implementation prompt, and the current slice implements only
that single bounded C4 validation-pack probe.

The source design review commit hardened by this slice is:

```text
0598bee test: review c4 scoped runner design
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
  ceiling, and the review route is complete.
- Canonicalize the accepted C4 design-only state as
  `c4_scoped_runner_design_hardening.v1`, resolve the stale
  `docs/project-context.md` review-state debt, and constrain the next useful
  route to `common-foundation-c4-probe-decision-packet-v1` as decision-only.
- Record `c4_probe_decision_packet.v1` with recommendation
  `recommend_c4_probe_authorization_later` and next route
  `common-foundation-c4-probe-authorization-review-v1`. This packet is
  decision-only and does not implement a C4 probe.
- Review the C4 probe decision packet as
  `c4_probe_authorization_review.v1`, decide
  `accepted_for_future_probe_prompt`, and recommend
  `common-foundation-c4-probe-minimal-implementation-v1` only as a future
  separate Supervisor-prompted slice. This review does not implement a C4
  probe.
- Implement the single bounded C4 `validation_pack_default_pretty` probe as
  `c4_probe_minimal_result.v1`, with hardcoded argv, shell disabled, timeout,
  output truncation, redaction, before/after repo state, no target repo
  writeback, no adapter validation controlled command, and C5/C6 locked.

## Safety Boundary

This project still has no general execution loop, arbitrary command runner,
scheduler, external notification integration, auto-render workflow, web server,
database, credential handling, or target-repository writeback system.

C3 production execution is limited to exactly two help-only command keys:
`status_snapshot_help` and `adapters_validate_help`. The second key maps only to
`python -m dev_cockpit.adapters --help`. Broad adapter validation, adapter
`default_validation`, target repo writeback, a generalized runner, and C4-C6
remain locked outside the single C4 probe. The current C4 implementation is
limited to exactly one command key, `validation_pack_default_pretty`, mapped
only to `python -m dev_cockpit.validation_pack --default --pretty`.

C3 remains the executable ceiling for the prior command set. C4 is unlocked
only for this one repo-local validation-pack probe. Any further C4 command,
general runner behavior, C5, or C6 remains forbidden until a later Supervisor
prompt authorizes and reviews it.

## Handoff Snapshot

This minimal implementation keeps all current re-entry context in project docs. The
next terminal should start from this file, `docs/project-context.md`, and
`docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_V1.md`, then verify current remote
parity before making decisions.

First live checks:

```bash
git status --short --branch
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count HEAD...origin/main
```

Last known full validation during this minimal-implementation slice:

- `python -m unittest discover`: 270 tests OK.
- C4 `validation_pack_default_pretty` probe: warn 18/18 with clean before/after
  worktree; known pseudo-git-tag fixture warning only.
- C3 `adapters_validate_help` probe: pass 11/11 after commit; dirty warning
  only while the implementation patch was uncommitted.
- `validation_pack --default`: warn only for historical pseudo-git-tag fixture
  residue.
- `cross_project_smoke --default`: DevCockpitCore passed after commit; optional
  sibling warnings only.

This minimal implementation intentionally changes only the single bounded C4
probe surface, docs, tests, and samples. It does not change C3 command keys,
adapters, target repositories, or sibling repositories.
