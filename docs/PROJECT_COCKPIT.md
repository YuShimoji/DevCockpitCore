# DevCockpitCore Project Cockpit

updated_at: 2026-07-13
snapshot_kind: persisted_navigation_snapshot
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

## About This Snapshot

This file is a timestamped, persisted navigation snapshot for people reading
the repository. It summarizes the product surface and points to review
evidence. It is not live development control: Git records code and version
truth, tests and generated evidence record validation truth, and the Web
Supervisor carries current development direction.

## Product State

DevCockpitCore provides read-only repository observation, normalized report
readback, gate classification, local validation evidence, cross-project smoke
observation, explicit manifest-bound cross-project supervision packets, and a
static review dashboard. A / Priority Review Console is the
selected production information architecture, and the A/B/C direction gate is
closed. Its first viewport is organized as current state, ordered priority,
Active Decision, and adjacent Evidence Inspector rather than the earlier
report/card-derived primary layout.

Production direction A is selected for the production dashboard. The tracked
sample remains point-in-time review evidence rather than a live-state claim.

The production surface consumes the existing Evidence Freshness V1 receipt and
keeps review actions non-executable. B / Narrative Status Brief is retained
only as a possible future handoff or summary view. C / Lane And Project
Overview is retained only as a possible future cross-project overview. Neither
is a production tab or an active slice. User production visual acceptance of A
is recorded as accepted.

## Capability Summary

| Capability | State | Boundary |
| --- | --- | --- |
| Repository observation and adapter validation | available | read-only against target repositories |
| Report normalization and gate classification | available | interpretation only; no prompt generation |
| Validation pack and cross-project smoke | available | local evidence; missing optional siblings warn |
| Cross-Project Supervision Packet V1 | available | explicit manifest-bound reports; global rank is attention, not execution |
| Priority Review Console and review actions | available | local, static, bilingual, and non-executable |
| Evidence Freshness V1 integration | available | consumes a validated point-in-time receipt; does not infer live authority |
| C3 probes | bounded | exactly two fixed help-only keys |
| C4 probe | bounded | exactly one fixed local validation-pack key |
| General runner, scheduler, external service, or writeback | absent | outside the accepted capability surface |

## Current Production Review Artifact

- [Production Priority Review Console](../samples/dashboard/devcockpitcore_dashboard.html)
- [Deterministic priority readback](../samples/dashboard/devcockpitcore_priority_readback.json)
- [Non-executable review actions JSON](../samples/dashboard/devcockpitcore_review_actions.json)
- [Non-executable review actions Markdown](../samples/dashboard/devcockpitcore_review_actions.md)
- [Production capture manifest](../samples/dashboard/production_capture/production_capture_manifest.json)
- [Production capture readback](../samples/dashboard/production_capture/production_capture_readback.json)
- [Production contact sheet](../samples/dashboard/production_capture/screenshots/priority-review-console-contact-sheet.png)
- [Cross-project supervision packet](../samples/supervision_packets/cross_project_supervision_packet_v1.json)
- [Project-aware packet readback](../samples/supervision_packets/cross_project_supervision_packet_v1.md)

Generate the default artifacts from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.dashboard `
  --supervision-packet samples/supervision_packets/cross_project_supervision_packet_v1.json
Start-Process .\samples\dashboard\devcockpitcore_dashboard.html
```

The production surface defaults to Japanese and switches the same priorities
and evidence to English in one HTML file. Priority selection synchronizes the
Active Decision and Evidence Inspector; dense evidence remains subordinate.
The capture package records Japanese desktop, English desktop, and Japanese
narrow-width output for review.

The [v2 comparison pack](../samples/dashboard/intent_comparison/verified_observation_surface_intent_pack.html)
and [layout research](design/DASHBOARD_LAYOUT_RESEARCH_V1.md) remain historical
selection provenance. They are not current-state authority and no longer
control the production direction.

## Evidence Freshness

The production generator loads and validates the landed
`evidence_freshness_receipt.v1` contract. It surfaces freshness, temporal and
revision-binding state, current-claim eligibility, assessed time, source route,
compact evidence identifier, authority boundary, and subordinate reason codes.
It consumes those decisions rather than reproducing the freshness evaluator.

Generate a read-only freshness and provenance receipt with:

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.evidence_freshness
```

The tracked policy and deterministic example outputs are:

- [Freshness policy](../samples/evidence_freshness/evidence_freshness_policy_v1.json)
- [Machine-readable receipt](../samples/evidence_freshness/evidence_freshness_receipt_v1.json)
- [Human-readable receipt](../samples/evidence_freshness/evidence_freshness_receipt_v1.md)

These receipts are point-in-time, non-live observer outputs. The tracked
example (`efr-cbae922571043527b800`, assessed
`2026-07-12T00:00:00Z`) is reproducible navigation evidence, not authority for
a current checkout; a current-state claim requires a newly generated and
assessed local receipt followed by dashboard regeneration.

## Navigation

- [Durable mission, architecture, and capability boundaries](project-context.md)
- [Bounded machine-facing restart projection](runtime-state.md)
- [Product hypotheses and parked directions](idea-ledger.md)
- [Durable product and architecture decisions](decision-log.md)
- [Dashboard artifact guide](../samples/dashboard/README.md)

## Current Review Decision

A / Priority Review Console is selected and is the accepted production
direction. The user confirmed the elements, layout, Japanese-first display,
English switch, and Priority Lane / Active Decision / Evidence Inspector
structure. `user_visual_acceptance` is therefore `accepted`; this surface does
not request the same visual review again. Global attention rank remains review
priority rather than a sequential execution schedule.

The tracked packet is deterministic non-live fixture evidence covering two
fictional projects and four reports. It proves task identity, global ranking,
closed-item separation, and project-workset reprojection, but does not claim
live coverage. Live reports remain explicit future inputs; absent live coverage
does not block this contract or dashboard integration.

This document is navigation and decision context, not live workflow authority.
Verify Git state, the receipt authority boundary, generated readback, raster
manifest, and local tests before treating any status as current.
