# Controlled Runner Probe Review Samples

This directory contains the C3 probe acceptance review config and generated
`controlled_runner_probe_review_result.v1` sample.

The review consumes existing `controlled_runner_probe_result.v1` evidence. It
does not run the probe command, add command keys, or unlock C4-C6.

Regenerate the review result from a checkout with `src` on `PYTHONPATH`:

```bash
PYTHONPATH=src python -m dev_cockpit.controlled_runner_probe_review \
  --review samples/controlled_runner_probe_reviews/controlled_runner_probe_review_v1.json \
  --probe-result samples/controlled_runner_probes/controlled_runner_probe_result_v1_post_commit.json \
  --dirty-sample samples/controlled_runner_probes/controlled_runner_probe_result_v1.json \
  --output samples/controlled_runner_probe_reviews/controlled_runner_probe_review_result_v1.json \
  --pretty
```
