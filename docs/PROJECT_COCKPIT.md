# DevCockpitCore Project Cockpit

updated_at: 2026-07-19
snapshot_kind: persisted_navigation_snapshot
current_review_artifact: h3-report-authority-envelope-v1
current_review_artifact_path: artifacts/review/h3-report-authority-envelope-v1/dashboard/devcockpitcore_dashboard.html
priority_readback_path: artifacts/review/h3-report-authority-envelope-v1/dashboard/devcockpitcore_priority_readback.json
authority_envelope_path: artifacts/review/h3-report-authority-envelope-v1/supervision_report_authority_envelope_v1.json
authority_readback_path: artifacts/review/h3-report-authority-envelope-v1/authority_envelope_machine_readback_v1.json
supervision_packet_path: artifacts/review/h2-authentic-single-report-round-trip-v1/cross_project_supervision_packet_v1.json
supervision_packet_manifest_path: artifacts/review/h2-authentic-single-report-round-trip-v1/task_report_manifest_v1.json
selected_information_architecture: A_priority_review_console
selection_state: closed
user_visual_acceptance: accepted
tracked_receipt_capture_id: efr-cbae922571043527b800
tracked_receipt_assessed_at: 2026-07-12T00:00:00Z
tracked_receipt_authority: point_in_time_non_live
blocking_issue_count: 0
current_development_axis: report_authority_contract_readiness
current_local_slice: h3_report_authority_envelope_contract_verified_without_live_promotion_v1
recommended_next_horizon: H4_multi_project_pilot_not_started_requires_explicit_authorized_inputs

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
| Cross-Project Supervision Packet V1 | available | explicit manifest-bound reports; paired manifest intake reprojects source and packet before use |
| Report Authority Envelope V1 | available | exact-key sidecar; source, manifest, packet, and derived authority are reprojected before use |
| Priority Review Console and review actions | available | local, static, bilingual, and non-executable |
| Evidence Freshness V1 integration | available | consumes a validated point-in-time receipt; does not infer live authority |
| C3 probes | bounded | exactly two fixed help-only keys |
| C4 probe | bounded | exactly one fixed local validation-pack key |
| General runner, scheduler, external service, or writeback | absent | outside the accepted capability surface |

## Current Development Entrance

H1 packet ingress and Windows checkout transport are closed on the remote
mainline. Manifest and report objects use exact key surfaces, task continuation
fields are typed before projection, and manifest-bound report hashes bind
canonical UTF-8 LF bytes. Invalid UTF-8, bare carriage returns, path drift, and
substantive content changes still fail closed. The root `.gitattributes`
contract keeps tracked text at LF for new checkouts.

The authorized H2 input has been received and the authentic single-report
round-trip is complete. The exact NLMYTGen report at revision
`d38075b97efabc99d1a23e8e0afafd5d44f1e2de` and SHA-256
`d93f15b3f3441aee6d741adbfd54b285e1850e645998f34fb5384a223d82a65b`
is copied byte-for-byte into the H2 review package. Canonical v7 normalization,
gate classification, packet generation, source-bound full narrative
reprojection, and package-local Priority Review Console projection are
verified.

H3 is complete. `supervision_report_authority_envelope.v1` now binds the H2
source, manifest, packet, identity, revision, report time, assessment time,
permission, and observer-only scope as a separate exact-key sidecar. Its loader
re-reads and reprojects every derived claim before Dashboard projection. The
real H2 report remains authentic owner-attached point-in-time evidence, but its
H2-only permission, absent authorized re-observation, and unobserved current
revision keep `current_claim_eligibility: false`; `live_coverage` and
`executable` also remain false. H4 has not started. A real current claim needs
a new fresh report/observation that explicitly permits the H3/current use.

Resume through this Cockpit for human navigation, `docs/runtime-state.md` for
the machine-facing projection, and `docs/project-context.md` for durable
boundaries. Verify branch, revision, parity, worktree, tests, and generated
evidence directly. Dated handoffs are point-in-time history and are not part of
the normal current-state route.

## Current Production Review Artifact

The current review entrance is the H3 package-local review surface and its
deterministic authority readback:

- [H3 package-local Priority Review Console](../artifacts/review/h3-report-authority-envelope-v1/dashboard/devcockpitcore_dashboard.html)
- [H3 authority-envelope readback](../artifacts/review/h3-report-authority-envelope-v1/AUTHORITY_ENVELOPE_READBACK_V1.md)
- [H3 strict Authority Envelope](../artifacts/review/h3-report-authority-envelope-v1/supervision_report_authority_envelope_v1.json)
- [H3 binding inventory](../artifacts/review/h3-report-authority-envelope-v1/binding_inventory_v1.json)

The H2 source-bound package remains the immutable input baseline:

- [H2 package-local Priority Review Console](../artifacts/review/h2-authentic-single-report-round-trip-v1/dashboard/devcockpitcore_dashboard.html)
- [H2 round-trip readback](../artifacts/review/h2-authentic-single-report-round-trip-v1/h2_authentic_round_trip_readback_v1.md)
- [H2 source-bound packet](../artifacts/review/h2-authentic-single-report-round-trip-v1/cross_project_supervision_packet_v1.json)
- [H2 manifest](../artifacts/review/h2-authentic-single-report-round-trip-v1/task_report_manifest_v1.json)

The accepted production surface remains unchanged:

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

The canonical tracked packet remains deterministic non-live fixture evidence
covering two fictional projects and four reports. H2 adds a separate package
bound to one authentic owner-authorized NLMYTGen report. That package projects
`task-31aac3069238ee38` as `active_safe_continuation`, with
`integrate_and_continue / INTEGRATE_AND_CONTINUE`, rank 1, and
`executable: false`. It does not promote either evidence family to live or
current authority.

H3 adds a strict sidecar without changing Packet V1 or Manifest V1. For the
real H2 input it independently exposes authenticity `true`, temporal state
`fresh`, revision state `unknown`, permission state `insufficient_h2_only`,
current eligibility `false`, live coverage `false`, and executable `false`.
Only the isolated pure-predicate test reaches current eligibility `true`; that
fixture is not tracked as project evidence. H4 multi-project work is not
started.

`QD-PACKET-UNKNOWN-KEY-01` is closed. The packet root, every active or closed
task, and every `task.next_state` now reject missing or unexpected keys before
Dashboard model or HTML projection. Existing nested packet objects remain exact
through strict equality or deterministic reprojection. JSON object key order is
still accepted, schema identity remains `cross_project_supervision_packet.v1`,
and the canonical JSON, Markdown, Dashboard, and accepted visual state are
unchanged.

Packet ingress and checkout transport are closed for H1. The manifest root and
each report entry now reject missing or unexpected keys against their exact
four-key and six-key surfaces. Every active or closed `task.next_state`
requires non-empty string values for `owner`, `user_work`, and `agent_work`,
with `recommended_slice` limited to `null` or a non-empty string. Invalid
values become `DashboardError` before model or HTML projection. Report hashes
bind canonical UTF-8 LF bytes; CRLF checkout transport is normalized before
hashing, while invalid UTF-8, bare carriage returns, and substantive edits fail
closed. The repository-root `* text=auto eol=lf` rule keeps tracked text
portable without weakening the content contract.

`QD-PACKET-NARRATIVE-REPROJECTION-01` is closed for paired manifest-plus-source
intake. `load_packet_with_manifest` strictly reloads the manifest, revalidates
the source bytes and SHA-256, normalizes and classifies the report, rebuilds the
packet at the manifest timestamp, strictly loads the stored packet, and
requires full JSON-type equality. Validly typed changes to outcome, current, or
next-state narrative therefore fail closed before Dashboard projection. The
standalone stored-packet authority boundary remains: `load_packet` proves
self-consistency but cannot independently establish source authenticity,
live/current authority, freshness, or current-claim eligibility.

The integrity-ready intake preserves canonical v6.5 ROUTE identity exactly,
keeps the legacy report dialect compatible, and rejects conflicting aliases.
Loaded packets are revalidated across bindings, identity-derived task IDs,
collections, ranks, worksets, coverage, policy, and observer-only scope. The
console separates local observer health from packet attention and treats a
zero-active all-closed packet as a valid informational state. Capture paths are
portable and deterministic timestamp overrides are explicitly non-current.

This document is navigation and decision context, not live workflow authority.
Verify Git state, the receipt authority boundary, generated readback, raster
manifest, and local tests before treating any status as current. Dated handoffs
may explain prior decisions but never override this route or live evidence.
