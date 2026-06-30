# C4 Probe Minimal Implementation V1

## Purpose

`common-foundation-c4-probe-minimal-implementation-v1` implements one minimal
C4 probe after the authorization review accepted future prompt eligibility.

The implemented command key is `validation_pack_default_pretty`.

## Why This Is A Minimal C4 Probe

This is a minimal C4 probe, not a generalized runner. The implementation lives
in `src/dev_cockpit/c4_scoped_runner_probe.py` and accepts exactly one C4
command key. It does not load commands from config, does not expose arbitrary
command execution, and does not add multiple C4 commands.

The command is hardcoded as:

```text
python -m dev_cockpit.validation_pack --default --pretty
```

The process is run repo-local with `shell` set to false, a required bounded
timeout, captured stdout and stderr previews, redaction, and before/after
repository state evidence.

## Current C3 Executable Ceiling

C3 command keys remain exactly:

```text
status_snapshot_help
adapters_validate_help
```

The C4 probe key is separate and cannot be selected as a C3 command. No third
C3 command is introduced.

## Single C4 Command Key Added

The only C4 command key is:

```text
validation_pack_default_pretty
```

The C4 command set is exactly one key. Adding any other C4 key requires a
separate future prompt, review, and test update.

## Exact Command Boundary

`validation_pack_default_pretty` maps only to:

```text
sys.executable -m dev_cockpit.validation_pack --default --pretty
```

The command class is `fixed_repo_local_validation_probe`. The command source is
`hardcoded_allowlist`.

## Config-Supplied Command Or Argv Is Forbidden

Configuration may select only the allowed command key. It cannot supply command
text, executable, argv, args, shell, cwd, environment, retries, credentials, or
write targets.

In short, configuration cannot supply command text or argv.

This preserves the C4 boundary as a narrow implementation of the reviewed
probe, not a configurable command runner.

## Adapter Validation Remains Outside

Adapter validation remains outside `controlled_runner_probe` behavior. This C4
probe executes `validation_pack --default --pretty`; it does not turn
`adapters --validate` into a controlled runner command, and it does not execute
adapter `default_validation` through `controlled_runner_probe`.

Adapter validation may still appear inside `validation_pack` as ordinary local
validation evidence.

## Target Repo Writeback Remains Forbidden

Target repository writeback remains forbidden. The C4 probe records before and
after DevCockpitCore repository state and does not write sibling or target
repositories.

The CLI may write the declared DevCockpitCore-local sample result artifact when
called with `--output`; that artifact write is not target repo writeback.

## Timeout, Truncation, Redaction, And Repo State

The C4 probe requires:

- bounded timeout.
- captured stdout and stderr previews.
- output truncation support.
- local user path redaction.
- before and after repository state capture.
- command exit code capture.
- blocker recording if worktree or HEAD changes during the command.

## Known Warning Handling

`validation_pack` may report the historical pseudo-git-tag fixture warning.
That warning remains non-blocking when the command exits successfully and no
probe safety blocker is present.

Worktree state is evidence. A dirty worktree before and after the command is a
warning, but a worktree or HEAD change during the command is a blocker.

## C5/C6 Lock

C5 and C6 remain locked. This slice does not add cross-project execution,
scheduler/autonomy behavior, credentials, external services, web UI, dashboard,
publish behavior, or target repository writeback.

## Required Next Review Slice

The required next route is:

```text
common-foundation-c4-probe-minimal-implementation-review-v1
```

That review should inspect the implementation evidence before any further C4
work is considered.

## What This Slice Does Not Do

This slice does not implement a generalized C4 runner, arbitrary command
execution, command registry behavior, config-supplied argv, a third C3 command,
multiple C4 commands, adapter validation as controlled runner behavior, adapter
`default_validation` through `controlled_runner_probe`, target repository
writeback, cross-project execution, scheduler/autonomy behavior, credentials,
external service handling, web UI, dashboard, rebase/reset/stash automation,
force push, C5, or C6.
