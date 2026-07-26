# H4-G01 Authentic Two-Project Review Candidate

This package binds two authentic, owner-authorized, point-in-time project reports to two strict read-only observation receipts and projects them through DevCockpitCore's canonical report normalizer, gate classifier, cross-project supervision packet, and Priority Review Console.

## Review Surface

Open `dashboard/devcockpitcore_dashboard.html` locally. The global rank is attention and review priority only. It is not an execution order. Project-local worksets keep the NLMYTGen dirty observation and the ClipPipeGen clean observation independently visible.

## Fixed Inputs

- `source/AGENT_REPORT_H4_G01_NLMYTGEN.md`
- `source/AGENT_REPORT_H4_G01_CLIPPIPEGEN.md`
- `receipts/nlmytgen_current_observation_v1.json`
- `receipts/clippipegen_current_observation_v1.json`
- `manifest/task_report_manifest_v1.json`

## Derived Outputs

- two normalization documents
- two explicit gate-classification documents
- one source-bound two-report supervision packet in JSON and Markdown
- one Priority Review Console with JSON and Markdown review actions
- one compact priority readback
- one package readback binding inputs, outputs, revisions, and scope

Run `python artifacts/review/h4-g01-authentic-two-project-review-v1/generate_package.py --verify` from the repository root to reproduce and compare every derived byte.

## Scope Boundary

The package is point-in-time, non-live, non-executable, and observer-only. It performs no source-repository writeback and confers no human acceptance, rights clearance, production authority, publication approval, release approval, main integration, or deployment authority.
