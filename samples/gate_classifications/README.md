# Sample Gate Classifications

This directory contains JSON gate classifications generated from report
normalization samples. They are readback artifacts only; they do not execute
commands or generate supervisor prompts.

Regenerate the adapter manifest sample with:

```bash
PYTHONPATH=src python -m dev_cockpit.gate_classifier \
  --report-normalization samples/report_normalizations/adapter_manifest_v1_readback.json \
  --status-snapshot samples/status_snapshots/devcockpitcore_status.json \
  --adapter adapters/devcockpitcore.json \
  --output samples/gate_classifications/adapter_manifest_v1_gate.json \
  --pretty
```
