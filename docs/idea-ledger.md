# DevCockpitCore Idea Ledger

This file is an opportunity portfolio, not a current-state document or a
development control surface. An idea stays here until product evidence promotes
it, rejects it, or shows that it is no longer timely.

## Product Exploration

### Dashboard Architecture Comparison

Hypothesis: choosing the information architecture before production generator
work will prevent another cycle of large delivery followed by card, copy, and
layout correction.

The current intent pack compares three low-fidelity directions with identical
semantic values and wording:

| Direction | User value | Cost to explore | Main risk | Decision unlocked |
| --- | --- | --- | --- | --- |
| Priority Review Console | Gives a repeat operator one ordered queue, active decision, and nearby proof. | Low; one prototype already exists. | Can feel too much like an internal tool for an occasional reader. | Whether queue-led master/detail should drive production. |
| Narrative Status Brief | Lets a low-context reader understand state, changes, decisions, and proof in one reading order. | Low; static wireframe and copy hierarchy only. | Cross-project comparison may require more navigation. | Whether handoff readability should dominate repeated triage. |
| Lane And Project Matrix | Makes observer, automation, execution, and product readiness comparable across projects. | Low to medium; needs realistic multi-project sample rows. | Equal-weight cells can recreate the card-grid problem. | Whether portfolio comparison is the primary job of the surface. |

Research recommendation: A remains the strongest repeated-triage candidate,
but the pack now includes real low-fidelity B and C alternatives. Collect one
free-form user preference before selecting an architecture. Do not add
production dashboard cards or copy before that choice.

### Japanese-First Reading And Localization Boundary

Hypothesis: Japanese-first display copy and typography will improve first-scan
clarity for the actual operator without requiring a full localization platform.

The intent pack now validates Japanese-first labels, preserved English
technical identifiers, a Japanese-capable system font stack, and a working
English toggle at low fidelity. After the layout direction is selected, decide
which of those behaviors belongs in the production generator:

- Japanese-first labels with English technical identifiers preserved as
  secondary text.
- A system-font stack optimized for Japanese body copy, tabular numbers, and
  code paths.
- Content-length tests for Japanese and English headings before deciding
  whether a runtime language switch is justified.

Value: clearer review and fewer forced translations in the operator's head.
Cost: low for copy and font-stack prototypes; medium if a true localization
schema is later selected. Reversible: yes until generated artifact contracts
change.

Decision timing: after information architecture selection and before final
spacing, typography, or responsive tuning.

### Visual And Motion Language

Hypothesis: a small visual token system will produce more coherence than
incremental component polish.

Compare no more than two directions after layout selection:

- **Calm editorial:** warm-neutral dark surfaces, restrained accent color,
  generous type hierarchy, and motion limited to disclosure and focus.
- **Technical observatory:** cool charcoal surfaces, mono/data accents,
  explicit lane colors, and short motion that explains selection and evidence
  linkage.

Both directions should define contrast, status color semantics, font roles,
focus states, reduced-motion behavior, and print fallback before component
polish. Do not use decorative animation as a substitute for priority.

### Adjacent Operator Content

Hypothesis: the dashboard becomes more useful when it explains change and
decisions, not only current evidence counts.

Candidate content, in preferred order:

1. **Since last verified checkpoint:** code, evidence, and decision changes
   since the previous clean baseline.
2. **Decision queue:** questions that need human preference, separated from
   evidence-integrity and artifact-maintenance work.
3. **What can wait:** explicitly deprioritized warnings, locked lanes, and
   optional sibling conditions.
4. **Opportunity pulse:** a small number of evidence-backed product hypotheses
   with value and tradeoffs.

These should be derived from source evidence where possible. They must not
become another hand-authored brief card or an executable action surface.

### Evidence Freshness And Provenance

Hypothesis: every review surface should expose `source_commit`, `observed_at`,
and `freshness_state` close enough to the evidence route that historical
artifacts cannot be mistaken for current repository state.

The smallest useful implementation keeps generation commands and source paths
available, distinguishes fresh, stale, and unknown observations, and treats a
stale artifact as potentially valid history rather than current proof. This is
a product evidence feature, not a claim that one document controls repository
state.

## Maintenance Options

### C4 Probe Minimal Implementation Hardening

Value: canonicalize the accepted single C4 validation-pack probe without
widening capability. Documentation and tests should preserve the exact command
surface and its evidence contract.

### Validation Fixture Hygiene

Value: remove or reclassify the known historical pseudo-git-tag warning so a
clean validation run can be fully green. Preserve the ability to detect real
copy-transport residue; do not weaken the hygiene check merely to remove a
warning.

## Parked Or Rejected Routes

### Production Dashboard Rewrite Before Intent Selection

State: rejected. The previous sequence delivered a large card-derived surface,
then iterated through Latest Brief, editorial brief, and report-first
corrections before returning to layout research. Production work resumes only
after low-fidelity direction selection.

### Manually Maintained Wiki Status

State: rejected as a second authority. GitHub Wiki is enabled but empty. If a
Wiki, Page, Notion workspace, or other external surface is later selected, it
should display or mirror the Project Cockpit in one direction and expose source
commit and freshness.

### Third C3 Command Or Additional C4 Commands

State: locked. Reopening the accepted command set requires a new capability
decision and evidence path.

### General Runner, C5, Or C6

State: locked. A cross-project runner, scheduler, autonomous loop, credentials,
external services, notifications, and target-repository writeback require new
product design, stop controls, monitoring, and capability review.
