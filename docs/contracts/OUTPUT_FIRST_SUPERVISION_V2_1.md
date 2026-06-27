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

## Handoff gate

The Handoff Gate applies to `AGENT_REPORT`, not to supervisor prompt generation.
Supervisor prompt generation is valid output when the supervisor lane decides
the next slice. Agent reports should explain whether a handoff is required and
why the current agent should not continue.

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
