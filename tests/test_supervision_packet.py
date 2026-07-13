from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from dev_cockpit.supervision_packet import (
    _project_worksets,
    _task_sort_key,
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

    def test_loaded_packet_rejects_known_unknown_key_payloads(self) -> None:
        cases = {
            "packet_execution_schedule": (
                lambda packet: packet.__setitem__("execution_schedule", True),
                r"unexpected keys: \['execution_schedule'\]",
            ),
            "task_action": (
                lambda packet: packet["global_attention_queue"][0].__setitem__(
                    "action",
                    {"executable": True, "command": "echo should-not-be-accepted"},
                ),
                r"unexpected keys: \['action'\]",
            ),
            "next_state_executable": (
                lambda packet: packet["global_attention_queue"][0]["next_state"].__setitem__(
                    "executable", True
                ),
                r"unexpected keys: \['executable'\]",
            ),
        }

        for name, (mutate, pattern) in cases.items():
            with self.subTest(name=name):
                self._assert_loaded_mutation_rejected(mutate, pattern)

    def test_unknown_key_rejection_is_value_independent(self) -> None:
        for value in (None, False, 0, "harmless", {}, []):
            with self.subTest(value=value):
                self._assert_loaded_mutation_rejected(
                    lambda packet, value=value: packet.__setitem__(
                        "harmless_metadata", value
                    ),
                    r"unexpected keys: \['harmless_metadata'\]",
                )

    def test_active_and_closed_tasks_reject_unknown_keys(self) -> None:
        for collection in ("global_attention_queue", "closed_or_informational"):
            for surface in ("task", "next_state"):
                with self.subTest(collection=collection, surface=surface):
                    def mutate(packet, collection=collection, surface=surface):
                        target = packet[collection][0]
                        if surface == "next_state":
                            target = target["next_state"]
                        target["harmless_metadata"] = None

                    self._assert_loaded_mutation_rejected(
                        mutate,
                        r"unexpected keys: \['harmless_metadata'\]",
                    )

    def test_required_keys_are_rejected_with_sorted_diagnostics(self) -> None:
        def mutate_packet(packet) -> None:
            packet.pop("producer")
            packet.pop("artifact_id")
            packet["zeta"] = None
            packet["alpha"] = None

        self._assert_loaded_mutation_rejected(
            mutate_packet,
            r"packet keys are invalid; missing keys: \['artifact_id', 'producer'\]; "
            r"unexpected keys: \['alpha', 'zeta'\]",
        )
        self._assert_loaded_mutation_rejected(
            lambda packet: packet["global_attention_queue"][0].pop("outcome_summary"),
            r"missing keys: \['outcome_summary'\]",
        )
        self._assert_loaded_mutation_rejected(
            lambda packet: packet["global_attention_queue"][0]["next_state"].pop("owner"),
            r"missing keys: \['owner'\]",
        )

    def test_exact_key_shape_prepass_precedes_value_validation(self) -> None:
        def invalid_schema_and_unknown_task_key(packet) -> None:
            packet["schema_version"] = "wrong"
            packet["global_attention_queue"][0]["action"] = {"executable": True}

        self._assert_loaded_mutation_rejected(
            invalid_schema_and_unknown_task_key,
            r"packet\.global_attention_queue\[0\] keys are invalid.*"
            r"unexpected keys: \['action'\]",
        )

        def invalid_first_task_and_later_unknown_key(packet) -> None:
            packet["global_attention_queue"][0]["executable"] = True
            packet["global_attention_queue"][1]["harmless_metadata"] = None

        self._assert_loaded_mutation_rejected(
            invalid_first_task_and_later_unknown_key,
            r"packet\.global_attention_queue\[1\] keys are invalid.*"
            r"unexpected keys: \['harmless_metadata'\]",
        )

    def test_json_object_key_order_is_not_significant(self) -> None:
        def reversed_object(value):
            return dict(reversed(list(value.items())))

        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        packet = reversed_object(packet)
        for collection in ("global_attention_queue", "closed_or_informational"):
            reordered_tasks = []
            for task in packet[collection]:
                reordered_task = reversed_object(task)
                reordered_task["next_state"] = reversed_object(
                    reordered_task["next_state"]
                )
                reordered_tasks.append(reordered_task)
            packet[collection] = reordered_tasks

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reordered-packet.json"
            path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
            loaded = load_packet(path)

        self.assertEqual(packet, loaded)

    def test_recommended_slice_null_remains_valid(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        packet["global_attention_queue"][0]["next_state"]["recommended_slice"] = None

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nullable-recommended-slice.json"
            path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
            loaded = load_packet(path)

        self.assertIsNone(
            loaded["global_attention_queue"][0]["next_state"]["recommended_slice"]
        )

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

    def test_loaded_packet_rejects_source_binding_mutations(self) -> None:
        cases = {
            "binding_removed": lambda packet: packet["source_bindings"].pop(),
            "binding_duplicated": lambda packet: packet["source_bindings"].append(
                copy.deepcopy(packet["source_bindings"][0])
            ),
            "project": lambda packet: packet["source_bindings"][0].__setitem__(
                "project_key", "wrong-project"
            ),
            "path": lambda packet: packet["source_bindings"][0].__setitem__(
                "report_path", "samples/wrong.txt"
            ),
            "hash": lambda packet: packet["source_bindings"][0].__setitem__(
                "content_sha256", "0" * 64
            ),
            "required": lambda packet: packet["source_bindings"][0].__setitem__(
                "required", not packet["source_bindings"][0]["required"]
            ),
            "required_type": lambda packet: packet["source_bindings"][0].__setitem__(
                "required", 1
            ),
            "evidence": lambda packet: packet["source_bindings"][0].__setitem__(
                "evidence_class", "changed"
            ),
            "authority": lambda packet: packet["source_bindings"][0].__setitem__(
                "authority_basis", "changed"
            ),
            "status": lambda packet: packet["source_bindings"][0].__setitem__(
                "binding_status", "unchecked"
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                self._assert_loaded_mutation_rejected(mutate, "source bindings")

    def test_loaded_packet_rejects_identity_class_and_collection_mutations(self) -> None:
        identity_fields = ("project_key", "thread_id", "lane_id", "slice_id", "artifact_id")
        for field in identity_fields:
            with self.subTest(identity_field=field):
                self._assert_loaded_mutation_rejected(
                    lambda packet, field=field: packet["global_attention_queue"][0].__setitem__(
                        field, "changed"
                    ),
                    "task_id does not match identity",
                )
        cases = {
            "task_id": (
                lambda packet: packet["global_attention_queue"][0].__setitem__("task_id", "task-wrong"),
                "task_id does not match identity",
            ),
            "precedence": (
                lambda packet: packet["global_attention_queue"][0].__setitem__("attention_precedence", 99),
                "attention_precedence",
            ),
            "class": (
                lambda packet: packet["global_attention_queue"][0].__setitem__("attention_class", "active_safe_continuation"),
                "attention_precedence",
            ),
            "rank_type": (
                lambda packet: packet["global_attention_queue"][0].__setitem__("global_rank", True),
                "global_rank",
            ),
            "active_closed_collection": (
                lambda packet: (
                    packet.__setitem__("global_attention_queue", [packet["closed_or_informational"][0]]),
                    packet.__setitem__("closed_or_informational", packet["global_attention_queue"][1:]),
                ),
                "wrong collection|global ranks",
            ),
        }
        for name, (mutate, pattern) in cases.items():
            with self.subTest(name=name):
                self._assert_loaded_mutation_rejected(mutate, pattern)

        def reorder(packet: dict[str, object]) -> None:
            queue = packet["global_attention_queue"]
            queue[0], queue[1] = queue[1], queue[0]
            queue[0]["global_rank"], queue[1]["global_rank"] = 1, 2

        self._assert_loaded_mutation_rejected(reorder, "queue order")

    def test_coherent_attention_projection_cannot_override_gate_semantics(self) -> None:
        def mutate(packet: dict[str, object]) -> None:
            active = packet["global_attention_queue"]
            closed = packet["closed_or_informational"]
            target = active[0]
            target["attention_class"] = "active_safe_continuation"
            target["attention_precedence"] = 4
            active.sort(key=_task_sort_key)
            for rank, task in enumerate(active, start=1):
                task["global_rank"] = rank
            packet["project_worksets"] = _project_worksets(
                [*active, *closed],
                active,
                closed,
            )

        self._assert_loaded_mutation_rejected(mutate, "does not match gate semantics")

    def test_loaded_packet_rejects_workset_projection_mutations(self) -> None:
        cases = {
            "cross_project_swap": lambda packet: (
                packet["project_worksets"][0]["active_task_ids"].__setitem__(
                    0, packet["project_worksets"][1]["active_task_ids"][0]
                ),
                packet["project_worksets"][0].__setitem__(
                    "project_local_first_task_id",
                    packet["project_worksets"][1]["active_task_ids"][0],
                ),
            ),
            "first_task": lambda packet: packet["project_worksets"][0].__setitem__(
                "project_local_first_task_id",
                packet["project_worksets"][0]["active_task_ids"][1],
            ),
            "rank_value": lambda packet: packet["project_worksets"][0]["global_rank_references"][0].__setitem__(
                "global_rank", 99
            ),
            "rank_missing": lambda packet: packet["project_worksets"][0]["global_rank_references"].pop(),
            "rank_duplicate": lambda packet: packet["project_worksets"][0]["global_rank_references"].append(
                copy.deepcopy(packet["project_worksets"][0]["global_rank_references"][0])
            ),
            "rank_reverse": lambda packet: packet["project_worksets"][0]["global_rank_references"].reverse(),
            "gate": lambda packet: packet["project_worksets"][0].__setitem__("user_or_supervisor_gate", "none"),
            "safe": lambda packet: packet["project_worksets"][0].__setitem__("safe_continuation", "none"),
            "active_closed_swap": lambda packet: (
                packet["project_worksets"][1]["active_task_ids"].__setitem__(
                    0, packet["project_worksets"][1]["closed_or_informational_task_ids"][0]
                ),
                packet["project_worksets"][1]["closed_or_informational_task_ids"].__setitem__(
                    0, packet["global_attention_queue"][1]["task_id"]
                ),
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                self._assert_loaded_mutation_rejected(mutate, "worksets")

    def test_loaded_packet_rejects_coverage_policy_and_scope_mutations(self) -> None:
        for field in (
            "project_count",
            "report_count",
            "active_task_count",
            "closed_or_informational_count",
            "required_report_count",
        ):
            with self.subTest(coverage=field):
                self._assert_loaded_mutation_rejected(
                    lambda packet, field=field: packet["coverage"].__setitem__(
                        field, packet["coverage"][field] + 1
                    ),
                    "coverage",
                )
        for name, mutate in {
            "live": lambda packet: packet["coverage"].__setitem__("live_coverage", True),
            "statement": lambda packet: packet["coverage"].__setitem__("coverage_statement", "changed"),
        }.items():
            with self.subTest(coverage=name):
                self._assert_loaded_mutation_rejected(mutate, "coverage")

        for name, mutate in {
            "removed": lambda packet: packet["attention_policy"].pop(),
            "reversed": lambda packet: packet["attention_policy"].reverse(),
            "precedence": lambda packet: packet["attention_policy"][0].__setitem__("precedence", 99),
            "precedence_type": lambda packet: packet["attention_policy"][0].__setitem__("precedence", True),
            "key": lambda packet: packet["attention_policy"][0].__setitem__("key", "changed"),
            "label": lambda packet: packet["attention_policy"][0].__setitem__("label", "changed"),
        }.items():
            with self.subTest(policy=name):
                self._assert_loaded_mutation_rejected(mutate, "attention policy")

        scope_values = {
            "observer_first": False,
            "explicit_manifest_only": False,
            "directory_latest_report_discovery": True,
            "conversation_or_clipboard_inference": True,
            "sibling_repository_writeback": True,
            "target_repository_writeback": True,
            "execution_schedule": True,
            "executable": True,
            "global_rank_meaning": "execution_order",
        }
        for field, changed in scope_values.items():
            with self.subTest(scope=field):
                self._assert_loaded_mutation_rejected(
                    lambda packet, field=field, changed=changed: packet["scope_boundary"].__setitem__(
                        field, changed
                    ),
                    "scope boundary",
                )
        self._assert_loaded_mutation_rejected(
            lambda packet: packet["scope_boundary"].__setitem__("observer_first", 1),
            "scope boundary",
        )

    def test_loaded_packet_rejects_unknown_keys_in_nested_objects(self) -> None:
        cases = {
            "source_binding": (
                lambda packet: packet["source_bindings"][0].__setitem__(
                    "harmless_metadata", None
                ),
                "source bindings",
            ),
            "coverage": (
                lambda packet: packet["coverage"].__setitem__("harmless_metadata", None),
                "coverage fields",
            ),
            "attention_policy": (
                lambda packet: packet["attention_policy"][0].__setitem__(
                    "harmless_metadata", None
                ),
                "attention policy",
            ),
            "source_evidence_reference": (
                lambda packet: packet["global_attention_queue"][0][
                    "evidence_references"
                ][0].__setitem__("harmless_metadata", None),
                "source evidence binding",
            ),
            "derived_evidence_reference": (
                lambda packet: packet["global_attention_queue"][0][
                    "evidence_references"
                ][1].__setitem__("harmless_metadata", None),
                "derived evidence binding",
            ),
            "project_workset": (
                lambda packet: packet["project_worksets"][0].__setitem__(
                    "harmless_metadata", None
                ),
                "worksets",
            ),
            "global_rank_reference": (
                lambda packet: packet["project_worksets"][0][
                    "global_rank_references"
                ][0].__setitem__("harmless_metadata", None),
                "worksets",
            ),
            "scope_boundary": (
                lambda packet: packet["scope_boundary"].__setitem__(
                    "harmless_metadata", None
                ),
                "scope boundary",
            ),
        }

        for name, (mutate, pattern) in cases.items():
            with self.subTest(name=name):
                self._assert_loaded_mutation_rejected(mutate, pattern)

    def test_every_task_remains_non_executable(self) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        locations = [
            ("global_attention_queue", index)
            for index in range(len(packet["global_attention_queue"]))
        ] + [
            ("closed_or_informational", index)
            for index in range(len(packet["closed_or_informational"]))
        ]
        for collection, index in locations:
            with self.subTest(collection=collection, index=index):
                self._assert_loaded_mutation_rejected(
                    lambda value, collection=collection, index=index: value[collection][index].__setitem__(
                        "executable", True
                    ),
                    "executable must be false",
                )

    def test_all_closed_packet_is_valid(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["reports"] = [
            entry
            for entry in manifest["reports"]
            if entry["report_path"].endswith("beta_closed_observation.txt")
        ]

        packet = build_supervision_packet(manifest, repo_root=ROOT)

        self.assertEqual([], packet["global_attention_queue"])
        self.assertEqual(1, len(packet["closed_or_informational"]))
        self.assertEqual(0, packet["coverage"]["active_task_count"])
        self.assertEqual(
            packet["closed_or_informational"][0]["task_id"],
            packet["project_worksets"][0]["project_local_first_task_id"],
        )
        self.assertEqual([], packet["project_worksets"][0]["global_rank_references"])

    def test_coherently_zeroed_packet_is_rejected(self) -> None:
        def zero_packet(packet: dict[str, object]) -> None:
            packet["global_attention_queue"] = []
            packet["closed_or_informational"] = []
            packet["source_bindings"] = []
            packet["project_worksets"] = []
            coverage = packet["coverage"]
            for field in (
                "project_count",
                "report_count",
                "active_task_count",
                "closed_or_informational_count",
                "required_report_count",
            ):
                coverage[field] = 0

        self._assert_loaded_mutation_rejected(zero_packet, "at least one manifest-bound task")

    def test_canonical_v65_task_identity_is_exact(self) -> None:
        report = """[ROUTE: DevCockpitCore | WORKER->SUPERVISOR | thread:devcockpitcore-cross-project-supervision-packet-v1 | lane:CROSS_PROJECT_SUPERVISION | slice:authority-repair-and-project-aware-packet-v1 | artifact:cross-project-supervision-packet-v1 | reply:Web Supervisor | confidence:high]
[PROGRESS: supervision-packet [#####] 20/20 | current:integrity repair completed | next:H1-live-report-round-trip | blocker:none | user_work:none]
[STATUS: health=green | gates=20/20 | stop_class=NONE]

## 到達した状態
Integrity repair completed and pushed. The worktree is clean and remote parity is 0 0.

## 引き継ぎゲート
pass; no blocked handoff required.
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "reports" / "canonical.txt"
            path.parent.mkdir(parents=True)
            path.write_text(report, encoding="utf-8", newline="\n")
            manifest = {
                "schema_version": "task_report_manifest.v1",
                "artifact_id": "canonical-v65-test",
                "generated_at": "2026-07-13T08:00:00Z",
                "reports": [{
                    "project_key": "DevCockpitCore",
                    "report_path": "reports/canonical.txt",
                    "required": True,
                    "evidence_class": "deterministic_non_live_fixture",
                    "authority_basis": "explicit_manifest_binding",
                    "content_sha256": sha256(path.read_bytes()).hexdigest(),
                }],
            }
            packet = build_supervision_packet(manifest, repo_root=root)

            conflicting = report.replace(
                " | reply:Web Supervisor",
                " | target:different-thread | reply:Web Supervisor",
            )
            path.write_text(conflicting, encoding="utf-8", newline="\n")
            manifest["reports"][0]["content_sha256"] = sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(
                SupervisionPacketError,
                "report identity normalization failed",
            ):
                build_supervision_packet(manifest, repo_root=root)

        task = self._tasks(packet)[0]
        self.assertEqual("devcockpitcore-cross-project-supervision-packet-v1", task["thread_id"])
        self.assertEqual("CROSS_PROJECT_SUPERVISION", task["lane_id"])
        self.assertEqual("authority-repair-and-project-aware-packet-v1", task["slice_id"])
        self.assertEqual("cross-project-supervision-packet-v1", task["artifact_id"])
        self.assertEqual("task-5fd580d71a060d0f", task["task_id"])

    def test_in_progress_canonical_reports_do_not_conflict_with_loaded_validation(self) -> None:
        reports = {
            "actionless_with_next": """[ROUTE: DevCockpitCore | WORKER->SUPERVISOR | thread:integrity-thread | lane:CROSS_PROJECT_SUPERVISION | slice:in-progress-v1 | artifact:integrity-artifact-v1 | reply:Web Supervisor | confidence:high]
[PROGRESS: supervision-packet [#-] 1/2 | current:implementation active | next:next-slice | blocker:none | user_work:none]
[STATUS: health=green | gates=1/2 | stop_class=NONE]

## 結果
Implementation remains in progress.
""",
            "completed_action_without_next": """[ROUTE: DevCockpitCore | WORKER->SUPERVISOR | thread:integrity-thread | lane:CROSS_PROJECT_SUPERVISION | slice:in-progress-v1 | artifact:integrity-artifact-v1 | reply:Web Supervisor | confidence:high]
[PROGRESS: supervision-packet [#-] 1/2 | current:implementation active | blocker:none | user_work:none]
[ACTION: decision=completed | now_owner:Worker | deliverable:integrity-artifact-v1 | trigger:none]
[STATUS: health=green | gates=1/2 | stop_class=NONE]

## 結果
The current slice is not yet complete.
""",
        }
        for name, report in reports.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                path = root / "report.txt"
                path.write_text(report, encoding="utf-8", newline="\n")
                manifest = {
                    "schema_version": "task_report_manifest.v1",
                    "artifact_id": "in-progress-canonical-test",
                    "generated_at": "2026-07-13T08:00:00Z",
                    "reports": [{
                        "project_key": "DevCockpitCore",
                        "report_path": "report.txt",
                        "required": True,
                        "evidence_class": "deterministic_non_live_fixture",
                        "authority_basis": "explicit_manifest_binding",
                        "content_sha256": sha256(path.read_bytes()).hexdigest(),
                    }],
                }

                packet = build_supervision_packet(manifest, repo_root=root)

                self.assertEqual(
                    "active_safe_continuation",
                    packet["global_attention_queue"][0]["attention_class"],
                )

    def test_packet_nested_duplicate_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "packet.json"
            source = PACKET_PATH.read_text(encoding="utf-8")
            path.write_text(
                source.replace(
                    '      "next_state": {\n        "owner":',
                    '      "next_state": {\n        "owner": "duplicate",\n        "owner":',
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SupervisionPacketError, "duplicate JSON key: owner"):
                load_packet(path)

    def _assert_loaded_mutation_rejected(self, mutate, pattern: str) -> None:
        packet = json.loads(PACKET_PATH.read_text(encoding="utf-8"))
        mutate(packet)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "packet.json"
            path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(SupervisionPacketError, pattern):
                load_packet(path)

    @staticmethod
    def _tasks(packet: dict[str, object]) -> list[dict[str, object]]:
        return [
            *packet["global_attention_queue"],  # type: ignore[list-item]
            *packet["closed_or_informational"],  # type: ignore[list-item]
        ]


if __name__ == "__main__":
    unittest.main()
