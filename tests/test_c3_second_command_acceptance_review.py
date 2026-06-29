from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEY, default_probe, validate_probe
from dev_cockpit.controlled_runner_probe_review import default_review, validate_review


REVIEW = ROOT / "samples" / "c3_second_command_acceptance" / "c3_second_command_acceptance_review_v1.json"
DOC = ROOT / "docs" / "design" / "C3_SECOND_COMMAND_ACCEPTANCE_REVIEW_V1.md"


class C3SecondCommandAcceptanceReviewTests(unittest.TestCase):
    def test_acceptance_packet_parses(self) -> None:
        data = _review()
        self.assertEqual(data["schema_version"], "c3_second_command_acceptance_review.v1")
        self.assertEqual(data["implementation_status"], "decision_packet_only")
        self.assertEqual(data["review_status"], "completed")

    def test_current_accepted_state_remains_single_production_command(self) -> None:
        state = _review()["current_accepted_state"]
        self.assertEqual(state["accepted_c3_command_keys"], ["status_snapshot_help"])
        self.assertEqual(state["only_accepted_c3_command"], "status_snapshot_help")
        self.assertEqual(state["candidate_under_review"], "adapters_validate_help")
        self.assertFalse(state["production_allowlist_expanded"])
        self.assertFalse(state["broad_adapter_validation_approved"])
        self.assertEqual(ALLOWED_COMMAND_KEY, "status_snapshot_help")
        self.assertEqual(validate_probe(default_probe())["command_key"], "status_snapshot_help")
        self.assertEqual(validate_review(default_review())["accepted_command_keys"], ["status_snapshot_help"])

    def test_evidence_summary_includes_design_help_probe_and_validation(self) -> None:
        evidence = _review()["evidence_summary"]
        self.assertEqual(evidence["design_evidence"]["selected_candidate"], "adapters_validate_help")
        self.assertFalse(evidence["design_evidence"]["implementation_allowed_now"])
        self.assertEqual(evidence["help_probe_evidence"]["fixed_argv_suffix"], ["-m", "dev_cockpit.adapters", "--help"])
        self.assertFalse(evidence["help_probe_evidence"]["adapter_validation_executed"])
        self.assertFalse(evidence["help_probe_evidence"]["target_repo_required"])
        self.assertTrue(evidence["absence_of_broad_adapter_validation"])
        self.assertFalse(evidence["validation_evidence"]["known_warning"]["blocking"])

    def test_decision_options_are_exactly_a_b_c(self) -> None:
        options = _review()["decision_options"]
        self.assertEqual([option["id"] for option in options], ["A", "B", "C"])
        self.assertEqual(options[0]["name"], "freeze C3 at one accepted command")
        self.assertEqual(options[1]["name"], "accept adapters_validate_help as help-only second C3 command candidate")
        self.assertEqual(options[2]["name"], "defer second-command adoption until C4 design")

    def test_each_option_has_required_review_fields(self) -> None:
        for option in _review()["decision_options"]:
            with self.subTest(option=option["id"]):
                for key in (
                    "meaning",
                    "required_evidence",
                    "risk",
                    "what_remains_locked",
                    "future_slice_allowed",
                    "not_approved",
                ):
                    self.assertIn(key, option)
                self.assertTrue(option["required_evidence"])
                self.assertTrue(option["not_approved"])

    def test_recommendation_is_candidate_acceptance_not_production_implementation(self) -> None:
        recommendation = _review()["recommendation"]
        self.assertEqual(recommendation["recommended_option"], "B")
        self.assertEqual(recommendation["decision"], "accept_help_only_second_c3_command_candidate")
        self.assertFalse(recommendation["production_command_implemented"])
        self.assertFalse(recommendation["production_allowlist_expanded"])
        self.assertFalse(recommendation["broad_adapter_validation_approved"])
        self.assertFalse(recommendation["c4_unlocked"])
        self.assertFalse(recommendation["c5_unlocked"])
        self.assertFalse(recommendation["c6_unlocked"])

    def test_no_approval_boundary_rejects_broad_execution(self) -> None:
        boundary = _review()["no_approval_boundary"]
        for key, value in boundary.items():
            with self.subTest(key=key):
                self.assertFalse(value)

    def test_next_routes_cover_all_options(self) -> None:
        next_routes = _review()["next_routes"]
        self.assertIn("if_A", next_routes)
        self.assertIn("if_B", next_routes)
        self.assertIn("if_C", next_routes)
        self.assertEqual(next_routes["recommended_next_slice"], "supervisor-decision-needed")
        self.assertTrue(next_routes["supervisor_should_generate_prompt"])

    def test_src_does_not_implement_adapters_validate_help(self) -> None:
        source_payload = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src" / "dev_cockpit").glob("*.py"))
        self.assertNotIn("adapters_validate_help", source_payload)
        self.assertIn('ALLOWED_COMMAND_KEY = "status_snapshot_help"', source_payload)

    def test_artifacts_do_not_contain_paste_ready_prompt(self) -> None:
        payload = REVIEW.read_text(encoding="utf-8") + "\n" + DOC.read_text(encoding="utf-8")
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)


def _review() -> dict[str, object]:
    return json.loads(REVIEW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
