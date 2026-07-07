# DevCockpitCore Project Context

DevCockpitCore is a cross-project development supervision substrate. Its first
purpose is to make project state easier to resume by producing structured,
read-only snapshots of target repositories.

## Readiness Lanes

- Foundation Observer Readiness: status schema, status producer, adapter config,
  tests, and docs.
- Foundation Automation Readiness: report normalizer, gate classifier,
  validation pack, and reusable project adapters.
- Execution Automation Readiness: controlled runner design and evidence gates
  after observer and classifier slices are mature.
- Project/Product Readiness: project-specific readiness stays outside this
  repository unless represented through adapters or snapshots.

## Current Development Axis

The current axis is common-foundation execution-readiness governance. The repo
has moved through read-only observation, report interpretation, validation
packaging, cross-project smoke observation, a bounded C3 help-probe surface,
C4 design-only boundary review, C4 design-state hardening, a decision-only C4
probe authorization packet plus authorization review, a single bounded C4
validation-pack probe implementation, and review acceptance of that minimal
implementation.

The active artifact is `c4-probe-minimal-implementation-review-v1`. It accepts
only the `validation_pack_default_pretty` C4 command key as a single bounded
repo-local validation-pack probe and recommends
`common-foundation-c4-probe-minimal-implementation-hardening-v1` as the next
route. C3 command set remains exactly two, while the current executable
capability includes one accepted minimal C4 repo-local validation-pack probe.
C4 is limited to one repo-local validation-pack probe, now accepted by the
minimal implementation review. C4 is limited to one accepted repo-local
validation-pack probe in the current review state.

The active dashboard checkpoint is
`dashboard-layout-research-and-prototype-v1`. It pauses production dashboard
polishing, audits the current report-first dashboard, compares layout models,
selects Priority Review Console as the recommended architecture, and adds a
separate low-fidelity static prototype for review before any generator rewrite.

The latest repo-level handoff refresh is
`docs/handoffs/2026-07-07-remote-sync-resume-handoff-v1.md`. It is a docs-only
remote-sync resume packet created after `main` was confirmed in parity with
`origin/main` at `c72ec47 docs: refresh report-first dashboard handoff`; it
does not change the active artifact or capability boundary.

The dashboard layout research responds to user-opened visual feedback: the dark
mode and information organization were usable, but the Latest Brief felt forced,
the card-based top layout remained the root problem, warnings lacked an obvious
operator sequence, projects were still presented as parallel, and the GUI
assumed prior context. The production dashboard remains available as audit
evidence, but additional production card polishing is paused pending review of
the selected Priority Review Console model.

## Completed Artifact Stack

- `status-producer-v1`
- `adapter-manifest-v1`
- `report-normalizer-v1`
- `gate-classifier-v1`
- `validation-pack-v1`
- `cross-project-smoke-v1`
- `controlled-runner-design-v1`
- `controlled-runner-probe-v1`
- `controlled-runner-probe-review-v1`
- `c3-probe-hardening-v1`
- `c3-second-command-design-v1`
- `c3-second-command-help-probe-v1`
- `c3-second-command-acceptance-review-v1`
- `c3-second-command-candidate-acceptance-v1`
- `c3-second-command-production-probe-v1`
- `c3-second-command-production-probe-review-v1`
- `c3-second-command-hardening-v1`
- `c3-command-set-freeze-and-c4-design-decision-v1`
- `c4-scoped-runner-design-v1`
- `c4-scoped-runner-design-review-v1`
- `c4-scoped-runner-design-hardening-v1`
- `c4-probe-decision-packet-v1`
- `c4-probe-authorization-review-v1`
- `c4-probe-minimal-implementation-v1`
- `c4-probe-minimal-implementation-review-v1`
- `devcockpit-local-test-dashboard-v0`
- `designer-dashboard-ia-v1`
- `dashboard-review-to-action-package-v1`
- `dashboard-accessibility-pass-v1`
- `dashboard-compact-dark-overview-v1`
- `dashboard-home-linked-meters-v1`
- `dashboard-latest-brief-checkpoint-v1`
- `dashboard-editorial-brief-v1`
- `dashboard-report-first-frontpage-v1`
- `dashboard-layout-research-and-prototype-v1`

## Current Capability Boundary

The implementation remains a standard-library Python package named
`dev_cockpit`.

Primary observer entry point:

```bash
python -m dev_cockpit.status_snapshot --repo <repo> --adapter <adapter.json> --output <status.json>
```

The accepted production C3 command keys are exactly:

```text
status_snapshot_help
adapters_validate_help
```

The C3 command set remains exactly two fixed help/readback probes.
`adapters_validate_help` maps only to:

```text
python -m dev_cockpit.adapters --help
```

It does not execute `adapters --validate`, adapter `default_validation`, target
repository writeback, scheduler/autonomy behavior, credentials, external
services, or arbitrary command execution.

C4 is implemented and review-accepted only as a single bounded probe in
`src/dev_cockpit/c4_scoped_runner_probe.py`. The C4 command set is exactly:

```text
validation_pack_default_pretty
```

That key maps only to:

```text
python -m dev_cockpit.validation_pack --default --pretty
```

It uses hardcoded argv, shell disabled, timeout, output truncation, redaction,
and before/after repository state evidence. A third C3 command, multiple C4
commands, C5, C6, arbitrary execution, adapter validation as controlled command
behavior, and target repository writeback remain unauthorized.

The local dashboard generator is a review surface only. It reads existing local
JSON and markdown evidence and writes a static HTML artifact at
`samples/dashboard/devcockpitcore_dashboard.html`. Its static GUI affordance is
local DOM filtering/search over already-rendered project cards.

The review action package is also local and non-executable. It derives review
actions from validation, smoke, status, and dashboard-review evidence, writes
`samples/dashboard/devcockpitcore_review_actions.json` and
`samples/dashboard/devcockpitcore_review_actions.md`, and marks every action
with `executable: false`.

The report-first frontpage checkpoint keeps the same static/local boundary and
turns the top viewport into a concise current-status report with a compact
Review Map for linked detail navigation. It does not add a reporting engine,
server, network, telemetry, scheduler, writeback, or execution behavior.

The layout research checkpoint keeps the same safety boundary and does not
rewrite the production generator. Its research memo is
`docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md`; its prototype is
`samples/dashboard/layout_research/devcockpitcore_layout_prototype.html`. The
recommended model is a queue-led split workspace: current-state report,
priority lane, active review workspace, evidence inspector, ordered
project/status list, and appendix evidence.

## Current Restart Surface

Start a new terminal or agent from:

1. `AGENTS.md`
2. `docs/runtime-state.md`
3. `docs/project-context.md`
4. `docs/handoffs/2026-07-07-remote-sync-resume-handoff-v1.md`
5. `docs/handoffs/2026-07-07-dashboard-report-first-frontpage-v1.md`
6. `docs/PROJECT_COCKPIT.md`
7. `docs/PROJECT_PIPELINE.mmd`
8. `docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md`
9. `samples/dashboard/layout_research/devcockpitcore_layout_prototype.html`
10. `samples/dashboard/README.md`
11. `samples/dashboard/devcockpitcore_dashboard.html`
12. `samples/dashboard/devcockpitcore_review_actions.json`
13. `samples/dashboard/devcockpitcore_review_actions.md`
14. `docs/handoffs/2026-07-01-c4-probe-minimal-implementation-review-handoff.md`
15. `docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_REVIEW_V1.md`
16. `samples/c4_probe_minimal_implementation_review/c4_probe_minimal_implementation_review_v1.json`
17. `docs/handoffs/2026-06-30-c4-probe-minimal-implementation-handoff.md`
18. `docs/design/C4_PROBE_MINIMAL_IMPLEMENTATION_V1.md`
19. `samples/c4_probe_minimal_implementation/c4_probe_minimal_implementation_v1.json`
20. `samples/c4_probe_minimal_implementation/c4_probe_minimal_result_v1.json`
21. `docs/design/C4_PROBE_AUTHORIZATION_REVIEW_V1.md`
22. `samples/c4_probe_authorization_review/c4_probe_authorization_review_v1.json`
23. `docs/design/C4_PROBE_DECISION_PACKET_V1.md`
24. `samples/c4_probe_decision_packet/c4_probe_decision_packet_v1.json`
25. `docs/design/C4_SCOPED_RUNNER_DESIGN_HARDENING_V1.md`
26. `samples/c4_scoped_runner_design_hardening/c4_scoped_runner_design_hardening_v1.json`
27. `docs/design/C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md`
28. `docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md`
29. `docs/design/C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md`
30. `docs/design/C3_SECOND_COMMAND_HARDENING_V1.md`
31. `docs/decision-log.md`
32. `docs/idea-ledger.md`

Then verify live state with:

```bash
git status --short --branch
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count HEAD...origin/main
```

Use the active Python runtime with `PYTHONPATH=src` for validation.

## Design Bias

DevCockpitCore should keep early execution-readiness slices narrow and
inspectable. Prefer machine-readable artifacts, explicit safety boundaries,
standard-library Python, local tests, and conservative unknowns over premature
automation.

Missing upstreams, missing sibling repositories, absent optional project docs,
and historical report-fixture residue should become structured warnings unless
they affect the current DevCockpitCore capability boundary.
