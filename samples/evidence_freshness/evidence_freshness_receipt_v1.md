# Evidence Freshness / Provenance Receipt

- Schema: `evidence_freshness_receipt.v1`
- Capture ID: `efr-cbae922571043527b800`
- Assessed at: `2026-07-12T00:00:00Z`
- Authority: `point_in_time_non_live` (live: `false`)
- Policy: `devcockpitcore-24-hour-v1`; `age_seconds <= threshold_seconds`
- Remote parity basis: `local_tracking_reference_no_fetch`; fetch performed: `false`

Tracked deterministic example; never authoritative for live state.

## Summary

Sources: fresh `3`, stale `4`, unknown `1`; current-state eligible `0`.

## Projects

| Project | Required | State | HEAD before -> after | Worktree before -> after | Stable | Before hash | After hash | Reasons |
| --- | ---: | --- | --- | --- | ---: | --- | --- | --- |
| clippipegen | false | observed | 111111111111 -> 111111111111 | dirty -> dirty | true | aaaaaaaaaaaa | aaaaaaaaaaaa | none |
| devcockpitcore | true | observed | 2fe1c659046a -> 2fe1c659046a | clean -> clean | true | bbbbbbbbbbbb | bbbbbbbbbbbb | none |
| nlmytgen | false | observed | 222222222222 -> 222222222222 | clean -> clean | true | cccccccccccc | cccccccccccc | none |
| writingpage | false | skipped | unknown -> unknown | unknown -> unknown | unknown | unknown | unknown | optional_project_missing |

## Sources

| Project / source | Kind | Path | Time | Fresh through | Temporal | Revision | Freshness | Eligible | SHA-256 | Reasons |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| clippipegen / clippipegen.live_status_observation | live_project_observation | git-observation:../ClipPipeGen | 2026-07-12T00:00:00Z | 2026-07-13T00:00:00Z | fresh | match | fresh | false | 26cc50320d94b1b1e98df78e9020cbfbe33d1aa66853e6913467b72ac4d297a3 | receipt_not_authoritative_for_live_state, revision_match, timestamp_within_threshold, worktree_not_clean_or_unknown |
| devcockpitcore / cross-project-smoke-sample | tracked_point_in_time_artifact | samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json | 2026-07-06T07:56:16Z | 2026-07-07T07:56:16Z | stale | mismatch | stale | false | 55d248ef4133f87867836bd57b2a60ed2b2b05964a8ae84c4a645b4069df60fb | receipt_not_authoritative_for_live_state, revision_mismatch, timestamp_threshold_exceeded |
| devcockpitcore / devcockpitcore.live_status_observation | live_project_observation | git-observation:. | 2026-07-12T00:00:00Z | 2026-07-13T00:00:00Z | fresh | match | fresh | false | 5914ab9662ecadb36287eb0a6b8c6308e764fc4cf383f9fd5b29c30282d773f0 | receipt_not_authoritative_for_live_state, revision_match, timestamp_within_threshold |
| devcockpitcore / intent-comparison-manifest-v2 | tracked_point_in_time_artifact | samples/dashboard/intent_comparison/intent_comparison_manifest.json | 2026-07-06T07:56:16Z | 2026-07-07T07:56:16Z | stale | mismatch | stale | false | 1c3a8f13aee8dfd48113f8201180f7d3a254f270358367d9e018b12342b189bd | receipt_not_authoritative_for_live_state, revision_mismatch, timestamp_threshold_exceeded |
| devcockpitcore / status-snapshot-sample | tracked_point_in_time_artifact | samples/status_snapshots/devcockpitcore_status.json | 2026-07-06T07:55:33Z | 2026-07-07T07:55:33Z | stale | mismatch | stale | false | 311de6f138c588ee137f72275edd085be2e30f1eb6a41beff525ec95bedb3958 | receipt_not_authoritative_for_live_state, revision_mismatch, timestamp_threshold_exceeded |
| devcockpitcore / validation-pack-sample | tracked_point_in_time_artifact | samples/validation_packs/devcockpitcore_validation_pack_result.json | 2026-07-06T07:55:56Z | 2026-07-07T07:55:56Z | stale | mismatch | stale | false | 91bc955113ecc00c5ddb008eeb447a30efe9eba74be6b2e3babef649cbbcf313 | receipt_not_authoritative_for_live_state, revision_mismatch, timestamp_threshold_exceeded |
| nlmytgen / nlmytgen.live_status_observation | live_project_observation | git-observation:../NLMYTGen | 2026-07-12T00:00:00Z | 2026-07-13T00:00:00Z | fresh | match | fresh | false | ec5099e92f06eb7f5743dc84b3ab5818f4f8fe59c42be8014cb394cc6e5cca4b | receipt_not_authoritative_for_live_state, revision_match, timestamp_within_threshold |
| writingpage / writingpage.live_status_observation | live_project_observation | git-observation:../WritingPage | unknown | unknown | unknown | unknown | unknown | false | unknown | optional_project_missing |

This receipt is a point-in-time observation, not a continuously live control plane. Reassess after the listed `fresh_through` time or after repository state changes.
