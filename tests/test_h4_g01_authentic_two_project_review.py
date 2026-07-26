from __future__ import annotations

import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.current_observation import load_current_observation
from dev_cockpit.supervision_packet import (
    SupervisionPacketError,
    load_packet_with_manifest,
)


PACKAGE = (
    ROOT
    / "artifacts"
    / "review"
    / "h4-g01-authentic-two-project-review-v1"
)
H3_PACKAGE = (
    ROOT
    / "artifacts"
    / "review"
    / "h3-real-current-nlmytgen-point-in-time-v1"
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


class H4G01AuthenticTwoProjectReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.package_module = runpy.run_path(
            str(PACKAGE / "generate_package.py"),
            run_name="h4_g01_authentic_two_project_review_test_module",
        )

    def test_two_receipts_and_source_bound_packet_preserve_project_local_state(
        self,
    ) -> None:
        observations = {
            project_key: load_current_observation(
                PACKAGE / "receipts" / f"{project_key}_current_observation_v1.json"
            )
            for project_key in ("clippipegen", "nlmytgen")
        }
        self.assertEqual(
            {
                key: receipt["observation"]["derived"]
                for key, receipt in observations.items()
            },
            {
                "clippipegen": {"actual": True, "clean": True, "stable": True},
                "nlmytgen": {"actual": True, "clean": False, "stable": True},
            },
        )
        for receipt in observations.values():
            self.assertFalse(receipt["scope_boundary"]["write_performed"])
            self.assertFalse(receipt["scope_boundary"]["target_repository_writeback"])
            self.assertFalse(
                receipt["scope_boundary"]["arbitrary_command_execution"]
            )

        packet = load_packet_with_manifest(
            PACKAGE / "packet" / "cross_project_supervision_packet_v1.json",
            PACKAGE / "manifest" / "task_report_manifest_v1.json",
            repo_root=ROOT,
        )
        self.assertEqual(2, packet["coverage"]["project_count"])
        self.assertEqual(2, packet["coverage"]["report_count"])
        self.assertEqual(2, packet["coverage"]["active_task_count"])
        self.assertFalse(packet["coverage"]["live_coverage"])
        self.assertFalse(packet["scope_boundary"]["executable"])
        self.assertEqual(
            "attention_and_review_priority_only",
            packet["scope_boundary"]["global_rank_meaning"],
        )

        tasks = packet["global_attention_queue"]
        self.assertEqual(
            ["clippipegen", "nlmytgen"],
            [task["project_key"] for task in tasks],
        )
        self.assertTrue(
            all(task["attention_class"] == "active_safe_continuation" for task in tasks)
        )
        self.assertTrue(all(task["executable"] is False for task in tasks))

        worksets = {
            item["project_key"]: item for item in packet["project_worksets"]
        }
        self.assertEqual({"clippipegen", "nlmytgen"}, set(worksets))
        self.assertNotEqual("none", worksets["clippipegen"]["safe_continuation"])
        self.assertNotEqual("none", worksets["nlmytgen"]["safe_continuation"])
        self.assertEqual("none", worksets["clippipegen"]["user_or_supervisor_gate"])
        self.assertEqual("none", worksets["nlmytgen"]["user_or_supervisor_gate"])

    def test_external_regeneration_is_exact_and_leaves_h3_unchanged(self) -> None:
        h3_before = _tree_bytes(H3_PACKAGE)
        with (
            tempfile.TemporaryDirectory(prefix="h4-g01-stage-a-") as stage_a,
            tempfile.TemporaryDirectory(prefix="h4-g01-stage-b-") as stage_b,
        ):
            outputs_a = self.package_module["generate"](stage_a)
            outputs_b = self.package_module["generate"](stage_b)
            expected_paths = set(self.package_module["DERIVED_OUTPUTS"])
            self.assertEqual(expected_paths, set(outputs_a))
            self.assertEqual(outputs_a, outputs_b)
            self.assertEqual(
                {
                    path: (PACKAGE / path).read_bytes()
                    for path in expected_paths
                },
                outputs_a,
            )
        self.package_module["verify_committed_package"]()
        self.assertEqual(h3_before, _tree_bytes(H3_PACKAGE))

    def test_mutated_report_is_rejected_before_packet_projection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="h4-g01-report-drift-") as temp_dir:
            reconstruction_root = Path(temp_dir) / "reconstruction-root"
            self.package_module["_prepare_reconstruction_root"](
                reconstruction_root
            )
            source_path = (
                reconstruction_root
                / self.package_module["REPORT_PATHS"]["clippipegen"]
            )
            source_path.write_bytes(source_path.read_bytes() + b"\nDRIFT\n")
            with self.assertRaisesRegex(
                SupervisionPacketError,
                "report hash mismatch",
            ):
                self.package_module["_reconstruct"](reconstruction_root)

    def test_console_and_readback_remain_observer_only(self) -> None:
        priority = _json(PACKAGE / "dashboard" / "priority_readback.json")
        self.assertEqual(2, priority["surface"]["priority_count"])
        self.assertFalse(priority["surface"]["executable"])
        self.assertEqual(
            "accepted", priority["surface"]["user_visual_acceptance"]
        )
        self.assertEqual(
            "attention_and_review_priority_only",
            priority["supervision_packet"]["scope_boundary"][
                "global_rank_meaning"
            ],
        )
        self.assertTrue(
            all(item["executable"] is False for item in priority["priorities"])
        )

        actions = _json(PACKAGE / "dashboard" / "review_actions.json")
        self.assertTrue(
            all(
                action["executable"] is False
                for action in actions["review_actions"]
            )
        )

        readback = _json(PACKAGE / "package_readback_v1.json")
        self.assertEqual(
            ["clippipegen", "nlmytgen"],
            readback["packet"]["project_keys"],
        )
        self.assertTrue(readback["scope_boundary"]["point_in_time"])
        self.assertFalse(readback["scope_boundary"]["live"])
        self.assertTrue(readback["scope_boundary"]["observer_only"])
        self.assertFalse(readback["scope_boundary"]["executable"])
        self.assertFalse(
            readback["scope_boundary"]["source_repository_writeback"]
        )
        self.assertFalse(readback["scope_boundary"]["main_integration"])
        self.assertFalse(readback["scope_boundary"]["deployment"])

        package_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in PACKAGE.rglob("*")
            if path.is_file()
        )
        source_root = "C:" + "\\Users\\" + "thank\\Storage\\Media Contents Projects\\"
        for forbidden in (
            "point-in-time-source-report-exported",
            "devcockpitcore-h3-g02-real-current-observation-v1",
            source_root + "NLMYTGen",
            source_root + "ClipPipeGen",
        ):
            self.assertNotIn(forbidden, package_text)


if __name__ == "__main__":
    unittest.main()
