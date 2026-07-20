# H3 Current Observation Ingress V1

This package records the operational closure of current-observation ingress.
It does not contain or claim a real project observation.

The controlled proof creates a temporary Git repository and invokes only the
public CLIs for current observation, source-bound packet generation, Authority
Envelope V2 generation, and Dashboard V2 intake. The strict Dashboard reload
must project `current_claim_eligibility: true` for that synthetic repository
while retaining `live_coverage: false` and `executable: false`.

No synthetic receipt, report, envelope, or Dashboard is tracked as project
state. `current_observation_ingress_machine_readback_v1.json` records the
contract, starting gaps, preserved baseline hashes, proof test identity, and
the boundary that no real current observation was attempted. Run the public
CLI proof through the named unit test; regenerate this deterministic metadata
with:

```powershell
$env:PYTHONPATH = "src"
python artifacts/review/h3-current-observation-ingress-v1/generate_package.py
```

H2 remains complete, the H3 V1 package remains immutable, H3.1 ingress is
operational, H4 is not started, and any real current claim requires a separate
owner-authorized report plus observation using the exact H3/current scope.
