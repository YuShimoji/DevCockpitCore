# Artifact Index

| Date | Type | Path / URL | Purpose | How to reproduce | Quality notes | Next improvement |
|---|---|---|---|---|---|---|
| 2026-07-11 | status-snapshot | `artifacts/review/2026-07-11-main-status-snapshot-v2.json` | second live verification of main/parity/worktree state | `$env:PYTHONPATH = "src"; python -m dev_cockpit.status_snapshot --repo . --adapter adapters/devcockpitcore.json --output artifacts/review/2026-07-11-main-status-snapshot-v2.json --pretty` | main at `dc6b5bb`, parity `0 0`, dirty-worktree warning, no blocking stop class | regenerate after the PR/authority decision |
| 2026-07-11 | validation-pack-result | `artifacts/review/2026-07-11-resync-validation-pack-v2.json` | repeated live development-readiness evidence after a new fetch/pull pass | `$env:PYTHONPATH = "src"; python -m dev_cockpit.validation_pack --default --output artifacts/review/2026-07-11-resync-validation-pack-v2.json --pretty` | Python 3.12.13; 16 checks done; 15 pass, 1 known fixture warning, 0 failed; 305 tests passed in 88.046s | rerun on the repaired PR landing candidate |
| 2026-07-11 | status-snapshot | `artifacts/review/2026-07-11-main-status-snapshot.json` | live main/parity/worktree evidence for supervisor handoff | `$env:PYTHONPATH = "src"; python -m dev_cockpit.status_snapshot --repo . --adapter adapters/devcockpitcore.json --output artifacts/review/2026-07-11-main-status-snapshot.json --pretty` | main at `dc6b5bb`, parity `0 0`, dirty-worktree warning, no blocking stop class | regenerate after the authority/PR landing decision |
| 2026-07-11 | validation-pack-result | `artifacts/review/2026-07-11-remote-sync-validation-pack.json` | fresh development-readiness evidence after remote sync | `$env:PYTHONPATH = "src"; python -m dev_cockpit.validation_pack --default --output artifacts/review/2026-07-11-remote-sync-validation-pack.json --pretty` | 16 checks done; 15 pass, 1 known pseudo-git-tag fixture warning, 0 failed; 305 tests passed | rerun on the repaired PR landing candidate |
| 2026-07-10 | validation-pack-result | `artifacts/review/2026-07-10-rekickstart-validation-pack.json` | material evidence for re-kickstart BUILD | `PYTHONPATH=src python -m dev_cockpit.validation_pack --default --output artifacts/review/2026-07-10-rekickstart-validation-pack.json --pretty` | 16 checks done; 15 pass, 1 known pseudo-git-tag fixture warning, 0 failed | rerun after committing or after the next implementation slice |
| 2026-07-07 | layout-prototype | `samples/dashboard/layout_research/devcockpitcore_layout_prototype.html` | active low-fidelity Priority Review Console review surface | committed artifact from `dashboard-layout-research-and-prototype-v1` | static, no scripts, review-only | accept/reject before production generator work |
| 2026-07-07 | generated-dashboard | `samples/dashboard/devcockpitcore_dashboard.html` | current production dashboard evidence | `PYTHONPATH=src python -m dev_cockpit.dashboard --output samples/dashboard/devcockpitcore_dashboard.html` | evidence for audit, not next design target | redesign only after layout acceptance |

## Rule

Generated videos, texts, images, previews, validation logs, and review outputs
must be indexed here before a BUILD turn is reported complete with artifact
evidence.
