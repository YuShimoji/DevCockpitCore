# DevCockpitCore Project Context

This document contains durable mission, architecture, product principles, and
capability boundaries. It intentionally excludes current commits, branches,
pull requests, active artifacts, live validation results, and other transient
repository state.

## Mission

DevCockpitCore is a cross-project development supervision substrate. It makes
local development state reviewable from structured evidence before broader
automation is considered.

The first principle is observer-first behavior: inspect repositories, normalize
reports, classify gates, and package validation evidence without turning
missing optional inputs into hard stops or writing back to target projects.

## Readiness Lanes

- **Foundation Observer Readiness:** status schema, status producer, adapter
  configuration, tests, and documentation.
- **Foundation Automation Readiness:** report normalization, gate
  classification, validation packs, cross-project smoke, dashboards, and
  reusable adapters.
- **Execution Automation Readiness:** narrowly controlled command design and
  evidence gates only after observer slices are stable.
- **Project/Product Readiness:** project-specific readiness stays outside this
  repository unless represented through adapters, snapshots, or review
  evidence.

These lanes must not be collapsed into one readiness claim. A healthy observer
surface does not imply general execution authorization, and a project-specific
UI decision does not alter the runner boundary.

## Architecture

The implementation is a standard-library Python package named `dev_cockpit`.
Its durable components are:

| Component | Responsibility |
| --- | --- |
| Adapter manifests | Describe safe, project-local observation expectations. |
| Status snapshot | Read repository, document, artifact, and validation-hint state without modifying the target. |
| Report normalizer | Convert AGENT_REPORT-like text into structured readback. |
| Gate classifier | Separate readiness, residue, validation, user-work, and execution gates. |
| Validation pack | Run a fixed allowlist of DevCockpitCore-local checks. |
| Cross-project smoke | Observe optional sibling repositories and return warnings when unavailable. |
| Static dashboard | Render local checkpoint evidence for human review without a server. |
| Review actions | Derive non-executable, source-backed review items. |
| Controlled probes | Exercise a fixed, hardcoded C3/C4 command-key surface with evidence and safety checks. |

## Durable Capability Boundary

The accepted C3 command surface has exactly two help-only keys:

```text
status_snapshot_help
adapters_validate_help
```

The accepted C4 surface has exactly one repo-local validation-pack key:

```text
validation_pack_default_pretty
```

It maps only to:

```text
python -m dev_cockpit.validation_pack --default --pretty
```

Configuration cannot supply executable paths, argv, shell flags, or arbitrary
command strings. The probes use hardcoded argv, shell-disabled execution,
timeouts, redaction, truncation, and before/after repository-state evidence.

The repository does not authorize a general execution loop, arbitrary runner,
scheduler, watcher, background daemon, external service or notification path,
credentials, database, target-repository writeback, C5, or C6.

## Durable Product Principles

- A supervision surface should answer current state, priority, next decision,
  ignorable work, and evidence route before presenting raw inventories.
- Generated evidence remains source-backed and reviewable.
- Review actions remain non-executable.
- The dashboard remains local, static, and usable without JavaScript for core
  content.
- Raw validation, smoke, action, and source data should be secondary to the
  operator decision path.
- Materially different low-fidelity layouts should be compared before choosing
  a production dashboard architecture.
- Japanese-first display may coexist with English presentation while technical
  IDs, paths, enum values, and hashes retain their exact meaning.
- Evidence displays should expose source, observation time, and freshness.

## Document Responsibilities

| Resource | Durable responsibility |
| --- | --- |
| `AGENTS.md` | Stable technical architecture and capability restrictions. |
| `docs/PROJECT_COCKPIT.md` | Timestamped human-facing repository navigation snapshot. |
| `docs/runtime-state.md` | Bounded machine-facing restart and artifact-access projection. |
| `docs/project-context.md` | Mission, architecture, product principles, and capability boundaries. |
| `docs/decision-log.md` | Durable product and architecture decisions. |
| `docs/idea-ledger.md` | Product hypotheses, alternatives, and parked directions. |
| `docs/design/*.md` | Evidence and acceptance criteria for a specific design. |
| `docs/handoffs/*.md` | Non-normative historical transfer records. |
| `docs/contracts/OUTPUT_FIRST_SUPERVISION_V2_1.md` | Report normalization, classification, and transport interface semantics. |
