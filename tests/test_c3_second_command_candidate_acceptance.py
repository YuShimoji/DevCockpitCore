from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEY, default_probe, validate_probe
from dev_cockpit.controlled_runner_probe_review import default_review, validate_review


PACKET = ROOT / "samples" / "c3_second_command_candidate_acceptance" / "c3_second_command_candidate_acceptance_v1.json"
DOC = ROOT / "docs" / "design" / "C3_SECOND_COMMAND_CANDIDATE_ACCEPTANCE_V1.md"


class C3SecondCommandCandidateAcceptanceTests(unittest.TestCase):
    def test_candidate_acceptance_packet_parses(self) -> None:
        data = _packet()
        self.assertEqual(data["schema_version"], "c3_second_command_candidate_acceptance.v1")
        self.assertEqual(data["decision_status"], "option_b_selected")
        self.assertEqual(data["implementation_status"], "candidate_state_only")

    def test_decision_source_tracks_acceptance_review_option_b(self) -> None:
        source = _packet()["decision_source"]
        self.assertEqual(source["review_recommended_option"], "B")
        self.assertEqual(source["work_judgment"], "select_option_b_from_passed_acceptance_review")
        self.assertEqual(source["review_status"], "completed")

    def test_candidate_is_accepted_only_as_help_only_state(self) -> None:
        state = _packet()["candidate_state"]
        self.assertEqual(state["accepted_help_only_candidate_keys"], ["adapters_validate_help"])
        self.assertEqual(state["candidate_fixed_argv_suffix"], ["-m", "dev_cockpit.adapters", "--help"])
        self.assertEqual(state["production_accepted_c3_command_keys"], ["status_snapshot_help"])
        self.assertFalse(state["production_allowlist_expanded"])
        self.assertFalse(state["production_command_implemented"])
        self.assertTrue(state["not_a_production_command"])

    def test_production_c3_surface_is_still_single_command(self) -> None:
        self.assertEqual(ALLOWED_COMMAND_KEY, "status_snapshot_help")
        self.assertEqual(validate_probe(default_probe())["command_key"], "status_snapshot_help")
        self.assertEqual(validate_review(default_review())["accepted_command_keys"], ["status_snapshot_help"])

    def test_scope_boundary_rejects_runner_and_adapter_expansion(self) -> None:
        scope = _packet()["scope_boundary"]
        self.assertTrue(scope["docs_and_test_state_update"])
        for key, value in scope.items():
            if key != "docs_and_test_state_update":
                with self.subTest(key=key):
                    self.assertFalse(value)

    def test_no_approval_boundary_keeps_c4_c6_locked(self) -> None:
        boundary = _packet()["no_approval_boundary"]
        for key, value in boundary.items():
            with self.subTest(key=key):
                self.assertFalse(value)

    def test_next_routes_require_separate_prompt_for_more_capability(self) -> None:
        next_routes = _packet()["next_routes"]
        self.assertEqual(next_routes["recommended_next_slice"], "supervisor-prompt-needed")
        self.assertIn("common-foundation-c3-second-command-production-probe-v1", next_routes["if_second_command_implementation_is_requested"])
        self.assertIn("separate C4 design prompt required", next_routes["if_c4_is_requested"])
        self.assertEqual(next_routes["user_work"], "none")

    def test_source_does_not_implement_candidate_key(self) -> None:
        source_payload = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src" / "dev_cockpit").glob("*.py"))
        self.assertNotIn("adapters_validate_help", source_payload)
        self.assertIn('ALLOWED_COMMAND_KEY = "status_snapshot_help"', source_payload)

    def test_docs_and_packet_do_not_contain_paste_ready_prompt(self) -> None:
        payload = PACKET.read_text(encoding="utf-8") + "\n" + DOC.read_text(encoding="utf-8")
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)


def _packet() -> dict[str, object]:
    return json.loads(PACKET.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
