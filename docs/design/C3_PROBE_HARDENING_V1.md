# C3 Probe Hardening V1

## Purpose

`common-foundation-c3-probe-hardening-v1` canonicalizes the accepted C3 probe
evidence so reviewers can evaluate the single fixed probe without ambiguity.
It converts the prior `accepted_with_constraints` review state into a cleaner
C3 package built around canonical post-commit evidence.

This is hardening, not expansion. It does not add command keys, introduce a
runner registry, or unlock C4-C6.

## Canonical Probe Evidence

The canonical probe evidence is
`samples/controlled_runner_probes/controlled_runner_probe_result_v1_canonical.json`.
It is generated from a clean worktree using the existing `--default`
`status_snapshot_help` probe and records clean before/after worktree state.

The probe command itself creates no artifacts. The CLI result writer may write
the declared DevCockpitCore-local sample JSON after the command evidence is
captured; that write is not a command side effect.

## Canonical Review Evidence

The canonical review evidence is
`samples/controlled_runner_probe_reviews/controlled_runner_probe_review_result_v1_canonical.json`.
It reviews the canonical probe result and records `accepted` for C3 while
leaving C4, C5, and C6 locked.

## Dirty During-Work Sample

The earlier `controlled_runner_probe_result_v1.json` can show a dirty worktree
because it was generated while implementation files were still being created.
That sample remains useful as during-work evidence, but it is not the canonical
acceptance surface.

Post-commit clean evidence is the canonical acceptance surface for C3.

## Accepted Semantics

`accepted` means the canonical C3 evidence is complete and clean. It does not
mean C4 readiness. `accepted_with_constraints` remains valid for evidence that
is safe but still carries documented non-blocking sample or documentation
constraints.

## Exactly-One-Command-Key Invariant

The only accepted command key remains `status_snapshot_help`. Unknown command
keys fail validation, and config cannot supply command strings, executable
paths, argv, args, or shell overrides.

## C4-C6 Lock

C4 scoped repo-local runner, C5 cross-project runner, and C6 scheduler or
autonomy loop remain locked. Any next action requires a separate Supervisor
decision.

## Relationships

`controlled_runner_probe.v1` emits the fixed C3 probe evidence.
`controlled_runner_probe_review.v1` classifies that evidence.
`c3_probe_hardening.v1` records the canonical acceptance package.

`gate_classification.v1` and `validation_pack_result.v1` remain supporting
supervision and repository-health tools. They do not unlock execution
automation.

## What This Does Not Do

C3 Probe Hardening V1 does not execute arbitrary commands, add command keys,
run adapter `default_validation`, create a generalized runner, schedule work,
send notifications, auto-render media, manage credentials, open a web UI, store
state in a database, write target repositories, publish, or unlock C4-C6.
