# DevCockpitCore Main Sync / Supervisor Roadmap Report V1

updated_at: 2026-07-11 JST
reverified_at: 2026-07-11 03:21 JST
report_kind: dated supervisor handoff snapshot
authority_note: this report records observed state; it does not replace the
current project authority chain or approve a pending design direction
workspace_branch: main
workspace_head: dc6b5bb
upstream: origin/main
remote_parity_after_fetch_and_pull: 0 ahead / 0 behind
active_product_checkpoint: dashboard-layout-research-and-prototype-v1
recommended_immediate_route: repair Draft PR #1, consolidate current-state
authority, then run a dashboard intent checkpoint

## Executive Readback

The local `main` checkout is synchronized with `origin/main` and is usable for
development. Fresh live validation has no blocking failure: source compilation,
305 unit tests, all four adapter manifests, JSON samples, CLI help surfaces,
conflict-marker checks, path redaction, mojibake checks, and forbidden-feature
checks passed.

The checkout is not a clean handoff boundary. Its dirty state has two distinct
causes:

1. Three tracked lowercase authority files are reported as modified because of
   LF/CRLF and stat-cache behavior, but their normalized content hashes exactly
   match `HEAD` and `git diff` is empty.
2. A local, untracked Project Capsule document set and review artifacts exist.
   They are real local work and must not be deleted or silently treated as
   canonical.

The newest remote development work is not on `main`. Remote branch
`origin/codex/workflow-handoff` is two commits ahead at `8b41166` and is exposed
as Draft PR #1. It contains a useful current-state authority and intent-gate
redesign, but it should not be merged unchanged. The draft currently conflicts
with the project-local rule that `AGENTS.md` must not grow into procedures, has
merge-unsafe branch/PR state embedded in current-state documents, and contains a
duplicate `handoff` key not rejected by its new contract test.

The current product decision remains intentionally open. The Priority Review
Console prototype is a recommended low-fidelity direction, not an accepted
production direction. Production dashboard generator work should wait until the
user compares the intended alternatives and selects an information architecture.

## Recovery Brief And Completion Estimate

Project thesis: make local multi-project development supervision reviewable and
source-backed before granting broader execution authority.

Current development axis: converge on one current-state authority, select the
dashboard information architecture through an Intent Gate, and make evidence
freshness and review priority deterministic before production UI work.

Final deliverable image: one explicitly generated, static local supervision
surface from which a low-context user or supervising agent can understand current
state, priority, next decision, deferrable work, evidence route, and freshness,
with every claim traceable to its source commit and no broad runner/writeback.

The following bars are completion estimates for their named lanes, not schedule
forecasts or production-readiness claims:

| Lane | Estimate | Rationale |
| --- | --- | --- |
| Foundation Observer Readiness | `[##########] 100%` | status schema/producer, adapters, read-only Git observation, warnings, and tests exist |
| Foundation Automation core | `[##########] 100%` | normalization, gates, validation pack, smoke, static dashboard, and review actions exist |
| Currently authorized C3/C4 scope | `[##########] 100%` | the exact bounded two-key C3 and one-key C4 capability is implemented and tested |
| Mainline authority convergence | `[####------] 40%` | a substantial Draft PR exists, but five merge blockers and local Capsule duplication remain |
| Dashboard intent selection | `[###-------] 30%` | research and one prototype exist; comparable alternatives and explicit user selection do not |
| Evidence freshness/provenance | `[#---------] 10%` | stale evidence is identified, but no deterministic contract/checker exists |
| Selected production review surface | `[----------] 0%` | intentionally blocked until intent and evidence contracts are ready |
| Mature verified observation plane | `[####------] about 40%` | core evidence producers are mature, while authority, freshness, prioritization, and selected UX remain open |

Major delivery gap: DevCockpitCore can produce and display evidence, but it cannot
yet prove that the displayed evidence is current or explain one canonical review
order inside a user-selected supervision layout.

## Remote Synchronization Evidence

Commands run from the repository root:

```powershell
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count "HEAD...origin/main"
```

Observed result:

- `git pull --ff-only origin main`: `Already up to date.`
- local `main`: `dc6b5bb docs: add layout research resume handoff`
- `origin/main`: `dc6b5bb docs: add layout research resume handoff`
- parity: `0 0`
- new fetched branch: `origin/codex/workflow-handoff`
- branch delta: `0 behind / 2 ahead` relative to `origin/main`
- branch tip: `8b41166 docs: record workflow handoff PR`
- PR: <https://github.com/YuShimoji/DevCockpitCore/pull/1>
- PR state at inspection: open draft, cleanly mergeable, no review decision, no
  reviews, no configured status checks, and no commit status contexts

Interpretation: the latest default-branch state is locally integrated. The
workflow branch is fetched and inspectable, but remains an unmerged review lane
and was deliberately not mixed into `main`.

## Worktree Readback

### Tracked paths reported as modified

```text
docs/decision-log.md
docs/project-context.md
docs/runtime-state.md
```

For each path, `git hash-object` matches the corresponding index/HEAD blob and
`git diff` produces no content diff. Global Git configuration has
`core.autocrlf=true`; the working files currently use a form that causes Git to
retain an `M` stat state. Treat these entries as line-ending/stat noise, not as
three undocumented semantic edits. Do not normalize the whole repository as an
incidental fix; any line-ending policy belongs in a separately reviewed slice.

### Real untracked local state

```text
artifacts/review/.gitkeep
artifacts/review/2026-07-10-rekickstart-validation-pack.json
artifacts/review/2026-07-11-main-status-snapshot.json
artifacts/review/2026-07-11-main-status-snapshot-v2.json
artifacts/review/2026-07-11-remote-sync-validation-pack.json
artifacts/review/2026-07-11-resync-validation-pack-v2.json
docs/ARTIFACT_INDEX.md
docs/DECISION_LOG.md
docs/PROJECT_BRIEF.md
docs/RESEARCH_NOTES.md
docs/RESEARCH_TODO.md
docs/ROADMAP.md
docs/RUNTIME_STATE.md
docs/UI_RUBRIC.md
docs/VALIDATION.md
docs/handoffs/2026-07-11-main-sync-supervisor-roadmap-report-v1.md
screenshots/.gitkeep
```

The uppercase/underscore Project Capsule documents are not path-identical to the
tracked lowercase/hyphen documents, but they duplicate current-state, roadmap,
decision, and validation semantics. They were created during a 2026-07-10
re-kickstart pass and are not part of `origin/main`. Preserve them until a human
or supervising agent chooses one of these outcomes:

- integrate their durable validation/artifact-index value into the canonical
  lowercase authority and retire the duplicate status surfaces;
- explicitly adopt a bounded subset and update the authority chain; or
- archive/reject them with a recorded decision.

## Fresh Live Validation

Runtime:

```text
C:\Users\thank\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

The repository has no `.venv` and no third-party runtime dependencies. A real
Python 3.11+ interpreter plus `PYTHONPATH=src` is sufficient; avoid the
WindowsApps Python stub.

Material validation command:

```powershell
$env:PYTHONPATH = "src"
& "C:\Users\thank\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" `
  -m dev_cockpit.validation_pack --default `
  --output artifacts/review/2026-07-11-resync-validation-pack-v2.json --pretty
```

Result:

| Evidence | Result |
| --- | --- |
| Validation checks | 16 of 16 completed |
| Passed | 15 |
| Warnings | 1 |
| Failed / missing / skipped | 0 / 0 / 0 |
| Unit tests | 305 passed |
| Unit-test duration in this recheck | 88.046 seconds |
| Source/test compilation | pass |
| Adapter manifests | 4 of 4 pass |
| CLI help surfaces | pass |
| JSON parsing | pass |
| Conflict/prompt/path/mojibake/forbidden-feature checks | pass |
| Warning | known pseudo-git-tag fixture in a redacted sample report |
| Stop class | `INTEGRATE_AND_CONTINUE` |

The warning is expected fixture residue, not an execution or production blocker.
The pack reports health `yellow` rather than `green` because the warning remains.

A fresh core status snapshot was also generated:

```text
artifacts/review/2026-07-11-main-status-snapshot-v2.json
```

It confirms branch `main`, head `dc6b5bb`, upstream `origin/main`, parity
`in_sync`, and a dirty-worktree warning with no blocking stop class.

### Evidence Freshness Debt

The tracked default dashboard inputs are checkpoint samples, not live truth:

| Tracked sample | Generated | Recorded DevCockpitCore head |
| --- | --- | --- |
| `samples/status_snapshots/devcockpitcore_status.json` | 2026-07-06 | `2e5e924` |
| `samples/validation_packs/devcockpitcore_validation_pack_result.json` | 2026-07-06 | `2e5e924` |
| `samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json` | 2026-07-06 | `2e5e924` |

They predate current `main` at `dc6b5bb` and Draft PR #1 at `8b41166`, and the
tracked self-status/smoke evidence records a dirty checkpoint. This is a real
decision-quality gap: future dashboard and supervision packets must display
source HEAD, generation time, dirty-at-generation state, and freshness status
rather than allowing old samples to look current.

## Implemented Capability State

### Foundation Observer Readiness

- adapter manifests and validation
- read-only Git/repository observation
- `status_snapshot.v1`
- structured warnings for missing upstreams, sibling repositories, and optional
  project documents

State: implemented and covered by live tests.

### Foundation Automation Readiness

- `report_normalization.v1`
- `gate_classification.v1`
- fixed local validation pack and `validation_pack_result.v1`
- read-only cross-project smoke result
- static local dashboard
- source-backed, non-executable review actions

State: implemented. Current dashboard output is evidence; its top-level layout
is not the accepted future product direction.

### Execution Automation Readiness

- C3 keys are exactly `status_snapshot_help` and `adapters_validate_help`.
- C4 contains exactly `validation_pack_default_pretty`.
- C4 maps only to
  `python -m dev_cockpit.validation_pack --default --pretty` with fixed argv,
  no shell, a timeout, output truncation/redaction, and before/after repo state.

State: deliberately bounded. No second C4 command, general registry, C5, or C6
is authorized.

### Explicitly Absent

- general execution loop or arbitrary command runner
- scheduler, daemon, or autonomous work loop
- external notifications or services
- web server, database, credentials, or telemetry
- target-repository writeback
- production/public dashboard claim

These are safety boundaries, not accidental missing features.

## Draft PR #1 Acceptance Audit

The branch's central ideas are valuable:

- make `docs/PROJECT_COCKPIT.md` the human-readable current-state authority;
- keep `docs/runtime-state.md` as a compact projection;
- keep durable architecture in `docs/project-context.md`;
- use Authority Gates for capability/external-impact decisions;
- use Intent Gates before expensive layout or information-architecture work;
- enforce a bounded restart surface with tests.

Must fix before merge:

1. Remove delivery procedure, exploration workflow, closeout template, and
   completion-report procedure from branch `AGENTS.md`; keep only project-local
   boundaries and references to the appropriate contract document.
2. Replace branch-specific `resume_branch`, draft-PR publication state, and
   branch URLs with landing-safe `main` state before or as part of the merge.
3. Resolve the duplicate `handoff` key in branch `docs/runtime-state.md` and make
   the contract parser reject duplicate keys.
4. Strengthen the PR URL contract so both missing values cannot pass by comparing
   `None == None`.
5. Decide how the untracked Project Capsule documents relate to the proposed
   single Cockpit authority; do not keep two live status systems by accident.
6. Re-run compilation, all branch tests, adapter validation, and the validation
   pack on the landing candidate. The draft reports 309 tests, but there is no
   configured CI check on the PR.

Acceptable debt after those fixes:

- no dedicated linter is configured;
- no repo-local screenshot command exists;
- tracked sample JSON/dashboard artifacts can remain historical if their
  freshness is explicit and machine-detectable;
- optional sibling repositories may continue to produce warnings.

## Residual Work Ownership

| Work | Purpose | Effect | Requirements | State | Owner | Next move |
| --- | --- | --- | --- | --- | --- | --- |
| Repair Draft PR #1 | land the useful authority/intent model safely | one small restart path and tested state contract | remove AGENTS procedures, fix runtime metadata/test gaps, validate landing candidate | must-fix before merge | agent, supervisor review | patch the PR branch; keep it draft until checks pass |
| Resolve Project Capsule duplication | prevent two competing live-state systems | clearer resumption and less stale-doc risk | preserve unique validation/artifact-index value and record the chosen fate | open docs decision | supervisor/user, agent implements | compare durable content, integrate or archive, then verify links |
| Dashboard intent checkpoint | choose the product direction before generator cost | avoids another card-polish loop | two or three low-fidelity alternatives, recommendation, explicit user choice | human decision gate | user/supervisor | compare Priority Review Console, Narrative Status Brief, and Lane/Project Matrix |
| Evidence freshness guard | distinguish checkpoint samples from live state | safer decisions from dashboard and packets | timestamp/head/source provenance rules and warning-only validation | ready after authority repair | agent | define and test a small freshness contract |
| Priority derivation model | turn warnings/actions into one explainable order | makes the dashboard operational rather than archival | deterministic rule, source links, fixtures, override/unknown semantics | design seed | agent, supervisor reviews | prototype a review-queue contract without execution behavior |
| Visual verification route | make UI acceptance reproducible | reduces responsive and Japanese-layout risk | bounded browser/DOM/screenshot procedure, no server requirement | acceptable tooling debt | agent | add only when a dashboard direction is selected |

## Proposed Long-Horizon Objective Ladder

These are proposals, not accepted scope. Each milestone must preserve the
observer-first boundary unless a separate authority decision explicitly changes
it.

### G0 — Mainline Integrity And One Authority

Outcome: Draft PR #1 lands in a main-safe form, local Project Capsule duplication
is resolved, and one tested current-state authority points to a compact restart
surface.

Acceptance evidence: clean landing candidate, no duplicate runtime keys, current
branch/PR metadata, authority-contract tests, fresh validation pack, and a
recorded decision for every retained/retired capsule file.

### G1 — Dashboard Intent Selection

Outcome: the user chooses a low-fidelity information architecture before any
production generator rewrite.

Acceptance evidence: side-by-side review of at least Priority Review Console,
Narrative Status Brief, and Lane/Project Matrix; explicit selection/rejection;
Japanese reading-order notes; rollback statement.

### G2 — Evidence Freshness And Review Queue Contracts

Outcome: every supervision surface can say whether evidence is current enough
and why one review item precedes another.

Acceptance evidence: versioned freshness/readback schema, deterministic queue
fixture, source provenance, unknown/stale warning behavior, adapter compatibility,
and no execution side effects.

### G3 — Selected Static Supervision Surface

Outcome: the chosen design is implemented as the production static local
dashboard without card-first regression.

Acceptance evidence: generator diff, regression tests, regenerated HTML and
review-action artifacts, wide/narrow visual or DOM evidence, keyboard/print
checks, Japanese-first labels, explicit static/local/non-executable readback.

### G4 — Cross-Project Supervision Packet V1

Outcome: status, normalization, gates, validation, smoke, freshness, queue, and
handoff evidence can be consumed as one versioned supervisor packet while
retaining source provenance.

Acceptance evidence: schema, producer, redacted samples across available
adapters, partial/missing-upstream behavior, compatibility tests, and a concise
human summary generated from the same packet.

### G5 — Adapter And Evidence Reliability

Outcome: additional projects can participate without making DevCockpitCore own
their product readiness.

Acceptance evidence: adapter conformance fixtures, schema migration policy,
artifact bounds, performance budget, deterministic warning taxonomy, and
cross-version compatibility tests.

### G6 — Controlled Execution Governance Decision

Outcome: after observer and supervision surfaces are stable, the supervisor
decides whether any additional bounded C4 behavior is justified.

Acceptance evidence before implementation: real use case, fixed command and
argv, explicit authority, dry-run/readback model, timeout/redaction/audit rules,
before/after state contract, rollback, and rejection of arbitrary config-supplied
execution. C5/C6 remain separately locked.

### G7 — Mature Local Development Cockpit

Outcome: a user can open one local surface, understand current multi-project
state, see evidence freshness and ordered decisions, hand work to another agent,
and resume safely without reading chat history or granting broad execution.

Success is measured by low-context resumption quality, explainable decisions,
fresh evidence, and bounded authority—not by the number of integrations or the
amount of automation.

## High-Value Strategic Branches

### Route A — Governance First, Then Product (recommended)

- Objective: repair and land the single-authority workflow, then run the intent
  checkpoint and build the selected surface.
- Becomes stronger: restartability, reviewability, and future changes all share
  one reliable authority model.
- Main risk: visible dashboard progress waits for a short governance cleanup.
- Best fit: when another terminal or supervising AI must resume reliably.

### Route B — Evidence Contract First

- Objective: implement freshness and deterministic review-queue semantics before
  choosing the final dashboard layout.
- Becomes stronger: any later UI is driven by explainable, current data rather
  than rearranged cards.
- Main risk: the contract may encode assumptions that visual exploration would
  have challenged.
- Best fit: when incorrect prioritization or stale evidence is the larger risk
  than presentation quality.

### Route C — Intent Prototype First

- Objective: make the three low-fidelity directions comparable immediately,
  while doing only the minimum PR safety repair needed for reliable review.
- Becomes stronger: the user can make the highest-leverage product decision
  quickly and avoid another production rewrite.
- Main risk: authority cleanup remains partially open and must not be forgotten
  after the design choice.
- Best fit: when the user is available now for visual/product judgment.

## Recommended Sequence

Use Route A as the default:

1. Preserve the current main working tree and the untracked capsule/artifacts.
2. Repair Draft PR #1 in its own branch; do not merge it unchanged.
3. Resolve the capsule-versus-Cockpit authority decision and make the landing
   metadata true for `main`.
4. Validate the landing candidate, review it, merge, fetch/pull `main`, and
   confirm `0 0` parity.
5. Run the three-direction dashboard intent checkpoint.
6. If a direction is selected, define freshness and priority semantics at the
   smallest level required by that design.
7. Implement and visually verify the selected static dashboard.
8. Only then consider a unified supervision packet and broader adapter
   reliability work.
9. Consider any execution expansion only through a new, explicit Supervisor
   authorization gate.

## Exact Restart Commands

```powershell
Set-Location "C:\Users\thank\Storage\Media Contents Projects\DevCockpitCore"
git fetch --prune origin
git pull --ff-only origin main
git status --short --branch
git rev-list --left-right --count "HEAD...origin/main"

$env:PYTHONPATH = "src"
& "C:\Users\thank\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover
& "C:\Users\thank\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m dev_cockpit.validation_pack --default --pretty
```

Read in this order for the immediate next decision:

1. `AGENTS.md`
2. this report
3. `docs/PROJECT_COCKPIT.md`
4. `docs/runtime-state.md`
5. Draft PR #1 diff and `docs/handoffs/2026-07-10-workflow-handoff.md` from its
   branch
6. `docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md` only when preparing the intent
   checkpoint

## Stop Conditions

- Do not call the worktree clean while the untracked capsule/artifacts remain.
- Do not merge Draft PR #1 before its AGENTS, landing metadata, duplicate-key,
  test, and authority-duplication gaps are resolved.
- Do not treat either uppercase Project Capsule state docs or the PR's Cockpit
  model as canonical without recording the authority decision.
- Do not rewrite the production dashboard generator before the user selects a
  direction.
- Do not expand C4, add C5/C6, or add external/writeback behavior from this
  roadmap alone.
