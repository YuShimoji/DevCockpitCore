from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.report_normalizer import (
    ReportNormalizationError,
    normalize_report,
    redact_absolute_user_paths,
)
from dev_cockpit.gate_classifier import classify_gate


SAMPLE_REPORT = """[ROUTE: DevCockpitCore | AGENT->SUPERVISOR | slice:common-foundation-adapter-manifest-v1 | turn:T+3 | target:ChatGPT Common Foundation supervisor thread | artifact_current:adapter-manifest-v1 | artifact_next:report-normalizer-v1 | reply:User/Supervisor | confidence:high]
[PROGRESS: FOUNDATION OBSERVER READINESS [########] 8/8 | current:adapter manifest v1 committed and pushed | next:report-normalizer-v1 | blocker:none | user_work:none]
[ACTION: decision=completed | now_owner:Supervisor | deliverable:adapter-manifest-v1 | trigger:none]
[STATUS: health=green | gates=8/8 | stop_class=NONE | estimate_agent:none | estimate_user:none]

**Outcome**
Completed adapter manifest v1 and pushed commit f5aa1c2 feat: define adapter manifest v1.

**What Changed**
Adapters now validate as adapter_manifest.v1.

**Commands And Results**
- Ran 10 tests.
- Final repo state was clean.
- Final parity check returned 0 0.

**Completion Matrix**
Slice Completion 8/8.

**Continuation State**
Next artifact is report-normalizer-v1.

**Handoff Gate**
pass; no blocked handoff required.

::git-stage{cwd="C:\\Users\\<redacted>\\DevCockpitCore"}
::git-commit{cwd="C:\\Users\\<redacted>\\DevCockpitCore"}
::git-push{cwd="C:\\Users\\<redacted>\\DevCockpitCore" branch="main"}
"""

CANONICAL_V65_REPORT = """[ROUTE: DevCockpitCore | WORKER->SUPERVISOR | thread:devcockpitcore-cross-project-supervision-packet-v1 | lane:CROSS_PROJECT_SUPERVISION | slice:authority-repair-and-project-aware-packet-v1 | artifact:cross-project-supervision-packet-v1 | reply:Web Supervisor | confidence:high]
[PROGRESS: supervision-packet [#####] 20/20 | current:integrity repair completed | next:H1-live-report-round-trip | blocker:none | user_work:none]
[STATUS: health=green | gates=20/20 | stop_class=NONE]

## 到達した状態

Integrity repair completed in commit 2a8673f and pushed. The worktree is clean and remote parity is 0 0.

## 残る不確実性と次の取っ掛かり

H1 requires authentic manifest-bound reports.

## 引き継ぎゲート

pass; no blocked handoff required.
"""

H2_REPORT_PATH = (
    ROOT
    / "artifacts"
    / "review"
    / "h2-authentic-single-report-round-trip-v1"
    / "source"
    / "AGENT_REPORT_H2_SOURCE_V1.md"
)


class ReportNormalizerTests(unittest.TestCase):
    def test_authentic_canonical_v7_identity_status_and_commit_boundary(self) -> None:
        result = normalize_report(
            H2_REPORT_PATH.read_text(encoding="utf-8"),
            input_path=H2_REPORT_PATH.relative_to(ROOT).as_posix(),
            generated_at="2026-07-19T15:12:24.4917578+09:00",
        )

        self.assertEqual("canonical_v7", result["routing"]["dialect"])
        self.assertEqual(
            "NLMYTGEN-H2-SOURCE-2026-07-19-01",
            result["routing"]["epoch"],
        )
        self.assertEqual(
            "d38075b97efabc99d1a23e8e0afafd5d44f1e2de",
            result["routing"]["base"],
        )
        self.assertEqual(result["routing"]["base"], result["routing"]["base_revision"])
        self.assertEqual(
            "nlmytgen-h2-authentic-source-export-v1",
            result["routing"]["thread_id"],
        )
        self.assertEqual("SUPERVISION_EVIDENCE_EXPORT", result["routing"]["lane_id"])
        self.assertTrue(result["status"]["reported"])
        self.assertFalse(result["status"]["blocked"])
        self.assertEqual("passed", result["status"]["acceptance"])
        self.assertEqual("none", result["status"]["stop"])
        self.assertEqual(
            "codex/new-banknote-successor-selective-integration-v1",
            result["status"]["branch"],
        )
        self.assertEqual("repository-root", result["status"]["worktree"])
        self.assertEqual([], result["normalized_outcome"]["commits"])
        self.assertEqual("green", result["health"]["normalization_status"])

    def test_base_and_source_revision_sha_are_not_commit_evidence(self) -> None:
        report = CANONICAL_V65_REPORT.replace(
            " | reply:Web Supervisor",
            " | epoch:DCC-TEST-01 | base:d38075b97efabc99d1a23e8e0afafd5d44f1e2de"
            " | reply:Web Supervisor",
        ).replace(
            "## 到達した状態",
            "## Source Binding\n\n- source_revision: "
            "d38075b97efabc99d1a23e8e0afafd5d44f1e2de observed checkout\n\n"
            "## 到達した状態",
        )

        result = normalize_report(report, generated_at="2026-07-19T00:00:00Z")

        self.assertEqual(
            ["2a8673f"],
            [commit["sha"] for commit in result["normalized_outcome"]["commits"]],
        )

    def test_canonical_v65_identity_round_trips_without_action(self) -> None:
        result = normalize_report(
            CANONICAL_V65_REPORT,
            generated_at="2026-07-13T08:00:00Z",
        )

        self.assertEqual("canonical_v6_5", result["routing"]["dialect"])
        self.assertEqual(
            "devcockpitcore-cross-project-supervision-packet-v1",
            result["routing"]["thread_id"],
        )
        self.assertEqual("CROSS_PROJECT_SUPERVISION", result["routing"]["lane_id"])
        self.assertEqual(
            "authority-repair-and-project-aware-packet-v1",
            result["routing"]["slice_id"],
        )
        self.assertEqual(
            "cross-project-supervision-packet-v1",
            result["routing"]["artifact_id"],
        )
        self.assertEqual("supervision-packet", result["progress"]["lane"])
        self.assertEqual("green", result["health"]["normalization_status"])
        self.assertNotIn("action header missing", result["health"]["warnings"])
        self.assertTrue(result["normalized_outcome"]["summary"])
        self.assertTrue(result["progress"]["current"])
        self.assertTrue(result["next"]["recommended_next_slice"])

        gate = classify_gate(result, generated_at="2026-07-13T08:00:00Z")
        self.assertNotEqual("unknown_review_required", gate["classification"]["decision"])
        self.assertEqual("NONE", gate["classification"]["stop_class"])

    def test_legacy_route_identity_remains_available(self) -> None:
        result = normalize_report(SAMPLE_REPORT, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual("legacy_compatible", result["routing"]["dialect"])
        self.assertEqual(
            "ChatGPT Common Foundation supervisor thread",
            result["routing"]["thread_id"],
        )
        self.assertEqual("FOUNDATION OBSERVER READINESS", result["routing"]["lane_id"])
        self.assertEqual("adapter-manifest-v1", result["routing"]["artifact_id"])

    def test_matching_canonical_and_legacy_aliases_are_accepted(self) -> None:
        report = CANONICAL_V65_REPORT.replace(
            " | reply:Web Supervisor",
            " | target:devcockpitcore-cross-project-supervision-packet-v1"
            " | artifact_current:cross-project-supervision-packet-v1"
            " | reply:Web Supervisor",
        )

        result = normalize_report(report, generated_at="2026-07-13T08:00:00Z")
        self.assertEqual("canonical_v6_5", result["routing"]["dialect"])

    def test_conflicting_canonical_and_legacy_identity_fails_closed(self) -> None:
        cases = {
            "thread": CANONICAL_V65_REPORT.replace(
                " | reply:Web Supervisor",
                " | target:different-thread | reply:Web Supervisor",
            ),
            "artifact_current": CANONICAL_V65_REPORT.replace(
                " | reply:Web Supervisor",
                " | artifact_current:different-artifact | reply:Web Supervisor",
            ),
            "duplicate_thread": CANONICAL_V65_REPORT.replace(
                " | lane:CROSS_PROJECT_SUPERVISION",
                " | thread:different-thread | lane:CROSS_PROJECT_SUPERVISION",
            ),
        }
        for name, report in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(ReportNormalizationError):
                    normalize_report(report, generated_at="2026-07-13T08:00:00Z")

    def test_matching_current_artifact_does_not_mask_conflicting_action_deliverable(self) -> None:
        report = CANONICAL_V65_REPORT.replace(
            " | reply:Web Supervisor",
            " | artifact_current:cross-project-supervision-packet-v1"
            " | reply:Web Supervisor",
        ).replace(
            "[STATUS:",
            "[ACTION: decision=completed | deliverable:different-artifact]\n[STATUS:",
        )

        with self.assertRaises(ReportNormalizationError):
            normalize_report(report, generated_at="2026-07-13T08:00:00Z")

    def test_conflicting_legacy_current_artifact_claims_fail_closed(self) -> None:
        report = SAMPLE_REPORT.replace(
            "deliverable:adapter-manifest-v1",
            "deliverable:different-artifact",
        )

        with self.assertRaises(ReportNormalizationError):
            normalize_report(report, generated_at="2026-01-01T00:00:00Z")

    def test_route_progress_action_status_parse(self) -> None:
        result = normalize_report(SAMPLE_REPORT, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["schema_version"], "report_normalization.v1")
        self.assertEqual(result["routing"]["route"], "DevCockpitCore")
        self.assertEqual(result["routing"]["direction"], "AGENT->SUPERVISOR")
        self.assertEqual(result["routing"]["slice"], "common-foundation-adapter-manifest-v1")
        self.assertEqual(result["progress"]["done"], 8)
        self.assertEqual(result["progress"]["total"], 8)
        self.assertEqual(result["action"]["decision"], "completed")
        self.assertEqual(result["status"]["gates_done"], 8)
        self.assertEqual(result["status"]["gates_total"], 8)

    def test_partial_report_does_not_crash(self) -> None:
        result = normalize_report("**Outcome**\nPartial report only.\n", generated_at="2026-01-01T00:00:00Z")
        self.assertIsNone(result["routing"]["route"])
        self.assertEqual(result["sections"]["outcome"], "Partial report only.")
        self.assertEqual(result["health"]["normalization_status"], "yellow")
        self.assertEqual(
            ["current_state", "next_state"],
            result["health"]["unknown_fields"],
        )

    def test_markdown_sections_and_commit_reference(self) -> None:
        result = normalize_report(SAMPLE_REPORT, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["sections"]["outcome"].splitlines()[0], "Completed adapter manifest v1 and pushed commit f5aa1c2 feat: define adapter manifest v1.")
        self.assertIn("Ran 10 tests.", result["sections"]["commands_and_results"])
        self.assertEqual(
            result["normalized_outcome"]["commits"],
            [{"sha": "f5aa1c2", "message": "feat: define adapter manifest v1"}],
        )
        self.assertTrue(result["normalized_outcome"]["pushed"])
        self.assertEqual(result["normalized_outcome"]["worktree"], "clean")
        self.assertEqual(result["normalized_outcome"]["remote_parity"], "0 0")
        self.assertEqual(result["normalized_outcome"]["tests"], [{"count": 10}])

    def test_handoff_false_pass_extraction(self) -> None:
        result = normalize_report(SAMPLE_REPORT, generated_at="2026-01-01T00:00:00Z")
        self.assertFalse(result["handoff"]["handoff_gate"])
        self.assertFalse(result["handoff"]["supervisor_should_generate_prompt"])

    def test_pseudo_git_tag_residue_detection(self) -> None:
        result = normalize_report(SAMPLE_REPORT, generated_at="2026-01-01T00:00:00Z")
        self.assertTrue(result["residue_audit"]["contains_pseudo_git_tags"])
        self.assertEqual(
            result["residue_audit"]["pseudo_git_tags"],
            ["::git-commit", "::git-push", "::git-stage"],
        )

    def test_paste_ready_prompt_residue_detection_without_prompt_output(self) -> None:
        prompt_text = """[PASTE TARGET: Codex/Example]
[CONTRACT: v2.1 | output_type=SUPERVISOR_PROMPT]
Goal Stack:
Allowed scope:
Report format:
"""
        result = normalize_report(prompt_text, generated_at="2026-01-01T00:00:00Z")
        payload = json.dumps(result)
        self.assertTrue(result["residue_audit"]["contains_paste_ready_prompt"])
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)

    def test_local_absolute_path_detection_and_redaction(self) -> None:
        text = "**Outcome**\nOpened C:\\Users\\example\\DevCockpitCore\\README.md.\n"
        self.assertEqual(
            redact_absolute_user_paths(text),
            "**Outcome**\nOpened C:\\Users\\<redacted>\\DevCockpitCore\\README.md.\n",
        )
        result = normalize_report(text, generated_at="2026-01-01T00:00:00Z")
        self.assertTrue(result["residue_audit"]["contains_absolute_user_paths"])
        self.assertFalse(result["residue_audit"]["absolute_user_paths_redacted"])
        self.assertIn("C:\\Users\\<redacted>\\DevCockpitCore", result["sections"]["outcome"])
        self.assertNotIn("example", json.dumps(result))

    def test_required_top_level_keys(self) -> None:
        result = normalize_report(SAMPLE_REPORT, input_path="sample.txt", generated_at="2026-01-01T00:00:00Z")
        for key in (
            "schema_version",
            "generated_at",
            "producer",
            "source",
            "routing",
            "progress",
            "action",
            "status",
            "sections",
            "normalized_outcome",
            "handoff",
            "next",
            "residue_audit",
            "health",
        ):
            self.assertIn(key, result)

    def test_sample_input_normalizes_to_json(self) -> None:
        sample = ROOT / "samples" / "reports" / "agent_report_adapter_manifest_v1_redacted.txt"
        if not sample.exists():
            self.skipTest("sample report has not been added")
        result = normalize_report(sample.read_text(encoding="utf-8"), input_path=sample.as_posix(), generated_at="2026-01-01T00:00:00Z")
        payload = json.dumps(result)
        self.assertEqual(json.loads(payload)["schema_version"], "report_normalization.v1")
        self.assertFalse(result["residue_audit"]["contains_paste_ready_prompt"])


if __name__ == "__main__":
    unittest.main()
