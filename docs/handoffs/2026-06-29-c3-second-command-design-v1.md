# 2026-06-29 C3 Second Command Design V1 Handoff

This handoff preserves the context for resuming after
`common-foundation-c3-second-command-design-v1`.

## Source Request

The user asked Codex to pull the latest remote state, inspect the attached
Supervisor reset prompt, analyze completion, decide the next work, and continue.

Remote was updated with:

```text
git pull --ff-only
```

The pull fast-forwarded to:

```text
fca8170 docs: refresh c3 hardening handoff state
```

The attached prompt and repository state agreed that completed slices already
included:

- `common-foundation-status-producer-v1`
- `common-foundation-adapter-manifest-v1`
- `common-foundation-report-normalizer-v1`
- `common-foundation-gate-classifier-v1`
- `common-foundation-validation-pack-v1`
- `common-foundation-cross-project-smoke-v1`
- `common-foundation-controlled-runner-design-v1`
- `common-foundation-controlled-runner-probe-v1`
- `common-foundation-controlled-runner-probe-review-v1`
- `common-foundation-c3-probe-hardening-v1`

The next intended slice was
`common-foundation-c3-second-command-design-v1`.

## Work Decision

The next slice was design-only. Implementation of a second command key was not
allowed.

The chosen deliverable was a candidate evaluation and decision packet that:

- keeps the current implemented command key set at exactly
  `status_snapshot_help`.
- recommends `adapters_validate_help` only as a future Supervisor-approved C3
  probe candidate.
- keeps `no_second_command_stop` as the safest alternative.
- does not unlock C4, C5, or C6.

## Added Artifacts

- `docs/design/C3_SECOND_COMMAND_DESIGN_V1.md`
- `samples/c3_second_command_design/README.md`
- `samples/c3_second_command_design/c3_second_command_design_v1.json`
- `tests/test_c3_second_command_design.py`

Context files updated:

- `README.md`
- `docs/runtime-state.md`
- `docs/project-context.md`

## Design Decision

Recommended result:

```text
decision: recommend_second_command
selected_candidate: adapters_validate_help
implementation_status: design_only
implementation_allowed_now: false
```

Rationale:

- `python -m dev_cockpit.adapters --help` is a fixed help-only command for an
  existing foundation CLI surface.
- The help path requires no target repository, input file, output path,
  credentials, network, or writeback.
- It is adjacent to adapter-manifest readiness without executing adapter
  validation or adapter `default_validation`.
- It can test a future two-key hardcoded allowlist without implying C4.

## Boundaries Preserved

The slice does not:

- add `adapters_validate_help` to `controlled_runner_probe.py`.
- change `ALLOWED_COMMAND_KEY`.
- change `controlled_runner_probe_review.py` accepted command keys.
- create a command registry.
- run a second C3 probe.
- execute adapter validation.
- execute arbitrary commands.
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
3. `docs/design/C3_SECOND_COMMAND_DESIGN_V1.md`
4. `samples/c3_second_command_design/c3_second_command_design_v1.json`

## Recommended Next Entrance

Supervisor should review the design packet. If accepted, the next prompt can be
`common-foundation-c3-second-command-probe-v1`. That future slice must still be
one fixed help command only, with no arbitrary args, no shell, no config-supplied
argv, no target repo writeback, and no C4-C6 unlock.
