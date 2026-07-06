# DevCockpitCore Review Actions

Non-executable review package generated from local dashboard evidence.

- generated_at: `2026-07-06T01:09:33Z`
- source_dashboard: `samples/dashboard/devcockpitcore_dashboard.html`
- total_actions: `22`
- blockers: `0`
- warnings: `18`
- info: `4`

## How to review this package

1. Confirm blocker count is zero before using the dashboard as an integration signal.
2. Review warning actions against their evidence paths and classify them as expected residue or future cleanup.
3. Treat locked-by-gate entries as boundary reminders, not work items.

| action_id | severity | source_type | project_key | title | evidence_path | executable |
| --- | --- | --- | --- | --- | --- | --- |
| validation-001 | warning | validation_pack | devcockpitcore | Review validation warning | samples/validation_packs/devcockpitcore_validation_pack_result.json | False |
| validation-002 | warning | validation_pack | devcockpitcore | Review validation warning | samples/validation_packs/devcockpitcore_validation_pack_result.json | False |
| validation-003 | warning | validation_pack | devcockpitcore | Review validation warning | samples/validation_packs/devcockpitcore_validation_pack_result.json | False |
| smoke-004 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-005 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-006 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-007 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-008 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-009 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| smoke-010 | warning | cross_project_smoke | None | Review cross-project smoke warning | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-devcockpitcore-011 | warning | cross_project_smoke | devcockpitcore | Review devcockpitcore smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-nlmytgen-012 | warning | cross_project_smoke | nlmytgen | Review nlmytgen smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-writingpage-013 | warning | cross_project_smoke | writingpage | Review writingpage smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-writingpage-014 | warning | cross_project_smoke | writingpage | Review writingpage smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-clippipegen-015 | warning | cross_project_smoke | clippipegen | Review clippipegen smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-clippipegen-016 | warning | cross_project_smoke | clippipegen | Review clippipegen smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| project-clippipegen-017 | warning | cross_project_smoke | clippipegen | Review clippipegen smoke row | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | False |
| status-018 | warning | status_snapshot | devcockpitcore | Review current repository status note | samples/status_snapshots/devcockpitcore_status.json | False |
| checkpoint-019 | info | dashboard_review | devcockpitcore | 1. Warning Ownership | Warnings Triage | False |
| checkpoint-020 | info | dashboard_review | devcockpitcore | 2. Blocker Check | Health, Gate, Readiness | False |
| checkpoint-021 | info | dashboard_review | devcockpitcore | 3. Evidence Freshness | Sources and Access | False |
| locked-gate-022 | info | locked_gate | devcockpitcore | Keep locked lanes gated | samples/dashboard/devcockpitcore_dashboard.html | False |

Review notes:
- These actions are review-only and not a runner.
- Do not treat locked-by-gate entries as work items.
- Use source evidence paths to inspect the underlying JSON before deciding next work.
