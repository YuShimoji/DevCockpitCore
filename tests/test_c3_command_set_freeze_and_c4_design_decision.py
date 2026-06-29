from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEYS


ARTIFACT = (
    ROOT
    / "samples"
    / "c3_command_set_freeze_and_c4_design_decision"
    / "c3_command_set_freeze_and_c4_design_decision_v1.json"
)
DOC = ROOT / "docs" / "design" / "C3_COMMAND_SET_FREEZE_AND_C4_DESIGN_DECISION_V1.md"
SOURCE = ROOT / "src" / "dev_cockpit" / "controlled_runner_probe.py"


class C3CommandSetFreezeAndC4DesignDecisionTests(unittest.TestCase):
    def test_decision_artifact_parses_and_has_required_top_level_keys(self) -> None:
        data = _artifact()
        required = {
            "schema_version",
            "generated_at",
            "project_key",
            "source_hardening_artifact",
            "latest_verified_commit",
            "command_set",
            "c3_freeze_readiness",
            "c4_design_readiness",
            "route_options",
            "recommended_decision",
            "forbidden_next_actions",
            "invariants",
            "summary",
        }
        self.assertEqual(data["schema_version"], "c3_command_set_freeze_and_c4_design_decision.v1")
        self.assertTrue(required.issubset(data))

    def test_command_set_is_exactly_two_keys_and_no_third_command(self) -> None:
        command_set = _artifact()["command_set"]
        expected = ["status_snapshot_help", "adapters_validate_help"]
        self.assertEqual(command_set["production_command_keys"], expected)
        self.assertEqual(command_set["expected_command_keys"], expected)
        self.assertEqual(command_set["production_command_count"], 2)
        self.assertTrue(command_set["no_third_command"])
        self.assertEqual(ALLOWED_COMMAND_KEYS, tuple(expected))

    def test_c4_design_readiness_does_not_permit_implementation(self) -> None:
        readiness = _artifact()["c4_design_readiness"]
        self.assertTrue(readiness["design_only_allowed"])
        self.assertFalse(readiness["implementation_allowed"])
        self.assertIn("runner implementation", readiness["non_goals"])
        self.assertIn("target repository writeback", readiness["non_goals"])

    def test_recommended_next_slice_is_documented_allowed_route(self) -> None:
        data = _artifact()
        decision = data["recommended_decision"]
        self.assertEqual(decision["decision"], "recommend_c4_design_only")
        self.assertEqual(decision["recommended_next_slice"], "common-foundation-c4-scoped-runner-design-v1")
        self.assertTrue(decision["supervisor_should_generate_prompt"])
        self.assertIn("c4-scoped-runner-design-only", data["route_options"])
        self.assertTrue(data["route_options"]["c4-scoped-runner-design-only"]["allowed"])

    def test_forbidden_next_actions_remain_explicit(self) -> None:
        forbidden = set(_artifact()["forbidden_next_actions"])
        self.assertIn("direct C4 implementation", forbidden)
        self.assertIn("third C3 command", forbidden)
        self.assertIn("C5", forbidden)
        self.assertIn("C6", forbidden)
        self.assertIn("arbitrary execution", forbidden)
        self.assertIn("adapter validation as controlled command", forbidden)

    def test_invariants_pass_and_match_required_set(self) -> None:
        invariants = _artifact()["invariants"]
        expected = {
            "exact_two_command_keys",
            "no_third_command",
            "help_only_boundary",
            "adapters_validate_help_does_not_validate",
            "c4_c5_c6_locked",
            "no_generalized_runner",
            "no_target_repo_writeback",
            "no_scheduler",
        }
        self.assertEqual(set(invariants), expected)
        for key, invariant in invariants.items():
            with self.subTest(key=key):
                self.assertEqual(invariant["result"], "pass")
                self.assertIs(invariant["value"], True)

    def test_no_production_capability_expansion_is_present(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(ALLOWED_COMMAND_KEYS, ("status_snapshot_help", "adapters_validate_help"))
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "controlled_runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "command_registry.py").exists())
        self.assertNotIn("shell" + "=True", source)
        self.assertNotIn("Background" + "Scheduler", source)

    def test_artifacts_do_not_use_raw_local_identity_or_prompt_text(self) -> None:
        payload = ARTIFACT.read_text(encoding="utf-8") + "\n" + DOC.read_text(encoding="utf-8")
        for token in ("C:" + r"\Users\thank", "C:" + "/Users/thank"):
            self.assertNotIn(token, payload)
        for marker in (
            "[" + "PASTE TARGET:",
            "Goal " + "Stack:",
            "Allowed " + "scope:",
            "BEGIN_COPY_BLOCK" + "_FOR_CHATGPT",
        ):
            self.assertNotIn(marker, payload)


def _artifact() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
