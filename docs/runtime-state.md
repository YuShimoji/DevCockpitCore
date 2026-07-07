# DevCockpitCore Runtime State

updated_at: 2026-07-07
active_artifact: dashboard-report-first-frontpage-v1
artifact_current: dashboard-report-first-frontpage-v1
artifact_next: progress-driven-report-evolution-v1 or japanese-display-polish-v1
next: Open samples/dashboard/devcockpitcore_dashboard.html for report-first frontpage review, or harden the accepted single bounded C4 validation-pack probe
user_work: local dashboard report-first visual review
render_gate: not_applicable
handoff: docs/handoffs/2026-07-07-remote-sync-resume-handoff-v1.md
active_artifact_handoff: docs/handoffs/2026-07-07-dashboard-report-first-frontpage-v1.md
latest_remote_sync_resume_base_commit: c72ec47 docs: refresh report-first dashboard handoff
latest_dashboard_report_frontpage_commit: 28af7ff feat: add report-first dashboard frontpage
latest_dashboard_editorial_commit: 3ea0e1e feat: add dashboard editorial brief
remote_sync_state_at_handoff_start: origin/main fast-forwarded to 33250ab before local dashboard handoff was reapplied
latest_remote_handoff_refresh_commit: b99d8c6 docs: refresh c4 review handoff state
latest_hardening_commit: 763f9e9 test: harden c4 scoped runner design
latest_decision_packet_commit: 8f3312b docs: decide c4 probe authorization path
latest_authorization_review_commit: 53b3f45 test: review c4 probe authorization path
latest_minimal_implementation_commit: ed870bf feat: add minimal c4 validation-pack probe
latest_minimal_implementation_review_base_commit: d655fb5 docs: refresh c4 minimal implementation handoff
latest_remote_commit_before_local_handoff_commit: 33250ab test: review minimal c4 validation-pack probe

## Current State

DevCockpitCore has completed observer and foundation automation slices, the
bounded C3 probe/hardening path, C3 second-command design and help-probe
evidence, the production C3 help-only probe for `adapters_validate_help`, the
C4 design and decision path, and a review-accepted minimal C4 implementation.

Current executable capability is intentionally narrow:

- C3 has exactly two help-only command keys:
  `status_snapshot_help` and `adapters_validate_help`.
- C4 has exactly one bounded repo-local validation-pack probe key:
  `validation_pack_default_pretty`.
- The C4 key maps only to
  `python -m dev_cockpit.validation_pack --default --pretty`.

The current review-surface slice is `dashboard-report-first-frontpage-v1`. It
keeps the static dashboard and non-executable Review Actions package, preserves
native dark mode and linked detail evidence, and absorbs the former Latest
Brief into a concise Current Status / Supervision Report frontpage. The six
large meter cards are no longer the first viewport; their detail-navigation
role is demoted into a compact Review Map below the report. Dense evidence
remains available below the frontpage or in native details panels. It is an
offline review artifact, not an execution surface.

This runtime-state refresh is a docs-only remote-sync resume handoff. At
handoff start, `main` was already fast-forwarded to `origin/main` at
`c72ec47 docs: refresh report-first dashboard handoff`, `HEAD...origin/main`
was `0 0`, and the worktree was clean. The active artifact and capability
boundary are unchanged.

User visual review accepted the dark mode and improved organization as usable
for now, then flagged that the Latest Brief still felt forced and that the
card-heavy top viewport remained the root problem. The current correction is a
structural layout change, not another copy-only brief pass.

## Verified Capabilities

- Load read-only adapter manifests.
- Inspect a target git repository with read-only git commands.
- Emit `status_snapshot.v1` JSON.
- Handle missing target repositories, missing upstreams, and absent optional
  project docs as structured warnings.
- Normalize AGENT_REPORT-like text into `report_normalization.v1`.
- Classify normalized reports and status snapshots into
  `gate_classification.v1`.
- Run the fixed DevCockpitCore-local validation pack and emit
  `validation_pack_result.v1`.
- Run read-only cross-project smoke observations with warning states for
  optional sibling repository conditions.
- Preserve the exact C3 command set and no-third-command rule.
- Preserve the exact C4 command set as one accepted validation-pack key.
- Generate a local static dashboard at
  `samples/dashboard/devcockpitcore_dashboard.html`.
- Generate non-executable review actions at
  `samples/dashboard/devcockpitcore_review_actions.json` and
  `samples/dashboard/devcockpitcore_review_actions.md`.
- Present the dashboard as a report-first dark frontpage with a compact Review
  Map, short display labels, keyboard/focus markers, non-JS fallback text,
  print-oriented CSS, Review Stack targets, back-to-review-map links, and
  progressive disclosure for dense evidence.

## Safety Boundary

This project still has no general execution loop, arbitrary command runner,
scheduler, external notification integration, auto-render workflow, web server,
database, credential handling, target-repository writeback system, public
actions, C5, or C6.

Broad adapter validation, adapter `default_validation`, target repo writeback,
multiple C4 commands, a generalized runner, and any C5/C6 behavior remain
locked until a later Supervisor prompt authorizes and reviews them.

## Restart Surface

Start a new terminal or agent from:

1. `AGENTS.md`
2. `docs/runtime-state.md`
3. `docs/project-context.md`
4. `docs/handoffs/2026-07-07-remote-sync-resume-handoff-v1.md`
5. `docs/handoffs/2026-07-07-dashboard-report-first-frontpage-v1.md`
6. `docs/PROJECT_COCKPIT.md`
7. `docs/PROJECT_PIPELINE.mmd`
8. `samples/dashboard/README.md`
9. `samples/dashboard/devcockpitcore_dashboard.html`
10. `samples/dashboard/devcockpitcore_review_actions.json`
11. `samples/dashboard/devcockpitcore_review_actions.md`
12. `docs/handoffs/2026-07-01-c4-probe-minimal-implementation-review-handoff.md`
13. `docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_REVIEW_V1.md`
14. `samples/c4_probe_minimal_implementation_review/c4_probe_minimal_implementation_review_v1.json`
15. `docs/handoffs/2026-06-30-c4-probe-minimal-implementation-handoff.md`
16. `docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_V1.md`
17. `samples/c4_probe_minimal_implementation/c4_probe_minimal_result_v1.json`
18. `docs/design/C4_PROBE_AUTHORIZATION_REVIEW_V1.md`
19. `docs/design/C4_PROBE_DECISION_PACKET_V1.md`
20. `docs/decision-log.md`
21. `docs/idea-ledger.md`

First live checks:

```powershell
git status --short --branch
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count "HEAD...@{u}"
```

Use the bundled Python runtime or a real Python 3.11+ interpreter with
`PYTHONPATH=src`. Avoid the WindowsApps `python.exe` stub.

## Last Validation

Last known validation before commit/push for the report-first frontpage slice:

- bundled `python -m compileall src tests`: pass.
- bundled `PYTHONPATH=src python -m unittest tests.test_dashboard`: 18 tests OK.
- bundled `PYTHONPATH=src python -m unittest discover`: 300 tests OK.
- bundled `PYTHONPATH=src python -m dev_cockpit.dashboard --output samples/dashboard/devcockpitcore_dashboard.html`: pass, with review action JSON/Markdown outputs.
- bundled `python -m json.tool samples/dashboard/devcockpitcore_review_actions.json`: pass.
- Playwright `file://` smoke: `report-first-frontpage` variant present, old Latest Brief absent, old meter board absent, old decision-meter cards absent, 6 Review Map links present, Review Stack collapsed.
- Generated artifact scan: no prompt delimiters, raw host paths, `shell=True`, old top-surface classes, or `executable: true` matches.
- Review action package readback: 20 actions, all `executable: false`.
- `git diff --check`: pass; Git emitted line-ending normalization warnings only.

## Handoff Notes

- The latest remote-sync resume refresh is docs-only. It preserves the
  `c72ec47 docs: refresh report-first dashboard handoff` remote state as the
  starting point and keeps the active artifact at
  `dashboard-report-first-frontpage-v1`.
- `dashboard-report-first-frontpage-v1` was committed and pushed as
  `28af7ff feat: add report-first dashboard frontpage`; post-push parity was
  `0 0` and the worktree was clean.
- Latest dashboard editorial checkpoint is `3ea0e1e feat: add dashboard
  editorial brief`, pushed to `origin/main` with parity `0 0` before this
  handoff refresh began.
- The prior editorial handoff remains useful only as history:
  `docs/handoffs/2026-07-06-dashboard-editorial-brief-v1.md`.
- The older C4 handoff remains in the restart surface as boundary memory, not
  as the first active dashboard continuation target.
- No sibling repositories were edited.
