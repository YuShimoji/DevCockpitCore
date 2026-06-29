# C3 Second Command Design V1

## Purpose

`common-foundation-c3-second-command-design-v1` evaluates whether DevCockpitCore
should later propose a second fixed C3 help/read-only command.

This slice is design-only. It does not add a command key, change the controlled
runner probe allowlist, run a second probe, create a registry, or unlock C4-C6.

## Current Accepted C3 State

The accepted C3 surface has exactly one fixed command key:
`status_snapshot_help`.

That command key maps to fixed argv equivalent to:

```text
sys.executable -m dev_cockpit.status_snapshot --help
```

The canonical acceptance package is recorded by `c3-probe-hardening-v1`.

## Candidate Set

The design packet evaluates these options:

- `adapters_validate_help`
- `report_normalizer_help`
- `gate_classifier_help`
- `validation_pack_help`
- `cross_project_smoke_help`
- `controlled_runner_probe_review_help`
- `no_second_command_stop`

All executable candidates are help-only candidates. None is approved by this
slice.

## Recommendation

The recommended future candidate is `adapters_validate_help`, mapped only after
a later Supervisor prompt to fixed argv equivalent to:

```text
sys.executable -m dev_cockpit.adapters --help
```

This candidate is the narrowest useful expansion because it exercises a second
foundation CLI surface without reading target repositories, requiring input
files, running validation packs, reviewing probe evidence, or touching command
execution paths beyond help text.

`no_second_command_stop` remains the safest alternative if the Supervisor wants
to freeze C3 at one command key.

## Required Future Gates

A later `c3-second-command-probe-v1` prompt would still need to require:

- fixed hardcoded command key only.
- no config-supplied executable, argv, args, shell, or command strings.
- `shell=False`.
- cwd confined to DevCockpitCore.
- timeout, output truncation, and redaction.
- before/after git status.
- no target repository writeback.
- no credentials, network, scheduler, or background loop.
- explicit C4, C5, and C6 lock state.
- post-probe review before acceptance.

## What This Does Not Do

This design does not implement `adapters_validate_help`, run a second command,
execute adapter validation, run adapter `default_validation`, create a general
runner, add arbitrary command execution, write target repositories, access
credentials, use a network service, schedule work, publish, or unlock C4-C6.
