# Controlled Runner Design V1

## Purpose

`common-foundation-controlled-runner-design-v1` defines the architecture,
authority boundaries, capability ladder, evidence contract, stop conditions, and
future unlock gates for a possible controlled runner. It is intentionally a
design-only slice.

Execution automation remains locked. This slice does not create a runnable
command runner, command registry, subprocess orchestrator, scheduler, background
loop, notification integration, auto-render workflow, credential handler, web UI,
database, target-repository writeback, or production/public action.

## Design-Only Status

The durable design packet is
`samples/controlled_runner_design/controlled_runner_design_v1.json` with
`schema_version: controlled_runner_design.v1`,
`implementation_status: design_only`, and
`execution_automation_readiness: locked`.

The companion review artifact is
`samples/controlled_runner_design/controlled_runner_readiness_review_v1.json`.
It records that `controlled-runner-probe-v1` is not approved by this slice and
requires a later Supervisor decision.

## Why Implementation Is Not Allowed

DevCockpitCore is observer-first. The previous foundation slices now provide
status snapshots, adapter manifests, report normalization, gate classification,
validation packs, and cross-project smoke observations. None of those artifacts
grant authority to run arbitrary commands or write target repositories.

Implementing a runner in this slice would collapse the distinction between
Foundation Automation Readiness and Execution Automation Readiness. The correct
output is a design contract that a future prompt can review, not executable
automation.

## Capability Ladder

The ladder is encoded in the design packet:

- `C0 observer_only`: current. Read-only repository and artifact observation.
- `C1 fixed_validation_pack`: current. DevCockpitCore-local fixed checks by
  allowlisted keys.
- `C2 command_proposal_only`: design-only. Classify and propose a command
  without executing it.
- `C3 guarded_single_command_probe`: locked. A future one-command no-op or
  help/read-only probe only after Supervisor approval.
- `C4 scoped_repo_local_runner`: locked. DevCockpitCore-local fixed-command
  runner after accepted probe evidence.
- `C5 cross_project_runner`: locked. Requires separate design, user approval,
  per-project write contract, and rollback plan.
- `C6 scheduler_or_autonomy_loop`: locked. Requires separate autonomy design,
  user approval, monitoring, stop controls, and credential policy.

## Command Class Taxonomy

The design packet classifies command requests into:

- `read_only_observation`
- `fixed_repo_local_validation`
- `repo_local_writeback`
- `target_repo_read_only_observation`
- `target_repo_writeback`
- `destructive_git`
- `network_or_external_service`
- `credential_or_secret_access`
- `render_or_media_generation`
- `publish_or_public_action`
- `scheduler_or_background_loop`

Each class records examples, risk, whether it is allowed in the current slice,
the future unlock gate, required owner, and stop class if requested now.

## Authority Boundaries

Supervisor-owned decisions include selecting the next slice, approving or
rejecting a future probe, and accepting warning-only evidence.

Agent-owned decisions include maintaining design docs, running DevCockpitCore
validation, producing design-only samples, and refusing unsafe implementation
drift.

User-owned decisions include credentials, external services, destructive git,
production or public action, and cross-repository writeback.

Forbidden until explicit unlock: arbitrary command execution, subprocess runner,
scheduler or background loop, target repository writeback, credential access,
and publishing.

## Stop Conditions

Stop rather than continue when a request requires destructive git, force push,
reset, rebase, stash, credentials, external authorization, target repository
writeback, arbitrary command strings from config, a runnable runner module, or
safe redaction cannot be maintained.

## Future Unlock Gates

A future `controlled-runner-probe-v1` may only be considered after a Supervisor
accepts this design packet and issues a new prompt. The design packet requires:

- fixed command keys only.
- no arbitrary command strings from config.
- subprocess shell option remains false.
- cwd confinement.
- timeout.
- output truncation and redaction.
- before/after git status.
- rollback note.
- no cross-repo writeback.
- no credentials.
- no network or external service.
- no scheduler or background loop.

## Evidence Contract

Any future probe evidence must include:

- `run_id`
- `command_key`
- `command_class`
- `cwd`
- `args_policy`
- `allowlist_source`
- `start_time`
- `end_time`
- `duration`
- `exit_code`
- `stdout_excerpt`
- `stderr_excerpt`
- `redactions_applied`
- `before_state`
- `after_state`
- `artifacts_written`
- `safety_gates`
- `stop_class`

Output excerpts must be truncated and redacted. Before/after state is required
even for no-op or help/read-only commands.

## Rollback And State Expectations

Observer and proposal-only capabilities should not require rollback because they
do not write target repositories. DevCockpitCore-local generated artifacts must
be reviewable through normal git diff. Cross-project writes require a separate
per-project rollback plan and are not unlocked by this design.

## Adapter default_validation

Adapter `default_validation` remains declarative. A future runner must not
execute adapter validation strings unless a later slice defines a fixed command
registry and explicit approval path.

## Relationship To Existing Artifacts

`status_snapshot.v1` provides read-only repo state. `adapter_manifest.v1`
describes project context and validation hints. `report_normalization.v1` and
`gate_classification.v1` interpret returned reports and safety boundaries.
`validation_pack_result.v1` provides fixed local validation evidence.
`cross_project_smoke_result.v1` shows read-only multi-project observation.

Controlled Runner Design V1 consumes these as governance inputs only.

## Copy-Transport Residue Rule

See `docs/design/COPY_TRANSPORT_RESIDUE_V1.md`. UI transport markers copied at
the tail of a pasted report are classified separately from Agent-authored report
residue. Authored samples and committed artifacts should still avoid unexplained
pseudo action markers.

## v2.3 Gate Separation

AGENT_REPORT v2.3 should report the completed slice in `current_slice_gates`.
When the next slice has not started, `next_slice_gates` should remain
`[--------] 0/8` or the equivalent empty meter for that denominator.

Completion Matrix meter cells should include a compact bracketed meter plus a
denominator, such as `[#] 1/1`. Visual Summary meters should use compact forms
such as `[~~~~~] 5/5`, not spaced forms.

## Future Probe Scope

If a future Supervisor prompt approves `controlled-runner-probe-v1`, its maximum
scope should be one fixed DevCockpitCore-local no-op or help/read-only command.
It must not include target-repository writeback, credentials, network calls,
scheduler/background loops, destructive git, or production/public action.

## What This Does Not Do

Controlled Runner Design V1 does not implement a runner, execute arbitrary
commands, run adapter validation strings, schedule work, send notifications,
auto-render media, manage credentials, open a web UI, store state in a database,
write target repositories, publish content, or approve a future probe.
