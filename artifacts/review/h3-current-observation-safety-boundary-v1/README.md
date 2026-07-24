# H3 Current Observation Safety Boundary V1

This versioned Outcome Artifact binds the observer changes that isolate every
read-only Git subprocess from inherited `GIT_*`, global Git configuration, and
system Git configuration. It also records the public-CLI contract for a stable
dirty repository: the receipt is authentic point-in-time negative observation
with `actual: true`, `clean: false`, and `stable: true`; current-claim
eligibility, live coverage, and execution remain false.

The artifact contains no real NLMYTGen observation. The earlier H3.1 package is
historical evidence and remains byte-identical. This package adds a new binding
inventory and machine readback without changing
`supervision_current_observation.v1`, Authority Envelope V2, Packet V1, or the
accepted production Dashboard.

Verify the committed deterministic metadata from the repository root without
writing the tracked package:

```powershell
$env:PYTHONPATH = "src"
python artifacts/review/h3-current-observation-safety-boundary-v1/generate_package.py
```

To write only to a temporary/staging directory, pass `--output-dir`. The
tracked package path is rejected as an output destination. The binding
`source_tree_sha256` covers only the selected `BOUND_PATHS`; it is not a
repository-wide tree hash. Focused test names are evidence locators, not
execution receipts, and declarative state booleans are package claims rather
than observed execution results.

The generator fails before writing if the H2, H3, H3.1, canonical packet, or
production review baselines differ from their accepted raw-byte hashes.
