from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEYS


ARTIFACT = ROOT / "samples" / "c3_second_command_hardening" / "c3_second_command_hardening_v1.json"
DOC = ROOT / "docs" / "design" / "C3_SECOND_COMMAND_HARDENING_V1.md"
SOURCE = ROOT / "src" / "dev_cockpit" / "controlled_runner_probe.py"


class C3SecondCommandHardeningTests(unittest.TestCase):
    def test_hardening_artifact_parses_and_has_required_top_level_keys(self) -> None:
        data = _artifact()
        required = {
            "schema_version",
            "generated_at",
            "project_key",
            "source_review_artifact",
            "reviewed_commit",
            "review_commit",
            "production_command_keys",
            "production_command_count",
            "expected_command_keys",
            "command_set_status",
            "c3_status",
            "c4_status",
            "c5_status",
            "c6_status",
            "invariants",
            "known_warnings",
            "next_decision",
            "summary",
        }
        self.assertEqual(data["schema_version"], "c3_second_command_hardening.v1")
        self.assertTrue(required.issubset(data))

    def test_production_command_set_is_exactly_two_keys(self) -> None:
        data = _artifact()
        expected = ["status_snapshot_help", "adapters_validate_help"]
        self.assertEqual(data["production_command_keys"], expected)
        self.assertEqual(data["expected_command_keys"], expected)
        self.assertEqual(data["production_command_count"], 2)
        self.assertEqual(len(data["production_command_keys"]), 2)
        self.assertEqual(ALLOWED_COMMAND_KEYS, tuple(expected))

    def test_no_third_command_and_c4_c5_c6_locked(self) -> None:
        data = _artifact()
        self.assertTrue(_invariant(data, "no_third_command_key"))
        self.assertEqual(data["c4_status"], "locked")
        self.assertEqual(data["c5_status"], "locked")
        self.assertEqual(data["c6_status"], "locked")
        self.assertTrue(_invariant(data, "c4_c5_c6_locked"))

    def test_help_only_and_no_validation_runner_drift(self) -> None:
        data = _artifact()
        self.assertTrue(_invariant(data, "adapters_validate_help_help_only"))
        self.assertTrue(_invariant(data, "adapters_validate_help_does_not_validate"))
        self.assertTrue(_invariant(data, "adapter_default_validation_not_executed"))
        self.assertTrue(_invariant(data, "target_repo_writeback_false"))

    def test_next_decision_is_constrained_and_not_direct_c4_implementation(self) -> None:
        next_decision = _artifact()["next_decision"]
        self.assertEqual(next_decision["recommended_next_slice"], "c3-command-set-freeze-and-c4-design-decision-v1")
        self.assertTrue(next_decision["supervisor_decision_required"])
        self.assertNotIn("direct C4 implementation", next_decision["allowed_next_actions"])
        self.assertIn("direct C4 implementation", next_decision["forbidden_next_actions"])
        self.assertIn("third C3 command key", next_decision["forbidden_next_actions"])

    def test_all_required_invariants_pass(self) -> None:
        expected = {
            "exact_two_command_keys",
            "no_third_command_key",
            "status_snapshot_help_present",
            "adapters_validate_help_present",
            "adapters_validate_help_help_only",
            "adapters_validate_help_does_not_validate",
            "adapter_default_validation_not_executed",
            "config_command_override_blocked",
            "config_executable_override_blocked",
            "config_argv_args_override_blocked",
            "shell_false_enforced",
            "timeout_required",
            "output_truncation_present",
            "redaction_present",
            "before_after_repo_state_present",
            "target_repo_writeback_false",
            "c4_c5_c6_locked",
            "no_generalized_runner",
        }
        invariants = _artifact()["invariants"]
        self.assertEqual(set(invariants), expected)
        for key, invariant in invariants.items():
            with self.subTest(key=key):
                self.assertEqual(invariant["result"], "pass")
                self.assertIs(invariant["value"], True)

    def test_no_generalized_runner_module_or_shell_true(self) -> None:
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "controlled_runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "command_registry.py").exists())
        self.assertNotIn("shell" + "=True", SOURCE.read_text(encoding="utf-8"))

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


def _invariant(data: dict[str, object], key: str) -> bool:
    invariants = data["invariants"]
    assert isinstance(invariants, dict)
    invariant = invariants[key]
    assert isinstance(invariant, dict)
    return invariant["result"] == "pass" and invariant["value"] is True


if __name__ == "__main__":
    unittest.main()
