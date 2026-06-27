# Cross Project Smoke V1

## Purpose

`common-foundation-cross-project-smoke-v1` proves that DevCockpitCore can observe
multiple configured project adapters through the existing read-only foundation
artifacts. It emits `cross_project_smoke_result.v1` JSON for DevCockpitCore,
NLMYTGen, WritingPage, and ClipPipeGen without writing to target repositories.

This slice advances Foundation Automation Readiness only. It does not advance
Execution Automation Readiness.

## cross_project_smoke.v1 Schema

A smoke config is a JSON object with:

- `schema_version`: must be `cross_project_smoke.v1`.
- `smoke_key`: stable smoke identifier, such as
  `devcockpitcore_cross_project_observer`.
- `project_key`: stable owner project key, such as `devcockpitcore`.
- `description`: human-readable purpose.
- `adapters`: non-empty list of adapter observations.

Each adapter observation includes:

- `adapter_path`: repo-relative path to an `adapter_manifest.v1` JSON file.
- `required`: boolean. DevCockpitCore self-smoke is required; sibling project
  observations are optional.
- `repo_path_override`: optional relative path. It may point outside
  DevCockpitCore with `..`, but committed config must not use absolute paths.
- `expected_default_branch`: optional branch expectation for warning-level drift.
- `notes`: explanatory text.

The config rejects `command`, `commands`, `cmd`, `args`, and `argv` fields. Repo
resolution is declarative; config cannot provide executable command strings.

## cross_project_smoke_result.v1 Schema

The result JSON contains:

- `schema_version`: `cross_project_smoke_result.v1`.
- `generated_at`: UTC timestamp.
- `producer`: `dev_cockpit.cross_project_smoke`.
- `smoke`: smoke key, smoke path, and project key.
- `summary`: result, done, total, unknown, meter, passed, warnings, failed,
  skipped, and missing.
- `projects`: one row per adapter with repo resolution, status snapshot summary,
  adapter validation, scope boundary, result, and meter fields.
- `hygiene`: report hygiene findings for pseudo git tags, weak meter cells,
  paste-ready prompt residue, raw local paths, mojibake tokens, and forbidden
  implementation terms.
- `readiness`: readiness lane status and notes.
- `gate_input`: conservative gate recommendation for later classifiers.
- `health`: status, warnings, blockers, and stop class.

Every project row includes `done`, `total`, `unknown`, `meter`, and `missing`.

## Read-Only Target Repo Boundary

The smoke calls `dev_cockpit.status_snapshot` for each resolved target repo.
That producer uses only fixed read-only git inspection commands and shallow file
inspection. Cross Project Smoke V1 does not write files into target repositories
and records `target_repo_modified: false` when the target worktree is unchanged
before and after observation.

DevCockpitCore sample output is written only inside this repository. Sibling
repositories never receive sample files or generated artifacts.

## No Adapter default_validation Execution

Adapter `default_validation` remains a declarative hint. Cross Project Smoke V1
does not execute adapter validation commands and does not run tests, lint,
builds, renders, git add, git commit, git push, or validation packs in target
repositories.

## CLI Usage

Run the sample smoke:

```bash
PYTHONPATH=src python -m dev_cockpit.cross_project_smoke \
  --smoke samples/cross_project_smokes/devcockpitcore_cross_project_smoke.json \
  --output samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json \
  --pretty
```

Run the built-in default smoke:

```bash
PYTHONPATH=src python -m dev_cockpit.cross_project_smoke --default --pretty
```

If `--output` is omitted, JSON is written to stdout. Invalid config structure or
a disallowed command field exits cleanly with an input error.

## Result Semantics

- `pass`: required DevCockpitCore self-smoke passed and no project or hygiene
  warning was found.
- `warn`: optional sibling repositories are missing, target repos are dirty,
  branch differs from expectation, remote parity is unknown or behind, project
  docs are missing, or hygiene warnings are present.
- `fail`: required self-smoke fails, required adapter validation fails, required
  status snapshot generation fails, a target worktree changes during
  observation, raw local paths are committed, or forbidden implementation terms
  are found in source.
- `skipped`: optional project path is absent.

Dirty optional repos and branch mismatches are warnings, not failures. Missing
NLMYTGen, WritingPage, or ClipPipeGen sibling repos are warnings or skipped
observations, not true stops.

## Required Self-Smoke

DevCockpitCore self-smoke is required. It validates the self adapter, resolves
the current repository through adapter hints, generates a status snapshot summary,
and verifies that the snapshot observation did not alter the worktree.

## Optional Sibling Handling

Sibling observations use adapter `repo_hints.preferred_relative_paths` first.
When no hint exists, conservative defaults are available for known project keys:
`../NLMYTGen`, `../WritingPage`, and `../ClipPipeGen`. Missing sibling paths are
structured results.

## Artifact And Path Redaction

Runtime output may contain local absolute paths. Committed sample JSON redacts
local user segments, for example `C:\Users\<redacted>\...`. Adapter files and
committed smoke configs use relative paths only.

## Meter Requirements

Every progress-like summary includes `done`, `total`, `unknown`, `meter`, and
`missing`. Meters use ASCII-safe symbols only:

- `#`: done
- `-`: missing
- `?`: unknown
- `~`: partial or warning
- `!`: risk or failure

For totals of 12 or fewer, exact meters are used. Current-lane readiness and
next-slice gates remain separate.

## Report Hygiene Checks

The smoke includes hygiene scans for:

- pseudo git tags such as git-stage style action markers in historical reports.
- weak meter cells such as bare `#` in markdown progress matrices.
- paste-ready prompt markers in AGENT_REPORT samples.
- raw local absolute user paths.
- mojibake or encoding artifact tokens.
- forbidden source implementation terms for runner, scheduler, notification,
  database, credential, auto-render, execution-loop, or target writeback work.

Detector and boundary wording in docs/tests is allowed; actionable source
implementation is not.

## Relationship To Existing Artifacts

`adapter_manifest.v1` tells the smoke which projects can be observed.
`status_snapshot.v1` provides the read-only project observation.
`report_normalization.v1`, `gate_classification.v1`, and
`validation_pack_result.v1` remain separate foundation artifacts that can consume
or complement smoke evidence later.

## Future Controlled Runner Design

Cross Project Smoke V1 prepares evidence for `controlled-runner-design-v1`, but
it is not a runner. Any future controlled execution design must be a separate
slice with explicit authorization and guardrails.

## What This Does Not Do

Cross Project Smoke V1 does not implement arbitrary command execution, adapter
default validation execution, a subprocess orchestrator, Codex execution loop,
scheduler, external notifications, auto-rendering, credential handling,
databases, web UI, multi-repo writeback, auto-merge, rebase, force push,
tests/builds/renders in target repos, or production/public action.
