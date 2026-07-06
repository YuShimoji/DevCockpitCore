# DevCockpitCore Runtime State

updated_at: 2026-07-06
active_artifact: dashboard-editorial-brief-v1
artifact_current: dashboard-editorial-brief-v1
artifact_next: japanese-display-polish-v1 or progress-driven-brief-evolution-v1
next: Open samples/dashboard/devcockpitcore_dashboard.html for editorial Latest Brief review, or harden the accepted single bounded C4 validation-pack probe
user_work: local dashboard editorial brief visual review
render_gate: not_applicable
handoff: docs/PROJECT_COCKPIT.md
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

The current review-surface slice is `dashboard-editorial-brief-v1`. It keeps
the static dashboard and non-executable Review Actions package, preserves the
native dark home-linked decision meter HUD, and replaces the ingredient-label
Latest Brief with a compact editorial status note. The brief gives a headline
judgment, implication, compact three-step cue, and one primary review link
before the meter board. Dense evidence remains available below the overview or
in native details panels. It is an offline review artifact, not an execution
surface.

User visual review accepted the dark mode and improved organization as usable
for now, then flagged the first Latest Brief as too factual and not meaningful
enough. The remaining caveat is visual tone: the editorial note should be
opened locally and judged against the meter board for whether it is worth
reading first every time.

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
- Present the dashboard as a home-linked dark decision meter HUD with an
  editorial Latest Brief, short display labels, keyboard/focus markers, non-JS
  fallback text, print-oriented CSS, Review Stack targets, back-to-overview
  links, and progressive disclosure for dense evidence.

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
4. `docs/handoffs/2026-07-01-c4-probe-minimal-implementation-review-handoff.md`
5. `docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_REVIEW_V1.md`
6. `samples/c4_probe_minimal_implementation_review/c4_probe_minimal_implementation_review_v1.json`
7. `docs/handoffs/2026-06-30-c4-probe-minimal-implementation-handoff.md`
8. `docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_V1.md`
9. `samples/c4_probe_minimal_implementation/c4_probe_minimal_result_v1.json`
10. `docs/design/C4_PROBE_AUTHORIZATION_REVIEW_V1.md`
11. `docs/design/C4_PROBE_DECISION_PACKET_V1.md`
12. `docs/PROJECT_COCKPIT.md`
13. `docs/PROJECT_PIPELINE.mmd`
14. `samples/dashboard/devcockpitcore_dashboard.html`
15. `samples/dashboard/devcockpitcore_review_actions.json`
16. `samples/dashboard/devcockpitcore_review_actions.md`
17. `docs/decision-log.md`
18. `docs/idea-ledger.md`

First live checks:

```bash
git status --short --branch
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count HEAD...origin/main
```

Use the bundled Python runtime or a real Python 3.11+ interpreter with
`PYTHONPATH=src`. Avoid the WindowsApps `python.exe` stub.

## Last Validation

Last known validation before commit/push:

- `python -m compileall src tests`: pass.
- `python -m unittest tests.test_dashboard`: 18 tests OK.
- `python -m unittest discover`: 300 tests OK.
- `python -m dev_cockpit.status_snapshot --repo . --adapter adapters\devcockpitcore.json --output samples\status_snapshots\devcockpitcore_status.json --pretty`: pass.
- `python -m dev_cockpit.validation_pack --default --output samples\validation_packs\devcockpitcore_validation_pack_result.json --pretty`: pass, warning-level historical pseudo-git-tag fixture residue.
- `python -m dev_cockpit.cross_project_smoke --default --output samples\cross_project_smokes\devcockpitcore_cross_project_smoke_result.json --pretty`: pass, warning-level observer rows.
- `python -m dev_cockpit.dashboard --output samples/dashboard/devcockpitcore_dashboard.html`: pass, with review action JSON/Markdown outputs.
- `python -m json.tool samples/dashboard/devcockpitcore_review_actions.json`: pass.
- Review action package readback: 20 actions, 0 blockers, 16 warnings, 4 info, 1 locked-by-gate, all `executable: false`.
- `validation_pack --default`: warn only for historical pseudo-git-tag fixture residue.
- `cross_project_smoke --default`: warning-level observer rows, no blockers.
- `git diff --check`: pass.

## Handoff Notes

- Remote `origin/main` had advanced to `33250ab`; the local dashboard work was
  stashed, the repo was fast-forwarded, and the dashboard handoff was reapplied.
- This handoff intentionally preserves the remote C4 minimal implementation
  review state and layers the compact dark dashboard review surface on top.
- No sibling repositories were edited.
- No staging, commit, or push should be assumed complete until the final chat
  report names the pushed commit.
