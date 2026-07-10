# Output-First Supervision v2.1 Anchor

This project keeps a local anchor for the supervision contract used by
DevCockpitCore work. It is intentionally concise and does not copy external
project resources.

## Prompt and report separation

`SUPERVISOR_PROMPT` is the input lane from a supervising thread to an agent. It
may describe task, goal stack, allowed scope, validation, stop conditions, and
expected report shape.

`AGENT_REPORT` is the return lane from the agent to the supervisor. It should
return evidence, completed work, validation results, user-side work if any, and
continuation state.

An `AGENT_REPORT` must not include a paste-ready next-agent prompt. If a handoff
is needed, it should provide a handoff request with the minimum verified state
needed for the supervisor to generate the next prompt.

Prompt/report separation is a transport rule, not a work-granularity rule. It
does not require one prompt per design note, implementation step, review, or
hardening pass.

## Outcome envelope and continuation

A `SUPERVISOR_PROMPT` should authorize one coherent user-visible outcome. The
envelope may include investigation, low-cost exploration, implementation,
related fixes, tests, generated evidence, cleanup, and current-state document
updates. The agent should continue across those steps without waiting for a new
prompt while the work remains inside the same scope and capability boundary.

Finishing an intermediate artifact is not, by itself, a handoff condition. A
new prompt is needed for a new outcome, an authority expansion, or a material
direction change, not for the next mechanical step of the current outcome.

The prompt should make six things explicit:

| Field | What it establishes |
| --- | --- |
| Outcome | What the user will be able to use or decide when the work is complete. |
| Known decisions | Direction that should not be reopened without new evidence. |
| Autonomy | Investigation, implementation, related fixes, tests, cleanup, and state synchronization that may proceed continuously. |
| Intent checkpoint | Subjective, expensive-to-rework choices that need low-cost alternatives before production work. |
| Authority checkpoint | Destructive work, dependencies, DB/auth/API contracts, credentials, external side effects, writeback, or capability expansion that require approval. |
| Acceptance and closure | Observable behavior, validation, preserved boundaries, and current-state resources that must be updated. |

## Two stop gates

The **Authority Gate** is for permissions and contracts. It applies to
destructive or difficult-to-reverse changes, dependencies, databases,
authentication, API contracts, credentials, external writes or notifications,
target-repository writeback, execution-capability expansion, and material
specification conflicts.

The **Intent Gate** is for preference-sensitive work with high rework cost. It
applies to information architecture, layout, visual identity, color and type
systems, motion language, copy tone, localization scope, and similarly
subjective directions. The agent should first show two or three materially
different low-cost options, state a recommendation, and wait for selection
before a production-scale implementation. Once selected, the same outcome
envelope continues through build and verification.

Expected warnings, missing optional inputs, reversible repo-local choices,
routine fixes, tests, and documentation updates are not stop gates.

## Handoff gate

The Handoff Gate applies to `AGENT_REPORT`, not to supervisor prompt generation.
Supervisor prompt generation is valid output when the supervisor lane decides
the next slice. Agent reports should explain whether a handoff is required and
why the current agent should not continue.

If the current agent can complete the authorized outcome safely, it should do
so. Handoffs are reserved for a real context transfer, an exhausted authority
envelope, or a stop gate that requires a decision. They are not mandatory at
every slice boundary.

## Progress, creative options, and closure

Progress reporting should mark meaningful transitions without asking for
permission to perform routine continuation work. The final report should lead
with the outcome, then give verification, remaining uncertainty, and two to
four next entrances that relieve different bottlenecks.

At orientation and closure, check for repeated workflow friction and useful
adjacent opportunities. When relevant, return no more than two creative
proposals with their user value, cost, reversibility, and why deciding now is
useful. High-cost subjective proposals still pass through the Intent Gate.

When project state changes, closure includes synchronizing the repository's
declared current-state authority. For DevCockpitCore that authority is
`docs/PROJECT_COCKPIT.md`; `docs/runtime-state.md` is the compact machine-facing
projection. Decision logs, idea ledgers, README text, generated evidence, and
handoffs are updated only when their stated responsibility is triggered.

## User input and future classifiers

User input remains freeform. Fixed forms are not required for this repository's
first observer slice.

Stop classes, gate separation, and readiness lanes are future classifier
targets. The status producer should preserve those concepts without claiming
execution automation readiness.

## Report normalization

`report_normalization.v1` is a readback artifact for AGENT_REPORT-like text. It
may identify route, progress, action, status, residue, handoff state, and a
recommended next slice, but it must not generate a paste-ready next-agent prompt.

## Gate classification

`gate_classification.v1` is a decision readback over normalized reports. It may
set `supervisor_should_generate_prompt: true` and a minimal next task, but it
must not write the prompt body or convert an AGENT_REPORT into a SUPERVISOR_PROMPT.

## v2.3 Meter Coverage Anchor

For v2.3-compatible AGENT_REPORTs, every progress-like summary or gate matrix
should include `done`, `total`, `unknown`, `meter`, and `missing`. Meters must
use ASCII-safe symbols only: `#` for done, `-` for missing, `?` for unknown, `~`
for partial or warning, and `!` for risk. Current-lane readiness and next-slice
gates should remain separate.

## v2.3 Gate And Transport Anchor

Reports should distinguish the completed slice from the next slice. Use
`current_slice_gates` for the slice being reported, and leave `next_slice_gates`
empty, such as `[--------] 0/8`, when the next slice has not started.

UI copy-transport markers appended outside the authored report body should be
classified separately from report residue. Authored reports and committed
samples should still avoid unexplained pseudo action markers.

## v2.5 Clipboard Transport Anchor

For v2.5-compatible AGENT_REPORTs, clipboard or paste-pack state is metadata
about the transport, not a next-agent prompt. A report may declare that no
clipboard pack is included, but the authored body must still avoid paste-ready
`SUPERVISOR_PROMPT` content.

If a UI appends action markers after the authored report, classifiers should
read them as copy-transport residue. They must not convert an AGENT_REPORT into
a next prompt, and they must not count as project evidence unless the authored
report explicitly cites the produced artifact.
