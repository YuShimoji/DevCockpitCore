# Copy Transport Residue V1

## Purpose

Copy Transport Residue V1 separates UI transport artifacts from Agent-authored
AGENT_REPORT content. This distinction matters before any future controlled
runner probe because report parsing should not mistake copied UI directives for
intentional execution instructions.

## Residue Types

Agent-authored report residue is text intentionally written inside the report
body. It can include prompt fragments, pseudo action markers, raw local paths, or
unsafe automation wording.

UI copy-transport residue is text appended by the client or transport surface
when a report is copied, pasted, staged, committed, or pushed through the UI. Git
stage, commit, and push transport markers at the pasted tail are warnings or
ignored transport residue, not automatic proof that the Agent authored unsafe
content.

## Handling Rule

Normalizers and classifiers may preserve raw input for audit, but they should
separate `transport_residue` from `report_residue` when there is enough context.
The safety warning applies when pseudo actions become actionable instructions,
enter committed artifacts without fixture explanation, or appear inside the
authored report body.

Committed docs and samples should avoid unexplained pseudo action markers. When
fixtures intentionally include them, the fixture should say they are historical
residue examples.

## Relationship To v2.3 Reports

AGENT_REPORT v2.3 bodies should keep prompt/report separation, use compact
bracketed meters with denominators, and keep `current_slice_gates` separate from
`next_slice_gates`. Copy-transport residue is not a substitute for authored
validation evidence.
