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
