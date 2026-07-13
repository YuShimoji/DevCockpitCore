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
| `evidence_class` | Evidence authority class, such as deterministic fixture. |
| `authority_basis` | Why this exact report is allowed into the packet. |
| `content_sha256` | Required byte-level binding for fail-closed input. |

The loader rejects duplicate JSON keys at any nesting depth, absolute or
escaping report paths, duplicate paths, missing files, invalid UTF-8, hash
drift, duplicate task identity, and malformed packet projection.

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

## Priority Review Console integration

The dashboard accepts an optional explicit input:

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.dashboard `
  --supervision-packet samples/supervision_packets/cross_project_supervision_packet_v1.json
```

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
coverage of user projects and does not complete the later report-routing
round-trip horizon.

Capture manifests keep source paths repository-relative or redacted. Capture
timestamps distinguish `actual_browser_observation` from
`deterministic_declared_override`; inspection timestamps use the separate
`actual_worker_inspection` authority when not overridden. Declared overrides
are never eligible as current observation evidence. A future live mode would require explicit
authority, freshness, revision binding, and current-claim eligibility fields.
Those fields are design prerequisites, not hard-coded live success in this
fixture slice.
