# C4 Probe Minimal Implementation Handoff

This handoff preserves the current DevCockpitCore continuation context after
`common-foundation-c4-probe-minimal-implementation-v1`.

## Current Repository State

- Branch: `main`
- Last implementation commit before this handoff refresh:
  `ed870bf feat: add minimal c4 validation-pack probe`
- Remote state at handoff check: `main == origin/main`, parity `0 0`
- Worktree state at handoff check: clean
- User-side work: none

## Active Artifact

Current artifact:

- `c4-probe-minimal-implementation-v1`

Primary files:

- `docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_V1.md`
- `samples/c4_probe_minimal_implementation/c4_probe_minimal_implementation_v1.json`
- `samples/c4_probe_minimal_implementation/c4_probe_minimal_result_v1.json`
- `src/dev_cockpit/c4_scoped_runner_probe.py`
- `tests/test_c4_probe_minimal_implementation.py`

## Current Capability Boundary

C3 command keys remain exactly:

```text
status_snapshot_help
adapters_validate_help
```

C4 is implemented only as one bounded repo-local probe:

```text
validation_pack_default_pretty
```

That C4 key maps only to:

```text
python -m dev_cockpit.validation_pack --default --pretty
```

The C4 probe is hardcoded, shell-disabled, timeout-bound, redacted, and records
before/after repository state. Config may select only the allowed key; it cannot
provide command text, executable, argv, args, shell, cwd, environment, retries,
credentials, endpoints, or write targets.

Still forbidden:

- third C3 command.
- multiple C4 commands.
- generalized runner.
- arbitrary command execution.
- adapter validation as controlled runner behavior.
- adapter `default_validation` through `controlled_runner_probe`.
- target repository writeback.
- cross-project execution.
- scheduler/autonomy.
- credentials or external services.
- destructive git, rebase/reset/stash automation, force push.
- C5 or C6 unlock.

## Last Validation Memory

Last known validation for the implementation slice:

- `python -m compileall src tests`: pass.
- `python -m unittest discover`: 270 tests OK.
- `python -m json.tool samples/c4_probe_minimal_implementation/c4_probe_minimal_implementation_v1.json`: pass.
- `python -m json.tool samples/c4_probe_minimal_implementation/c4_probe_minimal_result_v1.json`: pass.
- C3 `adapters_validate_help` probe: pass 11/11, green.
- C4 `validation_pack_default_pretty` probe: exit 0; result warn 18/18 because of the known pseudo-git-tag fixture warning only.
- `python -m dev_cockpit.validation_pack --default --pretty`: warn only for historical pseudo-git-tag fixture residue.
- `python -m dev_cockpit.cross_project_smoke --default --pretty`: DevCockpitCore passed; optional sibling warnings only.
- `python -m dev_cockpit.adapters --validate adapters/*.json`: all adapters OK.
- `git diff --check`, `git diff --cached --check`, and conflict-marker scan: pass.

Known non-blocking warnings:

- Historical pseudo-git-tag fixture warning in
  `samples/reports/agent_report_adapter_manifest_v1_redacted.txt`.
- Optional sibling warnings in cross-project smoke. They are observation-only
  and do not change the DevCockpitCore boundary.

## Resume Steps

From a fresh terminal:

```bash
git status --short --branch
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count HEAD...origin/main
```

Then read, in order:

1. `docs/runtime-state.md`
2. `docs/project-context.md`
3. `docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_V1.md`
4. `samples/c4_probe_minimal_implementation/c4_probe_minimal_result_v1.json`
5. `docs/design/C4_PROBE_AUTHORIZATION_REVIEW_V1.md`
6. `samples/c4_probe_authorization_review/c4_probe_authorization_review_v1.json`

## Recommended Next Route

Recommended next slice:

```text
common-foundation-c4-probe-minimal-implementation-review-v1
```

That next slice should review the implementation evidence and decide whether to
accept the single C4 probe, ask for a narrow fix, route to validation fixture
hygiene, or stop.

No user work is required before the next route.
