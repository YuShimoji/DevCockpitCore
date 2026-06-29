# C3 Second Command Production Probe V1

## Purpose

`common-foundation-c3-second-command-production-probe-v1` promotes the accepted
help-only candidate `adapters_validate_help` into the production C3 controlled
probe allowlist.

This slice adds exactly one new production C3 command key:

```text
adapters_validate_help
```

After this slice, the complete production C3 command-key set is:

```text
status_snapshot_help
adapters_validate_help
```

No third key is approved.

## Why This Is C3 And Not C4

This remains C3 because the command surface is fixed, hardcoded, repo-local,
bounded, and help-only. The config can select a command key but cannot provide
an executable, argv, args, shell flag, or arbitrary command string.

C4 scoped repo-local runner behavior remains locked because this slice does not
add a command registry, run project tasks, execute validation packs through the
controlled runner, or accept configurable command behavior.

## Help-Only Boundary

`adapters_validate_help` maps only to fixed argv equivalent to:

```text
sys.executable -m dev_cockpit.adapters --help
```

The probe does not run:

```text
python -m dev_cockpit.adapters --validate ...
```

It does not execute adapter validation, adapter `default_validation`, or any
target repository command.

## Hardcoded Allowlist Boundary

The implementation keeps the allowlist in source code. Probe JSON may contain
`command_key: adapters_validate_help`, but it cannot supply command strings,
executable paths, argv, args, or shell overrides. Unknown command keys fail
validation before execution.

The process runs with `shell=False`, a required timeout, cwd confined to the
DevCockpitCore repository, captured stdout and stderr, output truncation, and
local user path redaction.

## Evidence Contract

The production-probe result is:

```text
samples/controlled_runner_probes/controlled_runner_probe_adapters_validate_help_result_v1.json
```

It records:

- command key and command class.
- hardcoded allowlist authority.
- exactly two production C3 command keys.
- `shell: false`.
- no config-supplied command, executable, argv, or args.
- no adapter `default_validation` execution.
- no target repository writeback.
- no credentials or network requirement.
- before and after repository worktree, HEAD, and remote-parity state.
- timeout, duration, exit code, redacted argv and cwd.
- stdout and stderr excerpts with truncation flags.
- C4, C5, and C6 locked.

## Relationships

This slice follows `c3_second_command_candidate_acceptance.v1`, which selected
option B and preserved `adapters_validate_help` as a help-only accepted
candidate.

It extends `controlled_runner_probe.v1` by adding one fixed command key while
preserving the same C3 safety model. The earlier `status_snapshot_help` probe
remains valid and remains the built-in default probe.

## What This Does Not Do

This production probe does not create a generalized runner, load a command
registry from config, run adapter validation, run adapter `default_validation`,
execute validation commands, write target repositories, access credentials, use
network services, schedule work, notify external systems, auto-render, publish,
or unlock C4-C6.
