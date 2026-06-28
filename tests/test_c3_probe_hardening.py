from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ControlledRunnerProbeError, default_probe, validate_probe


CANONICAL_PROBE = ROOT / "samples" / "controlled_runner_probes" / "controlled_runner_probe_result_v1_canonical.json"
CANONICAL_REVIEW = (
    ROOT / "samples" / "controlled_runner_probe_reviews" / "controlled_runner_probe_review_result_v1_canonical.json"
)
HARDENING = ROOT / "samples" / "c3_probe_hardening" / "c3_probe_hardening_v1.json"
REVIEW_CONFIG = ROOT / "samples" / "controlled_runner_probe_reviews" / "controlled_runner_probe_review_v1.json"


class C3ProbeHardeningTests(unittest.TestCase):
    def test_canonical_probe_result_json_parses(self) -> None:
        data = _load_json(CANONICAL_PROBE)
        self.assertEqual(data["schema_version"], "controlled_runner_probe_result.v1")
        self.assertEqual(data["summary"]["result"], "pass")
        self.assertEqual(data["repo"]["worktree_before"]["state"], "clean")
        self.assertEqual(data["repo"]["worktree_after"]["state"], "clean")

    def test_canonical_review_result_json_parses(self) -> None:
        data = _load_json(CANONICAL_REVIEW)
        self.assertEqual(data["schema_version"], "controlled_runner_probe_review_result.v1")
        self.assertEqual(data["acceptance"]["decision"], "accepted")
        self.assertEqual(data["acceptance"]["recommended_next_slice"], "supervisor-decision-needed")

    def test_hardening_artifact_contains_required_top_level_keys(self) -> None:
        data = _load_json(HARDENING)
        for key in (
            "schema_version",
            "generated_at",
            "project_key",
            "canonical_probe_result",
            "canonical_review_result",
            "decision",
            "remaining_constraints",
            "dirty_sample_interpretation",
            "safety_invariants",
            "summary",
            "next",
            "health",
        ):
            self.assertIn(key, data)
        self.assertEqual(data["schema_version"], "c3_probe_hardening.v1")

    def test_exactly_one_command_key_remains_allowed(self) -> None:
        review = _load_json(REVIEW_CONFIG)
        self.assertEqual(review["accepted_command_keys"], ["status_snapshot_help"])

    def test_unknown_command_key_still_fails_cleanly(self) -> None:
        probe = default_probe()
        probe["command_key"] = "other_command"
        with self.assertRaises(ControlledRunnerProbeError):
            validate_probe(probe)

    def test_config_command_fields_remain_rejected(self) -> None:
        for field in ("command", "executable", "argv", "args", "shell"):
            with self.subTest(field=field):
                probe = default_probe()
                probe[field] = True if field == "shell" else ["x"]
                with self.assertRaises(ControlledRunnerProbeError):
                    validate_probe(probe)

    def test_canonical_review_confirms_c4_c5_c6_locked(self) -> None:
        data = _load_json(CANONICAL_REVIEW)
        self.assertFalse(data["acceptance"]["c4_unlocked"])
        self.assertFalse(data["acceptance"]["c5_unlocked"])
        self.assertFalse(data["acceptance"]["c6_unlocked"])
        self.assertEqual(data["readiness"]["c4_scoped_repo_local_runner"], "locked")
        self.assertEqual(data["readiness"]["c5_cross_project_runner"], "locked")
        self.assertEqual(data["readiness"]["c6_scheduler_or_autonomy_loop"], "locked")

    def test_hardening_decision_does_not_claim_c4_readiness(self) -> None:
        data = _load_json(HARDENING)
        self.assertEqual(data["decision"], "accepted")
        self.assertEqual(data["c3_status"], "accepted")
        self.assertEqual(data["c4_status"], "locked")
        self.assertEqual(data["next"]["recommended_next_slice"], "supervisor-decision-needed")

    def test_dirty_sample_interpretation_is_documented(self) -> None:
        data = _load_json(HARDENING)
        interpretation = data["dirty_sample_interpretation"]
        self.assertIn("during_work_sample", interpretation)
        self.assertIn("canonical_acceptance_surface", interpretation)
        self.assertEqual(interpretation["result"], "documented_non_blocking_context")

    def test_no_raw_local_user_path_appears_in_canonical_samples(self) -> None:
        payload = "\n".join(path.read_text(encoding="utf-8") for path in (CANONICAL_PROBE, CANONICAL_REVIEW, HARDENING))
        self.assertNotIn(r"C:\Users\thank", payload)
        self.assertNotIn("C:/Users/thank", payload)

    def test_no_paste_ready_next_agent_prompt_is_emitted(self) -> None:
        payload = "\n".join(path.read_text(encoding="utf-8") for path in (CANONICAL_REVIEW, HARDENING))
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)

    def test_no_generalized_runner_module_is_created(self) -> None:
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "controlled_runner.py").exists())

    def test_no_shell_true_appears_in_changed_source_files(self) -> None:
        source = (ROOT / "src" / "dev_cockpit" / "controlled_runner_probe_review.py").read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
