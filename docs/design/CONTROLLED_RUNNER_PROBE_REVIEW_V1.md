# Controlled Runner Probe Review V1

## Purpose

`common-foundation-controlled-runner-probe-review-v1` reviews the first C3
controlled runner probe evidence. It decides whether the single fixed
`status_snapshot_help` probe is accepted, accepted with constraints, requires a
scoped fix, is rejected, or needs unknown review.

This is an acceptance review and hardening slice. It is not a runner expansion
slice.

## Why Review Is Required Before C4

Controlled Runner Probe V1 intentionally exercised only one fixed help/read-only
command. Before any later C4 scoped runner design can be considered, the C3
evidence must show fixed command identity, no arbitrary command strings,
`shell=False`, timeout, redaction, before/after repo state, no target repository
writeback, and explicit C4-C6 lock state.

C3 acceptance is evidence that the first probe boundary worked. It does not
approve C4, C5, C6, a command registry, a generalized runner, or scheduler-like
behavior.

## Schemas

`controlled_runner_probe_review.v1` records the review key, project key,
required capability level, accepted command keys, locked capability levels,
required safety gates, and notes.

`controlled_runner_probe_review_result.v1` records source probe evidence,
acceptance decision, evidence checks, sample interpretation, readiness, summary,
and health.

## Acceptance Decisions

- `accepted`: all C3 evidence checks pass and post-commit clean evidence exists.
- `accepted_with_constraints`: C3 evidence is safe, but non-blocking warnings
  remain, such as a during-work dirty sample that is explained by a clean
  post-commit probe result.
- `fix_required`: the implementation appears bounded, but evidence, samples,
  docs, or tests need a scoped fix.
- `rejected`: arbitrary execution, shell execution, target writeback,
  credentials, network, destructive git, or C4-C6 leakage is present.
- `unknown_review_required`: required evidence cannot be parsed or classified.

## Evidence Checks

The review checks fixed command key, hardcoded allowlist source, config args
blocking, `shell=False`, timeout, output truncation flags, redaction, before and
after repo state, target writeback false, credentials false, network false,
destructive git false, write scope explanation, clean post-commit probe evidence,
all required safety gates, C4-C6 lock state, and absence of paste-ready next
prompt markers.

## Dirty Sample Interpretation

The committed `controlled_runner_probe_result_v1.json` may show a dirty
worktree because it was generated while the probe implementation and docs were
being created. That is acceptable only when a separate post-commit clean result
shows the same C3 probe passing with clean before/after worktree state.

The post-commit clean sample is
`samples/controlled_runner_probes/controlled_runner_probe_result_v1_post_commit.json`.
The hardened canonical sample is
`samples/controlled_runner_probes/controlled_runner_probe_result_v1_canonical.json`.

## Relationship To Probe V1

Probe V1 runs the single fixed command and emits evidence. Probe Review V1 reads
that evidence and classifies it. The review CLI does not run the probe command
itself.

`c3_probe_hardening.v1` uses the canonical review result to remove ambiguity
from the prior `accepted_with_constraints` state without unlocking C4-C6.

## Relationship To Gate Classification And Validation Pack

`gate_classification.v1` classifies AGENT_REPORT-like outputs and supervision
gates. `validation_pack_result.v1` checks repository health. Probe Review V1 is
narrower: it reviews C3 controlled runner probe evidence and lock boundaries.

## Copy-Transport Residue Note

UI-appended copy transport markers at the tail of pasted reports are not
automatic authored report violations. Review samples and docs should still avoid
unexplained pseudo action markers.

## What This Does Not Do

Probe Review V1 does not add command keys, execute arbitrary commands, run
adapter `default_validation`, create a generalized runner, schedule work, send
notifications, auto-render media, handle credentials, open a web UI, store a
database, write target repositories, publish, or unlock C4-C6.
