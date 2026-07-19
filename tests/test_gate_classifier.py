from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.gate_classifier import classify_gate
from dev_cockpit.report_normalizer import normalize_report


H2_REPORT_PATH = (
    ROOT
    / "artifacts"
    / "review"
    / "h2-authentic-single-report-round-trip-v1"
    / "source"
    / "AGENT_REPORT_H2_SOURCE_V1.md"
)


class GateClassifierTests(unittest.TestCase):
    def test_authentic_report_postfix_negation_does_not_create_true_stop(self) -> None:
        normalization = normalize_report(
            H2_REPORT_PATH.read_text(encoding="utf-8"),
            input_path=H2_REPORT_PATH.relative_to(ROOT).as_posix(),
            generated_at="2026-07-19T15:12:24.4917578+09:00",
        )

        result = classify_gate(
            normalization,
            generated_at="2026-07-19T15:12:24.4917578+09:00",
        )

        self.assertEqual("green", result["gates"]["destructive_action_gate"]["status"])
        self.assertEqual("yellow", result["health"]["classification_status"])
        self.assertEqual("integrate_and_continue", result["classification"]["decision"])
        self.assertEqual("INTEGRATE_AND_CONTINUE", result["classification"]["stop_class"])
        self.assertEqual([], result["health"]["blockers"])
        self.assertEqual("yellow", normalization["status"]["health"])
        self.assertEqual("green", normalization["health"]["normalization_status"])

    def test_local_destructive_negations_remain_safe(self) -> None:
        for wording in (
            "rebase_stash_reset_clean: not performed",
            "reset was not performed",
            "no force push was used",
        ):
            with self.subTest(wording=wording):
                report = _base_report()
                report["sections"]["extra"] = {"git_state": wording}
                result = classify_gate(report, generated_at="2026-07-19T00:00:00Z")
                self.assertEqual(
                    "green",
                    result["gates"]["destructive_action_gate"]["status"],
                )

    def test_actual_destructive_directives_remain_red(self) -> None:
        for wording in (
            "run git reset --hard",
            "rebase the branch",
            "stash user changes",
            "force push required",
            "reset was not performed, but force push required",
            "no force push was used; run git reset --hard",
        ):
            with self.subTest(wording=wording):
                report = _base_report()
                report["sections"]["extra"] = {"next_command": wording}
                result = classify_gate(report, generated_at="2026-07-19T00:00:00Z")
                self.assertEqual(
                    "red",
                    result["gates"]["destructive_action_gate"]["status"],
                )
                self.assertEqual("TRUE_STOP", result["classification"]["stop_class"])

    def test_green_completed_pushed_clean_parity_report(self) -> None:
        result = classify_gate(_base_report(), generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["schema_version"], "gate_classification.v1")
        self.assertEqual(result["gates"]["push_gate"]["status"], "green")
        self.assertEqual(result["gates"]["validation_gate"]["status"], "green")
        self.assertEqual(result["classification"]["decision"], "supervisor_prompt_needed")
        self.assertEqual(result["classification"]["stop_class"], "NONE")
        self.assertTrue(result["classification"]["continue_allowed"])
        self.assertTrue(result["classification"]["commit_push_accepted"])

    def test_pseudo_git_tag_residue_is_hygiene_warning_not_true_stop(self) -> None:
        report = _base_report()
        report["residue_audit"]["contains_pseudo_git_tags"] = True
        report["residue_audit"]["pseudo_git_tags"] = ["::git-stage"]
        result = classify_gate(report, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["gates"]["residue_gate"]["status"], "yellow")
        self.assertEqual(result["classification"]["stop_class"], "NONE")
        self.assertTrue(result["classification"]["continue_allowed"])
        self.assertEqual(result["residue_findings"]["recommended_handling"], "hygiene warning; do not treat pseudo tags as a true blocker")

    def test_paste_ready_prompt_residue_is_contract_warning(self) -> None:
        report = _base_report()
        report["residue_audit"]["contains_paste_ready_prompt"] = True
        result = classify_gate(report, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["gates"]["residue_gate"]["status"], "yellow")
        self.assertIn("contract warning", result["residue_findings"]["recommended_handling"])
        self.assertEqual(result["classification"]["stop_class"], "NONE")

    def test_user_work_none_stays_no_user_action(self) -> None:
        result = classify_gate(_base_report(), generated_at="2026-01-01T00:00:00Z")
        self.assertFalse(result["classification"]["user_work_required"])
        self.assertEqual(result["gates"]["user_work_gate"]["status"], "green")

    def test_user_work_auth_requires_user_action(self) -> None:
        report = _base_report()
        report["progress"]["user_work"] = "auth required"
        result = classify_gate(report, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["classification"]["decision"], "blocked_auth")
        self.assertEqual(result["classification"]["stop_class"], "USER_AUTH_REQUIRED")
        self.assertTrue(result["classification"]["user_work_required"])

    def test_user_work_manual_decision_requires_user_action(self) -> None:
        report = _base_report()
        report["progress"]["user_work"] = "manual decision required"
        result = classify_gate(report, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["classification"]["decision"], "user_action_required")
        self.assertTrue(result["classification"]["user_work_required"])

    def test_handoff_false_pass_classification(self) -> None:
        result = classify_gate(_base_report(), generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["gates"]["handoff_gate"]["status"], "green")
        self.assertFalse(result["classification"]["handoff_required"])

    def test_handoff_true_classification(self) -> None:
        report = _base_report()
        report["handoff"]["handoff_gate"] = True
        result = classify_gate(report, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["classification"]["decision"], "handoff_required")
        self.assertEqual(result["classification"]["stop_class"], "HANDOFF_REQUIRED")
        self.assertTrue(result["classification"]["handoff_required"])

    def test_validation_failure_classification(self) -> None:
        report = _base_report()
        report["sections"]["validation"] = ["unit tests failed"]
        result = classify_gate(report, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["classification"]["decision"], "blocked_validation")
        self.assertEqual(result["classification"]["stop_class"], "VALIDATION_FAILED")
        self.assertEqual(result["gates"]["validation_gate"]["status"], "red")

    def test_missing_optional_status_snapshot_does_not_crash(self) -> None:
        result = classify_gate(_base_report(), generated_at="2026-01-01T00:00:00Z")
        self.assertIn("optional status snapshot not provided", result["source"]["warnings"])
        self.assertIn("optional adapter manifest not provided", result["source"]["warnings"])

    def test_partial_normalized_report_does_not_crash(self) -> None:
        result = classify_gate({"schema_version": "report_normalization.v1"}, generated_at="2026-01-01T00:00:00Z")
        self.assertIn(
            result["classification"]["decision"],
            {"integrate_and_continue", "unknown_review_required"},
        )
        self.assertIn(result["health"]["classification_status"], {"yellow", "red"})

    def test_execution_automation_overclaim_detected(self) -> None:
        report = _base_report()
        report["residue_audit"]["contains_execution_automation_overclaim"] = True
        result = classify_gate(report, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["classification"]["decision"], "blocked_safety_boundary")
        self.assertTrue(result["classification"]["execution_automation_scope_violation"])

    def test_runner_scheduler_wording_in_wrong_slice_detected(self) -> None:
        report = _base_report()
        report["sections"]["outcome"] = "Added scheduler for future automation."
        result = classify_gate(report, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["gates"]["execution_automation_gate"]["status"], "red")
        self.assertEqual(result["classification"]["stop_class"], "SAFETY_BOUNDARY")

    def test_classifier_does_not_emit_paste_ready_next_agent_prompt(self) -> None:
        report = _base_report()
        report["residue_audit"]["contains_paste_ready_prompt"] = True
        result = classify_gate(report, generated_at="2026-01-01T00:00:00Z")
        payload = json.dumps(result)
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)
        self.assertNotIn("SUPERVISOR->AGENT", payload)

    def test_sample_gate_classification_required_top_level_keys(self) -> None:
        sample = ROOT / "samples" / "report_normalizations" / "adapter_manifest_v1_readback.json"
        report = json.loads(sample.read_text(encoding="utf-8"))
        result = classify_gate(report, report_normalization_path=sample.as_posix(), generated_at="2026-01-01T00:00:00Z")
        for key in (
            "schema_version",
            "producer",
            "generated_at",
            "source",
            "routing",
            "input_summary",
            "classification",
            "gates",
            "residue_findings",
            "readiness",
            "next",
            "health",
        ):
            self.assertIn(key, result)


def _base_report() -> dict[str, object]:
    return {
        "schema_version": "report_normalization.v1",
        "routing": {
            "route": "DevCockpitCore",
            "direction": "AGENT->SUPERVISOR",
            "slice": "common-foundation-report-normalizer-v1",
            "artifact_current": "report-normalizer-v1",
            "artifact_next": "gate-classifier-v1",
            "confidence": "high",
        },
        "progress": {
            "lane": "FOUNDATION AUTOMATION READINESS",
            "done": 4,
            "total": 7,
            "current": "report normalizer v1 committed and pushed",
            "next": "gate-classifier-v1",
            "blocker": "none",
            "user_work": "none",
        },
        "action": {
            "decision": "completed",
            "now_owner": "Supervisor",
            "deliverable": "report-normalizer-v1",
            "trigger": "none",
        },
        "status": {
            "health": "green",
            "gates_done": 8,
            "gates_total": 8,
            "stop_class": "NONE",
        },
        "sections": {
            "outcome": "Completed report normalizer v1 and pushed commit f2149df feat: add report normalizer v1. Final repo state was clean with remote parity 0 0.",
            "commands_and_results": ["unittest discover passed with 19 tests"],
            "validation": ["validation passed"],
            "user_side_work": "none",
            "agent_side_work": "none",
            "handoff_gate": "pass; no blocked handoff required",
            "extra": {},
        },
        "normalized_outcome": {
            "decision": "completed",
            "commits": [{"sha": "f2149df", "message": "feat: add report normalizer v1"}],
            "pushed": True,
            "worktree": "clean",
            "remote_parity": "0 0",
            "tests": [{"count": 19}],
        },
        "handoff": {
            "handoff_gate": False,
            "supervisor_should_generate_prompt": False,
        },
        "next": {
            "artifact_next": "gate-classifier-v1",
            "recommended_next_slice": "gate-classifier-v1",
            "next_owner": "Supervisor",
            "minimal_next_task": "Implement gate classifier v1.",
        },
        "residue_audit": {
            "contains_paste_ready_prompt": False,
            "contains_pseudo_git_tags": False,
            "contains_absolute_user_paths": False,
            "absolute_user_paths_redacted": False,
            "contains_runner_or_scheduler_instruction": False,
            "contains_execution_automation_overclaim": False,
            "contains_production_readiness_overclaim": False,
            "notes": [],
        },
        "health": {
            "normalization_status": "green",
            "warnings": [],
            "stop_class": "NONE",
        },
    }


if __name__ == "__main__":
    unittest.main()
