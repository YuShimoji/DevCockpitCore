# Decision Log

## 2026-07-10: Adopt Project Capsule without overwriting repo-specific AGENTS

Decision:

- Add the re-kickstart Project Capsule docs and artifact/screenshot placeholders
  from the kit.
- Do not overwrite `AGENTS.md`; the existing file is repo-specific and contains
  the DevCockpitCore safety boundary.
- Treat the missing physical `PROJECT_REPO_TEMPLATE/` directory as stale kit
  packaging and use the inline template content in `ALL_FILES_INLINE.md`.

Reason:

- The user asked to place the template contents without overwriting existing
  files and to fill the kit placeholders from repo facts.
- Project-local instructions explicitly forbid growing `AGENTS.md` into
  procedures, status, roadmap, closeout templates, or history.

Effect:

- Future turns have `docs/VALIDATION.md`, `docs/ROADMAP.md`, `docs/RUNTIME_STATE.md`,
  and `docs/ARTIFACT_INDEX.md` as compact Project Capsule surfaces.
- Existing lowercase authority docs remain intact and continue to preserve the
  active DevCockpitCore lane.

Evidence:

- `git fetch --prune origin` and `git pull --ff-only origin main` updated the
  repo to `dc6b5bb docs: add layout research resume handoff`.
- `HEAD...@{u}` was `0 0` after the fast-forward.
- `artifacts/review/2026-07-10-rekickstart-validation-pack.json` was generated
  as material evidence for this BUILD turn.

Reversal condition:

- If Project Capsule duplication becomes noisy, collapse the uppercase capsule
  docs into the existing lowercase authority docs while preserving validation
  commands and artifact index semantics.
