# DevCockpitCore Project Cockpit

updated_at: 2026-07-06

## North Star

Make local development supervision reviewable from structured evidence before
adding any broader automation capability.

## Current Active Slice

`dashboard-compact-dark-overview-v1`

Purpose: make the local dashboard a compact dark-mode overview-first
supervision HUD while preserving all source-backed evidence and non-executable
Review Actions.

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
| Compact dark overview | Project review surface | active |
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
| Dashboard artifact | generated local HTML | open and inspect dark overview, first-screen clarity, details panels, Review Actions, and print view |
| Review action package | JSON and Markdown artifacts | confirm actions are review-only and non-executable |
| Compact dark overview | static HTML/CSS | review native dark mode, short labels, and reduced text density |
| C4 probe boundary | exactly one validation-pack key accepted | harden docs/tests before any further execution-readiness work |
| Execution expansion | locked beyond accepted single C4 probe | keep outside this slice |
| Public or production claims | locked | keep dashboard local and review-only |

## Review Axis

- Can a user open one local file and see current testability?
- Are warning ownership, blocker count, and access state visible in the first scan?
- Does the first viewport feel like a compact supervision HUD rather than a text-heavy evidence page?
- Are source JSON paths and generated_at values visible enough for audit?
- Do review actions stay non-executable and source-backed?
- Are skip link, keyboard focus, details panels, non-JS fallback, and print view usable enough for manual review?
- Is the accepted C4 surface still exactly one repo-local validation-pack probe?
- Does the surface stay static, local, and non-executing?
