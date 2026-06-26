# Adapter Manifest V1

## Purpose

`adapter_manifest.v1` defines the read-only project adapter contract used by
DevCockpitCore status snapshots. The manifest makes project-specific repository
paths, docs, artifact roots, status labels, and validation hints explicit before
later report normalization or gate classification slices consume them.

This slice advances Foundation Observer Readiness only.

## Schema

Each adapter is a JSON object with these required fields:

- `schema_version`: must be `adapter_manifest.v1`.
- `project`: non-empty display name.
- `project_key`: stable lowercase identifier matching `[a-z][a-z0-9_-]*`.
- `default_branch`: non-empty branch hint.
- `repo_hints.preferred_relative_paths`: relative paths a user or supervisor may
  try when locating the project.
- `documents.runtime_state`: repo-relative path to the runtime state document.
- `documents.project_context`: repo-relative path to the project context document.
- `artifact_roots`: repo-relative roots to inspect for bounded candidate files.
- `status_hints.active_artifact_patterns`: line prefixes for current artifact
  extraction.
- `status_hints.next_action_patterns`: line prefixes for next-action extraction.
- `status_hints.user_work_patterns`: line prefixes for user-work extraction.
- `status_hints.gate_patterns`: line prefixes for gate-related extraction.
- `forbidden_stage_patterns`: staged file globs that should create a red status
  when matched.
- `default_validation`: commands to report as hints. The status producer does not
  run them.
- `read_only`: must be `true`.

Adapters may add extra document keys under `documents` later, but every document
path must be relative and must stay inside the target repository. Adapter files
must not contain credentials, token-like values, absolute Windows paths, Unix
user paths, or production endpoints.

## Safety Boundary

Adapters describe observation only. They do not grant permission to run tests,
render files, write target repositories, schedule work, send notifications,
open servers, access credentials, or perform autonomous execution.

The status producer treats missing repositories, missing upstreams, and absent
optional project files as structured warnings rather than hard crashes.

## Status Producer Relationship

`dev_cockpit.status_snapshot` loads one adapter, inspects the target repository
with read-only git commands, and emits a `status_snapshot.v1` JSON document. The
snapshot `adapter` block includes the adapter `schema_version`, `project`,
`project_key`, `adapter_path`, `default_branch`, and `read_only` state.

`status_hints` guide shallow label extraction from configured documents. The
producer still reports unknowns conservatively when labels are absent.

## Future Consumers

Future report normalizer and gate classifier slices may use adapter fields to
map project-specific labels into a common supervision vocabulary. That future
work should consume this contract without adding runner, scheduler, writeback,
or notification behavior to the observer slice.

## Adding A Project Adapter

1. Copy an existing file in `adapters/`.
2. Set `schema_version` to `adapter_manifest.v1`.
3. Choose a stable `project_key`.
4. Keep paths relative. Use `repo_hints.preferred_relative_paths` for sibling
   locations and `documents` / `artifact_roots` for paths inside the target repo.
5. Set `read_only` to `true`.
6. Validate the adapter:

```bash
PYTHONPATH=src python -m dev_cockpit.adapters --validate adapters/*.json
```

## Examples

DevCockpitCore uses `adapters/devcockpitcore.json`:

```json
{
  "schema_version": "adapter_manifest.v1",
  "project": "DevCockpitCore",
  "project_key": "devcockpitcore",
  "default_branch": "main",
  "repo_hints": {
    "preferred_relative_paths": ["."]
  },
  "documents": {
    "runtime_state": "docs/runtime-state.md",
    "project_context": "docs/project-context.md"
  },
  "artifact_roots": ["docs/handoffs", "samples/status_snapshots"],
  "status_hints": {
    "active_artifact_patterns": ["artifact_current:", "artifact_next:", "active_artifact"],
    "next_action_patterns": ["next:", "next_action"],
    "user_work_patterns": ["user_work:"],
    "gate_patterns": ["render_gate:", "stop_class:", "health="]
  },
  "forbidden_stage_patterns": [],
  "default_validation": [
    "python -m compileall src tests",
    "PYTHONPATH=src python -m unittest discover",
    "git diff --check",
    "git diff --cached --check"
  ],
  "read_only": true
}
```

NLMYTGen uses `adapters/nlmytgen.json` with `project_key: "nlmytgen"`,
`default_branch: "master"`, `repo_hints.preferred_relative_paths:
["../NLMYTGen"]`, and artifact roots for `samples/_probe/newsroom_handoff` and
`docs/verification`.

## What This Does Not Do

Adapter Manifest V1 does not normalize AGENT_REPORTs, classify gates, execute
validation packs, run commands in target repositories, render artifacts, manage
credentials, start services, write target repositories, or implement execution
automation.
