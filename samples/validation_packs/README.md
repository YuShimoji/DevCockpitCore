# Validation Pack Samples

This directory contains the default DevCockpitCore validation pack and a sample
`validation_pack_result.v1` output generated from it.

Regenerate the result from a checkout with `src` on `PYTHONPATH`:

```bash
PYTHONPATH=src python -m dev_cockpit.validation_pack \
  --pack samples/validation_packs/devcockpitcore_validation_pack.json \
  --output samples/validation_packs/devcockpitcore_validation_pack_result.json \
  --pretty
```

The pack is fixed and repo-local. It does not run commands from adapter
`default_validation`, user input, report text, or arbitrary config fields.
