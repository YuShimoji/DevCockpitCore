# DevCockpitCore Project Cockpit

updated_at: 2026-07-10
status_authority: this file
runtime_projection: docs/runtime-state.md
last_verified_base: dc6b5bb
resume_branch: codex/workflow-handoff
handoff: docs/handoffs/2026-07-10-workflow-handoff.md
active_product_checkpoint: dashboard-layout-research-and-prototype-v1
active_workflow_checkpoint: outcome-envelope-and-cockpit-authority-v1
blocking_issue_count: 0
external_status: https://github.com/YuShimoji/DevCockpitCore/blob/codex/workflow-handoff/docs/PROJECT_COCKPIT.md
external_publish_state: draft_pr_before_main_merge
pull_request: https://github.com/YuShimoji/DevCockpitCore/pull/1
wiki_sync: not_configured

## Status In One Minute

DevCockpitCore starts from the `origin/main` verified base `dc6b5bb` and is
locally developable. The standard-library Python package,
309 unit tests, four adapters, live observer path, bounded C3/C4 probes, and
validation pack all run successfully. There is no code or environment blocker.

The active product decision is deliberately before another production
dashboard rewrite. The existing report-first dashboard remains audit evidence;
the separate Priority Review Console prototype is one candidate, not an
implicitly approved final direction. Production UI work stays paused until a
small set of materially different low-fidelity directions is compared and the
user selects one.

The development workflow now treats one prompt as an outcome envelope.
Investigation, implementation, related fixes, tests, cleanup, and state
synchronization continue without a new prompt while they stay in scope.
Authority-sensitive changes and expensive subjective directions are the two
explicit stop gates.

## Lane State

| Lane | Current state | What that means |
| --- | --- | --- |
| Foundation Observer Readiness | Complete | Read-only status snapshots and four project adapters are available. |
| Foundation Automation Readiness | Complete and usable | Report normalization, gate classification, validation packs, cross-project smoke, dashboard generation, and review actions are available. |
| Execution Automation Readiness | Intentionally bounded | C3 has two help-only keys; C4 has one fixed local validation-pack key. No general runner is authorized. |
| Project Review Surface | Intent checkpoint | Layout research and one low-fidelity prototype exist; production generator redesign is waiting for a direction choice. |
| Development Workflow | Operating model refreshed | Mission-sized prompts, narrow stop gates, creative intent checkpoints, and cockpit closure are the project-local default. |

## Current Product Decision

Do not continue card-by-card polish on
`samples/dashboard/devcockpitcore_dashboard.html`. Before production work,
compare two or three low-cost directions. The current exploration set is:

| Direction | Primary experience | Strength | Main tradeoff |
| --- | --- | --- | --- |
| Priority Review Console | Ordered queue, active decision workspace, adjacent evidence inspector | Best at telling an operator what to decide next | Can feel tool-like if the narrative state report is too thin |
| Narrative Status Brief | A concise current-state story with decisions and evidence revealed in reading order | Best for low-context handoff and occasional users | Slower for repeated triage across many projects |
| Lane And Project Matrix | Readiness lanes by project with one selected detail drawer | Best for cross-project comparison and expansion | Risks returning to equal-weight tiles unless priority is explicit |

The existing prototype represents only the first direction:
`samples/dashboard/layout_research/devcockpitcore_layout_prototype.html`.
The other directions should remain low fidelity until the intent checkpoint is
used.

## Live Verification

The following checks were run against the synchronized checkout on 2026-07-10:

| Check | Result | Interpretation |
| --- | --- | --- |
| Source and test compilation | Pass | Python sources and tests compile. |
| Unit tests | 309 passed | No failing local test, including the current-state contract guard. |
| Adapter validation | 4 of 4 passed | All tracked adapters satisfy the manifest contract. |
| Live status snapshot | Clean checkpoint after commit | The workflow change set is committed on the resume branch; verify remote parity after fetching. |
| Validation pack | 15 pass, 1 known warning, 0 fail | The warning is the intentional pseudo-git-tag fixture, not a live defect. |
| C3 probe | 11 of 11 passed | Both bounded help-only paths remain healthy. |
| C4 probe | 18 of 18 completed, exit 0 | The single validation-pack probe remains within its fixed boundary. |
| Cross-project smoke | Core passed; 3 optional siblings warned | Optional sibling state does not block DevCockpitCore development. |
| Git whitespace check | Pass | No whitespace error at the synchronized base. |

## Known Drift And Uncertainty

- Tracked status, validation, cross-project smoke, dashboard, and review-action
  samples are checkpoint evidence generated on 2026-07-06 or 2026-07-07. They
  do not represent the current live checkout and must not be used as the sole
  current-state authority.
- GitHub Wiki is enabled for the public repository, but it has no pages and no
  wiki repository yet. The branch Cockpit link above is the external viewing
  route for this handoff. Draft PR #1 carries the branch into `main` when it
  is reviewed and merged. A second manually edited status source should not be
  created.
- The Priority Review Console has low-fidelity evidence and tests but no user
  acceptance. The production generator remains intentionally unchanged.
- Local verification depends on Python 3.11+, `PYTHONPATH=src`, `unittest`,
  and the repository validation pack. There is no CI workflow or bootstrap
  script yet.

## Operating Loop

1. The Supervisor reads this cockpit and frames one user-visible outcome,
   known decisions, autonomy, stop gates, acceptance, and closure.
2. The development agent continues through the entire authorized outcome.
3. An Authority Gate stops destructive work, dependencies, contracts,
   credentials, external effects, writeback, or capability expansion.
4. An Intent Gate stops expensive subjective work before production and
   presents two or three low-cost directions plus a recommendation.
5. Completion updates this cockpit and its runtime projection once, then
   reports evidence and different next entrances.

Prompt/report separation remains useful, but it does not force a new prompt for
each mechanical substep. See
`docs/contracts/OUTPUT_FIRST_SUPERVISION_V2_1.md`.

## Next Entrances

| Entrance | Friction removed | What becomes possible |
| --- | --- | --- |
| Explore — dashboard intent checkpoint | Large UI delivery followed by correction churn | The user can choose a layout, language, visual, and content direction before generator work. |
| Verify — current-state freshness guard | Stale samples and duplicated live-state claims | Validation can warn when cockpit/runtime labels or generated evidence fall behind. |
| Excise — historical restart duplication | Long restart lists and routine handoff creation | A new agent can resume from AGENTS, this cockpit, and one active design artifact. |
| Advance — macro-prompt pilot | Prompt fragmentation and repeated safe approvals | One selected outcome can run from implementation through verification and cockpit closure. |

## Update Contract

- Update this file when the active outcome, lane state, next decision,
  validation state, or material uncertainty changes.
- Update `docs/runtime-state.md` in the same change as the compact
  machine-facing projection.
- Keep `docs/project-context.md` limited to durable mission, architecture, and
  capability boundaries.
- Record only durable choices in `docs/decision-log.md`.
- Keep creative opportunities, alternatives, and rejected routes in
  `docs/idea-ledger.md`.
- Create a dated handoff only for a real context transfer that cannot be
  reconstructed from this cockpit and the active design artifact.
- Treat any external Wiki, Page, or workspace as a one-way view of this file,
  never as a second status authority.
