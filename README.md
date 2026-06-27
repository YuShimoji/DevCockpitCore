# DevCockpitCore

DevCockpitCore is a cross-project supervision substrate for development work. It
starts with read-only observation: produce a consistent status snapshot for a
target repository so a supervisor thread or a future automation layer can resume
work with less ambiguity.

This repository is not an execution runner. The first slice,
`common-foundation-status-producer-v1`, only inspects repository state, adapter
configuration, known project documents, artifact roots, and validation hints.

## First slice

The status producer can:

- read a target repository path without modifying it
- load a project adapter manifest
- report branch, HEAD, upstream parity, and worktree cleanliness
- record whether known project context files exist
- list bounded artifact candidates under configured roots
- emit a machine-readable `status_snapshot.v1` JSON document

It does not:

- run tests in the target repository
- render media or documents
- schedule work
- send notifications
- open a web server or GUI
- commit, push, rebase, reset, stash, or merge target repository changes
- implement a Codex execution loop or autonomous runner

## Usage

From an editable install or any environment where `src` is on `PYTHONPATH`:

```bash
python -m dev_cockpit.status_snapshot \
  --repo ../NLMYTGen \
  --adapter adapters/nlmytgen.json \
  --output samples/status_snapshots/nlmytgen_status.json \
  --pretty
```

From a fresh checkout without installing:

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.status_snapshot --help
```

Use `--no-write` to print the snapshot to stdout without writing the output
file:

```bash
python -m dev_cockpit.status_snapshot \
  --repo ../NLMYTGen \
  --adapter adapters/nlmytgen.json \
  --no-write \
  --pretty
```

The console script name is also wired in `pyproject.toml`:

```bash
dev-cockpit-status --repo ../NLMYTGen --adapter adapters/nlmytgen.json --output out.json
```

## Adapter manifests

Adapters are small JSON files that follow `adapter_manifest.v1` and describe
safe project-local expectations:

- project name
- stable project key
- default branch hint
- preferred relative repository locations
- runtime state and project context document paths under `documents`
- artifact roots to inspect
- status hint patterns for shallow label extraction
- forbidden staged artifact patterns
- default validation commands to report but not run
- `read_only: true`

The first adapters live under `adapters/`:

- `adapters/devcockpitcore.json`
- `adapters/nlmytgen.json`
- `adapters/writingpage.json`
- `adapters/clippipegen.json`

Adapter data is intentionally conservative. The status producer reports what it
can observe and leaves uncertain fields as `unknown` or `null`.

Validate adapters with:

```bash
PYTHONPATH=src python -m dev_cockpit.adapters --validate adapters/*.json
```

Generate a self-smoke snapshot for this repository with:

```bash
PYTHONPATH=src python -m dev_cockpit.status_snapshot \
  --repo . \
  --adapter adapters/devcockpitcore.json \
  --output samples/status_snapshots/devcockpitcore_status.json \
  --pretty
```

To add a project adapter, copy an existing manifest, keep all paths relative,
set a stable lowercase `project_key`, keep `read_only: true`, then run the
adapter validation command. See `docs/design/ADAPTER_MANIFEST_V1.md` for the
full field contract.

## Report normalizer

The report normalizer reads AGENT_REPORT-like text and emits
`report_normalization.v1` JSON. It extracts route, progress, action, status,
sections, commits, validation evidence, continuation state, and handoff state.
It also audits residue such as pseudo git tags, paste-ready supervisor prompt
markers, local user paths, risky automation wording, and readiness overclaims.

Generate the sample normalization with:

```bash
PYTHONPATH=src python -m dev_cockpit.report_normalizer \
  --input samples/reports/agent_report_adapter_manifest_v1_redacted.txt \
  --output samples/report_normalizations/adapter_manifest_v1_readback.json \
  --pretty
```

The sample input lives at
`samples/reports/agent_report_adapter_manifest_v1_redacted.txt`; the normalized
readback lives at
`samples/report_normalizations/adapter_manifest_v1_readback.json`.

The normalizer does not emit paste-ready next-Agent Prompts. The next roadmap
step is `gate-classifier-v1`.

## Gate classifier

The gate classifier reads `report_normalization.v1` JSON and emits
`gate_classification.v1` JSON. It classifies push, handoff, user-work, residue,
validation, readiness, execution-automation, production/public, destructive
action, and form-burden gates without executing commands.

Generate the sample classification with:

```bash
PYTHONPATH=src python -m dev_cockpit.gate_classifier \
  --report-normalization samples/report_normalizations/adapter_manifest_v1_readback.json \
  --status-snapshot samples/status_snapshots/devcockpitcore_status.json \
  --adapter adapters/devcockpitcore.json \
  --output samples/gate_classifications/adapter_manifest_v1_gate.json \
  --pretty
```

The sample output lives at
`samples/gate_classifications/adapter_manifest_v1_gate.json`. The next roadmap
step is `validation-pack-v1`; there is still no execution automation.

## Validation pack

The validation pack runs a fixed allowlist of safe checks for this repository and
emits `validation_pack_result.v1` JSON. It validates source compilation, unit
tests, adapters, JSON samples, CLI help surfaces, git whitespace checks, repo
status, and report hygiene scans.

Generate the sample result with:

```bash
PYTHONPATH=src python -m dev_cockpit.validation_pack \
  --pack samples/validation_packs/devcockpitcore_validation_pack.json \
  --output samples/validation_packs/devcockpitcore_validation_pack_result.json \
  --pretty
```

Or use the built-in default pack:

```bash
PYTHONPATH=src python -m dev_cockpit.validation_pack --default --pretty
```

The sample input lives at
`samples/validation_packs/devcockpitcore_validation_pack.json`; the sample
result lives at
`samples/validation_packs/devcockpitcore_validation_pack_result.json`.

The validation pack is not a general runner. It does not execute adapter
`default_validation`, user-provided commands, report text, or arbitrary config
commands. The next roadmap step is `cross-project-smoke`; controlled runner
design remains later and out of scope for this slice.

## Cross-project smoke

The cross-project smoke observes configured project adapters with read-only
status snapshots and emits `cross_project_smoke_result.v1` JSON. DevCockpitCore
self-smoke is required; NLMYTGen, WritingPage, and ClipPipeGen are best-effort
sibling observations that become warnings or skipped rows when absent.

Generate the sample result with:

```bash
PYTHONPATH=src python -m dev_cockpit.cross_project_smoke \
  --smoke samples/cross_project_smokes/devcockpitcore_cross_project_smoke.json \
  --output samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json \
  --pretty
```

Or use the built-in default smoke:

```bash
PYTHONPATH=src python -m dev_cockpit.cross_project_smoke --default --pretty
```

The sample input lives at
`samples/cross_project_smokes/devcockpitcore_cross_project_smoke.json`; the
sample result lives at
`samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json`.

The smoke does not run tests, builds, renders, adapter `default_validation`, or
writeback in target repositories. The next roadmap step is
`controlled-runner-design`, still without execution automation in this slice.

## Safety boundary

The status producer is a read-only observer. Against the target repository it
only runs read-only git inspection commands such as `status`, `branch`,
`rev-parse`, `rev-list`, and `log`. It does not execute validation commands; it
only carries their names into the snapshot with
`not_run_reason: observer_only_slice`.

Missing upstreams, missing sibling repositories, and missing optional project
documents are structured warnings rather than true stop conditions.

## Resume context

When resuming from another terminal or agent, start with:

- `docs/runtime-state.md`
- `docs/project-context.md`
- `docs/handoffs/2026-06-26-status-producer-v1.md`

These files preserve the current artifact, validation evidence, safety boundary,
and recommended next entrances.

## Roadmap

1. status producer
2. adapter manifest
3. report normalizer
4. gate classifier
5. validation pack
6. cross-project smoke
7. controlled runner design
8. controlled runner probe
