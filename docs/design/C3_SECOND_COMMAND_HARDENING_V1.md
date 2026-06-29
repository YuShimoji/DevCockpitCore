# C3 Second Command Hardening V1

## Purpose

`common-foundation-c3-second-command-hardening-v1` canonicalizes the accepted
two-command C3 production state after the production probe review for
`adapters_validate_help`.

This is hardening, not a new capability. It records the accepted command set,
locks the invariants that keep the probe in C3, and prepares a clean Supervisor
decision point.

## Accepted C3 Production Command Set

The accepted production C3 command-key set is exactly:

```text
status_snapshot_help
adapters_validate_help
```

`status_snapshot_help` remains the original fixed help probe.
`adapters_validate_help` maps only to fixed module help behavior:

```text
sys.executable -m dev_cockpit.adapters --help
```

The production command count is exactly two. No third C3 command key is
accepted, proposed, or implied by this hardening package.

## Help-Only Boundary

`adapters_validate_help` is help-only. It may print help text that documents the
ordinary `--validate` option, but the controlled runner probe does not invoke
that option.

This hardening preserves the distinction between:

- controlled C3 help/readback behavior: `python -m dev_cockpit.adapters --help`
- ordinary repository validation evidence: `python -m dev_cockpit.adapters --validate adapters/*.json`

Adapter validation, adapter `default_validation`, and project task execution
remain outside the `controlled_runner_probe` command set.

## C3 Safety Invariants

The C3 command set remains safe only while all of these stay true:

- the command keys are exactly `status_snapshot_help` and `adapters_validate_help`.
- no third command key is present.
- both commands are hardcoded in source.
- probe config cannot supply command strings, executable paths, argv, args, or
  shell overrides.
- `shell=False` is enforced.
- timeout is required and bounded.
- output is captured, truncated, and redacted.
- before and after repository state is recorded.
- target repository writeback is false.
- adapter `default_validation` execution is false.
- no generalized runner, scheduler, command registry, or autonomy loop exists.
- C4, C5, and C6 remain locked.

## Relationship To Prior C3 Work

`c3_second_command_candidate_acceptance.v1` selected option B and preserved
`adapters_validate_help` as a help-only accepted candidate for a future bounded
C3 slice.

`c3_second_command_production_probe.v1` implemented that future bounded slice by
adding exactly one fixed production C3 key while keeping the command help-only
and hardcoded.

`c3_second_command_production_probe_review.v1` accepted the production probe
evidence and confirmed the two-command set, help-only boundary, no validation
runner drift, and C4-C6 locks.

This hardening package is the canonical freeze-ready state for that accepted
review.

## C4-C6 Lock Confirmation

This hardening does not authorize C4 implementation. It does not authorize C5,
C6, third-command expansion, arbitrary execution, config-driven command
execution, target-repository writeback, credentials, network services,
schedulers, notifications, auto-render behavior, or a web UI.

C4 scoped runner design, if pursued, requires a separate Supervisor decision and
must start as design-only unless explicitly authorized otherwise.

## Allowed Next Paths

Allowed next routes are:

- `controlled-runner-stop`
- `c3-command-set-freeze-and-c4-design-decision-v1`
- `c3-followup-fix-v1`, only if a real C3 issue appears

Supervisor decision is required before any next route starts.

## Forbidden Next Paths

This hardening forbids treating the accepted state as authorization for:

- direct C4 implementation.
- a third C3 command.
- C5 or C6 work.
- arbitrary execution.
- adapter validation as controlled runner command behavior.
- command registry, scheduler, autonomous runner, or target-repository writeback.

## What This Does Not Do

C3 Second Command Hardening V1 does not change source behavior, add command
keys, run adapter validation through the controlled runner, create a generalized
runner, execute target repository commands, publish artifacts, or unlock C4-C6.
