# DevCockpitCore Runtime State

updated_at: 2026-07-23
projection_kind: repository_restart_and_artifact_access
current_review_artifact: h3-report-authority-envelope-v1
current_review_artifact_path: artifacts/review/h3-report-authority-envelope-v1/dashboard/devcockpitcore_dashboard.html
priority_readback_path: artifacts/review/h3-report-authority-envelope-v1/dashboard/devcockpitcore_priority_readback.json
authority_envelope_path: artifacts/review/h3-report-authority-envelope-v1/supervision_report_authority_envelope_v1.json
authority_readback_path: artifacts/review/h3-report-authority-envelope-v1/authority_envelope_machine_readback_v1.json
authority_binding_inventory_path: artifacts/review/h3-report-authority-envelope-v1/binding_inventory_v1.json
supervision_packet_path: artifacts/review/h2-authentic-single-report-round-trip-v1/cross_project_supervision_packet_v1.json
supervision_packet_manifest_path: artifacts/review/h2-authentic-single-report-round-trip-v1/task_report_manifest_v1.json
selected_information_architecture: A_priority_review_console
selection_state: closed
user_visual_acceptance: accepted
tracked_receipt_capture_id: efr-cbae922571043527b800
tracked_receipt_assessed_at: 2026-07-12T00:00:00Z
tracked_receipt_authority: point_in_time_non_live
blocking_issue_count: 0
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
h2_round_trip_readback_path: artifacts/review/h2-authentic-single-report-round-trip-v1/h2_authentic_round_trip_readback_v1.json
h2_source_report_path: artifacts/review/h2-authentic-single-report-round-trip-v1/source/AGENT_REPORT_H2_SOURCE_V1.md
h2_source_revision: d38075b97efabc99d1a23e8e0afafd5d44f1e2de
h2_source_sha256: d93f15b3f3441aee6d741adbfd54b285e1850e645998f34fb5384a223d82a65b
h2_state: h2_authentic_single_report_round_trip_verified_non_live_v1
h3_state: h3_report_authority_envelope_contract_verified_without_live_promotion_v1
h3_1_state: h3_current_observation_ingress_operationally_verified_without_real_project_promotion_v1
h3_1_readback_path: artifacts/review/h3-current-observation-ingress-v1/current_observation_ingress_machine_readback_v1.json
h3_1_safety_boundary_state: h3_current_observation_environment_isolated_dirty_negative_contract_v1
h3_1_safety_boundary_readback_path: artifacts/review/h3-current-observation-safety-boundary-v1/safety_boundary_machine_readback_v1.json
h3_1_safety_boundary_binding_path: artifacts/review/h3-current-observation-safety-boundary-v1/binding_inventory_v1.json
real_current_observation_attempted: true
real_current_observation_receipt_created: false
h3_real_current_evaluation_state: historical_blocked_source_worktree_dirty_no_package_v1
h3_real_current_candidate_revision: 649ada5050be5b9b2153c50c938d855797d5c19f
h3_real_current_worktree_entry_count: 52
h3_real_current_worktree_sha256: fbfb42256576b212df3a69c2a7dba645eb25dfbd928e8a79335bb5be8546ee78
h3_real_current_assessed_at: not_created
h4_started: false
current_claim_eligibility: false
live_coverage: false
local_runtime_bootstrap: uv venv --python 3.11 .venv

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

## Current Development Entrance

H1 packet ingress and checkout transport are closed. The manifest root and
report entries are exact four-key and six-key objects. Active and closed
`task.next_state` values use one typed contract: `owner`, `user_work`, and
`agent_work` are non-empty strings, while `recommended_slice` is `null` or a
non-empty string. Invalid external packets are rejected as `DashboardError`
before model or HTML projection. Report hashes bind canonical UTF-8 LF bytes;
CRLF checkout transport is normalized before hashing, while invalid UTF-8,
bare carriage returns, and substantive content drift fail closed.

The authorized H2 report has been received and the authentic single-report
round-trip is verified. Its byte-exact source copy, manifest, normalization,
gate classification, source-bound packet, H2 readback, and package-local
Dashboard outputs are under
`artifacts/review/h2-authentic-single-report-round-trip-v1/`. The report is
bound to revision `d38075b97efabc99d1a23e8e0afafd5d44f1e2de` and the SHA-256
declared above.

H2 establishes authentic owner-authorized point-in-time evidence only. H3 has
verified the separate `supervision_report_authority_envelope.v1` contract and
its source-rederived Dashboard intake without promoting that evidence.
Authenticity is true, temporal state is fresh at the fixed H3 assessment,
revision state is unknown, and permission state is `insufficient_h2_only`.
`current_claim_eligibility`, `live_coverage`, and `executable` remain false.
H4 has not started. A real current claim requires a new fresh
report/observation with explicit H3/current authorization.

H3.1 has closed the public current-observation ingress gap. The new
`supervision_current_observation.v1` producer observes one explicit Git root
twice with fixed read-only Git arguments, keeps output outside the target,
sanitizes repository identity, and rederives actual/clean/stable state from
the before/after HEAD and complete porcelain hashes. Authority Envelope V2
requires the exact H3/current scope independently on both report and
observation, strict report/re-observation/assessment chronology, explicit
artifact IDs, and separate package, receipt, and repository/project/revision
provenance. Dashboard accepts V2 only as a complete seven-input set and fully
reprojects it before use.

The producer now applies `core.fsmonitor=false` and optional-lock suppression
to every Git command while preserving the V1 output schema. It rebuilds the
subprocess environment without inherited `GIT_*`, disables terminal and
credential-manager prompts, ignores system and global configuration, and reads
origin identity only from local config without includes. It rejects output
under the observed worktree, per-worktree Git directory, common Git directory,
or any registered linked worktree. Before and after observation it compares
the resolved top-level, Git directories, sanitized single-origin identity, and
linked-worktree registry in addition to the two HEAD/worktree snapshots.
Context mutation therefore fails before receipt creation.

Operational proof uses ephemeral temporary Git repositories and the public
CLIs only. The clean/stable proof reaches point-in-time current eligibility
while retaining live and execution false. The dirty/stable proof emits an
authentic negative observation with `actual: true`, `clean: false`, and
`stable: true`; V2 and Dashboard retain `current_claim_eligibility: false`,
`live_coverage: false`, and `executable: false`. Dirty state alone is not a
producer safety failure, while unstable snapshots or topology/identity drift
still fail closed.

A historical real-project preflight was attempted
against NLMYTGen revision `649ada5050be5b9b2153c50c938d855797d5c19f`.
Its repository context and paired snapshots stayed internally stable, but the
complete porcelain snapshot was dirty with 52 entries and SHA-256
`fbfb42256576b212df3a69c2a7dba645eb25dfbd928e8a79335bb5be8546ee78`.
That attempt stopped under its then-active contract before report intake, receipt or assessment creation,
manifest/packet/envelope generation, or Dashboard reload. No real review
package or current claim was created, and no NLMYTGen writeback or cleanup was
performed. This slice does not retroactively observe NLMYTGen. A later
authorized attempt may record dirty state as negative observation, but a
positive claim still requires clean/stable input and the exact
`allowed_for_DevCockpitCore_H3_current_claim` scope. H4 remains unstarted. Use
`docs/PROJECT_COCKPIT.md` for human navigation, `docs/project-context.md` for
durable boundaries, the Local Validation Entry below for repository checks,
and direct Git and generated-evidence readback for current facts.

## Artifact Access

The current review entrance is the H3 package-local A / Priority Review Console
declared above. It reuses the accepted production information architecture but
does not overwrite or supersede the production artifact at
`samples/dashboard/devcockpitcore_dashboard.html`. The A/B/C direction gate is
closed and A remains the accepted production direction.

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

`QD-PACKET-UNKNOWN-KEY-01` is closed. Exact-key validation rejects missing or
unexpected fields at the packet root, task, and `task.next_state` surfaces
before Dashboard model or HTML projection. Existing nested packet objects stay
exact through strict equality or deterministic reprojection. The v1 schema,
canonical generated artifacts, production UI, and accepted visual state are
unchanged.

H1 packet ingress and checkout transport are closed. The repository-root
`* text=auto eol=lf` rule keeps tracked text LF-stable on new checkouts, and
the loader's canonical binding keeps an existing Windows CRLF checkout valid
without weakening substantive content checks or schema identity.

`QD-PACKET-NARRATIVE-REPROJECTION-01` is closed for paired manifest-plus-source
intake. `load_packet_with_manifest` revalidates source bytes and hash, rebuilds
normalization, classification, task narratives, queues, worksets, coverage,
policy, and scope, then requires full typed JSON equality with the stored
packet. Dashboard uses that path whenever packet and manifest are both given,
and fails before projection on drift. Standalone packet validation remains a
self-consistency check only and must not be promoted to source-authentic,
live/current, or current-claim authority.

When a V1 `--supervision-authority-envelope` is present, Dashboard also requires
packet, manifest, and an explicit timezone-aware
`--supervision-authority-assessed-at`. It validates the source-bound packet,
strictly loads the Envelope, and rebuilds every binding and authority field
from the H2 sources plus the trusted assessment input before model projection.
Envelope-only or partial combinations fail as `DashboardError`. Packet-only,
packet-plus-manifest, and no-packet paths retain their prior behavior.

For V2, Dashboard additionally requires `--supervision-current-observation`,
`--supervision-authority-artifact-id`, and
`--supervision-current-observation-artifact-id`. Supplying any V2-specific
value without the complete packet/manifest/envelope/assessment/receipt/artifact
set fails before projection. V1 inputs do not accept or infer V2 identity.

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

The H2 source is authentic owner-authorized point-in-time evidence, but its
permission is explicitly limited to H2. The H3 Envelope therefore records
`permission_scope_h2_only`, absent authorized current re-observation, unknown
current revision, `current_claim_eligibility: false`, and
`live_coverage: false`. The deterministic fixture and production Dashboard
remain unchanged. H3.1 proves only that authorized current-observation ingress
is operational against a controlled temporary repository. H4 is not started;
no real later state may be inferred without a new explicitly authorized report
and observation.

This projection and the other repository documents are navigation and decision
records, not live workflow authority. Verify Git, tests, generated readback, and
the receipt authority boundary directly. A dated handoff may explain why a
decision was made but does not supersede this projection or live evidence.

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
python artifacts/review/h3-report-authority-envelope-v1/generate_package.py
Start-Process .\samples\dashboard\devcockpitcore_dashboard.html
```
