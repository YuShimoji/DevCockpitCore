# Roadmap

## Now

Re-kickstart DevCockpitCore into the material-evidence-first loop without
changing its active capability boundary. The active review surface remains
`dashboard-layout-research-and-prototype-v1`.

## Next

Review whether the Priority Review Console prototype should drive a future
production dashboard redesign.

## Later

If accepted, implement a scoped static generator redesign that preserves source
evidence, non-executable review actions, C3/C4 boundaries, and local-only output.

## Next BUILD Candidates

| Candidate | Impact | Effort | Risk | Evidence |
|---|---:|---:|---:|---|
| Layout acceptance review | high | low | low | written acceptance/rejection note tied to `docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md` and the prototype path |
| Priority queue model slice | high | medium | medium | deterministic sample JSON or tests showing how warning actions become one ordered queue |
| Production dashboard redesign spike | high | medium | medium | scoped diff in `src/dev_cockpit/dashboard.py`, updated tests, regenerated static dashboard, and screenshot or DOM-smoke evidence |

## Decision gates

| Gate | Owner | Evidence required |
|---|---|---|
| Accept Priority Review Console | user | prototype review and explicit acceptance/rejection |
| Rewrite production generator | user/supervisor | accepted layout model, rollback path, test plan |
| Expand controlled execution | user/supervisor | separate authorization; not implied by dashboard work |
| Public or external integration | user | explicit approval, rights/security review, and separate design |

## Not the next move

Do not continue polishing the current card-derived production dashboard before
the layout research/prototype is reviewed. Do not add a server, scheduler,
credentials, target-repository writeback, C5/C6 behavior, or a second C4 command.
