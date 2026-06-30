from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEYS


HARDENING = (
    ROOT
    / "samples"
    / "c4_scoped_runner_design_hardening"
    / "c4_scoped_runner_design_hardening_v1.json"
)
DOC = ROOT / "docs" / "design" / "C4_SCOPED_RUNNER_DESIGN_HARDENING_V1.md"
PROJECT_CONTEXT = ROOT / "docs" / "project-context.md"
SOURCE_ROOT = ROOT / "src" / "dev_cockpit"
CONTROLLED_PROBE_SOURCE = SOURCE_ROOT / "controlled_runner_probe.py"


class C4ScopedRunnerDesignHardeningTests(unittest.TestCase):
    def test_hardening_json_parses_and_has_required_top_level_keys(self) -> None:
        data = _hardening()
        required = {
            "schema_version",
            "generated_at",
            "project_key",
            "source_design_artifact",
            "source_design_review_artifact",
            "reviewed_design_commit",
            "design_review_commit",
            "current_executable_ceiling",
            "c4_design_state",
            "hardening_status",
            "context_sync",
            "invariants",
            "next_decision",
            "summary",
        }
        self.assertEqual(data["schema_version"], "c4_scoped_runner_design_hardening.v1")
        self.assertTrue(required.issubset(data))

    def test_design_state_is_accepted_design_only_without_implementation(self) -> None:
        state = _hardening()["c4_design_state"]
        self.assertTrue(state["design_accepted"])
        self.assertTrue(state["design_only"])
        self.assertFalse(state["implementation_authorized"])
        self.assertFalse(state["execution_added"])
        self.assertEqual(state["command_keys_added"], [])

    def test_current_executable_ceiling_remains_c3_with_exact_two_keys(self) -> None:
        ceiling = _hardening()["current_executable_ceiling"]
        expected = ["status_snapshot_help", "adapters_validate_help"]
        self.assertEqual(ceiling["capability_level"], "C3")
        self.assertEqual(ceiling["production_command_keys"], expected)
        self.assertEqual(ceiling["production_command_count"], 2)
        self.assertEqual(ceiling["c3_status"], "freeze_ready")
        self.assertEqual(ALLOWED_COMMAND_KEYS, tuple(expected))

    def test_invariants_keep_capability_surface_locked(self) -> None:
        invariants = _hardening()["invariants"]
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
                self.assertIs(invariants[key], True)

    def test_no_generalized_runner_module_or_shell_true_appears(self) -> None:
        self.assertFalse((SOURCE_ROOT / "runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "controlled_runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "command_registry.py").exists())
        source = CONTROLLED_PROBE_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("shell" + "=True", source)
        self.assertNotIn("Background" + "Scheduler", source)
        self.assertNotIn("schedule" + ".every(", source)
        self.assertNotIn("target" + "_repo_writeback = True", source)

    def test_target_writeback_scheduler_and_c5_c6_remain_forbidden(self) -> None:
        state = _hardening()["c4_design_state"]
        self.assertFalse(state["target_repo_writeback_allowed"])
        self.assertFalse(state["scheduler_allowed"])
        self.assertTrue(state["c5_c6_locked"])
        invariants = _hardening()["invariants"]
        self.assertTrue(invariants["no_target_repo_writeback"])
        self.assertTrue(invariants["no_scheduler_autonomy"])
        self.assertTrue(invariants["no_c5_c6_unlock"])

    def test_context_sync_resolves_project_context_debt_narrowly(self) -> None:
        data = _hardening()
        sync = data["context_sync"]
        self.assertTrue(sync["docs_project_context_checked"])
        self.assertTrue(sync["docs_project_context_updated"])
        self.assertFalse(sync["stale_context_debt_remaining"])
        context = PROJECT_CONTEXT.read_text(encoding="utf-8")
        normalized = " ".join(context.split())
        self.assertIn("c4-scoped-runner-design-hardening-v1", context)
        self.assertIn("C3 remains the executable ceiling", normalized)
        self.assertIn("C4 is limited to one repo-local validation-pack probe", normalized)

    def test_next_decision_is_decision_packet_stop_or_fix_not_implementation(self) -> None:
        next_decision = _hardening()["next_decision"]
        self.assertEqual(
            next_decision["recommended_next_slice"],
            "common-foundation-c4-probe-decision-packet-v1",
        )
        self.assertTrue(next_decision["supervisor_decision_required"])
        self.assertIn(
            "common-foundation-c4-probe-decision-packet-v1",
            next_decision["allowed_next_actions"],
        )
        self.assertIn("controlled-runner-stop", next_decision["allowed_next_actions"])
        self.assertIn(
            "common-foundation-c4-design-followup-fix-v1",
            next_decision["allowed_next_actions"],
        )
        self.assertNotIn("direct C4 implementation", next_decision["allowed_next_actions"])
        self.assertIn("direct C4 implementation", next_decision["forbidden_next_actions"])
        self.assertIn(
            "adapter validation as controlled runner command behavior",
            next_decision["forbidden_next_actions"],
        )

    def test_doc_records_required_hardening_boundaries(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        normalized = " ".join(doc.split())
        for phrase in (
            "This is hardening, not implementation.",
            "C3 remains the executable ceiling.",
            "C4 implementation remains prohibited.",
            "C5 and C6 remain locked.",
            "Target repository writeback remains forbidden.",
            "No scheduler",
            "Arbitrary execution remains forbidden.",
            "Adapter validation may still be run by an agent as ordinary repository validation evidence.",
            "That route is decision-only.",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)

    def test_artifacts_do_not_use_raw_local_identity_or_prompt_text(self) -> None:
        payload = "\n".join(
            [
                HARDENING.read_text(encoding="utf-8"),
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

    def test_summary_records_all_hardening_gates_done(self) -> None:
        summary = _hardening()["summary"]
        self.assertEqual(summary["result"], "pass")
        self.assertEqual(summary["done"], 14)
        self.assertEqual(summary["total"], 14)
        self.assertEqual(summary["unknown"], 0)
        self.assertEqual(summary["missing"], 0)


def _hardening() -> dict[str, object]:
    return json.loads(HARDENING.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
