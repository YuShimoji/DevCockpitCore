# Gate Classifier V1

## Purpose

`common-foundation-gate-classifier-v1` consumes `report_normalization.v1` JSON
and produces a structured `gate_classification.v1` decision readback. It helps a
Supervisor decide whether a lane can continue, needs user action, needs a
handoff, should ask the Supervisor to generate the next prompt, or must stop for
a true blocker.

This slice advances Foundation Automation Readiness only. It does not advance
Execution Automation Readiness.

## Schema

The classifier emits JSON with these top-level fields:

- `schema_version`: `gate_classification.v1`.
- `producer`: `dev_cockpit.gate_classifier`.
- `generated_at`: UTC ISO-8601 timestamp.
- `source`: report normalization path, optional status snapshot path, optional
  adapter path, input kind, and source warnings.
- `routing`: route, slice, current/next artifact, confidence, and direction from
  the normalized report.
- `input_summary`: compact evidence summary from the normalized report.
- `classification`: decision, health, stop class, next owner, continuation
  eligibility, and whether user/supervisor/handoff work is required.
- `gates`: push, handoff, user work, residue, validation, readiness, execution
  automation, production/public, destructive action, and form burden gates.
- `residue_findings`: residue booleans, severity, and recommended handling.
- `readiness`: readiness lane separation and notes.
- `next`: recommended next slice, minimal next task, owner, and side-work state.
- `health`: classifier status, warnings, blockers, and stop class.

Missing optional status snapshot or adapter inputs are source warnings, not
crashes. Invalid required report normalization JSON fails cleanly.

## CLI Usage

Classify a report normalization:

```bash
PYTHONPATH=src python -m dev_cockpit.gate_classifier \
  --report-normalization samples/report_normalizations/adapter_manifest_v1_readback.json \
  --output samples/gate_classifications/adapter_manifest_v1_gate.json \
  --pretty
```

Classify with optional context:

```bash
PYTHONPATH=src python -m dev_cockpit.gate_classifier \
  --report-normalization samples/report_normalizations/adapter_manifest_v1_readback.json \
  --status-snapshot samples/status_snapshots/devcockpitcore_status.json \
  --adapter adapters/devcockpitcore.json \
  --output samples/gate_classifications/adapter_manifest_v1_gate.json \
  --pretty
```

If `--output` is omitted, the classifier prints JSON to stdout.

## Decision Vocabulary

The stable decision values are:

- `completed_continue`
- `supervisor_prompt_needed`
- `user_action_required`
- `handoff_required`
- `integrate_and_continue`
- `blocked_true_stop`
- `blocked_auth`
- `blocked_validation`
- `blocked_safety_boundary`
- `unknown_review_required`

## Stop Class Vocabulary

The stable stop classes are:

- `NONE`
- `INTEGRATE_AND_CONTINUE`
- `USER_AUTH_REQUIRED`
- `HANDOFF_REQUIRED`
- `VALIDATION_FAILED`
- `REPO_STATE_CONFLICT`
- `SAFETY_BOUNDARY`
- `TRUE_STOP`
- `UNKNOWN_REVIEW_REQUIRED`

## Gate Semantics

Push Gate is green when report evidence says the work was committed, pushed, the
worktree was clean, and parity was `0 0`. It is yellow when commit/push/parity
evidence is incomplete.

Handoff Gate is green when the normalized report says the handoff gate passed or
no blocked handoff is required. It is red when handoff is required. Missing
handoff evidence is yellow.

User Work Gate is green when `user_work` is `none`. It becomes user action when
auth, credentials, manual review, manual decision, local operation, or blocked
setup terms are present. Auth and credential terms map to `USER_AUTH_REQUIRED`.

Residue Gate treats pseudo git tags as yellow hygiene warnings, not true
blockers. Paste-ready next-agent prompt residue is a stronger contract warning
because it violates report/prompt separation. Raw local user paths or actionable
runner/scheduler instructions can become red.

Validation Gate is green when tests or checks are reported as passing. It is
yellow when validation evidence is missing or partial, and red when validation
failure is reported.

Readiness Gate prevents Foundation Observer/Automation readiness from being
confused with Execution Automation readiness. Execution automation overclaims
are safety-boundary failures.

Production/Public Gate warns on production or public-readiness claims because
these foundation slices are not production/public action approvals.

Destructive Action Gate is red for unapproved force-push, reset, rebase, stash,
auto-merge, or destructive-action wording.

Form Burden Gate warns on fixed-form burden or paste-ready prompt residue. User
input should remain freeform unless another slice explicitly requires otherwise.

## Relationship To Inputs

The required input is `report_normalization.v1`. Optional `status_snapshot.v1`
and `adapter_manifest.v1` inputs add source context and readiness notes. The
classifier does not invent missing completion evidence and does not require a
perfect AGENT_REPORT structure.

## Future Validation Pack

`validation-pack-v1` can consume `gate_classification.v1` to plan non-executing
validation bundles and later compare reported evidence with expected checks. It
remains a future slice.

## What This Does Not Do

Gate Classifier V1 does not run commands, execute validation packs, generate
supervisor prompts, create a command runner, schedule work, send external
notifications, auto-render artifacts, handle credentials, write target
repositories, auto-merge, rebase, force push, or claim production readiness.
