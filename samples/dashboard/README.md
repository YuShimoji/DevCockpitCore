# DevCockpitCore Dashboard Samples

This folder holds generated local static dashboard artifacts.
The default dashboard is a report-first dark designer/operator review surface.
The first viewport is a concise Current Status / Supervision Report with a
headline judgment, short interpretation, compact status strip, one primary
review link, and one secondary evidence link. The former meter board is demoted
into a compact Review Map below the report. Each Review Map item links to the
matching detail panel and review action surface, while dense warning, project,
source, and table evidence stays available below the frontpage.

The generator also writes non-executable review action package artifacts:

- `samples/dashboard/devcockpitcore_review_actions.json`
- `samples/dashboard/devcockpitcore_review_actions.md`

## Three-direction intent comparison

The active review checkpoint compares three low-fidelity information
architectures using the same 24 semantic values and wording:

- A: Priority Review Console
- B: Narrative Status Brief
- C: Lane And Project Matrix

Open the Japanese-first comparison pack directly from PowerShell:

```powershell
Start-Process .\samples\dashboard\intent_comparison\verified_observation_surface_intent_pack.html
```

The page includes an English toggle and explicit `source_commit`,
`observed_at`, and `freshness_state` fields. Its adjacent evidence is:

- `samples/dashboard/intent_comparison/intent_comparison_fixture.json`
- `samples/dashboard/intent_comparison/intent_comparison_manifest.json`
- `samples/dashboard/intent_comparison/intent_comparison_readback.json`
- `samples/dashboard/intent_comparison/capture_intent_comparison.mjs`
- `samples/dashboard/intent_comparison/screenshots/priority-review-console.png`
- `samples/dashboard/intent_comparison/screenshots/narrative-status-brief.png`
- `samples/dashboard/intent_comparison/screenshots/lane-project-matrix.png`

The pack is point-in-time review evidence only; no direction is accepted yet
and `src/dev_cockpit/dashboard.py` remains unchanged.

## Earlier layout research prototype

The earlier research memo and single-direction prototype remain supporting
evidence for the current three-direction comparison. The report-first dashboard
remains available as the current generated artifact, but production layout
iteration is paused pending a user direction choice.

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

The recommended model is Priority Review Console: a current-state report,
ordered priority lane, active review workspace, evidence inspector, ordered
project/status list, and appendix-style raw evidence. It is a review artifact
only and does not replace `src/dev_cockpit/dashboard.py`.

Manual report-first review:

1. Open the dashboard file locally.
2. Read the Current Status / Supervision Report and confirm it feels like a concise status report.
3. Confirm the former Latest Brief is not rendered as a separate bolt-on card.
4. Confirm the page is natively dark without relying on a browser extension.
5. Check that the Review Map is compact and secondary to the report.
6. Follow each Review Map link to its detail panel, then use the back-to-review-map link.
7. Confirm the folded Review Stack has no more than three immediate review targets.
8. Use `Tab` to check the skip link, section navigation, filters, details panels, and action cards.
9. Confirm the core content remains visible if JavaScript is disabled.
10. Use browser print preview to inspect the light print handoff view.

Generate the default dashboard from the repository root with:

```bash
PYTHONPATH=src python -m dev_cockpit.dashboard --output samples/dashboard/devcockpitcore_dashboard.html
```

Open the generated file directly from PowerShell:

```powershell
Start-Process .\samples\dashboard\devcockpitcore_dashboard.html
```

The dashboard and action package are offline review surfaces. Their
search/filter controls only hide or show already-rendered local cards. The
action package is not a task runner, and every action is review-only with
`executable: false`. This is not a web server, execution runner, scheduler,
external notification path, credential store, or target repository writeback
mechanism.
