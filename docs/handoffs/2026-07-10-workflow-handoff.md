# Workflow Refresh Remote Resume Handoff

updated_at: 2026-07-10
resume_branch: codex/workflow-handoff
base_branch: main
verified_base: dc6b5bb
active_product_checkpoint: dashboard-layout-research-and-prototype-v1
active_workflow_checkpoint: outcome-envelope-and-cockpit-authority-v1
publication: draft PR before main merge

## Why This Handoff Exists

This is a real terminal and agent transfer. It records the workflow refresh,
the current product decision, the validation performed, and the exact
re-entry path so a different terminal can continue without reconstructing chat
history or reading historical micro-handoffs.

## Resume From Another Terminal

From any checkout of this repository:

```powershell
git fetch --prune origin
git switch codex/workflow-handoff
git pull --ff-only origin codex/workflow-handoff
git status --short --branch
git rev-list --left-right --count "HEAD...@{u}"

$env:PYTHONPATH = "src"
python -m unittest discover
python -m dev_cockpit.validation_pack --default --pretty
```

Read only these resources before selecting the next outcome:

1. `AGENTS.md`
2. `docs/PROJECT_COCKPIT.md`
3. `docs/runtime-state.md`
4. this handoff
5. `docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md` and its prototype when the
   work concerns the dashboard

## What Is Now In The Branch

- The agent operating model now treats one Prompt as an outcome envelope:
  investigation, implementation, related fixes, tests, cleanup, and status
  synchronization continue together.
- Routine reversible repo-local work no longer waits for an extra approval.
  Authority Gates cover destructive work, dependencies, contracts,
  credentials, external effects, writeback, and capability expansion.
- Intent Gates move layout, information architecture, visual identity, motion,
  copy tone, and localization choices before production-scale work. They
  require two or three low-fidelity options and a recommendation.
- `docs/PROJECT_COCKPIT.md` is the human-readable current-state authority;
  `docs/runtime-state.md` is its compact projection; project context now
  holds durable architecture rather than duplicated live state.
- README restart instructions are reduced from a long historical reading list
  to the small current-state path above.
- The Idea Ledger now contains concrete dashboard, Japanese-first reading,
  visual/motion, operator-content, freshness, and bootstrap opportunities.
- Tests enforce cockpit/runtime consistency, a visible README entry point,
  durable project context, and a bounded restart list.

## Current Product Decision

Do not revise the production dashboard by adding another card or copy pass.
The existing Priority Review Console prototype is a research recommendation,
not a user-accepted final direction.

Before a production dashboard rewrite, compare it with two low-fidelity
alternatives:

| Direction | What it optimizes | Why it is distinct |
| --- | --- | --- |
| Priority Review Console | Repeat-operator priority and evidence inspection | Queue-led master/detail workspace |
| Narrative Status Brief | Low-context reading and handoff | Report-led reading order with progressive evidence |
| Lane And Project Matrix | Cross-project comparison | Readiness rows with one selected detail drawer |

After the user selects a direction, the same outcome envelope can implement,
validate, and synchronize it without repeated micro-prompts.

## Validation Recorded For This Checkpoint

| Check | Result |
| --- | --- |
| Source and test compilation | Pass |
| Unit tests | 309 passed |
| Adapter validation | 4 of 4 passed |
| Validation Pack | 15 pass, 1 known pseudo-git-tag fixture warning, 0 fail |
| C3 probe | 11 of 11 passed at the verified base |
| C4 probe | 18 of 18 completed with exit 0 at the verified base |
| Cross-project smoke | DevCockpitCore pass; three optional sibling warnings |
| Git diff check | Pass |

The tracked dashboard and JSON evidence are historical checkpoint samples, not
live current state. Use the Cockpit and live commands above before making a
current decision.

## Boundaries That Remain Unchanged

- C3 keys remain exactly `status_snapshot_help` and
  `adapters_validate_help`.
- C4 remains exactly `validation_pack_default_pretty`.
- No general runner, arbitrary execution, scheduler, web server, database,
  credentials, external integration, target-repository writeback, C5, or C6.
- GitHub Wiki is not a second authority. The branch Cockpit is public after
  push; `main` changes only after the draft PR is merged.

## First Useful Entrances

| Entrance | Friction reduced | What it unlocks |
| --- | --- | --- |
| Explore — dashboard intent checkpoint | Late UI correction churn | A selected architecture before generator work |
| Verify — freshness guard | Historical samples mistaken for live state | Warning-only detection of stale evidence |
| Excise — historical context reduction | Re-reading past micro-artifacts | Faster low-context continuation |
| Advance — macro-prompt pilot | Prompt fragmentation | One outcome from implementation through verified closure |
