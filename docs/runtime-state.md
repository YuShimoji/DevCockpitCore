# DevCockpitCore Runtime State

updated_at: 2026-07-10
status_authority: docs/PROJECT_COCKPIT.md
active_artifact: dashboard-layout-research-and-prototype-v1
artifact_current: dashboard-layout-research-and-prototype-v1
artifact_next: dashboard-direction-intent-checkpoint-v1
next: compare two or three low-fidelity dashboard directions before any production generator rewrite
user_work: select the preferred information architecture and visual direction after the intent checkpoint
render_gate: intent_checkpoint_required
handoff: none
active_layout_research: docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md
active_layout_prototype: samples/dashboard/layout_research/devcockpitcore_layout_prototype.html
last_verified_base: dc6b5bb
resume_branch: codex/workflow-handoff
handoff: docs/handoffs/2026-07-10-workflow-handoff.md
blocking_issue_count: 0
external_status: https://github.com/YuShimoji/DevCockpitCore/blob/codex/workflow-handoff/docs/PROJECT_COCKPIT.md
external_publish_state: draft_pr_before_main_merge
pull_request: https://github.com/YuShimoji/DevCockpitCore/pull/1
wiki_sync: not_configured

## Current State

DevCockpitCore is locally developable and has no blocking validation failure.
Observer and foundation-automation capabilities are available. Execution
automation remains intentionally narrow:

- C3 command keys are exactly `status_snapshot_help` and
  `adapters_validate_help`.
- C4 command keys are exactly `validation_pack_default_pretty`.
- C4 maps only to
  `python -m dev_cockpit.validation_pack --default --pretty`.

The current product checkpoint is layout exploration. The report-first
production dashboard remains audit evidence, and the separate Priority Review
Console is one low-fidelity direction. It is not accepted production direction
until the user compares the intended alternatives.

The project-local development model is mission-sized execution. Safe,
reversible work continues through implementation, related fixes, tests, and
state synchronization. Authority expansion and expensive subjective direction
are the only explicit stop gates.

## Capability Boundary

There is no general execution loop, arbitrary command runner, scheduler,
external notification integration, auto-render workflow, web server, database,
credential handling, target-repository writeback, C5, or C6.

Missing upstreams, sibling repositories, and optional project documents remain
structured warnings rather than hard stops.

## Restart Surface

Read only what the active work requires:

1. `AGENTS.md`
2. `docs/PROJECT_COCKPIT.md`
3. `docs/runtime-state.md`
4. `docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md`
5. `samples/dashboard/layout_research/devcockpitcore_layout_prototype.html`

Dated handoffs are historical unless the cockpit names one for a real transfer.

## Last Live Verification

Verified on 2026-07-10 against base `dc6b5bb`:

- source and test compilation: pass.
- unit tests: 309 passed, including the current-state contract guard.
- adapter validation: 4 of 4 passed.
- live status snapshot: expected clean at the committed workflow checkpoint;
  verify branch parity after fetching.
- validation pack: 15 pass, 1 known fixture warning, 0 fail.
- C3 probe: 11 of 11 passed.
- C4 probe: 18 of 18 completed with exit 0.
- cross-project smoke: DevCockpitCore pass and three optional sibling warnings.
- git whitespace checks: pass.

## Evidence Freshness Warning

Tracked JSON and dashboard artifacts are checkpoint samples, not live status.
The current sample set predates `dc6b5bb`; consult
`docs/PROJECT_COCKPIT.md` and run live commands before using those samples for
a current decision. A future freshness guard should make this warning
deterministic.
