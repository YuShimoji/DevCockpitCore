# DevCockpitCore Project Cockpit

updated_at: 2026-07-07

## North Star

Make local development supervision reviewable from structured evidence before
adding any broader automation capability.

## Current Active Slice

`dashboard-layout-research-and-prototype-v1`

Purpose: pause production dashboard polishing, audit why the current report-first
surface still behaves like a card-heavy evidence warehouse, and define one
research-backed layout model before changing the generator again.

Research memo:

```text
docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md
```

Low-fidelity static prototype:

```text
samples/dashboard/layout_research/devcockpitcore_layout_prototype.html
```

Current production dashboard remains unchanged:

```text
samples/dashboard/devcockpitcore_dashboard.html
```

Review action package paths:

```text
samples/dashboard/devcockpitcore_review_actions.json
samples/dashboard/devcockpitcore_review_actions.md
```

Generator:

```text
src/dev_cockpit/dashboard.py
```

Latest repo-level handoff:

```text
docs/handoffs/2026-07-07-dashboard-layout-research-prototype-v1.md
```

## Roadmap Strip

| Step | Lane | State |
| --- | --- | --- |
| Status snapshot | Foundation Observer Readiness | complete |
| Adapter manifests | Foundation Observer Readiness | complete |
| Report normalizer | Foundation Automation Readiness | complete |
| Gate classifier | Foundation Automation Readiness | complete |
| Validation pack | Foundation Automation Readiness | complete |
| Cross-project smoke | Foundation Automation Readiness | complete |
| Controlled C3 help probes | Execution Automation Readiness | bounded and complete |
| C4 scoped runner design review | Execution Automation Readiness | design-only accepted |
| C4 minimal validation-pack probe | Execution Automation Readiness | one bounded key accepted |
| Local test dashboard | Foundation Automation Readiness | complete |
| Designer dashboard IA | Project review surface | complete |
| Review action package | Project review surface | complete |
| Dashboard accessibility pass | Project review surface | complete |
| Compact dark overview | Project review surface | complete |
| Home-linked decision meters | Project review surface | accepted with caveat |
| Latest brief checkpoint | Project review surface | complete with caveat |
| Editorial brief correction | Project review surface | complete with caveat |
| Report-first frontpage | Project review surface | paused after user structural rejection |
| Dashboard layout research/prototype | Project review surface | active |
| Production dashboard redesign from selected layout | Project review surface | future review slice |
| Japanese display polish | Project review surface | future review slice |

## Capability Glyph Grid

| Capability | Glyph | State |
| --- | --- | --- |
| Read-only repo observation | [#] | available |
| Adapter validation | [#] | available |
| Validation pack evidence | [#] | available |
| Cross-project smoke evidence | [#] | available |
| Static local dashboard | [#] | available after generation |
| Warning triage and project cards | [#] | available after generation |
| Non-executable review actions | [#] | available after generation |
| Skip link, focus states, print view | [#] | available after generation |
| Compact dark overview HUD | [#] | available after generation |
| Report-first frontpage | [#] | available after generation |
| Compact Review Map | [#] | available after generation |
| Priority Review Console prototype | [#] | static review artifact |
| C3 help-only probes | [#] | two fixed keys only |
| Single C4 validation-pack probe | [#] | one bounded key accepted |
| Additional C4 commands | [!] | locked |
| Arbitrary execution | [!] | locked |
| External services | [!] | locked |
| Target repository writeback | [!] | locked |

## Gate Board

| Gate | Current State | Next Move |
| --- | --- | --- |
| Validation evidence | warning-level historical residue expected | review dashboard warning rows |
| Smoke evidence | warning-level observer rows expected | confirm optional sibling warnings are acceptable |
| Dashboard artifact | generated local HTML, not rewritten in the active slice | use as audit evidence, not as the design target |
| Review action package | JSON and Markdown artifacts | confirm actions are review-only and non-executable |
| Report-first frontpage | static HTML/CSS | paused pending layout acceptance |
| Layout research memo | selected Priority Review Console | review whether the recommendation should drive the production redesign |
| Layout prototype | low-fidelity static HTML | open and assess queue, workspace, evidence inspector, project order, and appendix |
| C4 probe boundary | exactly one validation-pack key accepted | harden docs/tests before any further execution-readiness work |
| Execution expansion | locked beyond accepted single C4 probe | keep outside this slice |
| Public or production claims | locked | keep dashboard local and review-only |

## Review Axis

- Can a user open one local file and see current testability?
- Are warning ownership, blocker count, and access state visible in the first scan?
- Does the selected layout answer current state, priority, next action, ignorable work, and evidence route?
- Does the priority lane create a single ordered review sequence instead of parallel cards?
- Does the active workspace make the current decision clearer than the existing Review Map/Stack/Details sequence?
- Are source JSON paths and generated_at values visible enough for audit?
- Do review actions stay non-executable and source-backed?
- Are raw validation, smoke, action, and source details available as appendix material rather than top-level reading burden?
- Is the accepted C4 surface still exactly one repo-local validation-pack probe?
- Does the surface stay static, local, and non-executing?

## Review Memory

The user accepted the dark mode and improved information organization as good
enough for now, then flagged the Latest Brief as still forced and the card-based
top viewport as the root problem. The follow-up review rejected continued
card-first polishing: the current page still presents many warnings without a
clear operator sequence, treats projects as parallel, assumes prior context, and
risks becoming test-driven UI. The active checkpoint now recommends a Priority
Review Console with a current-state report, ordered priority lane, active review
workspace, adjacent evidence inspector, ordered project/status list, and
appendix-style raw evidence.
