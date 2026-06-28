from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe_review import (
    RESULT_SCHEMA_VERSION,
    REVIEW_SCHEMA_VERSION,
    ControlledRunnerProbeReviewError,
    default_review,
    load_review,
    review_probe_result,
    validate_review,
)


REVIEW_SAMPLE = ROOT / "samples" / "controlled_runner_probe_reviews" / "controlled_runner_probe_review_v1.json"
REVIEW_RESULT_SAMPLE = (
    ROOT / "samples" / "controlled_runner_probe_reviews" / "controlled_runner_probe_review_result_v1.json"
)
DIRTY_PROBE_RESULT = ROOT / "samples" / "controlled_runner_probes" / "controlled_runner_probe_result_v1.json"
POST_COMMIT_PROBE_RESULT = (
    ROOT / "samples" / "controlled_runner_probes" / "controlled_runner_probe_result_v1_post_commit.json"
)


class ControlledRunnerProbeReviewTests(unittest.TestCase):
    def test_review_config_loads_and_validates(self) -> None:
        review = load_review(REVIEW_SAMPLE)
        self.assertEqual(review["schema_version"], REVIEW_SCHEMA_VERSION)
        self.assertEqual(review["accepted_command_keys"], ["status_snapshot_help"])

    def test_review_accepts_status_snapshot_help_when_required_evidence_is_present(self) -> None:
        result = review_probe_result(
            validate_review(default_review()),
            _load_json(POST_COMMIT_PROBE_RESULT),
            dirty_sample_result=_load_json(DIRTY_PROBE_RESULT),
            generated_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(result["schema_version"], RESULT_SCHEMA_VERSION)
        self.assertEqual(result["acceptance"]["decision"], "accepted_with_constraints")
        self.assertTrue(result["acceptance"]["c3_accepted"])
        self.assertFalse(result["acceptance"]["c4_unlocked"])
        self.assertFalse(result["acceptance"]["c5_unlocked"])
        self.assertFalse(result["acceptance"]["c6_unlocked"])

    def test_review_rejects_unknown_command_key(self) -> None:
        probe = _mutated_probe_result()
        probe["probe"]["command_key"] = "other_command"
        probe["command"]["command_key"] = "other_command"
        result = review_probe_result(validate_review(default_review()), probe)
        self.assertEqual(result["evidence_checks"]["command_key_fixed"]["result"], "fail")
        self.assertEqual(result["acceptance"]["decision"], "rejected")

    def test_review_flags_missing_shell_gate(self) -> None:
        probe = _mutated_probe_result()
        del probe["safety_gates"]["shell_gate"]
        result = review_probe_result(validate_review(default_review()), probe)
        self.assertEqual(result["evidence_checks"]["shell_false"]["result"], "fail")
        self.assertEqual(result["evidence_checks"]["required_safety_gates_present"]["result"], "fail")

    def test_review_flags_missing_timeout(self) -> None:
        probe = _mutated_probe_result()
        del probe["command"]["timeout_seconds"]
        result = review_probe_result(validate_review(default_review()), probe)
        self.assertEqual(result["evidence_checks"]["timeout_present"]["result"], "fail")
        self.assertEqual(result["acceptance"]["decision"], "fix_required")

    def test_review_rejects_target_repo_writeback_true(self) -> None:
        probe = _mutated_probe_result()
        probe["authority"]["target_repo_writeback"] = True
        result = review_probe_result(validate_review(default_review()), probe)
        self.assertEqual(result["evidence_checks"]["target_repo_writeback_false"]["result"], "fail")
        self.assertEqual(result["acceptance"]["decision"], "rejected")

    def test_review_rejects_c4_c5_c6_unlock(self) -> None:
        for field in ("c4_unlocked", "c5_unlocked", "c6_unlocked"):
            with self.subTest(field=field):
                probe = _mutated_probe_result()
                probe["authority"][field] = True
                result = review_probe_result(validate_review(default_review()), probe)
                self.assertEqual(result["evidence_checks"]["c4_c5_c6_locked"]["result"], "fail")
                self.assertEqual(result["acceptance"]["decision"], "rejected")

    def test_review_handles_dirty_sample_with_post_commit_clean_evidence(self) -> None:
        result = review_probe_result(
            validate_review(default_review()),
            _load_json(POST_COMMIT_PROBE_RESULT),
            dirty_sample_result=_load_json(DIRTY_PROBE_RESULT),
            dirty_sample_path=DIRTY_PROBE_RESULT,
            generated_at="2026-01-01T00:00:00Z",
        )
        self.assertTrue(result["sample_interpretation"]["during_work_sample_dirty_warning"])
        self.assertTrue(result["sample_interpretation"]["post_commit_clean_probe_available"])
        self.assertEqual(
            result["sample_interpretation"]["dirty_warning_handling"],
            "accepted_as_expected_artifact_generation",
        )

    def test_review_result_summary_includes_meter_fields(self) -> None:
        result = review_probe_result(
            validate_review(default_review()),
            _load_json(POST_COMMIT_PROBE_RESULT),
            generated_at="2026-01-01T00:00:00Z",
        )
        for field in ("done", "total", "unknown", "meter", "missing"):
            self.assertIn(field, result["summary"])

    def test_no_paste_ready_next_agent_prompt_is_emitted(self) -> None:
        result = review_probe_result(
            validate_review(default_review()),
            _load_json(POST_COMMIT_PROBE_RESULT),
            generated_at="2026-01-01T00:00:00Z",
        )
        payload = json.dumps(result)
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)

    def test_review_config_rejects_new_command_key(self) -> None:
        review = default_review()
        review["accepted_command_keys"] = ["status_snapshot_help", "other_command"]
        with self.assertRaises(ControlledRunnerProbeReviewError):
            validate_review(review)

    def test_no_general_runner_module_exists(self) -> None:
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "controlled_runner.py").exists())

    def test_sample_review_result_json_is_valid_when_present(self) -> None:
        if not REVIEW_RESULT_SAMPLE.exists():
            self.skipTest("sample review result has not been generated")
        data = _load_json(REVIEW_RESULT_SAMPLE)
        self.assertEqual(data["schema_version"], RESULT_SCHEMA_VERSION)
        self.assertNotIn(r"C:\Users\thank", json.dumps(data))


def _mutated_probe_result() -> dict[str, object]:
    return copy.deepcopy(_load_json(POST_COMMIT_PROBE_RESULT))


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
