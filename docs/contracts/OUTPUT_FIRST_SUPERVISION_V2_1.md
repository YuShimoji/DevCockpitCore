# Output-First Report Interface v2.1

This document defines the report-shaped inputs and machine-readable outputs
handled by DevCockpitCore. It is a product interface contract for observation,
normalization, classification, and transport readback. It does not control how
a development agent works and is not a repository workflow authority.

## Input lanes

`SUPERVISOR_PROMPT` is the input lane from a supervising thread to an agent. It
may describe task, goal stack, allowed scope, validation, stop conditions, and
expected report shape.

`AGENT_REPORT` is the return lane from the agent to the supervisor. It should
return evidence, completed work, validation results, user-side work if any, and
continuation state.

An `AGENT_REPORT` must not include a paste-ready next-agent prompt. If a handoff
is needed, it should provide a handoff request with the minimum verified state
needed for the supervisor to generate the next prompt.

## Freeform input and classifier targets

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
