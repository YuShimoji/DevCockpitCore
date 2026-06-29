# C3 Second Command Help Probe V1

## Purpose

`common-foundation-c3-second-command-help-probe-v1` records bounded evidence for
the design candidate `adapters_validate_help`.

The proof target is fixed help/readback behavior only:

```text
sys.executable -m dev_cockpit.adapters --help
```

This slice does not add a production command key, change the controlled runner
probe allowlist, execute adapter validation, or accept the candidate as a
completed C3 command.

## Probe Scope

The help probe answers five questions:

- The candidate can be represented by a fixed module help invocation.
- The help invocation does not require input adapter files or target repo paths.
- The help invocation does not execute broad adapter validation.
- The currently accepted C3 command remains `status_snapshot_help`.
- A later implementation would still require a separate Supervisor prompt,
  review, and acceptance path.

## Evidence Artifact

The machine-readable evidence packet is:

```text
samples/c3_second_command_probe/c3_second_command_help_probe_v1.json
```

It records the fixed argv suffix, observed help-output expectations, safety
gates, future requirements, and explicit C4-C6 lock state.

## Current Command Boundary

The production controlled runner probe still accepts only
`status_snapshot_help`. `adapters_validate_help` is represented here as a
help-probe evidence target, not as an accepted command key.

## Future Acceptance Requirements

Before `adapters_validate_help` can become an accepted C3 command, a future
slice must still provide:

- a separate Supervisor prompt.
- hardcoded allowlist mapping for exactly the help invocation.
- no config-supplied executable, argv, args, command, or shell fields.
- `shell=False`.
- cwd confinement to DevCockpitCore.
- timeout, redaction, and truncation.
- before/after git status evidence.
- no target repository writeback.
- no credentials, network, scheduler, or autonomy loop.
- a review artifact that explicitly keeps C4-C6 locked.

## What This Does Not Do

This help probe does not execute adapter validation, run adapter
`default_validation`, add arbitrary command execution, create a command
registry, write target repositories, access credentials, use network services,
schedule work, publish, or unlock C4-C6.
