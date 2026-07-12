# Evidence freshness/provenance samples

`evidence_freshness_receipt_v1.json` and its Markdown projection are a
deterministic, point-in-time example. They are non-live and never authoritative
for the current state of any repository.

Regenerate them from the repository root with a fixed assessment and injected
observations:

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.evidence_freshness `
  --policy samples/evidence_freshness/evidence_freshness_policy_v1.json `
  --repo-root . `
  --observations samples/evidence_freshness/evidence_freshness_example_observations_v1.json `
  --assessed-at 2026-07-12T00:00:00Z `
  --tracked-example `
  --output-json samples/evidence_freshness/evidence_freshness_receipt_v1.json `
  --output-markdown samples/evidence_freshness/evidence_freshness_receipt_v1.md `
  --pretty
```

Omit `--observations` and `--tracked-example` to perform a new read-only local
capture. Remote parity remains based on local tracking references because this
observer never fetches target repositories.
