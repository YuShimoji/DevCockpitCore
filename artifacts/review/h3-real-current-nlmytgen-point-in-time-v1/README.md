# H3-G02 Real NLMYTGen Point-In-Time Outcome Artifact

This package binds one owner-authorized source report and one separate
environment-isolated `supervision_current_observation.v1` receipt for the
same NLMYTGen repository identity and revision. The observed source checkout
was stable but dirty, so the package is valid negative point-in-time evidence:
`actual: true`, `clean: false`, `stable: true`,
`current_claim_eligibility: false`, `live_coverage: false`, and
`executable: false` with reason `worktree_not_clean`.

The package contains no NLMYTGen writeback, dirty path names, local absolute
paths, credentials, secrets, or private identifiers. Reprojection uses only
the captured report, receipt, manifest, packet, fixed assessment timestamp,
and derived package files; it never re-observes NLMYTGen.

## Inputs and outputs

- `source/AGENT_REPORT_G02_NLMYTGEN_V1.md`: fresh source report.
- `receipt/current_observation_v1.json`: one fixed Git observation receipt.
- `manifest/task_report_manifest_v1.json`: strict report binding.
- `packet/cross_project_supervision_packet_v1.json` and `.md`: source-bound
  Packet V1 and readback.
- `authority/supervision_report_authority_envelope_v2.json`: strict four-source
  Authority Envelope V2.
- `dashboard/`: package-local Dashboard, review actions, and priority readback.
- `binding_inventory_v1.json` and `package_readback_v1.json`: package identity,
  hashes, chronology, state, and safety-boundary evidence.

Run the package generator without arguments to verify committed bytes. Use
`--output-dir` only for temporary/staging output; the tracked package path is
rejected as an output destination.
