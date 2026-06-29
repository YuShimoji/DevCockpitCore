from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEYS


DESIGN = ROOT / "samples" / "c4_scoped_runner_design" / "c4_scoped_runner_design_v1.json"
DECISION = ROOT / "samples" / "c4_scoped_runner_design" / "c4_scoped_runner_decision_packet_v1.json"
DOC = ROOT / "docs" / "design" / "C4_SCOPED_RUNNER_DESIGN_V1.md"
SOURCE = ROOT / "src" / "dev_cockpit" / "controlled_runner_probe.py"


class C4ScopedRunnerDesignTests(unittest.TestCase):
    def test_c4_design_json_parses_and_has_required_top_level_keys(self) -> None:
        data = _design()
        required = {
            "schema_version",
            "generated_at",
            "project_key",
            "source_decision_artifact",
            "current_executable_ceiling",
            "c4_scope",
            "c4_candidate_capability",
            "safety_gates",
            "required_future_artifacts",
            "decision",
            "invariants",
            "summary",
        }
        self.assertEqual(data["schema_version"], "c4_scoped_runner_design.v1")
        self.assertTrue(required.issubset(data))

    def test_c4_decision_packet_parses_and_separates_design_from_implementation(self) -> None:
        packet = _decision()
        self.assertEqual(packet["schema_version"], "c4_scoped_runner_decision_packet.v1")
        self.assertTrue(packet["design_only_acceptance"]["recommended"])
        self.assertFalse(packet["implementation_authorization"]["implementation_allowed_now"])
        self.assertFalse(packet["implementation_authorization"]["execution_added"])
        self.assertEqual(packet["implementation_authorization"]["command_keys_added"], [])
        self.assertTrue(packet["forbidden_direct_implementation"]["direct_c4_implementation"])

    def test_current_executable_ceiling_remains_c3_with_exact_two_keys(self) -> None:
        ceiling = _design()["current_executable_ceiling"]
        expected = ["status_snapshot_help", "adapters_validate_help"]
        self.assertEqual(ceiling["capability_level"], "C3")
        self.assertEqual(ceiling["production_command_keys"], expected)
        self.assertEqual(ceiling["production_command_count"], 2)
        self.assertEqual(ALLOWED_COMMAND_KEYS, tuple(expected))

    def test_scope_is_design_only_and_adds_no_execution(self) -> None:
        scope = _design()["c4_scope"]
        self.assertEqual(scope["design_status"], "design_only")
        self.assertFalse(scope["implementation_allowed"])
        self.assertFalse(scope["execution_added"])
        self.assertEqual(scope["command_keys_added"], [])
        self.assertFalse(scope["target_repo_writeback_allowed"])
        self.assertFalse(scope["cross_project_execution_allowed"])
        self.assertFalse(scope["scheduler_allowed"])

    def test_safety_gates_keep_writeback_scheduler_c5_c6_and_config_commands_locked(self) -> None:
        gates = _design()["safety_gates"]
        for key in (
            "hardcoded_allowlist_required",
            "no_config_supplied_command",
            "no_config_supplied_argv",
            "shell_false_required",
            "timeout_required",
            "output_truncation_required",
            "redaction_required",
            "before_after_repo_state_required",
            "no_target_repo_writeback",
            "no_credentials",
            "no_network_unless_explicitly_approved",
            "no_destructive_git",
            "no_force_push",
            "no_scheduler",
            "no_c5_c6_unlock",
        ):
            with self.subTest(key=key):
                self.assertIs(gates[key], True)

    def test_recommended_next_slice_is_design_review_not_implementation(self) -> None:
        decision = _design()["decision"]
        self.assertEqual(decision["recommendation"], "recommend_design_acceptance_review")
        self.assertEqual(decision["recommended_next_slice"], "common-foundation-c4-scoped-runner-design-review-v1")
        self.assertFalse(decision["implementation_allowed_now"])
        self.assertTrue(decision["supervisor_should_generate_prompt"])
        self.assertIn("design-review", decision["recommended_next_slice"])
        self.assertNotIn("implementation", decision["recommended_next_slice"])

    def test_invariants_pass_and_no_third_command_or_c4_implementation_appears(self) -> None:
        invariants = _design()["invariants"]
        expected = {
            "c3_command_set_unchanged",
            "exact_two_c3_command_keys",
            "no_third_c3_command",
            "no_c4_implementation",
            "no_c5_c6_unlock",
            "no_generalized_runner",
        }
        self.assertEqual(set(invariants), expected)
        for key, invariant in invariants.items():
            with self.subTest(key=key):
                self.assertEqual(invariant["result"], "pass")
                self.assertIs(invariant["value"], True)

    def test_no_generalized_runner_module_or_changed_execution_source_exists(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "controlled_runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "command_registry.py").exists())
        self.assertNotIn("shell" + "=True", source)
        self.assertNotIn("Background" + "Scheduler", source)

    def test_artifacts_do_not_use_raw_local_identity_or_prompt_text(self) -> None:
        payload = "\n".join(
            [
                DESIGN.read_text(encoding="utf-8"),
                DECISION.read_text(encoding="utf-8"),
                DOC.read_text(encoding="utf-8"),
            ]
        )
        for token in ("C:" + r"\Users\thank", "C:" + "/Users/thank"):
            self.assertNotIn(token, payload)
        for marker in (
            "[" + "PASTE TARGET:",
            "Goal " + "Stack:",
            "Allowed " + "scope:",
            "BEGIN_COPY_BLOCK" + "_FOR_CHATGPT",
        ):
            self.assertNotIn(marker, payload)


def _design() -> dict[str, object]:
    return json.loads(DESIGN.read_text(encoding="utf-8"))


def _decision() -> dict[str, object]:
    return json.loads(DECISION.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
