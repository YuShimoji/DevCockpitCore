# Controlled Runner Probe Samples

This directory contains the first guarded C3 probe config and a generated
`controlled_runner_probe_result.v1` sample.

Regenerate the result from a checkout with `src` on `PYTHONPATH`:

```bash
PYTHONPATH=src python -m dev_cockpit.controlled_runner_probe \
  --probe samples/controlled_runner_probes/controlled_runner_probe_v1.json \
  --output samples/controlled_runner_probes/controlled_runner_probe_result_v1.json \
  --pretty
```

The sample selects exactly one hardcoded command key: `status_snapshot_help`.
The config cannot provide argv, shell flags, executable paths, or arbitrary
command strings.
