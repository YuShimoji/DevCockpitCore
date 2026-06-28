# Controlled Runner Probe V1

## Purpose

`common-foundation-controlled-runner-probe-v1` is the first guarded execution
probe for DevCockpitCore. It validates the Controlled Runner Design V1 evidence
contract with exactly one hardcoded DevCockpitCore-local help/read-only command:
`status_snapshot_help`.

This is only a probe. It is not a general runner, command registry, scheduler,
autonomy loop, cross-project runner, target repository writer, or production
automation.

## Capability Level

The probe exercises `C3_guarded_single_command_probe` only. `C4
scoped_repo_local_runner`, `C5 cross_project_runner`, and `C6
scheduler_or_autonomy_loop` remain locked.

## Hardcoded Command Key Model

The only accepted command key is `status_snapshot_help`. The implementation maps
that key to fixed argv equivalent to:

```text
sys.executable -m dev_cockpit.status_snapshot --help
```

The config can select the key but cannot supply executable paths, argv, args,
shell flags, or arbitrary command strings. Unknown command keys fail validation.

## Safety Boundary

The probe uses `sys.executable`, a fixed module invocation, `shell=False`, cwd
confinement to DevCockpitCore, a required timeout, captured stdout/stderr,
redaction, and safe truncation. It records before/after repo state and fails if
the command changes the worktree or HEAD.

The command itself writes no artifacts. The CLI may write the declared sample
result JSON inside DevCockpitCore, which is separate from command side effects.

## Evidence Contract

`controlled_runner_probe_result.v1` records:

- probe identity and command key.
- authority fields showing hardcoded allowlist source and no arbitrary command
  execution.
- repo path, branch, head, worktree before/after, and remote parity before/after.
- redacted argv, cwd, timeout, exit code, duration, stdout/stderr excerpts,
  truncation flags, and redactions applied.
- declared artifacts written by the result writer.
- safety gates for allowlist, args, shell, cwd, timeout, write scope, target
  repo, credentials, network, and destructive git.
- summary meter and health.
- next review recommendation.

## Failure Semantics

The probe fails when a safety gate fails, the fixed command exits non-zero,
timeout occurs, worktree or HEAD changes during the command, config attempts to
provide executable fields, shell execution would be required, credentials or
network are requested, or target repo writeback is attempted.

Warnings cover optional uncertainty such as a dirty worktree before the probe or
unknown upstream parity.

## Relationship To Existing Artifacts

Controlled Runner Probe V1 consumes the governance constraints from
`controlled_runner_design.v1`. It can be evaluated alongside
`validation_pack_result.v1` and `gate_classification.v1`, but it does not expand
the validation pack, execute adapter `default_validation`, or add a general
command runner.

`controlled_runner_probe_review.v1` is the acceptance-review layer for this
probe evidence. It reads probe result JSON and classifies C3 acceptance without
running commands or unlocking C4-C6.

`c3_probe_hardening.v1` identifies the canonical post-commit clean probe result
as the C3 acceptance surface. Dirty during-work samples remain explanatory
context, not command side-effect proof.

## What This Does Not Do

Controlled Runner Probe V1 does not execute arbitrary commands, load a command
registry from config, run adapter validation strings, accept user-supplied args,
write target repositories, run tests/builds/renders in target repos, send
notifications, access credentials, use a database or web UI, schedule work,
auto-render, publish, or approve C4-C6 execution automation.
