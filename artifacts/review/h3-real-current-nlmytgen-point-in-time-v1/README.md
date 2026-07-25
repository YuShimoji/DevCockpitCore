# H3-G02 Real NLMYTGen Point-In-Time Outcome Artifact

This package binds one owner-authorized source report and one separate
environment-isolated `supervision_current_observation.v1` receipt for the
same NLMYTGen repository identity and revision. The observed source checkout
was stable but dirty, so the package is valid negative point-in-time evidence:
`actual: true`, `clean: false`, `stable: true`,
`current_claim_eligibility: false`, `live_coverage: false`, and
`executable: false` with reason `worktree_not_clean`.

The package contains no NLMYTGen writeback, dirty path names, local absolute
paths, credentials, secrets, or private identifiers. Reprojection uses the
three fixed captured inputs, explicit immutable producer dependencies, and
the fixed timestamp from the manifest. Committed derived files are comparison
oracles only; they are not producer inputs, and reconstruction never
re-observes NLMYTGen.

## Inputs and outputs

- source/AGENT_REPORT_G02_NLMYTGEN_V1.md: fresh source report.
- receipt/current_observation_v1.json: one fixed Git observation receipt.
- manifest/task_report_manifest_v1.json: strict report binding.
- README.md, generate_package.py, the safety-boundary package, and the
  explicitly listed src/, samples/, adapters/, and docs/ files are immutable
  producer dependencies.
- normalization/, packet/, authority/, and dashboard/ are regenerated derived
  outputs. binding_inventory_v2.json and package_readback_v2.json describe
  their exact path set and bindings.

The generator reconstructs normalization, Packet V1, Authority V2, Dashboard,
review actions, priority readback, binding inventory, and package readback in
two independent temporary staging roots. It requires the generated mapping
to equal the declared derived-output path set, rejects repository-contained
destinations, and reports deterministic drift when a fixed input is mutated.

Run the package generator without arguments to verify committed bytes. Use
`--output-dir` only for temporary/staging output; the tracked package path is
rejected as an output destination.
