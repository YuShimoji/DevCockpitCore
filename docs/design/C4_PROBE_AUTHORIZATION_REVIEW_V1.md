# C4 Probe Authorization Review V1

## Purpose

`common-foundation-c4-probe-authorization-review-v1` reviews the C4 probe
decision packet and decides whether a later C4 probe implementation prompt may
be considered by the Supervisor.

This is an authorization review. It is not probe implementation.

## Reviewed Decision Packet

Reviewed input:

- `docs/design/C4_PROBE_DECISION_PACKET_V1.md`
- `samples/c4_probe_decision_packet/c4_probe_decision_packet_v1.json`

The decision packet recommends `recommend_c4_probe_authorization_later` and
routes to this authorization review before any implementation prompt can exist.

## Review Decision

Decision: `accepted_for_future_probe_prompt`.

Recommended next slice:
`common-foundation-c4-probe-minimal-implementation-v1`.

This means the Supervisor may later consider a separate implementation prompt.
It does not authorize implementation in this slice.

The implementation successor is
`docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_V1.md`. It implements only the
single bounded `validation_pack_default_pretty` C4 probe and routes next to a
separate implementation review.

## Why This Is Authorization Review, Not Implementation

This slice reviews policy, evidence, and constraints. It does not add source
code, command execution, command keys, probe configs, subprocess behavior,
target repository writeback, or scheduling.

Implementation remains explicitly disallowed now.

## Current C3 Executable Ceiling

C3 remains the executable ceiling. The production C3 command keys are exactly:

```text
status_snapshot_help
adapters_validate_help
```

`adapters_validate_help` remains fixed help-only behavior. It does not execute
`adapters --validate`, adapter `default_validation`, target repository
writeback, or arbitrary commands.

## Current C4 Design-Only Hardened State

The C4 scoped runner boundary has been accepted and hardened as design-only
evidence. C4 implementation remains unauthorized now.

No C4 command, C4 runner, generalized runner, config command registry, target
writeback, scheduler, autonomy loop, C5 unlock, or C6 unlock exists.

## Future Probe Prompt Eligibility

A future C4 probe prompt may be considered only after Supervisor acceptance of
this review. That later prompt must still be separate and narrow.

The future probe must be a single bounded C4 probe. It must not generalize the
runner, execute arbitrary commands, run adapter validation through
`controlled_runner_probe`, write target repositories, or unlock C5/C6.

## Future Probe Constraints

If a later implementation prompt is issued, it must preserve these constraints:

- single probe only.
- source-hardcoded allowlist only.
- no config-supplied command or argv.
- shell remains false.
- timeout required and bounded.
- output truncation required.
- local path and sensitive-looking value redaction required.
- before and after repository state required.
- no target repository writeback.
- no cross-project execution.
- no scheduler or autonomy behavior.
- no credentials or external authorization.
- no destructive git.
- no force push.

## Exact Non-Goals

This review does not authorize:

- implementation in this slice.
- direct C4 implementation without a separate prompt.
- a third C3 command.
- arbitrary execution.
- command strings or argv supplied by config.
- adapter validation as controlled runner command behavior.
- adapter `default_validation` through `controlled_runner_probe`.
- target repository writeback.
- cross-project execution.
- scheduler or autonomy behavior.
- credentials, external services, web UI, dashboard, publish, render, or
  production actions.
- C5 or C6.

## Arbitrary Execution Prohibition

Arbitrary command execution remains forbidden. A future C4 probe must be a
single bounded probe, not a general command runner.

## Config-Supplied Command Or Argv Prohibition

Configuration must not provide command strings, executables, argv, args, shell
flags, cwd overrides, environment changes, retries, credentials, endpoints, or
write targets.

## Target Repo Writeback Prohibition

Target repository writeback remains forbidden. Target and sibling repositories
may only be observed through existing read-only mechanisms unless a later
design creates a separate reviewed policy.

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

## Known Warnings

The historical pseudo-git-tag fixture warning remains a validation-pack hygiene
warning. It does not block this authorization review because it does not change
command keys, implementation authorization, or the C4 boundary.

Optional sibling repository warnings may appear in cross-project smoke. They do
not block this review because sibling repositories are best-effort observations
and remain read-only.

## Allowed Next Routes

Allowed next routes are:

- `common-foundation-c4-probe-minimal-implementation-v1`
- `common-foundation-validation-fixture-hygiene-v1`
- `common-foundation-c4-design-followup-fix-v1`
- `controlled-runner-stop`

The first route still requires a separate Supervisor prompt. This review is not
that prompt.

## Forbidden Next Routes

Forbidden next routes are:

- direct C4 implementation without separate prompt.
- third C3 command.
- C5.
- C6.
- arbitrary execution.
- adapter validation as controlled command.
- target repo writeback.

## What This Slice Does Not Do

C4 Probe Authorization Review V1 does not change production source, implement a
probe, create a runner, add command behavior, add command keys, run adapter
validation through `controlled_runner_probe`, write target repositories, run
across projects, schedule work, handle credentials, call external services,
publish, render, or unlock C5/C6.
