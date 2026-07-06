# DevCockpitCore Dashboard Samples

This folder holds generated local static dashboard artifacts.
The default dashboard is a latest-brief-first, home-linked dark
designer/operator review surface. The first readout is an editorial status note
with a headline judgment, a short implication, a compact three-step cue, and
one primary review link. It is meant to explain what the state means before the
meter board shows stop gate, warning debt, evidence freshness, review queue,
project smoke, and local access readiness. Each meter links to the matching
detail panel and review action surface, while dense warning, project, source,
and table evidence stays available below the overview.

The generator also writes non-executable review action package artifacts:

- `samples/dashboard/devcockpitcore_review_actions.json`
- `samples/dashboard/devcockpitcore_review_actions.md`

Manual latest-brief review:

1. Open the dashboard file locally.
2. Read the Latest Brief and confirm it is worth reading before the meters.
3. Confirm it does not read like a five-row key-value label.
4. Confirm the page is natively dark without relying on a browser extension.
5. Check that the top meters answer which subsystem to inspect first.
6. Follow each meter link to its detail panel, then use the back-to-overview link.
7. Confirm the Review Stack has no more than three immediate review targets.
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
