# Dashboard Layout Research Prototype Handoff

This handoff keeps the current DevCockpitCore layout-research context inside
the repository so another terminal can resume without relying on chat history.

## Current Repository State

- Branch: `main`
- Remote: `origin` at `https://github.com/YuShimoji/DevCockpitCore.git`
- Layout checkpoint commit: `22e926a docs: add dashboard layout research prototype`
- Layout checkpoint push: completed to `origin/main`
- Post-checkpoint parity: `HEAD...origin/main = 0 0`
- Post-checkpoint worktree: clean
- Active artifact: `dashboard-layout-research-and-prototype-v1`
- Current production dashboard: unchanged and still generated at
  `samples/dashboard/devcockpitcore_dashboard.html`
- Current generator: unchanged at `src/dev_cockpit/dashboard.py`

## Why This Handoff Exists

The user asked to preserve all working context in the project and push local
state so another terminal can resume immediately.

The latest completed work responded to user feedback that the report-first
dashboard was still structurally card-based, text-heavy, scroll-heavy, and
unclear about the next operator action. The work stopped production card
polishing and produced a research-backed layout recommendation plus a separate
low-fidelity static prototype.

## Active Files To Read

Read these first:

1. `AGENTS.md`
2. `docs/runtime-state.md`
3. `docs/project-context.md`
4. `docs/handoffs/2026-07-07-dashboard-layout-research-prototype-v1.md`
5. `docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md`
6. `samples/dashboard/layout_research/devcockpitcore_layout_prototype.html`
7. `docs/PROJECT_COCKPIT.md`
8. `docs/PROJECT_PIPELINE.mmd`
9. `samples/dashboard/README.md`

Then use the prior dashboard and action package as evidence, not as the next
production design target:

10. `samples/dashboard/devcockpitcore_dashboard.html`
11. `samples/dashboard/devcockpitcore_review_actions.json`
12. `samples/dashboard/devcockpitcore_review_actions.md`
13. `docs/handoffs/2026-07-07-dashboard-report-first-frontpage-v1.md`
14. `docs/handoffs/2026-07-07-remote-sync-resume-handoff-v1.md`

## Access Routes

Open the prototype from the repository root:

```powershell
Start-Process .\samples\dashboard\layout_research\devcockpitcore_layout_prototype.html
```

Open the current production dashboard only as audit evidence:

```powershell
Start-Process .\samples\dashboard\devcockpitcore_dashboard.html
```

## Decision Memory

The selected recommendation is exactly one layout model:

```text
Priority Review Console
```

It is a queue-led split workspace:

- current-state report.
- ordered priority lane.
- active review workspace.
- adjacent evidence inspector.
- ordered project/status list.
- appendix-style raw validation, smoke, action, and source evidence.

The rejected direction is continued card-grid-first production polishing. The
current dashboard improved the first viewport, but still exposes Review Map,
Review Stack, Linked Detail Map, Warnings, Actions, Projects, and Sources as a
large evidence inventory before it gives a low-context operator one ordered
decision path.

## Validation Memory

Latest validation before the layout checkpoint push:

- `python -m unittest tests.test_dashboard_layout_research`: 5 tests OK.
- `python -m compileall src tests`: pass.
- `PYTHONPATH=src python -m unittest discover`: 305 tests OK.
- `python -m json.tool samples/dashboard/devcockpitcore_review_actions.json`: pass.
- `git diff --check`: pass.
- `git diff --cached --check`: pass.
- Residue/path scan on research/prototype/docs/test files: no prompt
  delimiters, raw host paths, shell-true spelling, or true executable flag
  findings.
- Playwright set-content smoke for current dashboard: `report-first-frontpage`,
  6 Review Map items, 8 project cards, 20 review action cards, 12 disclosure
  sections.
- Playwright set-content smoke for prototype: `priority-review-console`, 5
  priority rows, 4 project/status rows, 4 appendix disclosures, 0 scripts, no
  `card-grid` marker.
- Prototype text overflow check: 0 sampled text/code overflow findings at
  1440px after source-path wrapping fix.

## Capability Boundary

This handoff does not authorize or implement:

- production dashboard rewrite.
- arbitrary runner or general execution loop.
- scheduler, watcher, background daemon, or web server.
- external service integration, credentials, webhooks, telemetry, or database.
- target repository writeback.
- new controlled command keys, C5, or C6 expansion.
- public action surface beyond normal repository push.
- full i18n or formal accessibility compliance claims.

The accepted execution boundary remains:

- C3 command keys are exactly `status_snapshot_help` and
  `adapters_validate_help`.
- C4 command keys are exactly `validation_pack_default_pretty`.
- Dashboard and review action artifacts are static, local, and review-only.

## Resume Commands

From a fresh terminal on this host:

```powershell
cd "C:\Users\PLANNER007\DevCockpitCore"
git status --short --branch
git fetch --prune origin
git pull --ff-only origin main
git rev-list --left-right --count "HEAD...@{u}"
```

Use a real Python 3.11+ interpreter or the bundled runtime with
`PYTHONPATH=src`. Avoid the WindowsApps `python.exe` stub.

## Recommended Next Entrances

| Entrance | Purpose | What it unlocks |
| --- | --- | --- |
| Accept layout | Decide whether Priority Review Console should drive production implementation. | Allows a scoped generator redesign slice. |
| Model queue | Decide how review actions, warning triage, and smoke rows become an ordered priority lane. | Makes the future dashboard deterministic rather than hand-authored. |
| Excise card surfaces | Plan how to demote project cards, action cards, and raw detail maps into appendix evidence. | Reduces scroll burden and card proliferation. |
| Verify responsive behavior | Review the prototype on narrow viewports before production implementation. | Reduces layout risk for the generator rewrite. |

## Not The Next Move

Do not start with another copy pass on the current report-first dashboard. Do
not add new cards, new warning panels, or more top-level notes as the fix. The
next useful decision is whether the selected layout model is accepted for a
future production redesign.
