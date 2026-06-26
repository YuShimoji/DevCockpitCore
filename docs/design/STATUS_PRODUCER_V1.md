# Status Producer V1

## Purpose

`common-foundation-status-producer-v1` creates a read-only status snapshot for a
target repository. The snapshot gives a supervisor enough structured context to
resume or route work without asking the target project to run tests, render
artifacts, or modify state.

This slice advances Foundation Observer Readiness only. It does not advance
Execution Automation Readiness.

## Schema

The producer emits JSON with `schema_version: status_snapshot.v1`. Required
sections are:

- `adapter`: project name, adapter path, default branch hint, and read-only
  state
- `repo`: target path, existence, git repo detection, branch, HEAD, upstream,
  remote parity, and worktree status
- `project_state`: existence of configured runtime and context documents plus
  lightweight optional labels
- `artifacts`: configured roots and bounded latest file candidates
- `validation`: default commands from the adapter, explicitly not run in this
  observer slice
- `health`: conservative status, stop class, and notes

Unknown or not confidently extractable values remain `null` or `unknown`.

## Command behavior

The module entry point is:

```bash
python -m dev_cockpit.status_snapshot --repo <repo> --adapter <adapter.json> --output <status.json>
```

Options:

- `--pretty`: write indented JSON
- `--no-write`: print JSON to stdout and skip output file writes

The output parent directory is created when writing a file. Adapter errors are
reported as CLI errors. Missing target repositories become structured snapshots
instead of crashes.

## Target repo read-only rule

Against the target repository, the producer only runs read-only git inspection
commands:

- `git -C <repo> status --short --branch`
- `git -C <repo> branch --show-current`
- `git -C <repo> rev-parse --short HEAD`
- `git -C <repo> rev-parse --abbrev-ref --symbolic-full-name @{u}`
- `git -C <repo> rev-list --left-right --count HEAD...@{u}`
- `git -C <repo> log -1 --oneline`

It does not run tests, commit, push, render, merge, rebase, reset, stash, or
write files in the target repository.

## Known limitations

- Project state extraction is intentionally shallow and bounded.
- Artifact candidate scanning is bounded and should not be treated as a complete
  inventory.
- Missing upstream information yields `remote_parity.status: unknown`.
- Branch names and default branch hints are reported as observations; they are
  not enforcement.
- Validation commands are carried as hints and are not executed.

## Future extension points

- adapter manifest schema versioning
- report normalizer
- gate classifier
- validation pack planner
- cross-project smoke checks
- controlled runner design after observer readiness is stable
