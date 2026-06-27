# Sample Report Normalizations

This directory contains JSON readbacks generated from redacted sample reports.
The JSON files should be reproducible with:

```bash
PYTHONPATH=src python -m dev_cockpit.report_normalizer \
  --input samples/reports/agent_report_adapter_manifest_v1_redacted.txt \
  --output samples/report_normalizations/adapter_manifest_v1_readback.json \
  --pretty
```
