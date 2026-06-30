# C4 Scoped Runner Design V1

## Purpose

`common-foundation-c4-scoped-runner-design-v1` defines the boundary for a
possible future C4 scoped repo-local runner. This slice is design-only.

It does not implement C4, create a runner, add command execution behavior, add a
third C3 command, generalize `controlled_runner_probe`, or unlock C5/C6.

## Review Status

`docs/design/C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md` accepts this boundary as
design-only evidence. That acceptance does not authorize C4 implementation. C3
remains the executable ceiling, and the recommended next route is
`common-foundation-c4-scoped-runner-design-hardening-v1`.

`docs/design/C4_SCOPED_RUNNER_DESIGN_HARDENING_V1.md` canonicalizes the
accepted design-only state. It keeps C4 implementation unauthorized and
recommends `common-foundation-c4-probe-decision-packet-v1` only as a
decision-only next route.

## Current C3 Executable Ceiling

The current executable ceiling remains C3. The only production C3 command keys
are:

```text
status_snapshot_help
adapters_validate_help
```

Both are fixed help/readback probes. `adapters_validate_help` maps only to:

```text
sys.executable -m dev_cockpit.adapters --help
```

It does not run `adapters --validate`, execute adapter `default_validation`, or
write target repositories.

## Why C4 Is Design-Only Here

The preceding decision packet recommends C4 design-only because the hardened C3
state is freeze-ready. That recommendation does not authorize implementation.

C4 would be a capability expansion beyond fixed help probes. It therefore needs
a design artifact, a design acceptance review, and a separate future probe
authorization before any runnable behavior can be considered.

## What C4 Could Mean Later

If later approved by a separate Supervisor prompt, C4 may mean a scoped
DevCockpitCore-local runner for a very small hardcoded command class. The future
runner would still be repo-local, explicitly allowlisted in source, timeout
bounded, `shell=False`, redacted, truncated, and covered by before/after
repository state capture.

Any future C4 command class must be more constrained than arbitrary command
execution and must remain reviewable as a small production surface.

## What C4 Must Not Mean

C4 must not mean:

- command strings or argv supplied by config.
- a command registry loaded from config.
- arbitrary command execution.
- adapter validation through `controlled_runner_probe`.
- adapter `default_validation` execution through `controlled_runner_probe`.
- target repository writeback.
- cross-project execution.
- scheduler or autonomy behavior.
- credentials or external service handling.
- destructive git, force push, merge, rebase, reset, stash, publish, or render
  production artifacts.

## C3 Fixed Help Probes Versus Future C4

C3 is fixed help/readback only. Its config can select one of two existing
hardcoded command keys but cannot provide executable, argv, args, shell, or
command fields.

A future C4 design may describe a scoped repo-local runner, but implementation
would require a separate accepted probe slice. C4 must not reuse the C3 probe as
a back door for adapter validation or broader task execution.

## Required Future Approval Chain

Before C4 implementation can be considered, the project needs:

- `common-foundation-c4-scoped-runner-design-review-v1`
- a separate C4 probe prompt
- C4 probe result evidence
- C4 probe review
- C4 hardening

Each step must preserve Supervisor decision gates and may reject the route if
the design or evidence expands beyond the approved boundary.

## Safety Gates

Any future C4 probe must require:

- hardcoded allowlist in source.
- no config-supplied command.
- no config-supplied argv or args.
- `shell=False`.
- bounded timeout.
- output truncation.
- local path redaction.
- before/after repository state.
- no target repository writeback.
- no credentials.
- no network unless explicitly approved by a later prompt.
- no destructive git.
- no force push.
- no scheduler.
- no C5/C6 unlock.

## Command And Config Policy

Configuration may identify an approved key only. It must not supply command
strings, executable paths, argv, args, shell flags, environment changes, working
directory overrides, write targets, credentials, network endpoints, or retry
policies.

Unknown keys must fail validation before any process can run.

## Output And Redaction Policy

Any future output must be captured as bounded excerpts with truncation flags.
Local user paths and sensitive-looking values must be redacted before artifacts
are written.

The design does not authorize writing command output into target repositories.

## Before And After Repo State Policy

Before and after repository state must be captured for the DevCockpitCore repo
for any future C4 probe. If a future slice proposes target-repository
observation, it must remain read-only and must not write to that repository.

Worktree, HEAD, branch, and remote parity changes must be visible in evidence.

## Validation Policy

Adapter validation may remain ordinary validation evidence outside
`controlled_runner_probe`. This C4 design does not approve executing
`adapters --validate` through the controlled runner.

Validation artifacts must distinguish checks run by the agent during review
from commands executed by any future controlled runner.

## Git, Push, And Destructive Gate Separation

Normal agent-side git operations for committing repository artifacts remain
separate from controlled runner behavior. A future C4 runner must not merge,
rebase, reset, stash, force push, or push at all unless a later prompt creates a
separate explicit design and review path.

## No Target Repo Writeback

Target repository writeback remains forbidden. Missing upstreams, absent sibling
repositories, and missing optional docs should remain structured warnings, not a
reason to introduce writes.

## No C5/C6 Unlock

C4 design does not unlock C5 cross-project execution or C6 scheduler/autonomy.
Those remain separate capability lanes with their own future design, review,
approval, and hardening requirements.

## Recommended Next Step

The recommended next step is
`common-foundation-c4-scoped-runner-design-review-v1`.

That review may accept, reject, or require corrections to this design. It must
not implement a runner.

## What This Slice Does Not Do

C4 Scoped Runner Design V1 does not implement a runner, add command execution,
add command keys, create a command registry, run adapter validation through
`controlled_runner_probe`, execute adapter `default_validation`, write target
repositories, run across projects, schedule work, handle credentials, call
external services, create a web UI, render, publish, or unlock C5/C6.
