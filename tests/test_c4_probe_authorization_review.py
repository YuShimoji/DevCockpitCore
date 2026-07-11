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
    / "c4_probe_authorization_review"
    / "c4_probe_authorization_review_v1.json"
)
DOC = ROOT / "docs" / "design" / "C4_PROBE_AUTHORIZATION_REVIEW_V1.md"
PROJECT_CONTEXT = ROOT / "docs" / "project-context.md"
SOURCE_ROOT = ROOT / "src" / "dev_cockpit"
CONTROLLED_PROBE_SOURCE = SOURCE_ROOT / "controlled_runner_probe.py"


class C4ProbeAuthorizationReviewTests(unittest.TestCase):
    def test_authorization_review_json_parses_and_has_required_top_level_keys(self) -> None:
        data = _review()
        required = {
            "schema_version",
            "generated_at",
            "project_key",
            "source_decision_packet",
            "latest_verified_commit",
            "current_state",
            "review_decision",
            "evidence_checks",
            "future_probe_authorization_constraints",
            "known_warnings",
            "allowed_next_routes",
            "forbidden_next_routes",
            "summary",
        }
        self.assertEqual(data["schema_version"], "c4_probe_authorization_review.v1")
        self.assertTrue(required.issubset(data))

    def test_review_accepts_future_prompt_without_implementation_now(self) -> None:
        decision = _review()["review_decision"]
        self.assertEqual(decision["decision"], "accepted_for_future_probe_prompt")
        self.assertEqual(
            decision["recommended_next_slice"],
            "common-foundation-c4-probe-minimal-implementation-v1",
        )
        self.assertFalse(decision["implementation_allowed_now"])
        self.assertTrue(decision["future_probe_prompt_allowed_after_supervisor_acceptance"])
        self.assertTrue(decision["supervisor_should_generate_prompt"])

    def test_current_state_preserves_c3_ceiling_and_exact_two_command_keys(self) -> None:
        current = _review()["current_state"]
        expected = ["status_snapshot_help", "adapters_validate_help"]
        self.assertEqual(current["executable_ceiling"], "C3")
        self.assertEqual(current["production_c3_command_keys"], expected)
        self.assertEqual(current["production_c3_command_count"], 2)
        self.assertEqual(ALLOWED_COMMAND_KEYS, tuple(expected))
        self.assertTrue(current["c4_design_accepted"])
        self.assertTrue(current["c4_design_hardened"])
        self.assertTrue(current["c4_probe_decision_packet_present"])
        self.assertFalse(current["c4_implementation_authorized_now"])
        self.assertTrue(current["c5_c6_locked"])

    def test_evidence_checks_keep_review_and_capability_surface_clean(self) -> None:
        checks = _review()["evidence_checks"]
        expected = {
            "decision_packet_present",
            "decision_packet_json_valid",
            "recommendation_recorded",
            "implementation_allowed_now_false",
            "future_probe_requires_separate_supervisor_prompt",
            "current_executable_ceiling_c3",
            "exact_two_c3_command_keys",
            "no_third_c3_command",
            "no_c4_implementation",
            "no_generalized_runner",
            "no_target_repo_writeback",
            "no_scheduler_autonomy",
            "no_c5_c6_unlock",
            "no_adapter_validation_controlled_command",
            "no_arbitrary_execution",
            "no_paste_ready_prompt_in_artifacts",
            "no_raw_host_path_as_artifact_identity",
        }
        self.assertEqual(set(checks), expected)
        for key in expected:
            with self.subTest(key=key):
                self.assertTrue(checks[key])

    def test_future_probe_constraints_are_single_bounded_and_no_writeback(self) -> None:
        constraints = _review()["future_probe_authorization_constraints"]
        expected = {
            "single_probe_only",
            "hardcoded_allowlist_only",
            "no_config_supplied_command_or_argv",
            "shell_false",
            "timeout_required",
            "output_truncation_required",
            "redaction_required",
            "before_after_repo_state_required",
            "no_target_repo_writeback",
            "no_cross_project_execution",
            "no_scheduler_or_autonomy",
            "no_credentials",
            "no_destructive_git",
            "no_force_push",
        }
        self.assertEqual(set(constraints), expected)
        for key in expected:
            with self.subTest(key=key):
                self.assertTrue(constraints[key])

    def test_allowed_and_forbidden_routes_are_constrained(self) -> None:
        data = _review()
        self.assertIn("common-foundation-c4-probe-minimal-implementation-v1", data["allowed_next_routes"])
        self.assertIn("common-foundation-validation-fixture-hygiene-v1", data["allowed_next_routes"])
        self.assertIn("common-foundation-c4-design-followup-fix-v1", data["allowed_next_routes"])
        self.assertIn("controlled-runner-stop", data["allowed_next_routes"])
        self.assertIn("direct C4 implementation without separate prompt", data["forbidden_next_routes"])
        self.assertIn("third C3 command", data["forbidden_next_routes"])
        self.assertIn("C5", data["forbidden_next_routes"])
        self.assertIn("C6", data["forbidden_next_routes"])
        self.assertIn("arbitrary execution", data["forbidden_next_routes"])
        self.assertIn("adapter validation as controlled command", data["forbidden_next_routes"])
        self.assertIn("target repo writeback", data["forbidden_next_routes"])

    def test_no_generalized_runner_module_or_shell_true_appears(self) -> None:
        self.assertFalse((SOURCE_ROOT / "runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "controlled_runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "command_registry.py").exists())
        source = CONTROLLED_PROBE_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("shell" + "=True", source)
        self.assertNotIn("Background" + "Scheduler", source)
        self.assertNotIn("schedule" + ".every(", source)
        self.assertNotIn("target" + "_repo_writeback = True", source)

    def test_doc_records_authorization_review_boundaries(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        normalized = " ".join(doc.split())
        for phrase in (
            "This is an authorization review.",
            "Decision: `accepted_for_future_probe_prompt`.",
            "It does not authorize implementation in this slice.",
            "C3 remains the executable ceiling.",
            "C4 implementation remains unauthorized now.",
            "single bounded C4 probe",
            "Arbitrary command execution remains forbidden.",
            "Target repository writeback remains forbidden.",
            "C5 and C6 remain locked.",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)

    def test_project_context_preserves_durable_capability_boundary(self) -> None:
        context = PROJECT_CONTEXT.read_text(encoding="utf-8")
        normalized = " ".join(context.split())
        self.assertIn(
            "accepted C3 command surface has exactly two help-only keys",
            normalized,
        )
        self.assertIn(
            "accepted C4 surface has exactly one repo-local validation-pack key",
            normalized,
        )
        self.assertIn("validation_pack_default_pretty", context)
        self.assertNotIn("C4 implementation is authorized", normalized)

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
        self.assertEqual(summary["done"], 17)
        self.assertEqual(summary["total"], 17)
        self.assertEqual(summary["unknown"], 0)
        self.assertEqual(summary["missing"], 0)


def _review() -> dict[str, object]:
    return json.loads(REVIEW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
