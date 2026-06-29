# C3 Command Set Freeze And C4 Design Decision V1

## Purpose

`common-foundation-c3-command-set-freeze-and-c4-design-decision-v1` records the
decision state after the hardened two-command C3 package.

This is a decision packet, not an implementation slice. It determines whether
the accepted C3 command set is freeze-ready and identifies the next safe route.

## Current Accepted C3 Command Set

The accepted production C3 command-key set is exactly:

```text
status_snapshot_help
adapters_validate_help
```

`status_snapshot_help` remains the original fixed help probe.
`adapters_validate_help` remains fixed help-only behavior:

```text
sys.executable -m dev_cockpit.adapters --help
```

No third C3 command key is present or recommended.

## Freeze Readiness

The C3 command set is freeze-ready.

The hardening artifact records the exact two-key set, no-third-command rule,
help-only boundary, config override rejection, `shell=False`, timeout,
redaction, output truncation, before/after repository state capture, no target
repository writeback, no adapter `default_validation` execution, and C4-C6
locks.

Known warnings do not block freeze readiness:

- historical pseudo-git-tag fixture residue in a report sample.
- optional sibling warnings from cross-project smoke.

Neither warning changes the C3 command set or controlled runner behavior.

## Decision Options

The decision packet keeps four routes separate:

- `controlled-runner-stop`: stop with the hardened two-command C3 state.
- `c3-command-set-freeze`: freeze the current C3 command set without moving to
  another capability lane.
- `c4-scoped-runner-design-only`: open a design-only C4 slice.
- `c3-followup-fix-v1`: return to C3 only if a material C3 issue appears.

## Recommended Decision

The recommended decision is `recommend_c4_design_only`, with
`common-foundation-c4-scoped-runner-design-v1` as the recommended next slice.

This recommendation does not authorize implementation. It only says the C3
command set is stable enough for a separate Supervisor prompt to explore C4
design boundaries.

## Why Direct C4 Implementation Is Forbidden

Direct C4 implementation is forbidden because the current authorization only
covers decision and freeze-readiness work. C4 would expand from a fixed
help-only C3 probe surface toward scoped repo-local runner design, and that
requires a separate design prompt before any implementation can be considered.

## What C4 Design-Only Would Mean

If later approved, C4 design-only work may define:

- intended scope and non-goals for a scoped repo-local runner.
- allowed and forbidden command classes.
- repository state observation and write boundaries.
- validation evidence requirements.
- operator approval and stop conditions.
- testable acceptance criteria.

## What C4 Design-Only Must Not Implement

C4 design-only must not implement a runner, command registry, command execution
path, adapter validation execution through `controlled_runner_probe`, target
repository writeback, scheduler, cross-project runner, credentials, external
service integration, web UI, or dashboard.

## Why No Third C3 Command Should Be Added Now

The current C3 value is a small, fixed, help-only command set with clear review
evidence. Adding a third command now would reopen C3 expansion instead of
freezing the accepted command set. Any future command expansion requires a
separate Supervisor decision and must not be bundled into C4 design.

## Remaining Risks And Warnings

The remaining risks are decision hygiene risks, not current implementation
blockers:

- C4 design could accidentally be interpreted as implementation approval.
- a future prompt could blur C3 command expansion with C4 design.
- existing pseudo-git-tag fixture residue still appears in validation-pack
  hygiene scans.
- optional sibling repository warnings may continue to appear in
  cross-project smoke.

The decision packet addresses these risks by making implementation forbidden,
keeping C4-C6 locked, and preserving Supervisor decision gates.

## Relationship To C3 Second-Command Hardening

`docs/design/C3_SECOND_COMMAND_HARDENING_V1.md` is the source hardening package.
It canonicalizes the accepted two-command state and identifies this decision
packet as the next freeze-ready route.

This decision packet uses that hardening state as evidence and does not replace
the hardening artifact.

## Relationship To Controlled Runner Design

The earlier controlled runner design established that execution automation must
remain bounded and Supervisor-gated. This decision packet does not change that
design. It only recommends that a future C4 design-only slice may inspect the
next boundary after the C3 command set is frozen.

## Required Supervisor Decision

Supervisor decision is required before any further capability expansion.

Until a later prompt explicitly opens design-only C4 work, C4 implementation,
C5, C6, third C3 commands, arbitrary execution, adapter validation as controlled
command behavior, schedulers, and target repository writeback remain forbidden.

The C4 design-only successor is
`docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md`.
