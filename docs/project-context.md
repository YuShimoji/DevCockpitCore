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

The current repository has completed observer and foundation automation slices,
plus a bounded C3 probe evidence package, a design-only C3 second-command
candidate packet, and a bounded help-probe packet for that candidate. It still
does not unlock general execution automation.

## Current Artifact Stack

The current active artifact is `c3-second-command-help-probe-v1`.

Completed artifacts include:

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

The implementation remains a standard-library Python package named
`dev_cockpit`.

Primary entry point:

```bash
python -m dev_cockpit.status_snapshot --repo <repo> --adapter <adapter.json> --output <status.json>
```

The producer reads adapter metadata, git branch and worktree state, upstream
parity when available, lightweight project-state labels, artifact-root
candidates, and validation hints.

The current C3 package uses only the hardcoded `status_snapshot_help` command
key. It records canonical clean probe and review evidence while keeping C4-C6
locked.

The second-command design packet recommends `adapters_validate_help` only as a
future Supervisor-reviewed candidate. It does not add that command key or run a
second probe.

The second-command help-probe packet records fixed help/readback evidence for
`python -m dev_cockpit.adapters --help`. It still does not add
`adapters_validate_help` to the production controlled runner allowlist or accept
it as a completed C3 command.

## Design Bias

DevCockpitCore should keep early slices narrow and inspectable. Prefer
machine-readable artifacts, explicit safety boundaries, and conservative
unknowns over premature automation.
