# C4 Probe Decision Packet V1

## Purpose

`common-foundation-c4-probe-decision-packet-v1` records whether the hardened
C4 design-only state is ready for a later C4 probe authorization review.

This is a decision packet. It is not a C4 probe implementation and it does not
add runnable behavior.

## Current C3 Executable Ceiling

C3 remains the executable ceiling. The accepted production C3 command keys are
exactly:

```text
status_snapshot_help
adapters_validate_help
```

`adapters_validate_help` remains fixed help-only behavior. It does not run
`adapters --validate`, adapter `default_validation`, target repository
writeback, or arbitrary commands.

## Current C4 Design-Only Hardened State

`docs/design/C4_SCOPED_RUNNER_DESIGN_HARDENING_V1.md` canonicalizes the
accepted C4 design boundary as design-only evidence.

C4 implementation remains unauthorized. There is no C4 command key, C4 runner,
generalized runner, config command registry, target repository writeback,
scheduler, autonomy loop, C5 unlock, or C6 unlock.

## Decision Recommendation

Recommendation:
`recommend_c4_probe_authorization_later`.

Recommended next slice:
`common-foundation-c4-probe-authorization-review-v1`.

The next slice should review this decision packet. It should not implement a
probe. Any actual C4 probe implementation would require a later separate
Supervisor prompt after review acceptance.

## Why This Is Not Probe Implementation

This slice records a policy decision and a minimum future shape. It does not
add source code, command execution, command keys, probe configs, subprocess
behavior, writeback, or scheduling.

Implementation is explicitly not allowed now.

## Future Probe Authorization Chain

Before any C4 probe implementation can exist, the project needs:

- this decision packet.
- a separate authorization review that accepts or rejects the packet.
- a later Supervisor prompt that explicitly authorizes one implementation
  slice.
- probe result evidence.
- probe review.
- hardening before any C4 state becomes canonical.

Skipping directly from this packet to implementation is forbidden.

## Minimum Future C4 Probe Shape

If a later review accepts this packet, the minimum safe future C4 probe shape is
a single hardcoded DevCockpitCore-local no-write diagnostic probe.

The future probe must keep these policies:

- command source: source-hardcoded allowlist only.
- config: select only one later-approved key; no command strings, executables,
  argv, args, shell flags, cwd overrides, environment changes, retries,
  credentials, endpoints, or write targets.
- shell: `shell=False`.
- timeout: required, bounded, and recorded.
- cwd: DevCockpitCore repository unless a later review narrows another
  repo-local cwd.
- output: bounded stdout and stderr excerpts with truncation flags.
- redaction: local user paths and sensitive-looking values redacted before
  artifact write.
- state: before and after worktree, HEAD, branch, and remote parity recorded.
- writes: no target repository writes.
- validation: adapter validation remains ordinary agent-side evidence, not a
  controlled runner command.
- git: no merge, rebase, reset, stash, force push, push, or destructive git.
- network: no network or external service unless later explicitly approved.
- credentials: no credentials or secrets.
- scheduler: no scheduler, daemon, background loop, retry loop, or autonomy.

## Exact Non-Goals

This packet does not authorize:

- C4 implementation.
- a C4 command key.
- a third C3 command key.
- arbitrary command execution.
- command strings or argv supplied by config.
- adapter validation through `controlled_runner_probe`.
- adapter `default_validation` through `controlled_runner_probe`.
- target repository writeback.
- cross-project execution.
- scheduler or autonomy behavior.
- credentials, external services, web UI, dashboard, publish, render, or
  production actions.
- C5 or C6.

## Arbitrary Execution Prohibition

Arbitrary command execution remains forbidden. A future C4 probe must be a
single fixed safe probe, not a general command runner.

## Config-Supplied Command Or Argv Prohibition

Configuration must not provide command strings, executables, argv, args, shell
flags, cwd overrides, environment changes, retries, credentials, endpoints, or
write targets.

## Target Repo Writeback Prohibition

Target repository writeback remains forbidden. Optional sibling repositories
may be observed through existing read-only status mechanisms only.

## Adapter Validation Controlled Command Prohibition

Adapter validation may still be run as ordinary local validation evidence by an
agent. It must not be executed through `controlled_runner_probe`, and adapter
`default_validation` remains outside the controlled runner surface.

## Scheduler And Autonomy Prohibition

No scheduler, daemon, background loop, retry loop, notification workflow, or
autonomy behavior is authorized.

## C5/C6 Lock

C5 and C6 remain locked. Cross-project execution and scheduler/autonomy lanes
require separate future design, review, approval, and hardening.

## Alternatives To Probing

Allowed alternatives are:

- `controlled-runner-stop`: stop with the hardened C3 and C4 design-only state.
- `validation-fixture-hygiene-first`: remove the historical pseudo-git-tag
  fixture warning before further C4 decisions.
- `c4-design-followup-fix`: repair the C4 design or hardening evidence if a
  reviewer finds a material gap.

## Known Warnings

The historical pseudo-git-tag fixture warning remains a validation-pack hygiene
warning. It does not change command keys, implementation authorization, or the
C4 boundary.

Optional sibling repository warnings may appear in cross-project smoke. They do
not affect the DevCockpitCore decision packet because sibling repositories are
best-effort observations and remain read-only.

## What This Slice Does Not Do

C4 Probe Decision Packet V1 does not change production source, implement a
probe, create a runner, add command behavior, add command keys, run adapter
validation through `controlled_runner_probe`, write target repositories, run
across projects, schedule work, handle credentials, call external services,
publish, render, or unlock C5/C6.
