# Cross-Project Smoke Samples

This directory contains the default DevCockpitCore cross-project smoke config
and a generated `cross_project_smoke_result.v1` sample.

Regenerate the result from a checkout with `src` on `PYTHONPATH`:

```bash
PYTHONPATH=src python -m dev_cockpit.cross_project_smoke \
  --smoke samples/cross_project_smokes/devcockpitcore_cross_project_smoke.json \
  --output samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json \
  --pretty
```

The smoke is read-only for target repositories. It does not run adapter
`default_validation`, tests, builds, renders, commits, pushes, or writes into
sibling project repositories.
