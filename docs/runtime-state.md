# DevCockpitCore Runtime State

updated_at: 2026-07-12
projection_kind: repository_restart_and_artifact_access
current_review_artifact: verified-observation-surface-intent-pack-v2
current_review_artifact_path: samples/dashboard/intent_comparison/verified_observation_surface_intent_pack.html
source_commit: 2e5e924b12a311260bf10c7b252c0695cac7f80c
observed_at: 2026-07-06T16:56:16+09:00
freshness_state: stale
blocking_issue_count: 0
durable_context_path: docs/project-context.md
layout_research_path: docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md
production_dashboard_path: samples/dashboard/devcockpitcore_dashboard.html
production_generator_path: src/dev_cockpit/dashboard.py
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

The current review artifact is the v2 three-direction, same-claim intent
comparison at
`samples/dashboard/intent_comparison/verified_observation_surface_intent_pack.html`.
Its directions are A (Priority Review Console), B (Narrative Status Brief), and
C (Lane And Project Overview). Its manifest and automated readback are in the
same directory, and its supporting research is
`docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md`. User direction selection remains
pending. The production dashboard and generator remain separate and unchanged
by this review checkpoint.

## Freshness

The projection records the comparison evidence source commit
`2e5e924b12a311260bf10c7b252c0695cac7f80c`; the latest generation time among
the three tracked source artifacts is `2026-07-06T16:56:16+09:00`. Its `stale`
state is explicit: re-read Git state
and regenerate validation evidence before treating the values as current after
that observation.

The tracked evidence-freshness policy and JSON/Markdown receipt examples are at
the paths declared above. They are deterministic, point-in-time, non-live
observer outputs rather than workflow control or authority for the current
checkout. A live claim requires a newly generated receipt assessed against its
recorded policy, observation time, and revision binding.

## Local Validation Entry

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover
python -m dev_cockpit.validation_pack --default --pretty
python -m dev_cockpit.evidence_freshness
```
