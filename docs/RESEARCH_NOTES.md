# Research Notes

| Date | Topic | Source | Observation | Design implication | Adopted | Reason |
|---|---|---|---|---|---|---|
| 2026-07-07 | dashboard layout | `docs/design/DASHBOARD_LAYOUT_RESEARCH_V1.md` | card-grid-first presentation keeps too many equal-priority regions visible | use a queue-led Priority Review Console before production dashboard rewrite | yes | aligns dashboard with operator decisions rather than evidence inventory |
| 2026-07-10 | re-kickstart kit | `C:/Users/thank/Downloads/codex_rekickstart_kit_2026-07-09/` | physical `PROJECT_REPO_TEMPLATE/` directory is absent, but template content exists in `ALL_FILES_INLINE.md` and `MANIFEST.json` | reconstruct Project Capsule docs from inline content without overwriting repo-specific `AGENTS.md` | yes | project-local AGENTS forbids growing AGENTS into procedures |

## Research rule

Research is valid only when it connects to one of:

- adopted design decision
- rejected design decision
- implementation diff
- next probe
- validation or artifact evidence

A research table alone does not complete BUILD.
