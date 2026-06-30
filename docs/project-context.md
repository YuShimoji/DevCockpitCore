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
packaging, cross-project smoke observation, a bounded C3 help-probe surface, and
C4 design-only boundary review.

The active artifact is `c4-scoped-runner-design-review-v1`. It accepts the C4
scoped runner design as design-only evidence and recommends
`common-foundation-c4-scoped-runner-design-hardening-v1` as the next safe route.

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

## Current Capability Boundary

The implementation remains a standard-library Python package named
`dev_cockpit`.

Primary observer entry point:

```bash
python -m dev_cockpit.status_snapshot --repo <repo> --adapter <adapter.json> --output <status.json>
```

The current production controlled-runner probe surface is C3 only. The accepted
production C3 command keys are exactly:

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

C4 is accepted only as a design boundary. C4 implementation, a third C3 command,
C5, C6, arbitrary execution, adapter validation as controlled command behavior,
and target repository writeback remain unauthorized.

## Current Restart Surface

Start a new terminal or agent from:

1. `AGENTS.md`
2. `docs/runtime-state.md`
3. `docs/project-context.md`
4. `docs/handoffs/2026-06-30-c4-scoped-runner-design-review-handoff.md`
5. `docs/design/C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md`
6. `docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md`
7. `docs/design/C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md`
8. `docs/design/C3_SECOND_COMMAND_HARDENING_V1.md`
9. `docs/decision-log.md`
10. `docs/idea-ledger.md`

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
