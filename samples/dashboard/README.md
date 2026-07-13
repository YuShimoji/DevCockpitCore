# DevCockpitCore Dashboard Samples

This folder holds generated local static dashboard artifacts. A / Priority
Review Console is the selected production information architecture; the A/B/C
selection is no longer pending. The first desktop viewport contains a concise
current-state strip, one ordered Priority Lane, the selected item's Active
Decision workspace, and an adjacent Evidence Inspector. Raw tables, project
lists, and historical evidence are subordinate appendix material.

The production generator writes:

- `samples/dashboard/devcockpitcore_dashboard.html`
- `samples/dashboard/devcockpitcore_priority_readback.json`
- `samples/dashboard/devcockpitcore_review_actions.json`
- `samples/dashboard/devcockpitcore_review_actions.md`

The priority readback records the deterministic evidence-derived order and the
Evidence Freshness V1 receipt used by the dashboard. Review Actions remain
non-executable and carry `executable: false`. Equal-precedence items place
required before optional, then sort by project, condition, and primary evidence
path; duplicate project-and-condition identities collapse into one priority.

An explicit `--supervision-packet` input projects manifest-bound report tasks
into the same Priority Lane. Each row shows project identity; Active Decision
adds thread/lane/slice identity; Evidence Inspector keeps the source report,
hash, and attention class synchronized. Project worksets are a secondary
disclosure using the same task IDs and global ranks. Without this option, the
existing evidence-derived dashboard route remains unchanged.

## Production capture package

The tracked production review package is under
`samples/dashboard/production_capture/`:

- `capture_priority_review_console.mjs`
- `production_capture_manifest.json`
- `production_capture_readback.json`
- `screenshots/priority-review-console-ja-desktop.png`
- `screenshots/priority-review-console-en-desktop.png`
- `screenshots/priority-review-console-ja-narrow.png`
- `screenshots/priority-review-console-contact-sheet.png`

The manifest and readback bind language, viewport, selected priority,
freshness/provenance landmarks, overflow checks, and final PNG hashes. Worker
inspection is capture-bound; user production visual acceptance is recorded as
`accepted` for this production surface.

## Historical three-direction intent comparison

The v2 comparison remains useful historical selection evidence. It compared
three low-fidelity information architectures with the same 24 semantic values:

- A: Priority Review Console — selected for production
- B: Narrative Status Brief — retained only as a possible future handoff or
  summary view
- C: Lane And Project Overview — retained only as a possible future
  cross-project overview

Neither B nor C is a production tab or an active implementation request. Open
the historical Japanese-first comparison pack from PowerShell with:

```powershell
Start-Process .\samples\dashboard\intent_comparison\verified_observation_surface_intent_pack.html
```

Its fixture, manifest, readback, capture helper, and screenshots remain in
`samples/dashboard/intent_comparison/`. They preserve point-in-time comparison
provenance and are not live-state authority or the current production surface.

## Earlier layout research prototype

The earlier research memo and single-direction prototype remain supporting
historical evidence for the selected Priority Review Console direction.

Research memo:

```text
docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md
```

Low-fidelity static prototype:

```text
samples/dashboard/layout_research/devcockpitcore_layout_prototype.html
```

Open the prototype directly from PowerShell:

```powershell
Start-Process .\samples\dashboard\layout_research\devcockpitcore_layout_prototype.html
```

The selected model is Priority Review Console: current-state strip, ordered
priority lane, active decision workspace, evidence inspector, and
appendix-style raw evidence. The production generator implements that structure;
the prototype does not control current behavior.

Manual production review:

1. Open the generated dashboard locally; Japanese should be the default.
2. In the first viewport, identify current state, rank 1, why it is first,
   owner, next operation, evidence location, and current-claim eligibility.
3. Select another priority by click and keyboard and confirm the Active Decision
   and Evidence Inspector update together.
4. Switch to English by click and keyboard and confirm the priority order and
   evidence remain identical.
5. Check that compact source labels remain readable and full paths are available
   only in subordinate detail or copy affordances.
6. Use `Tab` to inspect visible focus and appendix disclosures, and confirm the
   first priority and evidence remain available with JavaScript disabled.
7. Review the desktop and narrow captures and return one free-form visual or
   comprehension judgment.

Generate the default dashboard from the repository root with:

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.dashboard
```

Open the generated file directly from PowerShell:

```powershell
Start-Process .\samples\dashboard\devcockpitcore_dashboard.html
```

The dashboard consumes the existing tracked
`samples/evidence_freshness/evidence_freshness_receipt_v1.json` by default.
That receipt is a deterministic point-in-time example, not continuously live
proof. Generate a newly assessed receipt with
`python -m dev_cockpit.evidence_freshness --output-json <local-path>` before
making a current-state claim, then pass the same local path to the dashboard
with `--freshness-receipt <local-path>`. Override the output locations with
`--freshness-receipt`, `--output`, `--priority-readback`,
`--review-actions-json`, and `--review-actions-md` when producing an isolated
live package.

The dashboard and action package are offline review surfaces. Priority and
language controls operate only on already-rendered local evidence. The action
package is not a task runner, and every action is review-only with
`executable: false`. This is not a web server, execution runner, scheduler,
external notification path, credential store, or target-repository writeback
mechanism.
