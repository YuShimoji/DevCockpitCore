# C4 Scoped Runner Design Review V1

## Purpose

`common-foundation-c4-scoped-runner-design-review-v1` reviews the C4 scoped
runner design boundary and decides whether it is acceptable as design-only
evidence.

This review does not implement C4, create a runner, add a command key, execute
adapter validation through `controlled_runner_probe`, or authorize target
repository writeback.

## Reviewed Design Artifacts

Reviewed inputs:

- `docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md`
- `samples/c4_scoped_runner_design/c4_scoped_runner_design_v1.json`
- `samples/c4_scoped_runner_design/c4_scoped_runner_decision_packet_v1.json`
- `docs/design/C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md`
- `samples/c3_command_set_freeze_and_c4_design_decision/c3_command_set_freeze_and_c4_design_decision_v1.json`
- `src/dev_cockpit/controlled_runner_probe.py`

## Acceptance Decision

Decision: accepted.

The C4 scoped runner design can be accepted as a safe design-only boundary. The
design artifacts are present and coherent, `implementation_allowed` is false,
`execution_added` is false, and `command_keys_added` is empty.

The recommended next route is
`common-foundation-c4-scoped-runner-design-hardening-v1`, not direct C4
implementation.

## Why This Is Still Design-Only

The design defines a possible future C4 boundary, but it does not create
runnable behavior. It requires later Supervisor authorization, probe evidence,
probe review, and hardening before any C4 capability can be considered.

Design acceptance means the boundary is coherent enough to preserve as policy.
It does not mean implementation is authorized.

## Evidence That No Implementation Was Added

The reviewed source state keeps `controlled_runner_probe` at C3:

- the production command-key set is exactly `status_snapshot_help` and
  `adapters_validate_help`.
- `adapters_validate_help` maps only to `python -m dev_cockpit.adapters --help`.
- config cannot supply command strings, executables, argv, args, or shell flags.
- `shell=False` remains hardcoded for the subprocess call.
- no `runner.py`, `controlled_runner.py`, or `command_registry.py` module exists
  under `src/dev_cockpit`.
- target repository writeback, scheduler/autonomy behavior, credentials, and
  external services remain absent from the controlled runner surface.

## C3 Executable Ceiling

C3 remains the executable ceiling. The accepted production C3 command keys are:

```text
status_snapshot_help
adapters_validate_help
```

There is no third C3 command and no C4 command.

## C4 Implementation Prohibition

C4 implementation remains unauthorized. A future C4 probe would require a
separate prompt, a scoped probe packet, probe-result evidence, review, and
hardening. This review must not be used as a shortcut into implementation.

## Design Acceptance Versus Implementation Authorization

Design acceptance records that the policy boundary is internally consistent and
safe to preserve. Implementation authorization would allow new runnable
behavior. This artifact does only the former.

## Allowed Next Routes

Allowed next routes are:

- `common-foundation-c4-scoped-runner-design-hardening-v1`
- `common-foundation-c4-probe-decision-packet-v1`
- `controlled-runner-stop`
- `common-foundation-c4-design-fix-v1`

## Forbidden Next Routes

Forbidden next routes are:

- direct C4 implementation.
- third C3 command.
- C5.
- C6.
- arbitrary execution.
- adapter validation as controlled command behavior.
- target repository writeback.

## Known Warnings

Known warnings do not block this acceptance:

- `pseudo_git_tag_fixture_warning` is historical report-fixture residue.
- `optional_sibling_warnings` are best-effort sibling observation warnings.

Neither warning expands the command set or changes controlled runner behavior.

## Relation To C4 Scoped Runner Design

`docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md` is the source design boundary. This
review accepts that boundary as design-only and records the next safe route.

## Relation To C3 Command-Set Freeze

`docs/design/C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md` established
that the two-command C3 state is freeze-ready and that C4 should begin only as a
separate design route. This review confirms that the C4 design followed that
decision without implementation drift.

## What This Review Does Not Do

This review does not implement a runner, add command execution, add command
keys, create a command registry, run adapter validation through
`controlled_runner_probe`, execute adapter `default_validation`, write target
repositories, run across projects, schedule work, handle credentials, call
external services, create a web UI, render, publish, unlock C5/C6, or provide a
successor prompt.
