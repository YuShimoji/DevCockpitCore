# DevCockpitCore Decision Log

This file records durable decisions needed for restart and handoff. It is not a
full history; design artifacts remain the source of detailed evidence.

## 2026-06-30 - C4 Design Review Accepted As Design-Only

Purpose: decide whether `c4-scoped-runner-design-v1` is safe to accept as a
design-only boundary.

Decision: accepted as design-only evidence.

Effect: `c4-scoped-runner-design-review-v1` becomes the current artifact.
Recommended next route is
`common-foundation-c4-scoped-runner-design-hardening-v1`.

Requirements preserved:

- C3 remains the executable ceiling.
- Production C3 command keys remain exactly `status_snapshot_help` and
  `adapters_validate_help`.
- `adapters_validate_help` remains help-only and does not run
  `adapters --validate`.
- C4 implementation remains unauthorized.
- A third C3 command, C5, C6, arbitrary execution, adapter validation as
  controlled command behavior, scheduler/autonomy, and target repository
  writeback remain forbidden.

State: commit `0598bee test: review c4 scoped runner design` was pushed to
`origin/main` before this handoff refresh.

Owner: Supervisor decides the next route; Agent may execute only a separately
authorized next slice.

Next move: prefer `common-foundation-c4-scoped-runner-design-hardening-v1`.
Allowed alternatives are `common-foundation-c4-probe-decision-packet-v1`,
`controlled-runner-stop`, or `common-foundation-c4-design-fix-v1`.

## 2026-06-30 - Handoff Docs Are Project Authority

Purpose: make another terminal able to resume without relying on chat history.

Decision: keep the current context in `docs/runtime-state.md`,
`docs/project-context.md`, this decision log, `docs/idea-ledger.md`, and
`docs/handoffs/2026-06-30-c4-scoped-runner-design-review-handoff.md`.

Effect: repo-local docs are the restart authority after remote sync.

Requirements preserved: no production implementation changes and no capability
expansion.

State: docs-only handoff refresh.

Owner: Agent maintains docs; next terminal verifies parity and reads the
handoff before continuing.

Next move: fetch/pull, verify parity, then continue only on an allowed C4
review/hardening/decision route.
