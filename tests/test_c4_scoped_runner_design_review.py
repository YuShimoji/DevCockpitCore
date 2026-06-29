from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEYS


REVIEW = (
    ROOT
    / "samples"
    / "c4_scoped_runner_design_review"
    / "c4_scoped_runner_design_review_v1.json"
)
REVIEW_DOC = ROOT / "docs" / "design" / "C4_SCOPED_RUNNER_DESIGN_REVIEW_V1.md"
SOURCE_ROOT = ROOT / "src" / "dev_cockpit"


class C4ScopedRunnerDesignReviewTests(unittest.TestCase):
    def test_review_json_parses_and_has_required_top_level_keys(self) -> None:
        data = _review()
        required = {
            "schema_version",
            "generated_at",
            "project_key",
            "reviewed_commit",
            "reviewed_artifact",
            "source_design_artifact",
            "source_decision_packet",
            "current_executable_ceiling",
            "review_decision",
            "evidence_checks",
            "known_warnings",
            "allowed_next_routes",
            "forbidden_next_routes",
            "summary",
        }
        self.assertEqual(data["schema_version"], "c4_scoped_runner_design_review.v1")
        self.assertTrue(required.issubset(data))

    def test_review_decision_accepts_design_only_boundary(self) -> None:
        decision = _review()["review_decision"]
        self.assertEqual(decision["decision"], "accepted")
        self.assertEqual(
            decision["recommended_next_slice"],
            "common-foundation-c4-scoped-runner-design-hardening-v1",
        )
        self.assertTrue(decision["supervisor_should_generate_prompt"])
        self.assertNotIn("implementation", decision["recommended_next_slice"])

    def test_c3_executable_ceiling_remains_exactly_two_help_keys(self) -> None:
        ceiling = _review()["current_executable_ceiling"]
        expected = ["status_snapshot_help", "adapters_validate_help"]
        self.assertEqual(ceiling["capability_level"], "C3")
        self.assertEqual(ceiling["production_command_keys"], expected)
        self.assertEqual(ceiling["production_command_count"], 2)
        self.assertEqual(ALLOWED_COMMAND_KEYS, tuple(expected))

    def test_evidence_checks_keep_implementation_unauthorized(self) -> None:
        checks = _review()["evidence_checks"]
        for key in (
            "implementation_allowed_false",
            "execution_added_false",
            "command_keys_added_empty",
            "no_third_c3_command",
            "no_c4_implementation",
            "no_target_repo_writeback",
            "no_scheduler_autonomy",
            "no_c5_c6_unlock",
            "no_adapter_validation_controlled_command",
        ):
            with self.subTest(key=key):
                self.assertIs(checks[key], True)

    def test_no_generalized_runner_module_exists(self) -> None:
        self.assertFalse((SOURCE_ROOT / "runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "controlled_runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "command_registry.py").exists())

    def test_source_does_not_use_shell_true_or_scheduler_autonomy(self) -> None:
        forbidden = (
            "shell" + "=True",
            "Background" + "Scheduler",
            "schedule" + ".every(",
            "while " + "True:",
            "target" + "_repo_writeback = True",
        )
        path = SOURCE_ROOT / "controlled_runner_probe.py"
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            with self.subTest(path=path.name, token=token):
                self.assertNotIn(token, source)

    def test_allowed_and_forbidden_next_routes_are_constrained(self) -> None:
        data = _review()
        self.assertIn("c4-scoped-runner-design-hardening-v1", data["allowed_next_routes"])
        self.assertIn("c4-probe-decision-packet-v1", data["allowed_next_routes"])
        self.assertIn("controlled-runner-stop", data["allowed_next_routes"])
        self.assertIn("c4-design-fix-v1", data["allowed_next_routes"])
        self.assertIn("direct C4 implementation", data["forbidden_next_routes"])
        self.assertIn("third C3 command", data["forbidden_next_routes"])
        self.assertIn("C5", data["forbidden_next_routes"])
        self.assertIn("C6", data["forbidden_next_routes"])
        self.assertIn("arbitrary execution", data["forbidden_next_routes"])
        self.assertIn("adapter validation as controlled command", data["forbidden_next_routes"])
        self.assertIn("target repo writeback", data["forbidden_next_routes"])

    def test_summary_records_all_review_gates_done(self) -> None:
        summary = _review()["summary"]
        self.assertEqual(summary["result"], "accepted")
        self.assertEqual(summary["done"], 18)
        self.assertEqual(summary["total"], 18)
        self.assertEqual(summary["unknown"], 0)
        self.assertEqual(summary["missing"], 0)

    def test_review_doc_documents_design_acceptance_not_implementation(self) -> None:
        doc = REVIEW_DOC.read_text(encoding="utf-8")
        self.assertIn("Decision: accepted.", doc)
        self.assertIn("Design acceptance means", doc)
        self.assertIn("Implementation authorization would allow new runnable", doc)
        self.assertIn("behavior. This artifact does only the former.", doc)
        self.assertIn("C4 implementation remains unauthorized.", doc)
        self.assertIn("C3 remains the executable ceiling.", doc)
        self.assertIn("C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md", doc)

    def test_artifacts_do_not_use_raw_local_identity_or_prompt_text(self) -> None:
        payload = REVIEW.read_text(encoding="utf-8") + "\n" + REVIEW_DOC.read_text(encoding="utf-8")
        for token in ("C:" + r"\Users\thank", "C:" + "/Users/thank"):
            self.assertNotIn(token, payload)
        for marker in (
            "[" + "PASTE TARGET:",
            "Goal " + "Stack:",
            "Allowed " + "scope:",
            "BEGIN_COPY_BLOCK" + "_FOR_CHATGPT",
        ):
            self.assertNotIn(marker, payload)


def _review() -> dict[str, object]:
    return json.loads(REVIEW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
