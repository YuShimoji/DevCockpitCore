# DevCockpitCore Decision Log

This file records durable decisions needed for restart and handoff. It is not a
full history; design artifacts remain the source of detailed evidence.

## 2026-07-13 - Supervision Packet Integrity V1.1

Purpose: make canonical report intake and loaded-packet validation fail closed
without changing the accepted Priority Review Console layout.

Decision: preserve canonical v6.5 ROUTE `thread/lane/slice/artifact` identity,
retain legacy aliases, and reject material mixed-dialect conflicts. ACTION is
optional when structured progress/status and outcome evidence are sufficient.
At packet load, recompute identity-derived task IDs, source bindings,
active/closed collections, rank order, worksets, coverage, attention policy,
and the complete observer-only scope boundary.

Effect: local observer health and packet attention are separate header reads;
all-closed packets render as zero-priority informational states. Capture paths
are portable, and actual observation timestamps are distinguishable from
deterministic declared overrides.

Boundary: the tracked fixture remains non-live and every action remains
`executable: false`. H1 live round-trip still requires explicitly supplied
current AGENT_REPORT inputs; this decision does not discover or fabricate them.

## 2026-07-13 - Explicit Cross-Project Supervision Packet V1

Purpose: make multiple project/thread reports reviewable in one accepted
Priority Review Console without implying a sequential execution schedule.

Decision: accept `task_report_manifest.v1` as the only report-ingress contract
for Cross-Project Supervision Packet V1. Every report must be explicitly named,
repository-relative, UTF-8, and SHA-256 bound. Existing report normalization
and gate classification remain the interpretation path.

Effect: the packet emits one global attention queue, project-local worksets
using the same task IDs, and a separate closed/informational collection. Rank
is assigned once globally as attention/review priority. Project worksets never
recalculate it. The Priority Review Console can consume the packet explicitly
and shows project/thread/lane identity plus source report/hash while preserving
Priority Lane / Active Decision / Evidence Inspector.

Boundary: the tracked two-project, four-report package is deterministic
non-live fixture evidence. There is no latest-file discovery, conversation
inference, sibling-repository writeback, execution schedule, project tab,
matrix, B/C primary layout, or executable action. Live report routing and
round-trip resolution evidence remain later horizons.

## 2026-07-13 - Priority Review Console Visual Acceptance Closed

Purpose: close the remaining visual/comprehension gate without reopening the
A/B/C direction decision or expanding the production layout.

Decision: record `user_visual_acceptance: accepted` for A / Priority Review
Console. The user confirmed that the elements, layout, descriptions,
Japanese-first display, English switch, and Priority Lane / Active Decision /
Evidence Inspector structure are understandable. The same production surface
must not request another visual review.

Effect: the generator, generated dashboard, priority readback, production
capture readback, Project Cockpit, runtime projection, pipeline, and tests use
one accepted state. Worker raster inspection remains a separate hash-bound QA
record and does not replace or reset the user decision.

Boundary: acceptance applies to the current A skeleton. It does not turn global
attention rank into execution order, reopen B/C, authorize a project matrix or
new primary layout, or add any executable action.

## 2026-07-13 - Priority Review Console Selected For Production

Purpose: close the A/B/C material-direction gate and make the selected
production observation surface explicit without expanding execution authority.

Decision: select A / Priority Review Console as the production information
architecture. This decision supersedes the 2026-07-12 pending-selection entry.
B / Narrative Status Brief is retained only as a possible future handoff or
summary view. C / Lane And Project Overview is retained only as a possible
future cross-project overview. Neither B nor C is a production tab or an active
implementation request.

Effect: the production generator uses a concise current-state strip, one
deterministically ordered Priority Lane, the selected priority's Active
Decision workspace, and an adjacent Evidence Inspector as the primary
viewport. Dense project, validation, and historical material is subordinate.
The generator consumes the landed `evidence_freshness_receipt.v1` contract,
rather than recreating freshness logic, and produces:

- `samples/dashboard/devcockpitcore_dashboard.html`
- `samples/dashboard/devcockpitcore_priority_readback.json`
- `samples/dashboard/devcockpitcore_review_actions.json`
- `samples/dashboard/devcockpitcore_review_actions.md`
- the production capture package under `samples/dashboard/production_capture/`

Requirements preserved:

- Priority ranking is evidence-derived, deterministic, deduplicated, and
  review-only.
- Review Actions remain `executable: false`.
- Tracked freshness evidence remains explicitly point-in-time and non-live;
  receipt authority and current-claim eligibility remain visible.
- Japanese is the default and English uses the same priorities and evidence in
  the same HTML artifact.
- A general runner, scheduler, server, database, credentials, notifications,
  external services, and target-repository writeback remain absent.
- C3 and C4 capability boundaries remain unchanged.

State at selection time: the A/B/C direction gate was closed and the production
artifact, priority readback, and capture package became the review surfaces.
The later acceptance entry above supersedes the then-pending visual gate.

Historical owner at selection time: Agent maintained the local production
generator and evidence package; the user owned one free-form production
visual/comprehension judgment, now completed.

Historical next move (completed): inspect whether the first viewport exposed
current state, first priority, next operation, owner, evidence location, and
current-claim status. Do not reopen an A/B/C choice unless a later explicit
product decision supersedes this entry.

Navigation note: README, Project Cockpit, runtime-state, pipeline, and this log
are navigation and decision records, not live workflow authority. Verify Git,
tests, generated readback, receipt authority, and capture hashes directly.

## 2026-07-12 - Dashboard Intent Comparison Before Production Selection (Superseded)

Superseded by the 2026-07-13 A-selection decision above. The following text is
retained as historical provenance for the selection evidence and describes the
state at the time of this entry, not current direction.

Purpose: make the dashboard information-architecture choice reviewable without
changing the production generator or comparing different evidence across
directions.

Decision: use `verified-observation-surface-intent-pack-v1` as the current
review artifact. It presents Priority Review Console, Narrative Status Brief,
and Lane And Project Overview with the same 24 semantic values, Japanese-first
copy, an English toggle, and explicit point-in-time provenance.

Effect: one static comparison surface, a fixture, manifest, automated readback,
capture helper, and three same-viewport screenshots provided selection evidence.
At that checkpoint the earlier research recommendation for A was advisory, and
the entry did not accept a direction.

Requirements preserved:

- `src/dev_cockpit/dashboard.py` was unchanged at that checkpoint.
- The comparison is local, static, non-executable, and read-only.
- Stale observation evidence is labeled and is not promoted to current-state
  authority.
- The observer, automation, and bounded C3/C4 capability lanes remain separate.

Historical state at entry time: the comparison pack was available for review
and the user preference had not yet been recorded.

Historical owner: the user was to select A, B, or C. That gate was completed by
the 2026-07-13 decision.

Historical next move (completed): review the three directions in one viewport
and record a short free-form preference with the most important reason.

## 2026-07-07 - Remote Sync Resume Handoff (Historical)

The sync and restart provenance below is retained, but its report-first
dashboard state was superseded by the 2026-07-13 production A decision.

Purpose: make another terminal able to resume from the latest pushed
DevCockpitCore state without relying on chat context.

Decision: keep `dashboard-report-first-frontpage-v1` as the active artifact and
add a docs-only remote-sync resume packet at
`docs/handoffs/2026-07-07-remote-sync-resume-handoff-v1.md`.

Effect: `docs/runtime-state.md`, `docs/project-context.md`, this decision log,
`docs/idea-ledger.md`, and the new handoff file now preserve the latest
sync/parity state, restart order, capability boundary, and residual work.

Requirements preserved:

- No source code, tests, generated dashboard artifact, adapter manifest, or
  runner behavior changed.
- C3 command set remains exactly two help-only keys.
- C4 command set remains exactly one key: `validation_pack_default_pretty`.
- Dashboard and Review Actions remain static, local, and non-executable.
- No scheduler, web server, credentials, target repository writeback, C5, C6,
  or public action beyond normal repository push was added.

State: before the docs-only refresh, `main` was fast-forwarded to
`origin/main` at `c72ec47 docs: refresh report-first dashboard handoff`,
`HEAD...origin/main` was `0 0`, and the worktree was clean.

Owner: Agent maintains repo-local restart docs and pushes the docs-only
handoff; user owns visual acceptance of the dashboard.

Next move: from another terminal, fetch/pull, verify parity, read
`docs/runtime-state.md`, then open
`samples/dashboard/devcockpitcore_dashboard.html` for visual acceptance or
select the next explicit route.

## 2026-07-07 - Dashboard Report-First Frontpage Checkpoint (Superseded)

Superseded for the production dashboard by the 2026-07-13 Priority Review
Console decision. The checkpoint details remain as visual-history provenance.

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
