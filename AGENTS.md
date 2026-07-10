# DevCockpitCore Agent Notes

DevCockpitCore is observer-first. Keep the foundation lanes separate:

- Foundation Observer Readiness: status schema, status producer, adapter config,
  tests, and docs.
- Foundation Automation Readiness: report normalization, gate classification,
  validation packs, and reusable project adapters.
- Execution Automation Readiness: controlled runner design only after observer
  slices are stable.
- Project/Product Readiness: project-specific readiness stays outside this
  repository unless represented through adapters or snapshots.

## Delivery model

Treat a prompt as an outcome envelope, not as permission for only one small
file change. Within the requested outcome and the capability boundaries below,
continue through investigation, implementation, related fixes, local
validation, cleanup, and current-state documentation. A completed intermediate
step does not require a new Supervisor prompt when the remaining work is still
inside the same envelope.

Do not stop for reversible repository-local decisions, expected warning states,
missing optional upstreams or sibling repositories, routine test fixes, or
documentation synchronization. Make a reasonable assumption, keep the change
bounded, and record any meaningful uncertainty in the completion report.

Pause only when one of these gates is reached:

- **Authority gate:** destructive or difficult-to-reverse work, a new
  dependency, a database/authentication/API contract change, credentials or an
  external side effect, target-repository writeback, execution-capability
  expansion, or a material specification conflict.
- **Intent gate:** a subjective, expensive-to-rework direction such as
  information architecture, layout, visual identity, motion language, copy
  tone, or localization scope. Before production implementation, present two
  or three materially different low-cost directions, their tradeoffs, and one
  recommendation. After the user selects a direction, finish the agreed build
  and verification without asking for permission at each substep.

Progress updates are non-blocking checkpoints. Do not turn routine status
reporting into a sequence of approval requests.

## Exploration and closure

At orientation and before closure, check for repeated manual friction, a useful
adjacent opportunity, and an assumption that should be challenged. When
relevant, surface at most two creative proposals with user value, cost,
reversibility, and why the decision is timely. Do not silently implement a
high-cost subjective proposal before the intent gate.

`docs/PROJECT_COCKPIT.md` is the human-readable current-state authority. Update
it whenever the active outcome, lane state, next decision, validation state, or
material uncertainty changes. Keep `docs/runtime-state.md` as its compact
machine-facing projection. Keep `docs/project-context.md` durable rather than
copying live status into it. Use `docs/decision-log.md` only for durable
decisions, `docs/idea-ledger.md` for opportunities and rejected directions, and
create a handoff only for an actual transfer that cannot be resumed from the
cockpit and the active design artifact.

A completion report should explain the delivered outcome, why it changes the
workflow or decision, the verification performed, remaining uncertainty, and
two to four next entrances that remove different bottlenecks.

For the status producer slice, do not add an execution loop, autonomous runner,
scheduler, external notification integration, auto-render workflow, web server,
database, credential handling, or target-repository writeback.

Prefer standard-library Python and local tests. Missing upstreams, missing
sibling repositories, and absent optional project docs should become structured
warnings, not hard stops.
