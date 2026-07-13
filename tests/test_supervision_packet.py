from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from dev_cockpit.supervision_packet import (
    SupervisionPacketError,
    build_supervision_packet,
    dumps_packet,
    load_manifest,
    load_packet,
    main,
    render_packet_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "samples" / "supervision_packets" / "task_report_manifest_v1.json"
PACKET_PATH = ROOT / "samples" / "supervision_packets" / "cross_project_supervision_packet_v1.json"
MARKDOWN_PATH = ROOT / "samples" / "supervision_packets" / "cross_project_supervision_packet_v1.md"


class SupervisionPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_manifest(MANIFEST_PATH)

    def test_fixture_packet_has_two_projects_four_reports_and_policy_order(self) -> None:
        packet = build_supervision_packet(
            self.manifest,
            repo_root=ROOT,
            manifest_path="samples/supervision_packets/task_report_manifest_v1.json",
        )

        self.assertEqual("cross_project_supervision_packet.v1", packet["schema_version"])
        self.assertEqual(2, packet["coverage"]["project_count"])
        self.assertEqual(4, packet["coverage"]["report_count"])
        self.assertFalse(packet["coverage"]["live_coverage"])
        self.assertEqual(
            [
                "true_stop_or_required_failure",
                "user_authorization_or_material_decision",
                "active_safe_continuation",
            ],
            [task["attention_class"] for task in packet["global_attention_queue"]],
        )
        self.assertEqual([1, 2, 3], [task["global_rank"] for task in packet["global_attention_queue"]])
        self.assertEqual(1, len(packet["closed_or_informational"]))
        self.assertEqual(
            "closed_or_informational",
            packet["closed_or_informational"][0]["attention_class"],
        )
        self.assertTrue(
            all(task["executable"] is False for task in self._tasks(packet))
        )
        self.assertEqual(
            "attention_and_review_priority_only",
            packet["scope_boundary"]["global_rank_meaning"],
        )
        self.assertFalse(packet["scope_boundary"]["execution_schedule"])

    def test_project_worksets_reproject_exact_global_task_id_set(self) -> None:
        packet = build_supervision_packet(self.manifest, repo_root=ROOT)
        task_ids = {task["task_id"] for task in self._tasks(packet)}
        projected = [
            task_id
            for workset in packet["project_worksets"]
            for task_id in (
                workset["active_task_ids"]
                + workset["closed_or_informational_task_ids"]
            )
        ]

        self.assertEqual(task_ids, set(projected))
        self.assertEqual(len(task_ids), len(projected))
        alpha, beta = packet["project_worksets"]
        self.assertEqual("alpha-project", alpha["project_key"])
        self.assertEqual("beta-project", beta["project_key"])
        self.assertIn(alpha["project_local_first_task_id"], alpha["active_task_ids"])
        self.assertIn(beta["project_local_first_task_id"], beta["active_task_ids"])
        self.assertEqual(1, len(beta["closed_or_informational_task_ids"]))

    def test_task_identity_keeps_different_threads_and_lanes_separate(self) -> None:
        packet = build_supervision_packet(self.manifest, repo_root=ROOT)
        alpha = [
            task for task in self._tasks(packet) if task["project_key"] == "alpha-project"
        ]

        self.assertEqual(2, len(alpha))
        self.assertEqual(2, len({task["task_id"] for task in alpha}))
        self.assertEqual(2, len({task["thread_id"] for task in alpha}))
        self.assertEqual(2, len({task["lane_id"] for task in alpha}))

    def test_generation_is_deterministic_and_matches_tracked_artifacts(self) -> None:
        first = build_supervision_packet(
            self.manifest,
            repo_root=ROOT,
            manifest_path="samples/supervision_packets/task_report_manifest_v1.json",
        )
        second = build_supervision_packet(
            self.manifest,
            repo_root=ROOT,
            manifest_path="samples/supervision_packets/task_report_manifest_v1.json",
        )

        self.assertEqual(first, second)
        self.assertEqual(dumps_packet(first, pretty=True), PACKET_PATH.read_text(encoding="utf-8"))
        self.assertEqual(render_packet_markdown(first), MARKDOWN_PATH.read_text(encoding="utf-8"))
        self.assertEqual(first, load_packet(PACKET_PATH))

    def test_manifest_nested_duplicate_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(
                '{"schema_version":"task_report_manifest.v1",'
                '"artifact_id":"fixture","generated_at":"2026-07-13T06:30:00Z",'
                '"reports":[{"project_key":"alpha","project_key":"beta"}]}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SupervisionPacketError, "duplicate JSON key: project_key"):
                load_manifest(path)

    def test_manifest_hash_change_fails_closed(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["reports"][0]["content_sha256"] = "0" * 64

        with self.assertRaisesRegex(SupervisionPacketError, "report hash mismatch"):
            build_supervision_packet(manifest, repo_root=ROOT)

    def test_source_report_change_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "samples" / "supervision_packets" / "reports"
            target.parent.mkdir(parents=True)
            shutil.copytree(MANIFEST_PATH.parent / "reports", target)
            changed = target / "alpha_safe_continuation.txt"
            changed.write_text(changed.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")

            with self.assertRaisesRegex(SupervisionPacketError, "report hash mismatch"):
                build_supervision_packet(self.manifest, repo_root=root)

    def test_duplicate_task_identity_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        duplicate = copy.deepcopy(manifest["reports"][0])
        duplicate["report_path"] = manifest["reports"][0]["report_path"]
        manifest["reports"].append(duplicate)

        with self.assertRaisesRegex(SupervisionPacketError, "duplicate task identity"):
            build_supervision_packet(manifest, repo_root=ROOT)

    def test_cli_writes_strict_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_json = Path(temporary) / "packet.json"
            output_md = Path(temporary) / "packet.md"
            result = main(
                [
                    "--repo-root",
                    str(ROOT),
                    "--manifest",
                    "samples/supervision_packets/task_report_manifest_v1.json",
                    "--output-json",
                    str(output_json),
                    "--output-markdown",
                    str(output_md),
                    "--pretty",
                ]
            )

            self.assertEqual(0, result)
            self.assertEqual(PACKET_PATH.read_bytes(), output_json.read_bytes())
            self.assertEqual(MARKDOWN_PATH.read_bytes(), output_md.read_bytes())

    @staticmethod
    def _tasks(packet: dict[str, object]) -> list[dict[str, object]]:
        return [
            *packet["global_attention_queue"],  # type: ignore[list-item]
            *packet["closed_or_informational"],  # type: ignore[list-item]
        ]


if __name__ == "__main__":
    unittest.main()
