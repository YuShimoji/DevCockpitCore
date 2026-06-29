# C3 Second Command Candidate Acceptance V1

## Purpose

`common-foundation-c3-second-command-candidate-acceptance-v1` records the
work-decision continuation after the C3 second-command acceptance review.

The selected route is option B: carry `adapters_validate_help` forward as a
help-only accepted candidate.

This is a state and evidence update only. It does not add a production command
key, execute adapter validation, create a command registry, or unlock C4-C6.

## Decision Source

The decision is based on the completed acceptance review:

- `docs/design/C3_SECOND_COMMAND_ACCEPTANCE_REVIEW_V1.md`
- `samples/c3_second_command_acceptance/c3_second_command_acceptance_review_v1.json`

That review completed A/B/C evaluation and recommended option B because the
design packet and help-probe packet show that `python -m dev_cockpit.adapters
--help` is fixed help/readback behavior with no adapter input, target
repository, output write, broad validation execution, credentials, or network
requirement.

## Accepted Candidate Meaning

`adapters_validate_help` is accepted only as a help-only candidate for a future
bounded C3 slice. The accepted production C3 command surface remains:

```text
status_snapshot_help
```

The future candidate maps only to fixed argv equivalent to:

```text
sys.executable -m dev_cockpit.adapters --help
```

Candidate acceptance means the evidence is sufficient to preserve the option for
a later hardcoded allowlist/probe slice. It does not mean the command key exists
in production runner code.

## Current Boundary

This slice confirms:

- `status_snapshot_help` remains the only production accepted C3 command key.
- `adapters_validate_help` remains outside the production controlled runner
  allowlist.
- adapter validation execution remains unapproved.
- adapter `default_validation` execution remains unapproved.
- config-supplied executable, argv, args, shell, or command strings remain
  unapproved.
- target repository writeback remains unapproved.
- C4 scoped runner, C5 cross-project runner, and C6 scheduler/autonomy loop
  remain locked.

## Next Route

Any production second-command behavior still requires a separate prompt and a
bounded probe/review slice. That future slice must keep the command hardcoded,
help-only, `shell=False`, repo-local, timeout-bound, redacted, and covered by
before/after git status evidence.

Moving to C4 design remains a separate decision and is not unlocked by this
candidate state.

## What This Does Not Do

This candidate acceptance does not implement `adapters_validate_help`, execute
adapter validation, run adapter `default_validation`, create arbitrary command
execution, write target repositories, access credentials, use network services,
schedule work, publish, or unlock C4-C6.
