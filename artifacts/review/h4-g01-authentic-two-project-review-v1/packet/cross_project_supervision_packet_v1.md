# Cross-Project Supervision Packet V1

generated_at: 2026-07-26T07:38:05.567842+00:00
authentic_coverage: 2 projects / 2 reports
authority: owner_authorized_authentic_point_in_time_manifest_binding
global_rank: attention_and_review_priority_only
executable: false

## Global Attention Queue

Global rank expresses review attention, not execution order. Safe work in different projects may continue in parallel.

| Rank | Class | Required | Project | Thread / lane | Current state | Next state | Task ID |
| ---: | --- | :---: | --- | --- | --- | --- | --- |
| 1 | active_safe_continuation | yes | clippipegen | clippipegen-h4-g01-authentic-review-v1 / PROJECT_REVIEW | out13-integrated-baseline-observed-clean | m6-rights-readiness-review | `task-4d33ffccee3d295b` |
| 2 | active_safe_continuation | yes | nlmytgen | nlmytgen-h4-g01-authentic-review-v1 / PROJECT_REVIEW | three-real-topic-evidence-observed-dirty | factory-contract-v2-extraction-review | `task-2fde1abcc8fd553a` |

## Project Worksets

### clippipegen

- Project-local first task: `task-4d33ffccee3d295b` — m6-rights-readiness-review
- Active task IDs: `task-4d33ffccee3d295b`
- User/supervisor gate: none
- Safe continuation: task-4d33ffccee3d295b
- Closed/informational task IDs: none

### nlmytgen

- Project-local first task: `task-2fde1abcc8fd553a` — factory-contract-v2-extraction-review
- Active task IDs: `task-2fde1abcc8fd553a`
- User/supervisor gate: none
- Safe continuation: task-2fde1abcc8fd553a
- Closed/informational task IDs: none

## Evidence Boundary

Only reports explicitly named in the manifest were read. Every source is SHA-256 bound and the packet fails closed on missing, changed, duplicate-key, duplicate-identity, or projection-drift input.

This packet contains owner-authorized authentic point-in-time report evidence; it is not live/current coverage. It does not discover latest files, infer reports from conversation history, write to sibling repositories, schedule execution, or make any action executable.
