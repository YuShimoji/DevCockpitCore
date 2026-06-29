# 2026-06-29 C3 Probe Hardening V1 Handoff

This handoff preserves the current DevCockpitCore context for a fresh terminal
or another agent.

## Source Request

The user asked to keep all context in the project, reflect local state to the
remote, and leave the project ready to resume from another terminal.

## Current Repository State

At handoff refresh start:

```text
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count "HEAD...origin/main"
0 0
```

The latest implementation commit before this handoff refresh was:

```text
43d8737 test: harden controlled runner probe evidence
```

The handoff refresh itself is documentation and repository-hygiene only. It does
not change source behavior, tests, sample schemas, or controlled runner
capabilities.

## Active Artifact

`c3-probe-hardening-v1` is the current active artifact.

Canonical evidence:

- `samples/c3_probe_hardening/c3_probe_hardening_v1.json`
- `samples/controlled_runner_probes/controlled_runner_probe_result_v1_canonical.json`
- `samples/controlled_runner_probe_reviews/controlled_runner_probe_review_result_v1_canonical.json`
- `docs/design/C3_PROBE_HARDENING_V1.md`

The accepted scope is C3 only: one fixed `status_snapshot_help` probe with
hardcoded argv and clean before/after evidence. C4 scoped repo-local runner, C5
cross-project runner, and C6 scheduler or autonomy loop remain locked.

## Completed Capability Stack

- `status-producer-v1`: read-only repository snapshot producer.
- `adapter-manifest-v1`: conservative adapter schema and validation.
- `report-normalizer-v1`: AGENT_REPORT-like text normalization.
- `gate-classifier-v1`: structured gate classification.
- `validation-pack-v1`: fixed DevCockpitCore-local validation checks.
- `cross-project-smoke-v1`: read-only adapter smoke observations.
- `controlled-runner-design-v1`: design-only ladder and boundaries.
- `controlled-runner-probe-v1`: one guarded C3 probe.
- `controlled-runner-probe-review-v1`: C3 evidence review.
- `c3-probe-hardening-v1`: canonical accepted C3 evidence package.

## Safety Boundary

DevCockpitCore still has no general command runner, arbitrary command execution,
execution loop, scheduler, external notification integration, auto-render
workflow, web server, database, credential handling, or target-repository
writeback system.

The validation pack and cross-project smoke remain fixed, local, and bounded.
Adapter `default_validation` strings remain declarative hints unless a later
authorized slice changes that contract.

## Resume Order

From a fresh terminal:

```powershell
cd <DevCockpitCore checkout>
git pull --ff-only origin main
git status --short --branch
git rev-list --left-right --count "HEAD...origin/main"
```

Then read:

1. `docs/runtime-state.md`
2. `docs/project-context.md`
3. `docs/design/C3_PROBE_HARDENING_V1.md`
4. `docs/design/CONTROLLED_RUNNER_PROBE_REVIEW_V1.md`
5. `docs/design/CONTROLLED_RUNNER_PROBE_V1.md`
6. this handoff document

## Validation Commands

These checks were run during the handoff refresh:

```powershell
$py = "<path-to-python-3.11-or-newer>"
& $py -m compileall src tests
$env:PYTHONPATH = "src"; & $py -m unittest discover
$env:PYTHONPATH = "src"; & $py -m dev_cockpit.validation_pack --default --pretty
git diff --check
```

Results:

- `compileall`: passed.
- `unittest discover`: passed, 132 tests.
- `validation_pack --default --pretty`: completed with `warn`, 15 passed, 1
  warning.
- `git diff --check`: passed.
- This run used the Codex bundled Python runtime because the system `python`
  command was a WindowsApps stub.

Known validation warning:

- `samples/reports/agent_report_adapter_manifest_v1_redacted.txt` intentionally
  contains redacted Git action directive examples for report-hygiene coverage.
  The warning is not from this handoff report body.

## Recommended Next Entrances

| Entrance | Requirement | Boundary |
| --- | --- | --- |
| Supervisor decision for next slice | explicit prompt or decision | required before C4-C6 |
| Adapter/report/gate polish | bounded common-foundation scope | no target writeback |
| C3 evidence maintenance | only if evidence becomes stale | do not add command keys |
| C4 design or implementation | separate authorization | no implicit unlock from C3 |

## Local Hygiene Note

`.serena/` is treated as local tool state and ignored by Git. Durable project
context belongs in tracked docs, samples, and design files.
