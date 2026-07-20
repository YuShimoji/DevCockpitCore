# DevCockpitCore Decision Log

This file records durable decisions needed for restart and handoff. It is not a
full history; design artifacts remain the source of detailed evidence.

## 2026-07-21 - Current Observation Safety Hardening And Dirty-Source Stop

Purpose: make the first authorized real-project current-observation attempt
safe against fsmonitor hooks, Git metadata containment mistakes, linked
worktree topology, repository-identity drift, and concurrent context mutation.

Decision: preserve `supervision_current_observation.v1` and its exact serialized
key surface. Apply optional-lock suppression and `core.fsmonitor=false` to
every Git call. Reject output under the target worktree, per-worktree Git
directory, common Git directory, or any registered linked worktree. Capture
and compare the resolved top-level, Git directories, sanitized single-origin
identity, and linked-worktree registry before and after the paired snapshots.
Treat a dirty or unstable real source as an immediate stop before any report,
receipt, assessment, package, envelope, or Dashboard output is created.

Effect: focused safety and compatibility validation passes without changing
the V1 receipt schema. The authorized NLMYTGen preflight resolved revision
`649ada5050be5b9b2153c50c938d855797d5c19f`; its context and paired snapshots
were internally stable, but its complete porcelain state was dirty with 52
entries and SHA-256
`fbfb42256576b212df3a69c2a7dba645eb25dfbd928e8a79335bb5be8546ee78`.
The real-package phase therefore stopped at the required boundary. No
`assessed_at`, current-observation receipt, authority result, or
`h3-real-current-nlmytgen-v1` package exists.

Boundary: no NLMYTGen file was changed, cleaned, staged, tested, rendered,
fetched, pulled, or otherwise executed. The dirty paths were not enumerated or
claimed by DevCockpitCore. Existing H2, H3 V1, H3.1, canonical packet,
production Dashboard, readback, and capture artifacts remain the baselines.
Current eligibility, live coverage, execution authority, and H4 remain false
or unstarted.

State: Phase A safety hardening is complete. Phase B is blocked by a dirty
source checkout and produced no real current-claim package.

Owner: the NLMYTGen checkout owner controls the existing parallel work and any
decision to preserve, commit, relocate, or clean it. The Supervisor controls
renewed report/observation authorization and any future H4 contract.

Next move: do not retry automatically. After the owner supplies this checkout
or another authorized source as clean and stable, start a new bounded attempt
from preflight. Require the exact H3/current dual-source permission again and
keep H4 out of scope.

## 2026-07-20 - Current Observation Ingress V1 And Authority Envelope V2

Purpose: close the operational gap between the H3 authority predicate and an
actual read-only current-observation input without using a real project as the
first execution target.

Decision: add `supervision_current_observation.v1` as an exact-key sidecar and
producer, and add `supervision_report_authority_envelope.v2` as a separate
four-source contract. Keep Envelope V1, Packet V1, Manifest V1, the H2 package,
and the H3 V1 package compatible and unchanged. Observation is allowed only
for one explicit Git top-level directory, fixed shell-disabled read commands,
and an output outside the target. Actual, clean, and stable state must be
rederived from two full HEAD/worktree snapshots.

Effect: V2 current eligibility now requires exact H3/current permission from
both the report and observation, ordered and fresh report/re-observation times,
explicit artifact IDs, full revision equality, clean stable observation, and
separately verified package, receipt, and repository/project/revision
cross-binding provenance. Dashboard accepts V2 only with the complete input
set and performs full source reprojection before any model or output
projection. Missing, H2-only, insufficient, mismatched, malformed, stale,
future, pre-report, post-assessment, dirty, unstable, mutated, and cross-bound
inputs fail closed with distinct evidence.

Boundary: the controlled proof uses only an ephemeral temporary Git repository
and public CLIs. It does not observe or write a real project, fetch, checkout,
stage, commit, push, execute arbitrary commands, start monitoring, add a
runner/scheduler/server/database/credential/notification path, establish live
coverage, or authorize H4. Synthetic current eligibility is not real-project
current authority.

State: H2 remains complete, H3 V1 remains preserved, and H3.1 current
observation ingress is operationally verified without real-project promotion.
The accepted production Dashboard and capture remain unchanged. Real current
eligibility, live coverage, execution, and H4 remain false or unstarted.

Owner: the Supervisor or owner must separately authorize one fresh report and
one read-only observation using the exact
`allowed_for_DevCockpitCore_H3_current_claim` scope before a real current claim
can be assessed.

Next move: perform no real observation automatically. Wait for that explicit
dual-source authorization; keep any H4 pilot behind its own separately approved
contract.

## 2026-07-19 - Report Authority Envelope V1

Purpose: decide mechanically when an authentic AGENT_REPORT may support a
point-in-time current-state claim without conflating transport authenticity,
freshness, revision binding, permission, or live coverage.

Decision: add `supervision_report_authority_envelope.v1` as an exact-key
sidecar. Packet V1 and Manifest V1 remain unchanged. The loader must rebuild
source/manifest/packet hashes and identity, report revision and observation
time, explicit permission, temporal and revision states, authority booleans,
reason codes, and scope from bound sources plus a trusted `assessed_at`, then
require full JSON type-and-value equality. Temporal and revision semantics are
shared with Evidence Freshness V1.

Effect: Dashboard may project Authority Envelope fields only after both
source-bound packet verification and complete Envelope reprojection. The real
H2 report is authentic point-in-time evidence, but H2-only permission, absent
authorized current re-observation, and unknown observed revision keep current
eligibility false. Live coverage and executable remain false. A positive
current-eligibility case exists only as an isolated pure-predicate test.

Boundary: the sidecar adds no report discovery, target or sibling writeback,
runner, scheduler, live monitor, notification, credential, database, server,
or production/publication authority. It does not hard-code a later target
revision or expand H2 permission. H4 multi-project work is not started.

State: H3 authority-envelope contract verified with a deterministic package,
source-bound Dashboard projection, negative tamper matrix, and preserved H2,
canonical fixture, and production Dashboard baselines.

Owner: a future real current claim requires owner-supplied or owner-authorized
fresh report/observation input that explicitly permits H3/current use.

Next move: retain H4 as not started until that explicit input or a separate
supervisor-approved H4 pilot contract exists.

## 2026-07-14 - Portable Canonical Report Binding And Restart Handoff V1.2

Purpose: keep fail-closed manifest binding usable on Windows checkouts and make
the accepted H1 state restartable from another terminal.

Decision: `content_sha256` binds canonical UTF-8 LF bytes. The packet loader
must decode strict UTF-8, normalize CRLF to LF, reject any remaining bare
carriage return, and compare the resulting bytes to the explicit manifest
hash. Tracked supervision report fixtures declare `eol=lf` through
`.gitattributes`. The remote mainline is the restart authority; a separate
dirty local worktree is preserved as an explicitly unintegrated boundary.

Effect: Windows CRLF transport no longer causes an unchanged manifest-bound
report to fail validation. Substantive edits, invalid UTF-8, unsupported line
endings, path drift, and manifest hash drift still fail closed. The handoff
records remote parity, validation evidence, re-entry order, residual ownership,
and the H2 input gate without promoting deterministic fixtures to live claims.

Boundary: this does not add report discovery, weaken task or packet integrity,
write to sibling repositories, promote fixtures to live evidence, or expand the
C3/C4 execution surface.

State: integrated and remotely synchronized after focused and full local
validation. H2 authentic/live report round-trip remains input-gated.

Owner: Supervisor supplies or authorizes the exact current AGENT_REPORT for H2;
Agent performs observer-only binding, packet generation, reload, and readback.

Next move: start at the handoff's re-entry commands, verify remote parity, and
wait for one explicit current report before any live round-trip work.

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
