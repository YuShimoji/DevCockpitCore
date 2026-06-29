# DevCockpitCore

DevCockpitCore is a cross-project supervision substrate for development work. It
starts with read-only observation: produce a consistent status snapshot for a
target repository so a supervisor thread or a future automation layer can resume
work with less ambiguity.

This repository is not an execution runner. The first slice,
`common-foundation-status-producer-v1`, only inspects repository state, adapter
configuration, known project documents, artifact roots, and validation hints.

## First slice

The status producer can:

- read a target repository path without modifying it
- load a project adapter manifest
- report branch, HEAD, upstream parity, and worktree cleanliness
- record whether known project context files exist
- list bounded artifact candidates under configured roots
- emit a machine-readable `status_snapshot.v1` JSON document

It does not:

- run tests in the target repository
- render media or documents
- schedule work
- send notifications
- open a web server or GUI
- commit, push, rebase, reset, stash, or merge target repository changes
- implement a Codex execution loop or autonomous runner

## Usage

From an editable install or any environment where `src` is on `PYTHONPATH`:

```bash
python -m dev_cockpit.status_snapshot \
  --repo ../NLMYTGen \
  --adapter adapters/nlmytgen.json \
  --output samples/status_snapshots/nlmytgen_status.json \
  --pretty
```

From a fresh checkout without installing:

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.status_snapshot --help
```

Use `--no-write` to print the snapshot to stdout without writing the output
file:

```bash
python -m dev_cockpit.status_snapshot \
  --repo ../NLMYTGen \
  --adapter adapters/nlmytgen.json \
  --no-write \
  --pretty
```

The console script name is also wired in `pyproject.toml`:

```bash
dev-cockpit-status --repo ../NLMYTGen --adapter adapters/nlmytgen.json --output out.json
```

## Adapter manifests

Adapters are small JSON files that follow `adapter_manifest.v1` and describe
safe project-local expectations:

- project name
- stable project key
- default branch hint
- preferred relative repository locations
- runtime state and project context document paths under `documents`
- artifact roots to inspect
- status hint patterns for shallow label extraction
- forbidden staged artifact patterns
- default validation commands to report but not run
- `read_only: true`

The first adapters live under `adapters/`:

- `adapters/devcockpitcore.json`
- `adapters/nlmytgen.json`
- `adapters/writingpage.json`
- `adapters/clippipegen.json`

Adapter data is intentionally conservative. The status producer reports what it
can observe and leaves uncertain fields as `unknown` or `null`.

Validate adapters with:

```bash
PYTHONPATH=src python -m dev_cockpit.adapters --validate adapters/*.json
```

Generate a self-smoke snapshot for this repository with:

```bash
PYTHONPATH=src python -m dev_cockpit.status_snapshot \
  --repo . \
  --adapter adapters/devcockpitcore.json \
  --output samples/status_snapshots/devcockpitcore_status.json \
  --pretty
```

To add a project adapter, copy an existing manifest, keep all paths relative,
set a stable lowercase `project_key`, keep `read_only: true`, then run the
adapter validation command. See `docs/design/ADAPTER_MANIFEST_V1.md` for the
full field contract.

## Report normalizer

The report normalizer reads AGENT_REPORT-like text and emits
`report_normalization.v1` JSON. It extracts route, progress, action, status,
sections, commits, validation evidence, continuation state, and handoff state.
It also audits residue such as pseudo git tags, paste-ready supervisor prompt
markers, local user paths, risky automation wording, and readiness overclaims.

Generate the sample normalization with:

```bash
PYTHONPATH=src python -m dev_cockpit.report_normalizer \
  --input samples/reports/agent_report_adapter_manifest_v1_redacted.txt \
  --output samples/report_normalizations/adapter_manifest_v1_readback.json \
  --pretty
```

The sample input lives at
`samples/reports/agent_report_adapter_manifest_v1_redacted.txt`; the normalized
readback lives at
`samples/report_normalizations/adapter_manifest_v1_readback.json`.

The normalizer does not emit paste-ready next-Agent Prompts. The next roadmap
step is `gate-classifier-v1`.

## Gate classifier

The gate classifier reads `report_normalization.v1` JSON and emits
`gate_classification.v1` JSON. It classifies push, handoff, user-work, residue,
validation, readiness, execution-automation, production/public, destructive
action, and form-burden gates without executing commands.

Generate the sample classification with:

```bash
PYTHONPATH=src python -m dev_cockpit.gate_classifier \
  --report-normalization samples/report_normalizations/adapter_manifest_v1_readback.json \
  --status-snapshot samples/status_snapshots/devcockpitcore_status.json \
  --adapter adapters/devcockpitcore.json \
  --output samples/gate_classifications/adapter_manifest_v1_gate.json \
  --pretty
```

The sample output lives at
`samples/gate_classifications/adapter_manifest_v1_gate.json`. The next roadmap
step is `validation-pack-v1`; there is still no execution automation.

## Validation pack

The validation pack runs a fixed allowlist of safe checks for this repository and
emits `validation_pack_result.v1` JSON. It validates source compilation, unit
tests, adapters, JSON samples, CLI help surfaces, git whitespace checks, repo
status, and report hygiene scans.

Generate the sample result with:

```bash
PYTHONPATH=src python -m dev_cockpit.validation_pack \
  --pack samples/validation_packs/devcockpitcore_validation_pack.json \
  --output samples/validation_packs/devcockpitcore_validation_pack_result.json \
  --pretty
```

Or use the built-in default pack:

```bash
PYTHONPATH=src python -m dev_cockpit.validation_pack --default --pretty
```

The sample input lives at
`samples/validation_packs/devcockpitcore_validation_pack.json`; the sample
result lives at
`samples/validation_packs/devcockpitcore_validation_pack_result.json`.

The validation pack is not a general runner. It does not execute adapter
`default_validation`, user-provided commands, report text, or arbitrary config
commands. The next roadmap step is `cross-project-smoke`; controlled runner
design remains later and out of scope for this slice.

## Cross-project smoke

The cross-project smoke observes configured project adapters with read-only
status snapshots and emits `cross_project_smoke_result.v1` JSON. DevCockpitCore
self-smoke is required; NLMYTGen, WritingPage, and ClipPipeGen are best-effort
sibling observations that become warnings or skipped rows when absent.

Generate the sample result with:

```bash
PYTHONPATH=src python -m dev_cockpit.cross_project_smoke \
  --smoke samples/cross_project_smokes/devcockpitcore_cross_project_smoke.json \
  --output samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json \
  --pretty
```

Or use the built-in default smoke:

```bash
PYTHONPATH=src python -m dev_cockpit.cross_project_smoke --default --pretty
```

The sample input lives at
`samples/cross_project_smokes/devcockpitcore_cross_project_smoke.json`; the
sample result lives at
`samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json`.

The smoke does not run tests, builds, renders, adapter `default_validation`, or
writeback in target repositories. The next roadmap step is
`controlled-runner-design`, still without execution automation in this slice.

## Controlled runner design

Controlled Runner Design V1 defines the capability ladder, command taxonomy,
authority boundaries, evidence contract, and future unlock gates for a possible
controlled runner. It is design-only.

The design packet lives at
`samples/controlled_runner_design/controlled_runner_design_v1.json`; the
readiness review lives at
`samples/controlled_runner_design/controlled_runner_readiness_review_v1.json`.
The supporting docs are `docs/design/CONTROLLED_RUNNER_DESIGN_V1.md` and
`docs/design/COPY_TRANSPORT_RESIDUE_V1.md`.

In that design slice, execution automation remained locked. It did not add a
runner implementation, adapter `default_validation` execution, scheduler,
credential handling, target-repository writeback, or controlled-runner probe
approval.

## Controlled runner probe

Controlled Runner Probe V1 implements one guarded C3 probe for the fixed
`status_snapshot_help` command key. It records before/after repo state, fixed
argv evidence, safety gates, timeout, redacted output excerpts, and a
`controlled_runner_probe_result.v1` sample.

Run the sample probe with:

```bash
PYTHONPATH=src python -m dev_cockpit.controlled_runner_probe \
  --probe samples/controlled_runner_probes/controlled_runner_probe_v1.json \
  --output samples/controlled_runner_probes/controlled_runner_probe_result_v1.json \
  --pretty
```

This is still not a general runner. Config cannot supply argv, shell flags,
executable paths, or arbitrary command strings, and C4-C6 remain locked.

## Controlled runner probe review

Controlled Runner Probe Review V1 reviews existing
`controlled_runner_probe_result.v1` evidence and emits
`controlled_runner_probe_review_result.v1`. The review can accept the C3 probe
or require a scoped fix without expanding runner capability.

Run the sample review with:

```bash
PYTHONPATH=src python -m dev_cockpit.controlled_runner_probe_review \
  --review samples/controlled_runner_probe_reviews/controlled_runner_probe_review_v1.json \
  --probe-result samples/controlled_runner_probes/controlled_runner_probe_result_v1_post_commit.json \
  --dirty-sample samples/controlled_runner_probes/controlled_runner_probe_result_v1.json \
  --output samples/controlled_runner_probe_reviews/controlled_runner_probe_review_result_v1.json \
  --pretty
```

C3 acceptance does not unlock C4-C6. The next step still requires a Supervisor
decision.

## C3 probe hardening

C3 Probe Hardening V1 defines the canonical C3 acceptance package. It uses the
post-commit clean probe result and canonical review result as the review surface,
while keeping the earlier dirty during-work sample as non-canonical context.

The hardening artifact lives at
`samples/c3_probe_hardening/c3_probe_hardening_v1.json`. C3 remains the only
execution capability; C4-C6 stay locked and any next step requires a Supervisor
decision.

## C3 second command design

C3 Second Command Design V1 evaluates whether a second fixed help/read-only C3
command should be proposed later. It is design-only and does not implement a
second command key.

The design packet lives at
`samples/c3_second_command_design/c3_second_command_design_v1.json`; supporting
docs live at `docs/design/C3_SECOND_COMMAND_DESIGN_V1.md`.

The recommendation is `adapters_validate_help` as a future Supervisor-reviewed
candidate only. The implemented C3 allowlist still contains exactly
`status_snapshot_help`, and C4-C6 remain locked.

## C3 second command help probe

C3 Second Command Help Probe V1 records bounded help/readback evidence for the
`adapters_validate_help` candidate. It proves the candidate can be represented as
fixed `python -m dev_cockpit.adapters --help` behavior without executing adapter
validation.

The help-probe packet lives at
`samples/c3_second_command_probe/c3_second_command_help_probe_v1.json`;
supporting docs live at `docs/design/C3_SECOND_COMMAND_HELP_PROBE_V1.md`.

This evidence still does not accept `adapters_validate_help` as a production C3
command key. The accepted controlled runner allowlist remains
`status_snapshot_help`, and C4-C6 remain locked.

## C3 second command acceptance review

C3 Second Command Acceptance Review V1 reviews the design and help-probe
evidence for `adapters_validate_help`. It compares three explicit options:
freeze C3 at one command, accept the candidate as help-only, or defer adoption
until C4 design.

The acceptance packet lives at
`samples/c3_second_command_acceptance/c3_second_command_acceptance_review_v1.json`;
supporting docs live at
`docs/design/C3_SECOND_COMMAND_ACCEPTANCE_REVIEW_V1.md`.

The recommendation is option B: accept `adapters_validate_help` as a help-only
second C3 command candidate. This still does not implement it as a production
command key, does not execute adapter validation, and does not unlock C4-C6.

## C3 second command candidate acceptance

C3 Second Command Candidate Acceptance V1 records option B as the selected
continuation state after the acceptance review. It preserves
`adapters_validate_help` as a help-only accepted candidate while keeping
`status_snapshot_help` as the only production accepted C3 command key.

The candidate-acceptance packet lives at
`samples/c3_second_command_candidate_acceptance/c3_second_command_candidate_acceptance_v1.json`;
supporting docs live at
`docs/design/C3_SECOND_COMMAND_CANDIDATE_ACCEPTANCE_V1.md`.

This state update does not implement `adapters_validate_help`, does not execute
adapter validation, does not add a command registry, and does not unlock C4-C6.

## C3 second command production probe

C3 Second Command Production Probe V1 adds `adapters_validate_help` as the
second production C3 help-only probe key. It maps only to fixed
`python -m dev_cockpit.adapters --help` behavior and does not run
`adapters --validate`.

Run the sample probe with:

```bash
PYTHONPATH=src python -m dev_cockpit.controlled_runner_probe \
  --probe samples/controlled_runner_probes/controlled_runner_probe_adapters_validate_help_v1.json \
  --output samples/controlled_runner_probes/controlled_runner_probe_adapters_validate_help_result_v1.json \
  --pretty
```

The production C3 command-key set is exactly `status_snapshot_help` and
`adapters_validate_help`. Config-supplied command strings, executable paths,
argv, args, and shell overrides remain rejected. C4-C6 remain locked.

## C3 second command hardening

C3 Second Command Hardening V1 canonicalizes the accepted two-command C3 state
without adding capability. The hardening packet lives at
`samples/c3_second_command_hardening/c3_second_command_hardening_v1.json`;
supporting docs live at `docs/design/C3_SECOND_COMMAND_HARDENING_V1.md`.

The hardened command set remains exactly `status_snapshot_help` and
`adapters_validate_help`. No third command key is accepted, `adapters_validate_help`
remains help-only, adapter validation remains outside `controlled_runner_probe`,
and C4-C6 remain locked until a separate Supervisor decision.

## C3 command set freeze and C4 design decision

C3 Command Set Freeze And C4 Design Decision V1 records the hardened two-command
C3 state as freeze-ready and recommends
`common-foundation-c4-scoped-runner-design-v1` only as a future design-only
route.

The decision packet lives at
`samples/c3_command_set_freeze_and_c4_design_decision/c3_command_set_freeze_and_c4_design_decision_v1.json`;
supporting docs live at
`docs/design/C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md`.

C4 implementation, third C3 commands, C5, C6, arbitrary execution, adapter
validation as controlled command behavior, schedulers, and target repository
writeback remain forbidden until separately authorized.

## C4 scoped runner design

C4 Scoped Runner Design V1 defines a design-only boundary for a possible future
scoped DevCockpitCore-local runner. It preserves C3 as the executable ceiling
and recommends `common-foundation-c4-scoped-runner-design-review-v1` as the next
review route.

The design artifact lives at
`samples/c4_scoped_runner_design/c4_scoped_runner_design_v1.json`; the companion
decision packet lives at
`samples/c4_scoped_runner_design/c4_scoped_runner_decision_packet_v1.json`;
supporting docs live at `docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md`.

This design adds no runner implementation, command execution, command keys,
target repository writeback, scheduler, cross-project runner, credentials,
external service handling, web UI, or C5/C6 unlock.

## C4 scoped runner design review

C4 Scoped Runner Design Review V1 accepts the C4 boundary as design-only
evidence and recommends
`common-foundation-c4-scoped-runner-design-hardening-v1` as the next safe route.

The review artifact lives at
`samples/c4_scoped_runner_design_review/c4_scoped_runner_design_review_v1.json`;
supporting docs live at
`docs/design/C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md`.

This review does not authorize C4 implementation. C3 remains the executable
ceiling, the production C3 command-key set remains exactly
`status_snapshot_help` and `adapters_validate_help`, and C5/C6 remain locked.

## Safety boundary

The status producer is a read-only observer. Against the target repository it
only runs read-only git inspection commands such as `status`, `branch`,
`rev-parse`, `rev-list`, and `log`. It does not execute validation commands; it
only carries their names into the snapshot with
`not_run_reason: observer_only_slice`.

Missing upstreams, missing sibling repositories, and missing optional project
documents are structured warnings rather than true stop conditions.

## Resume context

When resuming from another terminal or agent, start with:

- `docs/runtime-state.md`
- `docs/project-context.md`
- `docs/design/C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md`
- `docs/design/C4_SCOPED_RUNNER_DESIGN_V1.md`
- `docs/design/C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md`
- `docs/design/C3_SECOND_COMMAND_HARDENING_V1.md`
- `docs/handoffs/2026-06-29-c3-second-command-candidate-acceptance-v1.md`
- `docs/handoffs/2026-06-29-c3-second-command-acceptance-review-v1.md`
- `docs/handoffs/2026-06-29-c3-second-command-help-probe-v1.md`
- `docs/handoffs/2026-06-29-c3-second-command-design-v1.md`
- `docs/handoffs/2026-06-29-c3-probe-hardening-v1.md`
- `docs/handoffs/2026-06-26-status-producer-v1.md`

These files preserve the current artifact, validation evidence, safety boundary,
and recommended next entrances.

## Roadmap

1. status producer
2. adapter manifest
3. report normalizer
4. gate classifier
5. validation pack
6. cross-project smoke
7. controlled runner design
8. controlled runner probe
9. controlled runner probe review
10. C3 probe hardening
11. C3 second command design
12. C3 second command help probe
13. C3 second command acceptance review
14. C3 second command candidate acceptance
15. C3 second command production probe
16. C3 second command hardening
17. C3 command set freeze and C4 design decision
18. C4 scoped runner design
19. C4 scoped runner design review
