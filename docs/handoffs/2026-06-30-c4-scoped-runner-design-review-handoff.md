# 2026-06-30 C4 Scoped Runner Design Review Handoff

## Stop Edge

DevCockpitCore is synced on `main`. The last accepted product slice is
`c4-scoped-runner-design-review-v1`, pushed as:

```text
0598bee test: review c4 scoped runner design
```

This handoff refresh records the same context in repo-local docs so another
terminal can resume without relying on chat history.

## What Finished

- C4 scoped runner design was reviewed and accepted as design-only evidence.
- C3 remains the executable ceiling.
- Production C3 command keys remain exactly `status_snapshot_help` and
  `adapters_validate_help`.
- C4 implementation remains unauthorized.
- Recommended next route is
  `common-foundation-c4-scoped-runner-design-hardening-v1`.

## What Remains

Purpose: choose the next allowed continuation route.

Effect: the next slice should either harden the accepted design boundary, create
a decision packet for a possible future C4 probe, stop, or fix a design issue.

Requirements: no direct C4 implementation, no third C3 command, no arbitrary
execution, no adapter validation as controlled command behavior, no target repo
writeback, no scheduler/autonomy, and no C5/C6 unlock.

State: ready for Supervisor decision.

Owner: Supervisor selects; Agent executes only the authorized slice.

Next move: prefer `common-foundation-c4-scoped-runner-design-hardening-v1`.

## What Was Intentionally Not Touched

- No production source changes.
- No adapters changed.
- No C3 command-key changes.
- No C4 implementation.
- No sibling repository changes, including NLMYTGen.
- No scheduler, notification, web server, database, credential, or external
  service behavior.

## Restart Order

1. `AGENTS.md`
2. `docs/runtime-state.md`
3. `docs/project-context.md`
4. `docs/decision-log.md`
5. `docs/idea-ledger.md`
6. `docs/design/C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md`
7. `docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md`
8. `docs/design/C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md`

## First Checks In A New Terminal

```bash
git status --short --branch
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count HEAD...origin/main
```

Then run focused validation as needed:

```bash
PYTHONPATH=src python -m unittest discover
PYTHONPATH=src python -m dev_cockpit.validation_pack --default --pretty
PYTHONPATH=src python -m dev_cockpit.cross_project_smoke --default --pretty
```

On Windows PowerShell, set `PYTHONPATH` with:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover
```

Use the active Codex or project Python runtime rather than a WindowsApps stub.

## Last Known Validation

- `python -m unittest discover`: 221 tests OK.
- C3 `adapters_validate_help` controlled probe: pass 11/11, green.
- `python -m dev_cockpit.adapters --validate adapters/*.json`: all four
  adapters OK.
- `validation_pack --default`: warning only for historical pseudo-git-tag
  fixture residue in `samples/reports/agent_report_adapter_manifest_v1_redacted.txt`.
- `cross_project_smoke --default`: DevCockpitCore passed; optional sibling
  warnings remained for NLMYTGen branch mismatch and missing optional runtime
  docs in WritingPage/ClipPipeGen.

## Unresolved Question

The next useful route is likely C4 design hardening, but Supervisor may instead
choose a C4 probe decision packet, controlled-runner stop, or C4 design fix.
Direct implementation is not an available route from this state.
