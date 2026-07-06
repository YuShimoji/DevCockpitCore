# DevCockpitCore Project Cockpit

updated_at: 2026-07-06

## North Star

Make local development supervision reviewable from structured evidence before
adding any broader automation capability.

## Current Active Slice

`dashboard-latest-brief-checkpoint-v1`

Purpose: checkpoint the accepted dark home-linked dashboard lane with a
lightweight Latest Brief before the meter board. The brief gives a concise
status readout while preserving meter/detail navigation, source-backed evidence,
and non-executable Review Actions.

Dashboard artifact path:

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
| Latest brief checkpoint | Project review surface | active |
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
| Home-linked meter HUD | [#] | available after generation |
| Latest Brief readout | [#] | available after generation |
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
| Dashboard artifact | generated local HTML | open and inspect meter clarity, detail anchors, Review Stack, Review Actions, and print view |
| Review action package | JSON and Markdown artifacts | confirm actions are review-only and non-executable |
| Latest Brief checkpoint | static HTML/CSS | confirm the first readout gives decision, blockers, focus, proof, and next action without becoming a new data table |
| C4 probe boundary | exactly one validation-pack key accepted | harden docs/tests before any further execution-readiness work |
| Execution expansion | locked beyond accepted single C4 probe | keep outside this slice |
| Public or production claims | locked | keep dashboard local and review-only |

## Review Axis

- Can a user open one local file and see current testability?
- Are warning ownership, blocker count, and access state visible in the first scan?
- Does the Latest Brief give an overview report before the parallel meter set?
- Does the first viewport feel like a decision meter HUD rather than a collapsed evidence closet?
- Does each top meter link to the exact detail panel and review action surface it explains?
- Are source JSON paths and generated_at values visible enough for audit?
- Do review actions stay non-executable and source-backed?
- Are skip link, keyboard focus, details panels, non-JS fallback, and print view usable enough for manual review?
- Is the accepted C4 surface still exactly one repo-local validation-pack probe?
- Does the surface stay static, local, and non-executing?

## Review Memory

The user accepted the dark mode and improved information organization as good
enough for now. The remaining caveat is that the dashboard can still present
too many signals in parallel; future progress should evolve brief-first status
reporting without turning this slice into a full reporting engine.
