# DevCockpitCore Project Context

DevCockpitCore is a cross-project development supervision substrate. Its first
purpose is to make project state easier to resume by producing structured,
read-only snapshots of target repositories.

## Readiness Lanes

- Foundation Observer Readiness: status schema, status producer, adapter config,
  tests, and docs.
- Foundation Automation Readiness: report normalizer, gate classifier,
  validation pack, and reusable project adapters.
- Execution Automation Readiness: controlled runner design after observer and
  classifier slices are mature.
- Project/Product Readiness: project-specific readiness for repositories such
  as NLMYTGen, WritingPage, and ClipPipeGen.

The current repository only advances Foundation Observer Readiness.

## Current Artifact

`status-producer-v1` is implemented as a standard-library Python package named
`dev_cockpit`.

Primary entry point:

```bash
python -m dev_cockpit.status_snapshot --repo <repo> --adapter <adapter.json> --output <status.json>
```

The producer reads adapter metadata, git branch and worktree state, upstream
parity when available, lightweight project-state labels, artifact-root
candidates, and validation hints.

## Design Bias

DevCockpitCore should keep early slices narrow and inspectable. Prefer
machine-readable artifacts, explicit safety boundaries, and conservative
unknowns over premature automation.
