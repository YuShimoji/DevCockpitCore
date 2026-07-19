# Cross-Project Supervision Packet V1

generated_at: 2026-07-19T15:12:24.4917578+09:00
authentic_coverage: 1 projects / 1 reports
authority: owner_authorized_authentic_point_in_time_manifest_binding
global_rank: attention_and_review_priority_only
executable: false

## Global Attention Queue

Global rank expresses review attention, not execution order. Safe work in different projects may continue in parallel.

| Rank | Class | Required | Project | Thread / lane | Current state | Next state | Task ID |
| ---: | --- | :---: | --- | --- | --- | --- | --- |
| 1 | active_safe_continuation | yes | nlmytgen | nlmytgen-h2-authentic-source-export-v1 / SUPERVISION_EVIDENCE_EXPORT | point-in-time-source-report-exported | devcockpitcore-h2-authentic-round-trip-v1 | `task-31aac3069238ee38` |

## Project Worksets

### nlmytgen

- Project-local first task: `task-31aac3069238ee38` — devcockpitcore-h2-authentic-round-trip-v1
- Active task IDs: `task-31aac3069238ee38`
- User/supervisor gate: none
- Safe continuation: task-31aac3069238ee38
- Closed/informational task IDs: none

## Evidence Boundary

Only reports explicitly named in the manifest were read. Every source is SHA-256 bound and the packet fails closed on missing, changed, duplicate-key, duplicate-identity, or projection-drift input.

This packet contains owner-authorized authentic point-in-time report evidence; it is not live/current coverage. It does not discover latest files, infer reports from conversation history, write to sibling repositories, schedule execution, or make any action executable.
