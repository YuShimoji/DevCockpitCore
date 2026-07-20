# Cross-Project Supervision Packet V1

## Purpose

Cross-Project Supervision Packet V1 turns explicitly supplied AGENT_REPORT
files into one review-priority queue and project-local worksets. It answers
which project/thread/lane needs attention without treating global rank as a
sequential execution schedule.

This is Foundation Automation Readiness. It normalizes and classifies evidence;
it does not run project work, discover reports, write to sibling repositories,
or generate a successor prompt.

## Input contract

The only accepted input is `task_report_manifest.v1`. Every `reports` entry
contains:

| Field | Meaning |
| --- | --- |
| `project_key` | Stable project identity supplied by the manifest owner. |
| `report_path` | Explicit repository-relative UTF-8 AGENT_REPORT path. |
| `required` | Whether the report participates as required evidence. |
| `evidence_class` | Evidence authority class, such as deterministic fixture or owner-authorized authentic point-in-time report. |
| `authority_basis` | Why this exact report is allowed into the packet. |
| `content_sha256` | Required SHA-256 binding over canonical UTF-8 LF bytes. CRLF checkout transport is normalized to LF before hashing. |

The manifest root is an exact-key object containing only `schema_version`,
`artifact_id`, `generated_at`, and `reports`. Every report entry is an
exact-key object containing only the six fields listed above. Missing and
unexpected keys fail closed with their object path and sorted diagnostics;
JSON object key order is not significant.

The loader rejects duplicate JSON keys at any nesting depth, absolute or
escaping report paths, duplicate paths, missing files, invalid UTF-8,
unsupported bare carriage returns, canonical content hash drift, duplicate
task identity, and malformed packet projection. Git declares the tracked
fixture reports as LF, while the loader also tolerates an existing Windows
CRLF checkout without weakening substantive content binding.

There is deliberately no directory-mtime search, latest-file heuristic,
conversation/clipboard inference, or automatic promotion of a dated handoff to
live authority.

## Existing interpretation pipeline

Each bound report is passed through the existing
`dev_cockpit.report_normalizer.normalize_report`, then through
`dev_cockpit.gate_classifier.classify_gate`. The packet generator does not
duplicate either parser or gate evaluator.

Task identity is:

```text
project_key / thread_id / lane_id / slice_id / artifact_id
```

Canonical v6.5 reports preserve `thread`, `lane`, `slice`, and `artifact` from
the ROUTE header exactly. ACTION is optional. A complete canonical ROUTE treats
the PROGRESS prefix as a progress-stream label rather than a competing lane
claim. Legacy reports remain compatible through `target`, the PROGRESS lane,
`artifact_current`, ACTION `deliverable`, and finally `artifact_next` aliases.
When a canonical identity and an explicit legacy identity alias are both
present, equal values normalize and material conflicts fail closed.

Canonical v7 reports additionally preserve ROUTE `epoch`, `base`, and the
machine-facing `base_revision` alias while retaining the same five-field packet
task identity. STATUS keeps bare `reported` / `blocked` state and the
`acceptance`, `stop`, `branch`, and `worktree` fields alongside existing
health, gates, and stop class. ROUTE base revisions and source-binding revision
metadata are excluded from commit evidence; explicit commit prose and log-like
commit lines remain supported. Canonical v6.5 and legacy dialects are unchanged.

The resolved five-field identity produces a SHA-256-derived `task_id`. The
report hash remains a separate evidence binding so wording changes fail closed
instead of silently merging or renaming work. Japanese headings used by the
current AGENT_REPORT style are normalized into outcome and continuation fields;
unavailable outcome/current/next fields remain explicit unknown diagnostics.

## Global attention policy

| Precedence | Class | Interpretation |
| ---: | --- | --- |
| 1 | `true_stop_or_required_failure` | True stop or failed required acceptance/validation. |
| 2 | `user_authorization_or_material_decision` | User action, authorization, or a material decision gate. |
| 3 | `awaiting_supervisor_acceptance` | Completed work waiting for supervisor acceptance/integration. |
| 4 | `active_safe_continuation` | Work that can continue safely in its own project. |
| 5 | `unknown_requiring_review` | Insufficiently classified work requiring review. |
| 6 | `closed_or_informational` | Closed evidence; excluded from the active queue. |

Within one class, required reports sort first, then `project_key`, `thread_id`,
`lane_id`, `slice_id`, and source report path. Rank is assigned once in the
global queue. It means attention/review priority only; it does not serialize
work, and project worksets never recalculate it.

## Packet contract

`cross_project_supervision_packet.v1` contains:

- `schema_version`, `artifact_id`, `generated_at`, and `producer`;
- exact `source_bindings` and aggregate `coverage`;
- the ordered `global_attention_queue`;
- `project_worksets` that reference the same task IDs;
- separate `closed_or_informational` tasks;
- `attention_policy` and a non-executable `scope_boundary`.

Each task carries project/thread/lane/slice/artifact identity, stable task ID,
global rank, classification, required state, outcome/current/next state,
report path/hash, evidence references, and `executable: false`.

Every declared object within the v1 packet is an exact-key surface. The packet
root accepts exactly its 11 declared fields, each task accepts exactly its 21
declared fields, and `task.next_state` accepts exactly `owner`,
`recommended_slice`, `user_work`, and `agent_work`. Missing and unexpected keys
fail closed before type, value, identity, binding, rank, queue, workset,
coverage, policy, or scope validation. Source bindings, coverage, attention
policy entries, evidence references, project worksets, rank references, and the
scope boundary remain exact through strict equality or deterministic
reprojection. JSON object key order is not significant, and valid values such
as `recommended_slice: null` remain accepted.

After the packet-wide exact-key prepass, every active and closed task applies
the same typed `next_state` contract before semantic classification:
`owner`, `user_work`, and `agent_work` are non-empty strings, while
`recommended_slice` is either `null` or a non-empty string. Empty or
whitespace-only strings, booleans, numbers, arrays, and objects fail closed.
The Dashboard converts that packet-ingress failure to `DashboardError` before
model or HTML projection.

`cross_project_supervision_packet.v1` has no open field set or extension
namespace. A future field or extension mechanism requires a new schema version
rather than silently widening v1.

Loaded-packet validation does not trust internal projections. It recomputes
task IDs from the five-field identity, class precedence, queue order, source
binding bijection, active/closed membership, project worksets, project-local
first tasks, global rank references, gate/safe references, coverage totals,
attention policy, and the complete observer-only scope boundary. Any missing,
unexpected, duplicate, cross-project, reordered, or type-changed projection
fails closed with `SupervisionPacketError`.

Coverage wording is rederived from task `evidence_class` during validation.
The canonical fixture retains its exact deterministic fixture statement and
bytes. An all-authentic H2 packet instead states that it is owner-authorized
authentic point-in-time coverage from explicit manifest binding and explicitly
denies live/current coverage. Every packet keeps `live_coverage: false`, every
task keeps `executable: false`, and global rank remains attention/review order.

## Priority Review Console integration

The dashboard accepts an optional explicit input:

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.dashboard `
  --supervision-packet artifacts/review/h2-authentic-single-report-round-trip-v1/cross_project_supervision_packet_v1.json `
  --supervision-manifest artifacts/review/h2-authentic-single-report-round-trip-v1/task_report_manifest_v1.json
```

With packet and manifest together, Dashboard must use
`load_packet_with_manifest`: the manifest is strictly loaded, every report is
re-read and hash-checked, normalization and classification are rerun at the
manifest timestamp, and the rebuilt packet must equal the strictly loaded
stored packet in JSON type and value at every path. Packet-only input retains
the existing standalone self-consistency path; no packet retains the existing
default Dashboard path; manifest-only input is an error. Any paired-source
drift fails before model, HTML, priority readback, or review-action projection.

When supplied, packet tasks occupy the existing Priority Lane. Rows expose
project/thread/lane identity; Active Decision exposes project/thread and
lane/slice; Evidence Inspector exposes source report, hash, and attention
classification. Project worksets are a secondary disclosure using the same
task IDs and original global ranks.

The header reports local observer substrate health separately from packet
attention counts. A local `Continue` therefore cannot be mistaken for a packet
stop decision. When a valid packet has zero active tasks, Priority Lane renders
an all-clear informational state while the closed workset and its Evidence
Inspector remain available; closed tasks are not promoted into the active
queue.

When omitted, the existing evidence-derived single-project dashboard path is
unchanged. The integration does not add a project tab, matrix, B/C primary
layout, server, runner, scheduler, or executable action.

## Tracked evidence boundary

The sample manifest contains four deterministic non-live reports across two
fictional projects and multiple threads/lanes. It proves contract behavior,
ranking, closed-item separation, and projection identity. It is not live
coverage of user projects and does not complete the H2 authentic report-routing
round-trip horizon.

The separate H2 package at
`artifacts/review/h2-authentic-single-report-round-trip-v1/` binds one exact
NLMYTGen report at revision
`d38075b97efabc99d1a23e8e0afafd5d44f1e2de` and SHA-256
`d93f15b3f3441aee6d741adbfd54b285e1850e645998f34fb5384a223d82a65b`.
It verifies canonical v7 normalization, local destructive-action negation,
`integrate_and_continue / INTEGRATE_AND_CONTINUE`, task
`task-31aac3069238ee38`, full source-bound narrative reprojection, and
package-local Dashboard projection. It is authentic owner-authorized
point-in-time evidence, not live/current coverage.

`content_sha256` binds canonical UTF-8 LF bytes. The loader decodes strict
UTF-8, normalizes CRLF to LF, rejects any remaining bare carriage return, and
then compares the canonical bytes to the explicit manifest hash. The
repository-root `.gitattributes` contract, `* text=auto eol=lf`, keeps tracked
text blobs and working-tree text at LF across operating systems while leaving
files detected as binary unconverted. This transport rule and loader behavior
keep deterministic reports usable on Windows without changing substantive
content or weakening the manifest contract.

Standalone packet validation guarantees self-consistency of schema, types,
identity, classification, queue, worksets, binding references, coverage,
policy, and scope. `source_report_sha256` is a reference to source evidence,
not a signature. Narrative fields such as `outcome_summary`, `current_state`,
and the textual contents of `next_state` can be reprojected from source only
during generation or intake, when the manifest and source report are available
and verified together. A standalone stored packet must therefore not be
promoted by itself to live or current authority.

`QD-PACKET-NARRATIVE-REPROJECTION-01` is closed for intake that pairs the
manifest, source reports, and stored packet through `load_packet_with_manifest`.
That path rejects source byte/hash drift and validly typed changes to
`outcome_summary`, `current_state`, or any `next_state` narrative field by full
reprojection equality. The standalone stored-packet authority boundary remains:
`load_packet` cannot independently re-prove narrative provenance or establish
source authenticity, live/current authority, freshness, revision eligibility,
or current-claim eligibility.

Capture manifests keep source paths repository-relative or redacted. Capture
timestamps distinguish `actual_browser_observation` from
`deterministic_declared_override`; inspection timestamps use the separate
`actual_worker_inspection` authority when not overridden. Declared overrides
are never eligible as current observation evidence.

## Report Authority Envelope V1

H3 adds `supervision_report_authority_envelope.v1` as a sidecar. Packet V1 and
Manifest V1 remain byte- and schema-compatible; authority fields are not added
to either contract. The Envelope has exact root and nested key surfaces and
rejects missing, unknown, duplicate, and wrongly typed values with object-path
diagnostics.

The production loader does not trust serialized hashes, identity, timestamps,
revision, permission, booleans, scope, or reason codes. It simultaneously
loads the Envelope, manifest, source report, and source-bound packet, then
rebuilds the complete Envelope from those sources and an explicit trusted
`assessed_at`. Full JSON type-and-value equality is required before Dashboard
projection.

Authority evaluation reuses `evaluate_temporal` and `evaluate_revision` from
Evidence Freshness V1. It separates transport/provenance authenticity,
point-in-time current-claim eligibility, and continuous live coverage. Current
eligibility is an AND of source bindings, report identity, explicit H3/current
permission, timezone-aware ordered freshness, full exact revision match,
actual clean stable re-observation, observer-only non-executable scope, and
verified provenance. A single point-in-time report can never set live coverage
in this contract.

For the real H2 package, authenticity and transport/source binding are valid,
but the source permission is H2-only, authorized current re-observation is
absent, and current revision is unobserved. The deterministic result is
`current_claim_eligibility: false`, `live_coverage: false`, and
`executable: false`, including reason code `permission_scope_h2_only`. The only
positive eligibility proof is an isolated pure-predicate test; it is not
tracked current or live evidence. H3 is verified and H4 is not started.

Dashboard Authority Envelope intake requires packet, manifest, and an explicit
assessment time. It performs source-bound packet verification and complete
Envelope reprojection before exposing authenticity, freshness, revision,
permission, current eligibility, or live coverage. Invalid partial inputs and
binding drift fail before model, HTML, readback, or review-action projection.
Legacy packet-only, packet-plus-manifest, and no-packet routes remain intact.

## Current Observation Ingress And Authority Envelope V2

H3.1 adds `supervision_current_observation.v1` and
`supervision_report_authority_envelope.v2` without modifying Packet V1,
Manifest V1, the H2 package, or the H3 V1 package. The observation receipt is
an exact-key sidecar with explicit project, repository, artifact, and
authorization identity. Its repository identity is a credential-free
canonical remote identity; no local absolute target path is serialized.

The producer accepts one explicit Git top-level directory and an output path
outside that directory. Its Git command surface is fixed to repository-root
verification, remote identity readback, full HEAD readback, and porcelain
worktree readback. It does not fetch, checkout, stage, commit, push, execute
caller-supplied commands, or write to the observed repository. Before and
after snapshots contain the full HEAD plus the hash and entry count of the
complete `git status --porcelain=v1 -z --untracked-files=all` payload. The
loader validates exact keys and types and rederives `actual`, `clean`, and
`stable` from those snapshots.

Envelope V2 binds source report, manifest, packet, and observation receipt.
The envelope artifact ID and expected observation artifact ID are explicit
loader inputs; neither is inferred from the H3 V1 deterministic package.
Authority separates:

- report permission state;
- observation authorization state;
- their exact-scope conjunction;
- report and re-observation temporal state;
- report/re-observation/assessment chronology;
- revision binding;
- package binding provenance;
- observation receipt provenance;
- repository/project/revision cross-binding provenance; and
- overall current-claim provenance.

Both authorization values must equal
`allowed_for_DevCockpitCore_H3_current_claim`. Missing values, the H2-only
scope, insufficient values, and mismatches have distinct states and reason
codes. Chronology requires
`report_observed_at <= reobserved_at <= assessed_at`; malformed,
timezone-missing, future, stale, pre-report, and post-assessment cases remain
distinguishable. Point-in-time eligibility is possible only when every
predicate is satisfied. V2 always retains `live_coverage: false` and the
observer-only non-executable scope.

Dashboard selects V2 only when packet, manifest, envelope, assessment time,
current observation, expected envelope artifact ID, and expected observation
artifact ID are all present. It strictly reloads the receipt and fully
reprojects the envelope before model, HTML, priority readback, or review-action
projection. Every partial V2 combination fails closed. The pre-existing V1,
packet-plus-manifest, packet-only, and no-packet paths retain their behavior and
deterministic bytes.

The operational proof is intentionally synthetic. A unit test creates an
ephemeral clean Git repository, invokes the observation, packet, envelope, and
Dashboard public CLIs, and requires current eligibility true together with
live coverage false and executable false. No synthetic report, receipt,
envelope, or Dashboard is retained as real project evidence. The tracked H3.1
readback records only the reproducible proof contract and preservation hashes.
H4 remains unstarted; a real current claim requires a separately authorized
report and observation.
