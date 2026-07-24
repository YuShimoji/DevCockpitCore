# Cross-Project Supervision Packet V1

generated_at: 2026-07-25T03:05:47.2597223+09:00
authentic_coverage: 1 projects / 1 reports
authority: owner_authorized_authentic_point_in_time_manifest_binding
global_rank: attention_and_review_priority_only
executable: false

## Global Attention Queue

Global rank expresses review attention, not execution order. Safe work in different projects may continue in parallel.

| Rank | Class | Required | Project | Thread / lane | Current state | Next state | Task ID |
| ---: | --- | :---: | --- | --- | --- | --- | --- |
| 1 | true_stop_or_required_failure | yes | nlmytgen | nlmytgen-h3-g02-real-current-observation-v1 / SUPERVISION_EVIDENCE_EXPORT | point-in-time-source-report-exported | devcockpitcore-h3-g02-real-current-observation-v1 | `task-d2ec75bacb888e49` |

## Project Worksets

### nlmytgen

- Project-local first task: `task-d2ec75bacb888e49` — devcockpitcore-h3-g02-real-current-observation-v1
- Active task IDs: `task-d2ec75bacb888e49`
- User/supervisor gate: task-d2ec75bacb888e49
- Safe continuation: none
- Closed/informational task IDs: none

## Evidence Boundary

Only reports explicitly named in the manifest were read. Every source is SHA-256 bound and the packet fails closed on missing, changed, duplicate-key, duplicate-identity, or projection-drift input.

This packet contains owner-authorized authentic point-in-time report evidence; it is not live/current coverage. It does not discover latest files, infer reports from conversation history, write to sibling repositories, schedule execution, or make any action executable.
