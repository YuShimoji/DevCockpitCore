# Report Normalizer V1

## Purpose

`common-foundation-report-normalizer-v1` converts AGENT_REPORT-like text into a
structured `report_normalization.v1` JSON readback. The goal is to reduce manual
report parsing burden before a later gate classifier consumes the result.

This slice advances Foundation Automation Readiness only. It does not advance
Execution Automation Readiness.

## Schema

The normalizer emits JSON with these top-level fields:

- `schema_version`: `report_normalization.v1`.
- `generated_at`: UTC ISO-8601 timestamp.
- `producer`: `dev_cockpit.report_normalizer`.
- `source`: input path or stdin metadata, input kind, byte count, and line count.
- `routing`: parsed `[ROUTE: ...]` values such as route, direction, slice, turn,
  target, current/next artifact, reply, and confidence.
- `progress`: parsed lane, meter, done/total count, current state, next state,
  blocker, and user work.
- `action`: parsed decision, owner, deliverable, and trigger.
- `status`: parsed health, gate count, stop class, and estimates.
- `sections`: normalized report sections plus an `extra` object for recognized
  but non-core sections.
- `normalized_outcome`: decision, summary, commits, push state, worktree state,
  remote parity, and test count mentions.
- `handoff`: handoff gate, reason, and whether a supervisor prompt should be
  generated later.
- `next`: next artifact, recommended next slice, next owner, and minimal next
  task when extractable.
- `residue_audit`: residue flags for pseudo git tags, paste-ready prompt
  markers, local user paths, risky automation wording, and readiness overclaims.
- `health`: normalizer health, warnings, and conservative stop class.

Unknown or missing values are represented as `null`, `unknown`, empty strings, or
empty lists depending on the field. Partial reports should normalize rather than
crash.

## CLI Usage

Normalize a file:

```bash
PYTHONPATH=src python -m dev_cockpit.report_normalizer \
  --input samples/reports/agent_report_adapter_manifest_v1_redacted.txt \
  --output samples/report_normalizations/adapter_manifest_v1_readback.json \
  --pretty
```

Normalize stdin to stdout:

```bash
cat report.txt | PYTHONPATH=src python -m dev_cockpit.report_normalizer --stdin --pretty
```

`--output` is optional. If omitted, JSON is printed to stdout.

## Parser Tolerance

The parser recognizes:

- `[ROUTE: ...]`, `[PROGRESS: ...]`, `[ACTION: ...]`, and `[STATUS: ...]`
  headers.
- Markdown headings, bold headings, and known plain headings such as `Outcome`,
  `What Changed`, `Commands And Results`, `Validation`, `Completion Matrix`,
  `Continuation State`, and `Handoff Gate`.
- commit references such as `f5aa1c2 feat: define adapter manifest v1`.
- push, worktree, remote parity, test-count, and handoff pass/fail mentions.

Unexpected formatting, missing headers, missing sections, and non-English body
text should not crash normalization.

## Residue Audit

The residue audit detects:

- pseudo git tags such as `::git-stage`, `::git-commit`, `::git-push`, and other
  `::git-*{...}` tags.
- paste-ready supervisor prompt markers such as `[PASTE TARGET:` or
  `output_type=SUPERVISOR_PROMPT`.
- Windows and Unix local user paths, with output redaction of the user segment.
- risky automation residue such as an unnegated scheduler, exec-loop, external
  notification, auto-render, force-push, or credential-handling instruction.
- overclaims that advance Execution Automation Readiness or production readiness
  from an observer/report slice.

Sample inputs may include redacted local paths to prove detection. Committed
samples must not include raw local user names or credentials.

## Safety Boundary

The normalizer reads text and writes JSON only. It does not run target-project
commands, execute validation packs, render artifacts, schedule work, send
notifications, open services, manage credentials, modify target repositories, or
generate paste-ready next-Agent Prompts.

It may set fields such as `supervisor_should_generate_prompt`,
`recommended_next_slice`, `minimal_next_task`, and `next_owner` for a supervisor
to consume later, but it must not emit a full `[ROUTE: ... SUPERVISOR->AGENT ...]`
prompt or any `Task:`, `Goal Stack:`, or `Allowed scope:` prompt body.

## Relationship To Existing Artifacts

The status producer and adapter manifest describe current repository state. The
report normalizer describes a returned AGENT_REPORT. Together they provide
structured observer inputs for a later gate classifier.

## Future Gate Classifier

`gate-classifier-v1` can consume `report_normalization.v1` fields to distinguish
completed work, partial work, blocked work, user-required work, residue risk, and
handoff readiness. That classifier remains a future slice.

## What This Does Not Do

Report Normalizer V1 does not classify final gates, execute commands, generate
supervisor prompts, create a command runner, start a scheduler, send external
notifications, auto-render artifacts, handle credentials, write target
repositories, or claim production readiness.
