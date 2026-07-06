# DevCockpitCore Dashboard Samples

This folder holds generated local static dashboard artifacts.
The default dashboard is a compact dark-mode designer/operator review surface.
The first view summarizes the continue/stop judgment, blocker count, warning
focus, source freshness, and next review step. Dense warning, project, source,
and table evidence stays available in native details panels below the overview.

The generator also writes non-executable review action package artifacts:

- `samples/dashboard/devcockpitcore_review_actions.json`
- `samples/dashboard/devcockpitcore_review_actions.md`

Manual compact/dark review:

1. Open the dashboard file locally.
2. Confirm the page is natively dark without relying on a browser extension.
3. Check that the first screen is overview-first and not text-heavy.
4. Use `Tab` to check the skip link, section navigation, filters, details panels, and action cards.
5. Confirm the core content remains visible if JavaScript is disabled.
6. Use browser print preview to inspect the light print handoff view.

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
