# DevCockpitCore Agent Notes

DevCockpitCore is observer-first. Keep the foundation lanes separate:

- Foundation Observer Readiness: status schema, status producer, adapter config,
  tests, and docs.
- Foundation Automation Readiness: report normalization, gate classification,
  validation packs, and reusable project adapters.
- Execution Automation Readiness: controlled runner design only after observer
  slices are stable.
- Project/Product Readiness: project-specific readiness stays outside this
  repository unless represented through adapters or snapshots.

For the status producer slice, do not add an execution loop, autonomous runner,
scheduler, external notification integration, auto-render workflow, web server,
database, credential handling, or target-repository writeback.

Prefer standard-library Python and local tests. Missing upstreams, missing
sibling repositories, and absent optional project docs should become structured
warnings, not hard stops.
