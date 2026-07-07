# Dashboard Layout Research V1

updated_at: 2026-07-07
artifact: dashboard-layout-research-and-prototype-v1
status: research_checkpoint
production_generator_status: unchanged

## Problem Statement

The current dashboard direction improved the first viewport, but the user
rejected the structural direction. The page still feels card-based,
text-heavy, scroll-heavy, and more like a warehouse of known facts than a
surface that tells a low-context operator what to do now.

The design problem is therefore not a copy polish problem. DevCockpitCore needs
a supervision layout that answers five questions quickly:

1. What is the current state?
2. What matters most?
3. What should I do next?
4. What can I ignore for now?
5. Where is the evidence if I need it?

## Research Sources

This research pass used the current repo artifact plus lightweight external
layout guidance:

- Nielsen Norman Group, "Dashboards: Making Charts and Graphs Easier to
  Understand": dashboards should communicate critical information quickly, with
  minimal cognitive processing.
  https://www.nngroup.com/articles/dashboards-preattentive/
- Nielsen Norman Group, "Visibility of System Status": system status must help
  users decide what to do next.
  https://www.nngroup.com/articles/visibility-system-status/
- IBM Carbon Design System, "Dashboards": dashboard data should be prioritized
  by importance, with a clear visual hierarchy and non-essential information
  supplied only as needed.
  https://carbondesignsystem.com/data-visualization/dashboards/
- Microsoft Learn, "List/details": list/detail layouts are useful when people
  need to locate and prioritize a collection, then move back and forth between
  overview and detail.
  https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/list-details
- Nielsen Norman Group, "Progressive Disclosure": show the most important
  options first and defer secondary details until requested.
  https://www.nngroup.com/articles/progressive-disclosure/
- GOV.UK Design System, "Complete multiple tasks": task lists help users
  understand tasks, order, and completion status.
  https://design-system.service.gov.uk/patterns/complete-multiple-tasks/
- Nielsen Norman Group, "Information Scent": link labels and surrounding
  context should make the next destination predictable.
  https://www.nngroup.com/articles/information-scent/

## Current Dashboard Audit

The current production artifact is
`samples/dashboard/devcockpitcore_dashboard.html`. A local screenshot audit at a
1440px viewport found a real improvement in the first viewport: the top strip
now reads as a report, the first CTA is visible, and the stop-gate count is
clear.

The structural issues remain:

| Audit Lens | Current Example | Effect On Operator |
| --- | --- | --- |
| First-time comprehension | The header says warning judgment matters, but the operator immediately sees Review Map, Review Stack, Linked Detail Map, Warnings, Actions, Projects, and Sources. | A newcomer sees many named regions before they know which one owns the decision. |
| Task sequencing | Six Review Map entries appear as equal-width navigation targets: Stop Gate, Warning Debt, Evidence Freshness, Review Queue, Project Smoke, Access Readiness. | The page implies parallel topics instead of a ranked work queue. |
| Information scent | Labels such as Review Stack, Linked Detail Map, Project Cards, and Access Readiness are internally meaningful. | Operators must already know the DevCockpit mental model to predict where evidence lives. |
| Visual hierarchy | The first viewport has a report header, then a nav row, then a six-column review map, then a disclosure stack, then a detail panel. | Hierarchy competes with structure; the page still exposes its inventory. |
| Warning triage clarity | The action package has 20 actions, 16 warning actions, several repeated "Review ... warning" titles, and project rows that are observer warnings. | The operator can see volume, but not ownership, severity, or the single next judgment. |
| Project ordering | Cross-project rows are presented as project cards or table rows, with warnings for DevCockpitCore, NLMYTGen, WritingPage, and ClipPipeGen. | Project order is evidence order, not operator relevance. |
| Scroll burden | The page continues through 12 disclosure sections, 8 project cards, 20 action cards, validation tables, smoke tables, locked lanes, notes, and sources. | The operator must scroll to understand what can be ignored. |
| Hardcoded note brittleness | Notes such as "Not urgent" and "Designer / Operator Notes" explain the current test state. | Guidance risks becoming local to the fixture instead of a durable layout rule. |
| Test-driven design risk | Existing tests assert report-first classes, Review Map labels, details panels, project cards, and old surface absence. | Tests protect the current implementation shape, so further production edits may polish around a flawed structure. |

## Layout Principles For DevCockpitCore

DevCockpitCore is not a business intelligence dashboard. It is a supervision
surface for resuming development safely. The layout should therefore behave
more like an operator console than a grid of independent content modules.

The next production redesign should follow these principles:

1. Start with a plain-language state report, not metric tiles.
2. Put one ordered priority queue above or beside all detail.
3. Make the selected review item the center of the workspace.
4. Keep proof close to the selected item, but visually secondary.
5. Order projects by current operator relevance, not by adapter listing.
6. Collapse raw validation, smoke, and action data into an appendix.
7. Treat locked execution lanes as boundary context, not top-level work.
8. Use links and labels that predict the destination for a first-time reader.
9. Avoid independent cards as the primary layout grammar.
10. Preserve the offline, static, non-executing artifact boundary.

## Layout Comparison

| Layout Model | Helps With | Fails For This Surface | Decision |
| --- | --- | --- | --- |
| Card-grid-first dashboard | Fast scanning when every metric has similar weight. | Encourages parallel tiles, repeated warnings, and card proliferation. It does not naturally answer "what should I do now?" | Reject as primary structure. |
| Status report plus priority queue | Makes current state and next action explicit. | Needs a paired evidence area or the queue becomes another list of claims. | Keep as part of selected model. |
| Incident command console | Strong for urgent severity, ownership, and active incident handling. | DevCockpitCore is mostly observer evidence and warning judgment, not live incident response. The tone would overstate urgency. | Borrow severity ordering, reject incident framing. |
| Master-detail workspace | Good for a large collection where one item must be inspected without losing the list. | Pure list/detail can underplay the summary state if it starts directly with the list. | Keep as part of selected model. |
| Left-rail navigation with central narrative | Good for stable app sections and repeat users. | Navigation categories do not solve first-time sequencing; a rail can hide the priority decision. | Reject as primary structure. |
| Timeline/current-state feed | Good for chronological change awareness. | The current evidence is not primarily a sequence of events; it is a set of readiness signals. | Reject for this slice. |
| Wizard-like review sequence | Good when every operator must complete a strict process. | Too linear for an observer dashboard where many details are optional and should be ignored. | Reject for primary use. |
| Single-page report with appendix evidence | Good for handoff and low-context reading. | Too static if the operator must compare warning rows and inspect one item repeatedly. | Keep as secondary appendix behavior. |

## Selected Recommendation

Choose exactly one architecture: Priority Review Console.

The model combines a short state report, an ordered priority lane, an active
review workspace, and an evidence inspector:

```text
current-state report
priority queue -> active review workspace -> evidence inspector
ordered project/status list
collapsed appendix for raw validation, smoke, action, and source data
```

This is not a card grid. It is a queue-led split workspace. The priority lane
answers "what matters most?". The workspace answers "what should I decide
now?". The inspector answers "where is the proof?". The ordered project list
answers "what can wait?" by ranking observer rows instead of presenting
parallel project cards. The appendix preserves auditability without making raw
evidence the main reading path.

## Why This Beats The Current Dashboard

The current dashboard still surfaces what the system knows. Priority Review
Console surfaces what the operator should decide.

The current design asks the operator to choose among Review Map, Stack,
Details, Warnings, Actions, Projects, and Sources. The recommended design
chooses the first review item for the operator and keeps the evidence one pane
away. It also makes "ignore for now" visible: locked execution lanes, raw
tables, and repeated review actions belong in the appendix unless the active
review item needs them.

## Low-Fidelity Prototype

Prototype path:

```text
samples/dashboard/layout_research/devcockpitcore_layout_prototype.html
```

The prototype demonstrates the selected architecture using current sample
evidence:

- 0 blockers.
- 9 warning signals.
- 20 review actions, 16 warning actions.
- 6/6 source evidence files loaded.
- Cross-project smoke warnings for DevCockpitCore, NLMYTGen, WritingPage, and
  ClipPipeGen.
- Locked execution expansion lanes stay non-executable and below the decision
  surface.

The prototype is intentionally static and low-fidelity. It should be reviewed
before any production generator rewrite.

## Acceptance Criteria For A Future Production Redesign

A future production dashboard redesign should pass these checks:

| Check | Acceptance Criteria |
| --- | --- |
| Current state | First viewport contains a concise prose state report and blocker/attention/access summary. |
| Priority ordering | There is exactly one ordered priority queue above raw evidence. |
| Active decision | One selected review item has a clear decision question and next safe action. |
| Evidence access | Source paths and relevant counts are adjacent to the selected item. |
| Project relevance | Project/status rows are ordered by operator attention, not adapter order or equal cards. |
| Ignore path | Locked lanes and raw validation/smoke/action data are visibly secondary. |
| Card control | Independent cards are not the primary structure and cannot proliferate as the top-level grammar. |
| Static boundary | No server, scheduler, external service, credential, writeback, or execution control is added. |
| Test posture | Tests protect layout intent and safety boundaries, not a brittle visual copy arrangement. |

## What Not To Change Yet

- Do not rewrite `src/dev_cockpit/dashboard.py` in this slice.
- Do not replace `samples/dashboard/devcockpitcore_dashboard.html` as the
  production output.
- Do not add more production cards, warning panels, or top-level notes.
- Do not add a web server, scheduler, database, credential handling,
  notification path, target repository writeback, C5, C6, or arbitrary command
  runner.
- Do not implement full localization or claim formal accessibility compliance.

## Review Debt

- Decide whether the queue-led split workspace should become the next
  production generator target.
- Decide whether the priority queue should be derived from review actions,
  warning triage, or a new normalized operator-decision model.
- Decide how much current source detail should remain visible by default on
  narrow screens.
