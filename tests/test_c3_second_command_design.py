from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEYS, default_probe, validate_probe
from dev_cockpit.controlled_runner_probe_review import default_review, validate_review


DESIGN = ROOT / "samples" / "c3_second_command_design" / "c3_second_command_design_v1.json"
DOC = ROOT / "docs" / "design" / "C3_SECOND_COMMAND_DESIGN_V1.md"


class C3SecondCommandDesignTests(unittest.TestCase):
    def test_design_packet_parses(self) -> None:
        data = _design()
        self.assertEqual(data["schema_version"], "c3_second_command_design.v1")
        self.assertEqual(data["implementation_status"], "design_only")
        self.assertFalse(data["implementation_allowed_now"])

    def test_design_recommends_second_command_without_implementing_it(self) -> None:
        data = _design()
        self.assertEqual(data["decision"], "recommend_second_command")
        self.assertEqual(data["selected_candidate"]["command_key"], "adapters_validate_help")
        self.assertEqual(data["selected_candidate"]["recommendation"], "propose_for_later_supervisor_prompt")
        self.assertEqual(data["next"]["recommended_next_slice"], "supervisor-decision-needed")

    def test_candidate_set_matches_supervisor_options(self) -> None:
        keys = {item["command_key"] for item in _design()["candidate_evaluations"]}
        self.assertEqual(
            keys,
            {
                "adapters_validate_help",
                "report_normalizer_help",
                "gate_classifier_help",
                "validation_pack_help",
                "cross_project_smoke_help",
                "controlled_runner_probe_review_help",
                "no_second_command_stop",
            },
        )

    def test_future_probe_requirements_keep_c4_c5_c6_locked(self) -> None:
        requirements = _design()["future_probe_requirements"]
        self.assertTrue(requirements["supervisor_prompt_required"])
        self.assertTrue(requirements["one_fixed_help_command_only"])
        self.assertTrue(requirements["shell_false"])
        self.assertFalse(requirements["target_repo_writeback"])
        self.assertFalse(requirements["credentials_required"])
        self.assertFalse(requirements["network_required"])
        self.assertFalse(requirements["c4_unlocked"])
        self.assertFalse(requirements["c5_unlocked"])
        self.assertFalse(requirements["c6_unlocked"])

    def test_design_default_probe_still_uses_status_snapshot_help(self) -> None:
        probe = validate_probe(default_probe())
        self.assertEqual(probe["command_key"], "status_snapshot_help")
        self.assertEqual(ALLOWED_COMMAND_KEYS, ("status_snapshot_help", "adapters_validate_help"))

    def test_probe_review_still_accepts_exactly_one_command_key(self) -> None:
        review = validate_review(default_review())
        self.assertEqual(review["accepted_command_keys"], ["status_snapshot_help"])

    def test_design_does_not_create_second_probe_sample_or_runner_module(self) -> None:
        self.assertFalse((ROOT / "samples" / "controlled_runner_probes" / "controlled_runner_second_probe_v1.json").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "controlled_runner.py").exists())

    def test_no_paste_ready_prompt_markers(self) -> None:
        payload = DESIGN.read_text(encoding="utf-8") + "\n" + DOC.read_text(encoding="utf-8")
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)


def _design() -> dict[str, object]:
    return json.loads(DESIGN.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
