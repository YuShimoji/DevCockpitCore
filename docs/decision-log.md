# DevCockpitCore Decision Log

This file records durable decisions needed for restart and handoff. It is not a
full history; design artifacts remain the source of detailed evidence.

## 2026-07-07 - Dashboard Report-First Frontpage Checkpoint

Purpose: preserve the structural correction after user visual feedback that the
Latest Brief still felt forced and the top viewport remained card-heavy.

Decision: make `dashboard-report-first-frontpage-v1` the active dashboard
review-surface artifact. The first viewport should read as a concise Current
Status / Supervision Report, with the former meter board demoted into a compact
Review Map below the report.

Effect: `src/dev_cockpit/dashboard.py`, `tests/test_dashboard.py`, generated
dashboard artifacts, `docs/runtime-state.md`, `docs/project-context.md`,
`docs/PROJECT_COCKPIT.md`, `docs/PROJECT_PIPELINE.mmd`, and
`docs/handoffs/2026-07-07-dashboard-report-first-frontpage-v1.md` now preserve
the report-first structure and restart context.

Requirements preserved:

- The dashboard and Review Actions remain static, local, and non-executable.
- Review Actions remain `executable: false`.
- C3 command set remains exactly two help-only keys.
- C4 command set remains exactly one key: `validation_pack_default_pretty`.
- No web server, scheduler, credentials, target repository writeback, C5, C6,
  or public action beyond normal repository push was added.

State: checkpoint `28af7ff feat: add report-first dashboard frontpage` was
pushed to `origin/main`; post-push parity was `0 0` and the worktree was clean.

Owner: user performs visual acceptance on
`samples/dashboard/devcockpitcore_dashboard.html`; next agent resumes from
`docs/runtime-state.md` and the 2026-07-07 handoff.

Next move: judge whether the first viewport now reads like a concise report.
If accepted, future work should be advisory only: progress-aware report logic,
Japanese display polish, or Review Action Markdown polish.

## 2026-07-06 - Compact Dark Dashboard Handoff After Remote Sync

Purpose: preserve the user-opened dashboard visual feedback and make another
terminal able to resume after syncing over the newer C4 minimal implementation
review state.

Decision: keep `c4-probe-minimal-implementation-review-v1` as the current
execution-readiness authority, and layer `dashboard-compact-dark-overview-v1`
as the current review-surface artifact.

Effect: `docs/runtime-state.md`, `docs/project-context.md`,
`docs/PROJECT_COCKPIT.md`, and dashboard samples are the restart surface for
the compact dark dashboard work. The C4 accepted capability remains exactly one
bounded repo-local validation-pack probe.

Requirements preserved:

- C3 command set remains exactly two help-only keys.
- C4 command set remains exactly one key: `validation_pack_default_pretty`.
- The dashboard and Review Actions remain static, local, and non-executable.
- No web server, scheduler, credentials, target repository writeback, C5, C6,
  or public action was added.

State: local dashboard work was stashed, `origin/main` was fast-forwarded to
`33250ab`, and the dashboard handoff was reapplied on top of the remote C4
minimal implementation review state.

Owner: next terminal should first verify parity, read `docs/runtime-state.md`,
then choose either C4 minimal implementation hardening or dashboard visual
polish.

Next move: prefer
`common-foundation-c4-probe-minimal-implementation-hardening-v1` for execution
readiness, or `japanese-display-polish-v1` for dashboard review ergonomics.

## 2026-07-01 - C4 Probe Minimal Implementation Review Accepted

Purpose: decide whether the single bounded C4 validation-pack probe implemented
as `validation_pack_default_pretty` is acceptable.

Decision: accepted.

Effect: `c4-probe-minimal-implementation-review-v1` becomes the current
artifact. Recommended next route is
`common-foundation-c4-probe-minimal-implementation-hardening-v1`.

Requirements preserved:

- The C3 command set remains exactly two.
- Production C3 command keys remain exactly `status_snapshot_help` and
  `adapters_validate_help`.
- C4 remains exactly one repo-local validation-pack probe:
  `validation_pack_default_pretty`.
- The C4 command is hardcoded, shell-disabled, timeout-bound, redacted, and
  records before/after repository state.
- Adapter validation remains outside controlled runner command behavior.
- A second C4 command, third C3 command, arbitrary execution, target repository
  writeback, scheduler/autonomy behavior, C5, and C6 remain forbidden.

State: live C4 probe readback on commit `d655fb5` exited 0, `main` was in sync
with `origin/main`, before/after worktree state was clean, and the only warning
was the known pseudo-git-tag fixture warning.

Owner: Supervisor decides the next route; Agent may execute a hardening,
fixture-hygiene, narrow fix, or stop slice only when selected by prompt.

Next move: prefer
`common-foundation-c4-probe-minimal-implementation-hardening-v1`. Allowed
alternatives are `common-foundation-validation-fixture-hygiene-v1`,
`common-foundation-c4-probe-minimal-fix-v1`, or
`controlled-runner-stop`.

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
