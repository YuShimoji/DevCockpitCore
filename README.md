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
