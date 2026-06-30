# C4 Scoped Runner Design Hardening V1

## Purpose

`common-foundation-c4-scoped-runner-design-hardening-v1` canonicalizes the
accepted C4 scoped runner design-only state after the design review.

This is hardening, not implementation. It records the accepted boundary,
synchronizes the restart context, and constrains the next decision point while
preserving C3 as the executable ceiling.

## Reviewed C4 Design State

The hardened inputs are:

- `docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md`
- `samples/c4_scoped_runner_design/c4_scoped_runner_design_v1.json`
- `samples/c4_scoped_runner_design/c4_scoped_runner_decision_packet_v1.json`
- `docs/design/C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md`
- `samples/c4_scoped_runner_design_review/c4_scoped_runner_design_review_v1.json`

The reviewed design commit is
`7964c31946bd56a243a35a6538c55efc7b2ce2f4`. The design review commit is
`0598beedfc22300a8515794bc8d92603037dbf22`.

The review decision is accepted. The acceptance applies only to the design
boundary.

## Why This Is Hardening, Not Implementation

This hardening does not create runnable behavior. It adds no source command
path, no command registry, no runner module, no C4 probe, and no additional C3
command key.

The artifact records policy and evidence so future work cannot treat design
acceptance as hidden implementation authorization.

## Current C3 Executable Ceiling

C3 remains the executable ceiling. The production command keys are exactly:

```text
status_snapshot_help
adapters_validate_help
```

The production command count is exactly two. There is no third C3 command key
and no C4 command key.

`adapters_validate_help` remains fixed help-only behavior. It maps to module
help and does not run adapter validation.

## C4 Design Acceptance Versus C4 Implementation Authorization

C4 design acceptance means the proposed boundary is coherent enough to preserve
as policy and evidence. It does not mean C4 implementation is authorized.

C4 implementation authorization would require a separate Supervisor decision,
a decision packet, a future probe prompt, probe evidence, probe review, and
hardening. None of those implementation steps are completed by this slice.

## Context Debt Handling

`docs/project-context.md` was checked and synchronized narrowly. It now records:

- C3 as the current executable ceiling.
- the accepted and hardened C4 design-only state.
- C4 implementation as unauthorized.
- the next route as decision-only, stop, or follow-up fix.

The stale context debt from the pre-hardening review state is resolved for this
slice.

## C4 Implementation Prohibition

C4 implementation remains prohibited. This hardening must not be used to add a
runner, execute commands, add a C4 key, broaden the C3 allowlist, or turn design
language into production behavior.

## C5/C6 Lock Confirmation

C5 and C6 remain locked. Cross-project execution, scheduler behavior, autonomy
loops, background execution, notifications, credentials, external services, web
UI, and production/public actions remain outside the authorized surface.

## No Target Repo Writeback

Target repository writeback remains forbidden. Missing upstreams, absent
optional sibling repositories, and optional project docs should remain
structured warnings, not reasons to introduce writes.

## No Scheduler Or Autonomy

No scheduler, daemon, background loop, retry loop, autonomous runner, or
notification workflow is introduced or authorized.

## No Arbitrary Execution

Config cannot supply command strings, executables, argv, args, shell flags, cwd
overrides, environment changes, retry policies, credentials, endpoints, or write
targets. Arbitrary execution remains forbidden.

## No Adapter Validation Controlled Command

Adapter validation may still be run by an agent as ordinary repository
validation evidence. It is not a controlled runner command, and adapter
`default_validation` remains outside `controlled_runner_probe`.

## Recommended Next Route

The recommended next route is
`common-foundation-c4-probe-decision-packet-v1`.

That route is decision-only. It may decide whether a future C4 probe should be
authorized later, but it must not implement a probe.

## Allowed Next Routes

Allowed next routes are:

- `common-foundation-c4-probe-decision-packet-v1`
- `controlled-runner-stop`
- `common-foundation-c4-design-followup-fix-v1`

Supervisor decision is required before any next route starts.

## Forbidden Next Routes

Forbidden next routes are:

- direct C4 implementation.
- C4 probe implementation without a prior decision packet.
- third C3 command expansion.
- C5 or C6 work.
- arbitrary execution.
- adapter validation as controlled runner command behavior.
- adapter `default_validation` as controlled runner behavior.
- generalized runner or command registry loaded from config.
- target repository writeback.
- scheduler or autonomy loop.

## What This Hardening Does Not Do

C4 Scoped Runner Design Hardening V1 does not change production source, add
command behavior, create a runner, run adapter validation through
`controlled_runner_probe`, write target repositories, run across projects,
schedule work, handle credentials, call external services, publish, render, or
unlock C5/C6.
