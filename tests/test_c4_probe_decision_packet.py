from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEYS


PACKET = ROOT / "samples" / "c4_probe_decision_packet" / "c4_probe_decision_packet_v1.json"
DOC = ROOT / "docs" / "design" / "C4_PROBE_DECISION_PACKET_V1.md"
PROJECT_CONTEXT = ROOT / "docs" / "project-context.md"
SOURCE_ROOT = ROOT / "src" / "dev_cockpit"
CONTROLLED_PROBE_SOURCE = SOURCE_ROOT / "controlled_runner_probe.py"


class C4ProbeDecisionPacketTests(unittest.TestCase):
    def test_decision_packet_json_parses_and_has_required_top_level_keys(self) -> None:
        data = _packet()
        required = {
            "schema_version",
            "generated_at",
            "project_key",
            "source_hardening_artifact",
            "latest_verified_commit",
            "current_state",
            "decision",
            "proposed_future_probe_scope",
            "future_probe_allowed_only_if",
            "forbidden_future_probe_behavior",
            "alternatives",
            "known_warnings",
            "invariants",
            "summary",
        }
        self.assertEqual(data["schema_version"], "c4_probe_decision_packet.v1")
        self.assertTrue(required.issubset(data))

    def test_current_state_preserves_c3_ceiling_and_exact_two_command_keys(self) -> None:
        current = _packet()["current_state"]
        expected = ["status_snapshot_help", "adapters_validate_help"]
        self.assertEqual(current["executable_ceiling"], "C3")
        self.assertEqual(current["production_c3_command_keys"], expected)
        self.assertEqual(current["production_c3_command_count"], 2)
        self.assertEqual(ALLOWED_COMMAND_KEYS, tuple(expected))
        self.assertTrue(current["c4_design_accepted"])
        self.assertTrue(current["c4_design_hardened"])
        self.assertFalse(current["c4_implementation_authorized"])
        self.assertTrue(current["c5_c6_locked"])

    def test_decision_is_authorization_later_not_implementation_now(self) -> None:
        decision = _packet()["decision"]
        self.assertEqual(decision["recommendation"], "recommend_c4_probe_authorization_later")
        self.assertEqual(
            decision["recommended_next_slice"],
            "common-foundation-c4-probe-authorization-review-v1",
        )
        self.assertFalse(decision["implementation_allowed_now"])
        self.assertTrue(decision["supervisor_should_generate_prompt"])
        self.assertNotIn("implementation", decision["recommended_next_slice"])

    def test_future_probe_requires_separate_supervisor_prompt_and_review_acceptance(self) -> None:
        allowed = _packet()["future_probe_allowed_only_if"]
        self.assertTrue(allowed["separate_supervisor_prompt"])
        self.assertTrue(allowed["reviewed_decision_packet_accepted"])
        self.assertTrue(allowed["no_c3_regression"])
        self.assertTrue(allowed["no_c5_c6_unlock"])
        self.assertTrue(allowed["no_target_repo_writeback"])
        self.assertTrue(allowed["no_arbitrary_execution"])
        self.assertTrue(allowed["no_adapter_validation_controlled_command"])

    def test_future_probe_scope_is_single_fixed_safe_and_not_generalized(self) -> None:
        scope = _packet()["proposed_future_probe_scope"]
        self.assertEqual(scope["probe_name"], "single_hardcoded_devcockpitcore_local_no_write_diagnostic_probe")
        self.assertEqual(scope["probe_class"], "single_fixed_safe_c4_probe_candidate")
        self.assertIn("source-hardcoded allowlist", scope["command_source_policy"])
        self.assertIn("must not supply command strings", scope["config_policy"])
        self.assertEqual(scope["shell_policy"], "shell must remain false.")
        self.assertIn("must not run through controlled_runner_probe", scope["validation_policy"])
        self.assertIn("forbidden", scope["target_repo_policy"])
        self.assertIn("No scheduler", scope["scheduler_policy"])

    def test_forbidden_future_behavior_blocks_command_expansion_and_writeback(self) -> None:
        forbidden = _packet()["forbidden_future_probe_behavior"]
        for key in (
            "arbitrary_command_execution",
            "config_supplied_command_or_argv",
            "shell_true",
            "adapter_default_validation_execution",
            "adapters_validate_as_controlled_command",
            "target_repo_writeback",
            "cross_project_execution",
            "scheduler_or_autonomy",
            "credentials",
            "destructive_git",
            "force_push",
        ):
            with self.subTest(key=key):
                self.assertTrue(forbidden[key])

    def test_invariants_keep_no_implementation_surface(self) -> None:
        invariants = _packet()["invariants"]
        expected = {
            "c3_executable_ceiling_preserved",
            "exact_two_c3_command_keys",
            "no_third_c3_command",
            "no_c4_implementation",
            "no_generalized_runner",
            "no_target_repo_writeback",
            "no_scheduler_autonomy",
            "no_c5_c6_unlock",
            "no_adapter_validation_controlled_command",
            "no_arbitrary_execution",
        }
        self.assertEqual(set(invariants), expected)
        for key in expected:
            with self.subTest(key=key):
                self.assertTrue(invariants[key])

    def test_no_generalized_runner_module_or_shell_true_appears(self) -> None:
        self.assertFalse((SOURCE_ROOT / "runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "controlled_runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "command_registry.py").exists())
        source = CONTROLLED_PROBE_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("shell" + "=True", source)
        self.assertNotIn("Background" + "Scheduler", source)
        self.assertNotIn("schedule" + ".every(", source)
        self.assertNotIn("target" + "_repo_writeback = True", source)

    def test_next_route_and_alternatives_are_not_direct_implementation(self) -> None:
        data = _packet()
        allowed_next = {
            "common-foundation-c4-probe-authorization-review-v1",
            "common-foundation-validation-fixture-hygiene-v1",
            "controlled-runner-stop",
            "common-foundation-c4-design-followup-fix-v1",
        }
        self.assertIn(data["decision"]["recommended_next_slice"], allowed_next)
        self.assertNotIn("implementation", data["decision"]["recommended_next_slice"])
        self.assertEqual(
            set(data["alternatives"]),
            {"controlled-runner-stop", "validation-fixture-hygiene-first", "c4-design-followup-fix"},
        )

    def test_doc_records_decision_boundaries(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        normalized = " ".join(doc.split())
        for phrase in (
            "This is a decision packet.",
            "C3 remains the executable ceiling.",
            "C4 implementation remains unauthorized.",
            "The next slice should review this decision packet.",
            "Skipping directly from this packet to implementation is forbidden.",
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
                PACKET.read_text(encoding="utf-8"),
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


def _packet() -> dict[str, object]:
    return json.loads(PACKET.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
