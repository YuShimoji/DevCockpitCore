# Validation Pack V1

## Purpose

`common-foundation-validation-pack-v1` provides a fixed, repo-local validation
harness for DevCockpitCore. It turns common verification steps into
`validation_pack_result.v1` JSON so gate classification can consume evidence
instead of relying on prose-only command lists.

This slice advances Foundation Automation Readiness only. It does not advance
Execution Automation Readiness.

## validation_pack.v1 Schema

A validation pack is a JSON object with:

- `schema_version`: must be `validation_pack.v1`.
- `pack_key`: stable pack identifier, such as `devcockpitcore_default`.
- `project_key`: stable project key, such as `devcockpitcore`.
- `description`: human-readable purpose.
- `checks`: non-empty list of check definitions.

Each check includes:

- `check_key`: one fixed allowlisted check key.
- `kind`: broad family such as `python`, `schema`, `cli`, `git`, `json`, or
  `scan`.
- `severity`: `required`, `warning`, or `optional`.
- `enabled`: boolean.
- `paths` or `targets`: declarative scan targets only.
- `allow_fixture_hits`: whether historical sample residue becomes a warning.
- `notes`: explanatory text.

The pack format does not accept `command`, `commands`, `cmd`, `args`, or `argv`
fields. Check keys select built-in behavior; config never supplies executable
strings.

## validation_pack_result.v1 Schema

The result JSON contains:

- `schema_version`: `validation_pack_result.v1`.
- `generated_at`: UTC timestamp.
- `producer`: `dev_cockpit.validation_pack`.
- `pack`: pack key, pack path, and project key.
- `repo`: current repo branch, head, worktree, and remote parity summary.
- `summary`: result, done, total, unknown, meter, missing, passed, warnings,
  failed, and skipped.
- `checks`: per-check result rows with the same meter fields plus command,
  exit code, findings, missing, and notes.
- `hygiene`: grouped findings for pseudo git tags, paste-ready prompt residue,
  raw local paths, mojibake tokens, and forbidden implementation terms.
- `gate_input`: conservative gate recommendation for a later classifier.
- `health`: status, warnings, blockers, and stop class.

## Fixed Allowlist Boundary

The pack can only run built-in checks for this repository:

- Python compile checks for `src` and `tests`.
- unittest discovery.
- adapter manifest validation through `dev_cockpit.adapters`.
- help checks for status snapshot, report normalizer, and gate classifier.
- JSON parsing under adapters and samples.
- `git diff --check`, `git diff --cached --check`, and
  `git status --short --branch` for the current repository.
- conflict marker, prompt residue, pseudo git tag, raw local path, mojibake, and
  forbidden implementation scans.

Subprocess calls use fixed argument lists with `shell=False`. The result records
command, exit code, duration, and redacted snippets. The implementation does not
run commands from user input, adapter JSON, report text, or validation pack
config.

## Adapter default_validation

Adapter `default_validation` values remain declarative hints. Validation Pack V1
does not execute them and does not run checks inside target project repositories.

## CLI Usage

Run the sample pack:

```bash
PYTHONPATH=src python -m dev_cockpit.validation_pack \
  --pack samples/validation_packs/devcockpitcore_validation_pack.json \
  --output samples/validation_packs/devcockpitcore_validation_pack_result.json \
  --pretty
```

Run the built-in default pack:

```bash
PYTHONPATH=src python -m dev_cockpit.validation_pack \
  --default \
  --output samples/validation_packs/devcockpitcore_validation_pack_result.json \
  --pretty
```

If `--output` is omitted, JSON is written to stdout. Invalid pack structure or a
disallowed command field exits cleanly with an input error.

## Check Result Semantics

- `pass`: the check completed and found no issue.
- `warn`: the check completed and found hygiene residue or optional uncertainty.
- `fail`: required validation failed or a safety boundary was violated.
- `skipped`: the check was disabled or optional input was absent.

Historical pseudo git tags in redacted AGENT_REPORT fixtures are warnings, not
true stops. Raw unredacted local user paths in committed samples are failures.
Detector and boundary wording in docs/tests is allowed; actionable source
implementation of a runner, scheduler, notification sender, database, web
server, credential manager, target-repo writeback, auto-render workflow, or
execution loop is a failure.

## Meter Requirements

Every summary row includes `done`, `total`, `unknown`, `meter`, and `missing`.
Meters use ASCII-safe symbols only:

- `#`: done
- `-`: missing
- `?`: unknown
- `~`: partial or warning
- `!`: risk or failure

Current-lane readiness and next-slice gates remain separate.

## Hygiene Scans

Validation Pack V1 scans committed report samples for paste-ready prompt markers
such as `[PASTE TARGET:]`, pseudo git tags, mojibake tokens, and local user
paths. Redacted local paths such as `C:\Users\<redacted>\Repo` are allowed and
may be noted; raw local usernames fail the path scan.

Mojibake detection covers common Japanese encoding artifacts. A finding is a
hygiene warning by default because historical report fixtures may intentionally
preserve bad header text as a regression example.

## Relationship To Existing Artifacts

`status_snapshot.v1` observes repository state. `adapter_manifest.v1` describes
project-local expectations. `report_normalization.v1` structures returned
AGENT_REPORT text. `gate_classification.v1` classifies the normalized report.
`validation_pack_result.v1` adds reproducible validation evidence that later
classifiers can consider.

## Future Controlled Execution Automation

This slice is a precursor to guarded execution governance, not the governance
runner itself. A future controlled runner design may use validation result data
as one input, but that future design must remain a separate slice with explicit
safety review.

## What This Does Not Do

Validation Pack V1 does not implement arbitrary command execution, adapter
validation command execution, a subprocess orchestrator, a Codex execution loop,
a scheduler, external notifications, auto-rendering, credential handling,
databases, web UI, multi-repo writeback, auto-merge, rebase, force push, or
production/public action.
