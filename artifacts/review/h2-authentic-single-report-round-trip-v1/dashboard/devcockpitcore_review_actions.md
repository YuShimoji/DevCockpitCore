# DevCockpitCore Review Actions

Non-executable review package generated from local dashboard evidence.

- generated_at: `2026-07-19T15:12:24.4917578+09:00`
- source_dashboard: `artifacts/review/h2-authentic-single-report-round-trip-v1/dashboard/devcockpitcore_dashboard.html`
- total_actions: `18`
- blockers: `0`
- warnings: `14`
- info: `4`

## How to review this package

1. Confirm blocker count is zero before using the dashboard as an integration signal.
2. Review warning actions against their evidence paths and classify them as expected residue or future cleanup.
3. Treat locked-by-gate entries as boundary reminders, not work items.

| action_id | severity | source_type | project_key | title | evidence_path | executable |
| --- | --- | --- | --- | --- | --- | --- |
| validation-001 | warning | validation_pack | devcockpitcore | Review validation warning | samples/validation_packs/devcockpitcore_validation_pack_result.json | False |
| validation-002 | warning | validation_pack | devcockpitcore | Review validation warning | samples/validation_packs/devcockpitcore_validation_pack_result.json | False |
| smoke-003 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-004 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-005 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-006 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-007 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-008 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-devcockpitcore-009 | warning | cross_project_smoke | devcockpitcore | Review devcockpitcore smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-nlmytgen-010 | warning | cross_project_smoke | nlmytgen | Review nlmytgen smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-writingpage-011 | warning | cross_project_smoke | writingpage | Review writingpage smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-clippipegen-012 | warning | cross_project_smoke | clippipegen | Review clippipegen smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-clippipegen-013 | warning | cross_project_smoke | clippipegen | Review clippipegen smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| status-014 | warning | status_snapshot | devcockpitcore | Review current repository status note | samples/status_snapshots/devcockpitcore_status.json | False |
| checkpoint-015 | info | dashboard_review | devcockpitcore | 1. Priority Comprehension | Priority Lane / Active Decision | False |
| checkpoint-016 | info | dashboard_review | devcockpitcore | 2. Selection Synchronization | Priority Review Console | False |
| checkpoint-017 | info | dashboard_review | devcockpitcore | 3. Evidence Eligibility | Evidence Inspector / receipt ledger | False |
| locked-gate-018 | info | locked_gate | devcockpitcore | Keep locked lanes gated | artifacts/review/h2-authentic-single-report-round-trip-v1/dashboard/devcockpitcore_dashboard.html | False |

Review notes:
- These actions are review-only and not a runner.
- Do not treat locked-by-gate entries as work items.
- Use source evidence paths to inspect the underlying JSON before deciding next work.
