# 2026-06-29 C3 Second Command Help Probe V1 Handoff

This handoff preserves the context for resuming after
`common-foundation-c3-second-command-help-probe-v1`.

## Source Request

The Supervisor prompt asked Codex to continue from:

```text
a206781 docs: add c3 second command design
```

The requested slice was a bounded C3 second-command help probe for the design
candidate `adapters_validate_help`.

Verified starting state:

```text
git pull --ff-only
Already up to date.

git branch --show-current
main

git rev-list --left-right --count HEAD...origin/main
0 0

git log -6 --oneline --decorate
a206781 (HEAD -> main, origin/main, origin/HEAD) docs: add c3 second command design
```

## Work Decision

The safe path was not to extend production controlled runner source. Instead,
the slice records a bounded help/readback proof and tests it:

- `adapters_validate_help` is represented by fixed argv suffix
  `-m dev_cockpit.adapters --help`.
- `python -m dev_cockpit.adapters --help` exits 0 and prints only help text.
- Adapter validation is not executed.
- `status_snapshot_help` remains the only accepted C3 command key.
- C4, C5, and C6 remain locked.

## Added Artifacts

- `docs/design/C3_SECOND_COMMAND_HELP_PROBE_V1.md`
- `samples/c3_second_command_probe/README.md`
- `samples/c3_second_command_probe/c3_second_command_help_probe_v1.json`
- `tests/test_c3_second_command_help_probe.py`

Context files updated:

- `README.md`
- `docs/runtime-state.md`
- `docs/project-context.md`

## Boundary Preserved

This slice does not:

- add `adapters_validate_help` to `controlled_runner_probe.py`.
- change `ALLOWED_COMMAND_KEY`.
- change `controlled_runner_probe_review.py` accepted command keys.
- create a command registry.
- execute adapter validation.
- execute adapter `default_validation`.
- write target repositories.
- unlock C4, C5, or C6.

## Fresh Terminal Resume

From a fresh terminal:

```powershell
git pull --ff-only origin main
git status --short --branch
$env:PYTHONPATH = "src"
python -m unittest discover
```

Then read:

1. `docs/runtime-state.md`
2. `docs/project-context.md`
3. `docs/design/C3_SECOND_COMMAND_HELP_PROBE_V1.md`
4. `samples/c3_second_command_probe/c3_second_command_help_probe_v1.json`

## Recommended Next Entrance

Supervisor should review the help-probe packet. If accepted, the next bounded
slice can be `common-foundation-c3-second-command-acceptance-review-v1`.

That future review should decide whether the proof is enough to authorize an
actual hardcoded allowlist mapping later. It must still avoid C4-C6 unlock,
arbitrary args, config-supplied commands, target repo writeback, credentials,
network behavior, and scheduler or autonomy loop behavior.
