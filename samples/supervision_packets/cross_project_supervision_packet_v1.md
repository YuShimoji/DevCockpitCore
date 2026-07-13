# Cross-Project Supervision Packet V1

generated_at: 2026-07-13T06:30:00Z
fixture_coverage: 2 projects / 4 reports
authority: deterministic_non_live_manifest_bound_fixture
global_rank: attention_and_review_priority_only
executable: false

## Global Attention Queue

Global rank expresses review attention, not execution order. Safe work in different projects may continue in parallel.

| Rank | Class | Required | Project | Thread / lane | Current state | Next state | Task ID |
| ---: | --- | :---: | --- | --- | --- | --- | --- |
| 1 | true_stop_or_required_failure | yes | alpha-project | alpha-release-thread / RELEASE VALIDATION | required validation failed | alpha-release-validation-repair-v1 | `task-de0aa9c2efa92270` |
| 2 | user_authorization_or_material_decision | no | beta-project | beta-product-thread / PRODUCT REVIEW | two viable information architectures remain | beta-layout-selection-v1 | `task-b12276783e599eb2` |
| 3 | active_safe_continuation | yes | alpha-project | alpha-observer-thread / OBSERVER DOCUMENTATION | read-only observation notes are being reconciled | alpha-observer-notes-v2 | `task-72cd8ffa26a76611` |

## Project Worksets

### alpha-project

- Project-local first task: `task-de0aa9c2efa92270` — alpha-release-validation-repair-v1
- Active task IDs: `task-de0aa9c2efa92270`, `task-72cd8ffa26a76611`
- User/supervisor gate: task-de0aa9c2efa92270
- Safe continuation: task-72cd8ffa26a76611
- Closed/informational task IDs: none

### beta-project

- Project-local first task: `task-b12276783e599eb2` — beta-layout-selection-v1
- Active task IDs: `task-b12276783e599eb2`
- User/supervisor gate: task-b12276783e599eb2
- Safe continuation: none
- Closed/informational task IDs: `task-f1a6406e7974148a`

## Evidence Boundary

Only reports explicitly named in the manifest were read. Every source is SHA-256 bound and the packet fails closed on missing, changed, duplicate-key, duplicate-identity, or projection-drift input.

This tracked packet is deterministic non-live fixture evidence. It does not discover latest files, infer reports from conversation history, write to sibling repositories, schedule execution, or make any action executable.
