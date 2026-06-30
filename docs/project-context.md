# DevCockpitCore Project Context

DevCockpitCore is a cross-project development supervision substrate. Its first
purpose is to make project state easier to resume by producing structured,
read-only snapshots of target repositories.

## Readiness Lanes

- Foundation Observer Readiness: status schema, status producer, adapter config,
  tests, and docs.
- Foundation Automation Readiness: report normalizer, gate classifier,
  validation pack, and reusable project adapters.
- Execution Automation Readiness: controlled runner design and evidence gates
  after observer and classifier slices are mature.
- Project/Product Readiness: project-specific readiness stays outside this
  repository unless represented through adapters or snapshots.

## Current Development Axis

The current axis is common-foundation execution-readiness governance. The repo
has moved through read-only observation, report interpretation, validation
packaging, cross-project smoke observation, a bounded C3 help-probe surface,
C4 design-only boundary review, C4 design-state hardening, a decision-only C4
probe authorization packet plus authorization review, and a single bounded C4
validation-pack probe implementation.

The active artifact is `c4-probe-minimal-implementation-v1`. It implements only
the `validation_pack_default_pretty` C4 command key and recommends
`common-foundation-c4-probe-minimal-implementation-review-v1` as the next route.
C3 remains the executable ceiling for the prior command set, and C4 is limited
to one repo-local validation-pack probe.

## Completed Artifact Stack

- `status-producer-v1`
- `adapter-manifest-v1`
- `report-normalizer-v1`
- `gate-classifier-v1`
- `validation-pack-v1`
- `cross-project-smoke-v1`
- `controlled-runner-design-v1`
- `controlled-runner-probe-v1`
- `controlled-runner-probe-review-v1`
- `c3-probe-hardening-v1`
- `c3-second-command-design-v1`
- `c3-second-command-help-probe-v1`
- `c3-second-command-acceptance-review-v1`
- `c3-second-command-candidate-acceptance-v1`
- `c3-second-command-production-probe-v1`
- `c3-second-command-production-probe-review-v1`
- `c3-second-command-hardening-v1`
- `c3-command-set-freeze-and-c4-design-decision-v1`
- `c4-scoped-runner-design-v1`
- `c4-scoped-runner-design-review-v1`
- `c4-scoped-runner-design-hardening-v1`
- `c4-probe-decision-packet-v1`
- `c4-probe-authorization-review-v1`
- `c4-probe-minimal-implementation-v1`

## Current Capability Boundary

The implementation remains a standard-library Python package named
`dev_cockpit`.

Primary observer entry point:

```bash
python -m dev_cockpit.status_snapshot --repo <repo> --adapter <adapter.json> --output <status.json>
```

The accepted production C3 command keys are exactly:

```text
status_snapshot_help
adapters_validate_help
```

Both are fixed help/readback probes. `adapters_validate_help` maps only to:

```text
python -m dev_cockpit.adapters --help
```

It does not execute `adapters --validate`, adapter `default_validation`, target
repository writeback, scheduler/autonomy behavior, credentials, external
services, or arbitrary command execution.

C4 is implemented only as a single bounded probe in
`src/dev_cockpit/c4_scoped_runner_probe.py`. The C4 command set is exactly:

```text
validation_pack_default_pretty
```

That key maps only to:

```text
python -m dev_cockpit.validation_pack --default --pretty
```

It uses hardcoded argv, shell disabled, timeout, output truncation, redaction,
and before/after repository state evidence. A third C3 command, multiple C4
commands, C5, C6, arbitrary execution, adapter validation as controlled command
behavior, and target repository writeback remain unauthorized.

## Current Restart Surface

Start a new terminal or agent from:

1. `AGENTS.md`
2. `docs/runtime-state.md`
3. `docs/project-context.md`
4. `docs/handoffs/2026-06-30-c4-scoped-runner-design-review-handoff.md`
5. `docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_V1.md`
6. `samples/c4_probe_minimal_implementation/c4_probe_minimal_implementation_v1.json`
7. `samples/c4_probe_minimal_implementation/c4_probe_minimal_result_v1.json`
8. `docs/design/C4_PROBE_AUTHORIZATION_REVIEW_V1.md`
9. `samples/c4_probe_authorization_review/c4_probe_authorization_review_v1.json`
10. `docs/design/C4_PROBE_DECISION_PACKET_V1.md`
11. `samples/c4_probe_decision_packet/c4_probe_decision_packet_v1.json`
12. `docs/design/C4_SCOPED_RUNNER_DESIGN_HARDENING_V1.md`
13. `samples/c4_scoped_runner_design_hardening/c4_scoped_runner_design_hardening_v1.json`
14. `docs/design/C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md`
15. `docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md`
16. `docs/design/C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md`
17. `docs/design/C3_SECOND_COMMAND_HARDENING_V1.md`
18. `docs/decision-log.md`
19. `docs/idea-ledger.md`

Then verify live state with:

```bash
git status --short --branch
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count HEAD...origin/main
```

Use the active Python runtime with `PYTHONPATH=src` for validation.

## Design Bias

DevCockpitCore should keep early execution-readiness slices narrow and
inspectable. Prefer machine-readable artifacts, explicit safety boundaries,
standard-library Python, local tests, and conservative unknowns over premature
automation.

Missing upstreams, missing sibling repositories, absent optional project docs,
and historical report-fixture residue should become structured warnings unless
they affect the current DevCockpitCore capability boundary.
