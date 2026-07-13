# DevCockpitCore Runtime State

updated_at: 2026-07-13
projection_kind: repository_restart_and_artifact_access
current_review_artifact: priority-review-console-production-observation-surface-v1
current_review_artifact_path: samples/dashboard/devcockpitcore_dashboard.html
priority_readback_path: samples/dashboard/devcockpitcore_priority_readback.json
supervision_packet_path: samples/supervision_packets/cross_project_supervision_packet_v1.json
supervision_packet_manifest_path: samples/supervision_packets/task_report_manifest_v1.json
selected_information_architecture: A_priority_review_console
selection_state: closed
user_visual_acceptance: accepted
tracked_receipt_capture_id: efr-cbae922571043527b800
tracked_receipt_assessed_at: 2026-07-12T00:00:00Z
tracked_receipt_authority: point_in_time_non_live
blocking_issue_count: 0
latest_local_validation_at: 2026-07-13T10:00:17Z
latest_local_validation_commit: 7b914b46733a7aff508d2c13fa8103a127152b7c
latest_local_validation_result: validation_pending_after_context_rebase
latest_supervisor_report_path: docs/handoffs/2026-07-13-remote-sync-development-readiness-supervisor-report-v1.md
durable_context_path: docs/project-context.md
layout_research_path: docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md
production_dashboard_path: samples/dashboard/devcockpitcore_dashboard.html
production_generator_path: src/dev_cockpit/dashboard.py
review_actions_json_path: samples/dashboard/devcockpitcore_review_actions.json
review_actions_markdown_path: samples/dashboard/devcockpitcore_review_actions.md
production_capture_manifest_path: samples/dashboard/production_capture/production_capture_manifest.json
production_capture_readback_path: samples/dashboard/production_capture/production_capture_readback.json
production_contact_sheet_path: samples/dashboard/production_capture/screenshots/priority-review-console-contact-sheet.png
supervision_packet_markdown_path: samples/supervision_packets/cross_project_supervision_packet_v1.md
supervision_packet_design_path: docs/design/CROSS_PROJECT_SUPERVISION_PACKET_V1.md
capability_state: bounded_c3_c4
evidence_freshness_policy_path: samples/evidence_freshness/evidence_freshness_policy_v1.json
evidence_freshness_receipt_json_path: samples/evidence_freshness/evidence_freshness_receipt_v1.json
evidence_freshness_receipt_markdown_path: samples/evidence_freshness/evidence_freshness_receipt_v1.md

## Projection Scope

This is a bounded machine-facing projection for repository restart and artifact
access. It contains no branch, pull-request, draft, or merge-state metadata and
does not act as a development workflow controller.

## Capability Boundary

- C3 command keys are exactly `status_snapshot_help` and
  `adapters_validate_help`.
- C4 command keys are exactly `validation_pack_default_pretty`.
- The C4 key maps only to
  `python -m dev_cockpit.validation_pack --default --pretty`.
- A general runner, scheduler, external notification integration, auto-render
  workflow, web server, database, credential handling, target-repository
  writeback, C5, and C6 are absent.

## Artifact Access

The current review artifact is the production A / Priority Review Console at
`samples/dashboard/devcockpitcore_dashboard.html`. The A/B/C direction gate is
closed and A is the production direction. Its deterministic priority readback,
non-executable review actions, capture manifest, capture readback, and contact
sheet are at the paths declared above.

The console can consume the explicit Cross-Project Supervision Packet V1 path
declared above. Its global queue ranks attention/review across projects while
its secondary worksets reuse the same task IDs and ranks by project. The
tracked fixture covers two fictional projects and four reports and is
deterministic non-live evidence, not a live multi-project claim.

Packet intake accepts canonical v6.5 identity and legacy aliases under one
fail-closed normalization contract. Packet loading recomputes binding,
identity, rank, collection, workset, coverage, policy, and scope projections.
The dashboard displays local observer health separately from packet attention;
all-closed packets remain valid with zero priorities and browsable closed
evidence. Tracked capture provenance contains no user-specific absolute path,
and declared timestamp overrides are marked ineligible as current observation.

Production direction A is selected for the production dashboard and
`user_visual_acceptance` is `accepted`.

The historical v2 comparison remains at
`samples/dashboard/intent_comparison/verified_observation_surface_intent_pack.html`
as selection provenance only. B / Narrative Status Brief is parked as a
possible future handoff or summary view. C / Lane And Project Overview is
parked as a possible future cross-project overview. Neither is part of the
production UI or current implementation scope. The production
visual/comprehension gate is closed and must not be requested again for the
same accepted surface.

## Freshness

The production generator consumes the existing validated
`evidence_freshness_receipt.v1`; it does not run a parallel freshness evaluator.
The tracked receipt identified above is deterministic, point-in-time, and
non-live. Its authority classification, assessed time, temporal state,
revision-binding state, provenance, and current-claim eligibility are displayed
in the console. A live claim requires a newly generated receipt assessed
against its recorded policy, observation time, and revision binding, followed
by dashboard regeneration.

H1 authentic/live round-trip remains input-gated: another project's current
AGENT_REPORT must be supplied through an explicit manifest binding. The
deterministic fixture is not promoted to live coverage.

This projection and the other repository documents are navigation and decision
records, not live workflow authority. Verify Git, tests, generated readback, and
the receipt authority boundary directly.

## Continuation Context

The report at `latest_supervisor_report_path` preserves the local readiness
evidence captured at `e5ab070`, then reconciles it with the later revert of the
competing Capsule authority and the Cross-Project Supervision Packet V1.1
integrity checkpoint at `latest_local_validation_commit`. The historical
checkpoint remains evidence, not current workflow authority. Continue from
this projection, `docs/PROJECT_COCKPIT.md`, the report, and direct Git/test
verification.

## Local Validation Entry

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover
python -m dev_cockpit.validation_pack --default --pretty
python -m dev_cockpit.evidence_freshness
python -m dev_cockpit.supervision_packet `
  --manifest samples/supervision_packets/task_report_manifest_v1.json `
  --output-json samples/supervision_packets/cross_project_supervision_packet_v1.json `
  --output-markdown samples/supervision_packets/cross_project_supervision_packet_v1.md `
  --pretty
python -m dev_cockpit.dashboard `
  --supervision-packet samples/supervision_packets/cross_project_supervision_packet_v1.json
Start-Process .\samples\dashboard\devcockpitcore_dashboard.html
```
