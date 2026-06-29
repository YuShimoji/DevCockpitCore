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
    / "c3_second_command_production_probe_review"
    / "c3_second_command_production_probe_review_v1.json"
)
DOC = ROOT / "docs" / "design" / "C3_SECOND_COMMAND_PRODUCTION_PROBE_REVIEW_V1.md"


class C3SecondCommandProductionProbeReviewTests(unittest.TestCase):
    def test_review_packet_parses_and_accepts(self) -> None:
        data = _review()
        self.assertEqual(data["schema_version"], "c3_second_command_production_probe_review.v1")
        self.assertEqual(data["decision"], "accepted")
        self.assertEqual(data["reviewed_artifact"], "c3-second-command-production-probe-v1")
        self.assertEqual(data["c3_status"], "accepted")

    def test_reviewed_command_set_is_exactly_two_keys(self) -> None:
        data = _review()
        expected = ["status_snapshot_help", "adapters_validate_help"]
        self.assertEqual(data["production_command_keys"], expected)
        self.assertEqual(data["expected_command_keys"], expected)
        self.assertEqual(data["production_command_count"], 2)
        self.assertEqual(ALLOWED_COMMAND_KEYS, tuple(expected))

    def test_all_evidence_checks_pass(self) -> None:
        checks = _review()["evidence_checks"]
        expected_keys = {
            "exact_two_command_keys",
            "status_snapshot_help_present",
            "adapters_validate_help_present",
            "no_third_key",
            "adapters_validate_help_help_only",
            "adapters_validate_help_does_not_validate",
            "config_command_override_blocked",
            "config_executable_override_blocked",
            "config_argv_args_override_blocked",
            "shell_false_enforced",
            "timeout_required",
            "output_truncation_present",
            "redaction_present",
            "before_after_repo_state_present",
            "target_repo_writeback_false",
            "adapter_default_validation_executed_false",
            "no_generalized_runner",
            "c4_c5_c6_locked",
        }
        self.assertEqual(set(checks), expected_keys)
        for key, check in checks.items():
            with self.subTest(key=key):
                self.assertEqual(check["result"], "pass")

    def test_live_probe_readback_verifies_current_reviewed_commit(self) -> None:
        live = _review()["live_probe_readback"]
        self.assertEqual(live["reviewed_commit_short"], "37e5202")
        self.assertEqual(live["worktree_before"], "clean")
        self.assertEqual(live["worktree_after"], "clean")
        self.assertEqual(live["remote_parity_before"], "in_sync")
        self.assertEqual(live["remote_parity_after"], "in_sync")
        self.assertEqual(live["argv_suffix"], ["-m", "dev_cockpit.adapters", "--help"])
        self.assertEqual(live["exit_code"], 0)

    def test_c4_c5_c6_remain_locked_and_next_is_constrained(self) -> None:
        data = _review()
        self.assertEqual(data["c4_status"], "locked")
        self.assertEqual(data["c5_status"], "locked")
        self.assertEqual(data["c6_status"], "locked")
        next_state = data["next"]
        self.assertEqual(next_state["recommended_next_slice"], "c3-second-command-hardening-v1")
        self.assertTrue(next_state["supervisor_decision_required"])
        self.assertIn("third C3 command key", next_state["forbidden_next_actions"])
        self.assertNotIn("direct C4 implementation", next_state["allowed_next_actions"])

    def test_known_warning_is_non_blocking_fixture_residue(self) -> None:
        warnings = _review()["known_warnings"]
        self.assertEqual(warnings[0]["warning_key"], "pseudo_git_tag_fixture_warning")
        self.assertFalse(warnings[0]["blocking"])

    def test_docs_and_packet_do_not_contain_paste_ready_prompt(self) -> None:
        payload = REVIEW.read_text(encoding="utf-8") + "\n" + DOC.read_text(encoding="utf-8")
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)


def _review() -> dict[str, object]:
    return json.loads(REVIEW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
