from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.c4_scoped_runner_probe import C4_COMMAND_KEY, C4_COMMAND_KEYS
from dev_cockpit.controlled_runner_probe import (
    ADAPTERS_VALIDATE_HELP_KEY,
    ALLOWED_COMMAND_KEYS,
    STATUS_SNAPSHOT_HELP_KEY,
)


REVIEW = (
    ROOT
    / "samples"
    / "c4_probe_minimal_implementation_review"
    / "c4_probe_minimal_implementation_review_v1.json"
)
DOC = ROOT / "docs" / "design" / "C4_PROBE_MINIMAL_IMPLEMENTATION_REVIEW_V1.md"
PROJECT_CONTEXT = ROOT / "docs" / "project-context.md"
SOURCE_ROOT = ROOT / "src" / "dev_cockpit"
C4_SOURCE = SOURCE_ROOT / "c4_scoped_runner_probe.py"


class C4ProbeMinimalImplementationReviewTests(unittest.TestCase):
    def test_review_json_parses_and_has_required_top_level_keys(self) -> None:
        data = _review()
        required = {
            "schema_version",
            "generated_at",
            "project_key",
            "reviewed_commit",
            "reviewed_artifact",
            "source_implementation_artifact",
            "source_result_artifact",
            "source_design_doc",
            "source_authorization_review",
            "live_readback",
            "current_capability_state",
            "review_decision",
            "evidence_checks",
            "known_warnings",
            "allowed_next_routes",
            "forbidden_next_routes",
            "summary",
        }
        self.assertEqual(data["schema_version"], "c4_probe_minimal_implementation_review.v1")
        self.assertTrue(required.issubset(data))

    def test_review_accepts_single_probe_and_recommends_hardening(self) -> None:
        decision = _review()["review_decision"]
        self.assertEqual(decision["decision"], "accepted")
        self.assertEqual(
            decision["recommended_next_slice"],
            "common-foundation-c4-probe-minimal-implementation-hardening-v1",
        )
        self.assertFalse(decision["implementation_fix_required"])
        self.assertFalse(decision["fixture_hygiene_required_before_acceptance"])
        self.assertTrue(decision["supervisor_should_generate_prompt"])

    def test_live_readback_records_clean_current_probe_evidence(self) -> None:
        readback = _review()["live_readback"]
        self.assertEqual(readback["exit_code"], 0)
        self.assertEqual(readback["result"], "warn")
        self.assertEqual(readback["remote_parity"], "in_sync")
        self.assertEqual(readback["worktree_before"], "clean")
        self.assertEqual(readback["worktree_after"], "clean")
        self.assertIn("pseudo-git-tag fixture warning", readback["warning_basis"])

    def test_current_capability_state_preserves_c3_and_single_c4_key(self) -> None:
        current = _review()["current_capability_state"]
        expected_c3 = [STATUS_SNAPSHOT_HELP_KEY, ADAPTERS_VALIDATE_HELP_KEY]
        self.assertEqual(current["c3_command_set"], expected_c3)
        self.assertEqual(current["c3_command_count"], 2)
        self.assertEqual(current["c4_command_set"], [C4_COMMAND_KEY])
        self.assertEqual(current["c4_command_count"], 1)
        self.assertEqual(
            current["current_executable_capability_level"],
            "C4_minimal_repo_local_probe_review_accepted",
        )
        self.assertEqual(ALLOWED_COMMAND_KEYS, tuple(expected_c3))
        self.assertEqual(C4_COMMAND_KEYS, (C4_COMMAND_KEY,))
        self.assertTrue(current["c5_c6_locked"])

    def test_evidence_checks_keep_probe_narrow_and_safe(self) -> None:
        checks = _review()["evidence_checks"]
        expected = {
            "implementation_artifact_present",
            "result_artifact_present",
            "c4_module_present",
            "exactly_one_c4_command_key",
            "c4_command_key_validation_pack_default_pretty",
            "c3_command_set_exactly_two",
            "no_third_c3_command",
            "no_second_c4_command",
            "command_hardcoded",
            "no_config_supplied_command",
            "no_config_supplied_executable",
            "no_config_supplied_argv_args",
            "shell_false_enforced",
            "timeout_required",
            "output_truncation_present",
            "redaction_present",
            "before_after_repo_state_present",
            "target_repo_writeback_false",
            "cross_project_execution_false",
            "scheduler_or_autonomy_false",
            "credentials_required_false",
            "adapter_default_validation_executed_false",
            "adapters_validate_as_controlled_command_false",
            "no_generalized_runner",
            "no_arbitrary_execution",
            "no_c5_c6_unlock",
            "no_raw_host_path_as_artifact_identity",
            "no_paste_ready_prompt_in_artifacts",
        }
        self.assertEqual(set(checks), expected)
        for key in expected:
            with self.subTest(key=key):
                self.assertTrue(checks[key])

    def test_known_warnings_are_non_blocking(self) -> None:
        warnings = _review()["known_warnings"]
        self.assertTrue(warnings["pseudo_git_tag_fixture_warning"]["present"])
        self.assertFalse(warnings["pseudo_git_tag_fixture_warning"]["blocking"])
        self.assertTrue(warnings["validation_pack_warn_result"]["present"])
        self.assertFalse(warnings["validation_pack_warn_result"]["blocking"])
        self.assertTrue(warnings["optional_sibling_warnings"]["present"])
        self.assertFalse(warnings["optional_sibling_warnings"]["blocking"])

    def test_allowed_and_forbidden_routes_are_constrained(self) -> None:
        data = _review()
        self.assertIn(
            "common-foundation-c4-probe-minimal-implementation-hardening-v1",
            data["allowed_next_routes"],
        )
        self.assertIn("common-foundation-validation-fixture-hygiene-v1", data["allowed_next_routes"])
        self.assertIn("common-foundation-c4-probe-minimal-fix-v1", data["allowed_next_routes"])
        self.assertIn("controlled-runner-stop", data["allowed_next_routes"])
        self.assertIn("second C4 command", data["forbidden_next_routes"])
        self.assertIn("third C3 command", data["forbidden_next_routes"])
        self.assertIn("generalized runner implementation", data["forbidden_next_routes"])
        self.assertIn("C5", data["forbidden_next_routes"])
        self.assertIn("C6", data["forbidden_next_routes"])
        self.assertIn("arbitrary execution", data["forbidden_next_routes"])
        self.assertIn("target repo writeback", data["forbidden_next_routes"])

    def test_no_generalized_runner_module_or_shell_true_appears(self) -> None:
        self.assertFalse((SOURCE_ROOT / "runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "controlled_runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "command_registry.py").exists())
        source = C4_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("shell" + "=True", source)
        self.assertNotIn("Background" + "Scheduler", source)
        self.assertNotIn("schedule" + ".every(", source)
        self.assertNotIn("target" + "_repo_writeback = True", source)

    def test_doc_records_review_acceptance_boundaries(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        normalized = " ".join(doc.split())
        for phrase in (
            "Decision: accepted.",
            "single bounded repo-local validation-pack probe",
            "`validation_pack_default_pretty`",
            "known pseudo-git-tag fixture warning",
            "Current Capability State Vocabulary",
            "C3 command keys remain exactly",
            "C4 is limited to exactly",
            "Configuration may select only the allowed key.",
            "C5 and C6 locked.",
            "common-foundation-c4-probe-minimal-implementation-hardening-v1",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)

    def test_project_context_records_review_as_current_state(self) -> None:
        context = PROJECT_CONTEXT.read_text(encoding="utf-8")
        normalized = " ".join(context.split())
        self.assertIn("c4-probe-minimal-implementation-review-v1", context)
        self.assertIn("C4 is limited to one accepted repo-local validation-pack probe", normalized)
        self.assertIn("C3 command set remains exactly two", normalized)

    def test_artifacts_do_not_use_raw_local_identity_or_prompt_text(self) -> None:
        payload = "\n".join(
            [
                REVIEW.read_text(encoding="utf-8"),
                DOC.read_text(encoding="utf-8"),
                PROJECT_CONTEXT.read_text(encoding="utf-8"),
            ]
        )
        for token in ("C:" + r"\Users\\", "C:" + "/Users/"):
            self.assertNotIn(token, payload)
        for marker in (
            "[" + "PASTE TARGET:",
            "Goal " + "Stack:",
            "Allowed " + "scope:",
            "BEGIN" + "_COPY_BLOCK" + "_FOR_CHATGPT",
            "next-" + "Agent Prompt",
        ):
            self.assertNotIn(marker, payload)

    def test_summary_records_all_review_gates_done(self) -> None:
        summary = _review()["summary"]
        self.assertEqual(summary["result"], "accepted")
        self.assertEqual(summary["done"], 28)
        self.assertEqual(summary["total"], 28)
        self.assertEqual(summary["unknown"], 0)
        self.assertEqual(summary["missing"], 0)


def _review() -> dict[str, object]:
    return json.loads(REVIEW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
