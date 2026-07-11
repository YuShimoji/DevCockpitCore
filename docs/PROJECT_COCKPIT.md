# DevCockpitCore Project Cockpit

updated_at: 2026-07-12
snapshot_kind: persisted_navigation_snapshot
current_review_artifact: verified-observation-surface-intent-pack-v1
current_review_artifact_path: samples/dashboard/intent_comparison/verified_observation_surface_intent_pack.html
source_commit: 2e5e924b12a311260bf10c7b252c0695cac7f80c
observed_at: 2026-07-06T16:56:16+09:00
freshness_state: stale
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
observation, and a static review dashboard. The production dashboard generator
is unchanged while its next information architecture is compared at low
fidelity.

The current layout research recommends Priority Review Console as one strong
candidate. That recommendation is not user acceptance. Narrative Status Brief
and Lane And Project Matrix remain materially different candidates for the
same observation data.

## Capability Summary

| Capability | State | Boundary |
| --- | --- | --- |
| Repository observation and adapter validation | available | read-only against target repositories |
| Report normalization and gate classification | available | interpretation only; no prompt generation |
| Validation pack and cross-project smoke | available | local evidence; missing optional siblings warn |
| Static dashboard and review actions | available | local, non-executable review surface |
| C3 probes | bounded | exactly two fixed help-only keys |
| C4 probe | bounded | exactly one fixed local validation-pack key |
| General runner, scheduler, external service, or writeback | absent | outside the accepted capability surface |

## Current Review Artifact

- [Dashboard layout research](design/DASHBOARD_LAYOUT_RESEARCH_V1.md)
- [Three-direction low-fidelity intent comparison](../samples/dashboard/intent_comparison/verified_observation_surface_intent_pack.html)
- [Machine-readable comparison manifest](../samples/dashboard/intent_comparison/intent_comparison_manifest.json)
- [Automated interaction and screenshot readback](../samples/dashboard/intent_comparison/intent_comparison_readback.json)
- [Current production dashboard](../samples/dashboard/devcockpitcore_dashboard.html)

The comparison pack is research evidence only. It keeps the same semantic data
and wording across A, B, and C, defaults to Japanese, provides an English
toggle, and does not modify or select the production dashboard implementation.

## Evidence Freshness

The comparison's tracked evidence was observed from
`2e5e924b12a311260bf10c7b252c0695cac7f80c`; `2026-07-06T16:56:16+09:00`
is the latest generation time among its status, validation, and smoke sources.
Its `stale` label means the evidence remains
useful for comparing information architecture but must not be treated as a
claim about the current checkout. Tracked dashboard, status, validation, smoke,
and review-action samples may remain valid historical evidence while being
stale for current-state claims.

## Navigation

- [Durable mission, architecture, and capability boundaries](project-context.md)
- [Bounded machine-facing restart projection](runtime-state.md)
- [Product hypotheses and parked directions](idea-ledger.md)
- [Durable product and architecture decisions](decision-log.md)
- [Dashboard artifact guide](../samples/dashboard/README.md)

## Next Product Decision

Choose A (Priority Review Console), B (Narrative Status Brief), or C (Lane And
Project Matrix) according to which makes current state and next action easiest
to understand. A remains the research recommendation, not an acceptance
decision. Do not change the production generator until that selection exists.
