from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.dashboard import (
    _priority_items,
    build_dashboard_model,
    main,
    priority_readback,
    render_dashboard,
    render_review_actions_markdown,
    review_action_package,
    write_dashboard,
    write_priority_readback,
    write_review_actions_json,
    write_review_actions_markdown,
)


class DashboardTests(unittest.TestCase):
    def test_supervision_packet_projects_project_identity_without_changing_layout(self) -> None:
        packet_path = "samples/supervision_packets/cross_project_supervision_packet_v1.json"
        model = build_dashboard_model(
            repo_root=ROOT,
            supervision_packet_path=packet_path,
            generated_at="2026-07-13T06:30:00Z",
        )
        html = render_dashboard(model)
        readback = priority_readback(model)

        priorities = model["priority_items"]
        self.assertEqual([1, 2, 3], [item["rank"] for item in priorities])
        self.assertEqual(
            [
                "true_stop_or_required_failure",
                "user_authorization_or_material_decision",
                "active_safe_continuation",
            ],
            [item["attention_class"] for item in priorities],
        )
        self.assertTrue(all(item["executable"] is False for item in priorities))
        self.assertTrue(all(item["project_key"] for item in priorities))
        self.assertTrue(all(item["thread_id"] for item in priorities))
        self.assertTrue(all(item["lane_id"] for item in priorities))
        self.assertEqual(
            "attention_and_review_priority_only",
            priorities[0]["global_rank_meaning"],
        )
        for expected in (
            'id="priority-lane"',
            'id="active-decision"',
            'id="evidence-inspector"',
            'id="project-worksets"',
            'data-project-key="alpha-project"',
            'data-thread-id="alpha-release-thread"',
            'data-field="project-identity"',
            'data-field="lane-identity"',
            'data-field="attention-class"',
            "Global rank is attention and review priority, not execution order.",
        ):
            self.assertIn(expected, html)
        self.assertNotIn('role="tablist"', html)
        self.assertNotIn('data-direction="lane-and-project-overview"', html)
        self.assertTrue(readback["supervision_packet"]["loaded"])
        self.assertEqual(2, readback["supervision_packet"]["coverage"]["project_count"])
        projected_ids = {
            task_id
            for workset in readback["supervision_packet"]["project_worksets"]
            for task_id in (
                workset["active_task_ids"]
                + workset["closed_or_informational_task_ids"]
            )
        }
        packet_ids = {
            task["task_id"]
            for task in (
                model["supervision_packet"]["global_attention_queue"]
                + model["supervision_packet"]["closed_or_informational"]
            )
        }
        self.assertEqual(packet_ids, projected_ids)

    def test_model_loads_receipt_and_builds_priority_console_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)

            model = build_dashboard_model(
                repo_root=root,
                generated_at="2026-07-12T00:00:00Z",
            )

        self.assertEqual(model["schema_version"], "devcockpit_local_dashboard.v1")
        self.assertEqual(model["project"]["key"], "devcockpitcore")
        self.assertEqual(model["health"]["tone"], "yellow")
        self.assertEqual({source["state"] for source in model["sources"]}, {"loaded"})
        self.assertEqual(len(model["sources"]), 7)
        self.assertEqual(model["source_freshness"]["loaded_count"], "7/7")
        self.assertEqual(
            model["output"]["repo_relative_path"],
            "samples/dashboard/devcockpitcore_dashboard.html",
        )
        self.assertEqual(model["output"]["access_state"], "worker_generated_not_user_opened")
        self.assertEqual(
            model["priority_readback"]["repo_relative_path"],
            "samples/dashboard/devcockpitcore_priority_readback.json",
        )
        self.assertEqual(model["freshness"]["loaded_count"], "7/7")
        self.assertEqual(
            set(model["freshness"]),
            {"loaded_count", "latest_generated_at", "source_summary"},
        )
        self.assertEqual(model["evidence_freshness"]["schema_version"], "evidence_freshness_receipt.v1")
        self.assertEqual(model["evidence_freshness"]["capture_id"], "efr-cbae922571043527b800")
        self.assertEqual([item["precedence"] for item in model["priority_policy"]], list(range(1, 7)))
        self.assertGreaterEqual(len(model["priority_items"]), 1)
        self.assertEqual(model["selected_priority_id"], model["priority_items"][0]["priority_id"])
        self.assertEqual(model["user_visual_acceptance"], "accepted")

    def test_receipt_projection_is_consumed_without_re_evaluating_freshness(self) -> None:
        receipt = json.loads(
            (ROOT / "samples" / "evidence_freshness" / "evidence_freshness_receipt_v1.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(
                repo_root=root,
                generated_at="2035-01-01T00:00:00Z",
            )

        projected = model["evidence_freshness"]
        self.assertEqual(projected["assessed_at"], receipt["assessed_at"])
        self.assertEqual(projected["authority"], receipt["authority"])
        self.assertEqual(projected["source_counts"], receipt["summary"]["source_counts"])
        self.assertEqual(
            projected["current_state_claim_eligible"],
            receipt["summary"]["current_state_claim_eligible"],
        )
        receipt_source = next(
            source for source in model["sources"] if source["label"] == "evidence_freshness_receipt"
        )
        self.assertIs(receipt_source["hashes_verified"], False)

    def test_priority_ranking_is_deterministic_deduplicated_and_required_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            first = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")
            second = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        priorities = first["priority_items"]
        self.assertEqual(priorities, second["priority_items"])
        self.assertEqual([item["rank"] for item in priorities], list(range(1, len(priorities) + 1)))
        self.assertEqual(
            [item["precedence"] for item in priorities],
            sorted(item["precedence"] for item in priorities),
        )
        identities = [(item["project_key"], item["condition_key"]) for item in priorities]
        self.assertEqual(len(identities), len(set(identities)))
        required_ranks = [item["rank"] for item in priorities if item["required"] is True]
        optional_ranks = [item["rank"] for item in priorities if item["required"] is False]
        self.assertTrue(required_ranks)
        self.assertTrue(optional_ranks)
        self.assertLess(max(required_ranks), min(optional_ranks))

        worktree = [
            item
            for item in priorities
            if item["project_key"] == "devcockpitcore" and item["condition_key"] == "worktree_dirty"
        ]
        self.assertEqual(len(worktree), 1)
        self.assertGreaterEqual(len(worktree[0]["evidence_refs"]), 2)
        self.assertEqual(worktree[0]["primary_evidence_id"], "cross-project-smoke-sample")
        writing_conditions = [
            item["condition_key"]
            for item in priorities
            if item["project_key"] == "writingpage"
        ]
        self.assertEqual(writing_conditions, ["optional_project_missing"])

    def test_required_blocker_and_validation_failure_precede_freshness_and_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            validation_path = root / "samples" / "validation_packs" / "devcockpitcore_validation_pack_result.json"
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            validation["checks"][1]["result"] = "fail"
            validation["checks"][1]["severity"] = "required"
            validation["health"]["blockers"] = ["required observation contract broken"]
            _write_json(validation_path, validation)

            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        priorities = model["priority_items"]
        self.assertEqual([item["precedence"] for item in priorities[:3]], [1, 2, 3])
        self.assertTrue(priorities[0]["condition_key"].startswith("blocker:"))
        self.assertEqual(
            priorities[1]["condition_key"],
            "validation_check:historical_fixture_scan",
        )
        self.assertEqual(priorities[2]["condition_key"], "current_claim_ineligible")
        blocker_html = render_dashboard(model)
        self.assertIn('<span class="lang-ja">停止</span>', blocker_html)
        self.assertIn('<span class="lang-en">Blocked</span>', blocker_html)

    def test_matching_required_failure_and_blocker_collapse_with_correct_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            validation_path = root / "samples" / "validation_packs" / "devcockpitcore_validation_pack_result.json"
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            validation["checks"][1]["result"] = "fail"
            validation["checks"][1]["severity"] = "required"
            validation["summary"]["result"] = "fail"
            validation["health"]["blockers"] = ["historical_fixture_scan failed"]
            _write_json(validation_path, validation)

            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        matching = [
            item
            for item in model["priority_items"]
            if item["condition_key"] == "validation_check:historical_fixture_scan"
        ]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["precedence"], 1)
        self.assertEqual(matching[0]["primary_evidence_id"], "validation-pack-sample")

    def test_red_status_note_collapses_with_matching_smoke_condition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            status_path = root / "samples" / "status_snapshots" / "devcockpitcore_status.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status["health"] = {
                "status": "red",
                "notes": ["worktree is dirty"],
                "stop_class": "STOP",
            }
            _write_json(status_path, status)

            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        worktree = [
            item for item in model["priority_items"] if item["condition_key"] == "worktree_dirty"
        ]
        self.assertEqual(len(worktree), 1)
        self.assertEqual(worktree[0]["precedence"], 1)
        self.assertGreaterEqual(len(worktree[0]["evidence_refs"]), 2)

    def test_priority_items_are_non_executable_source_backed_and_keep_locked_lanes_out(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        priorities = model["priority_items"]
        self.assertTrue(all(item["executable"] is False for item in priorities))
        self.assertTrue(all(item["primary_evidence_path"] for item in priorities))
        self.assertTrue(all(item["evidence_refs"] for item in priorities))
        self.assertTrue(any(item["review_action_refs"] for item in priorities))
        self.assertTrue(
            all(
                ref["executable"] is False
                for item in priorities
                for ref in item["review_action_refs"]
            )
        )
        self.assertTrue(
            all(
                ref["source_id"] and ref["source_path"]
                for item in priorities
                for ref in item["evidence_refs"]
            )
        )
        payload = json.dumps(priorities)
        self.assertTrue(all(item["claim_class"] == "derived" for item in priorities))
        self.assertTrue(all(item["evidence_claim_class"] == "observed" for item in priorities))
        self.assertTrue(all(item["display_copy_claim_class"] == "editorial" for item in priorities))
        self.assertTrue(all(item["ranking_policy_claim_class"] == "policy" for item in priorities))
        for forbidden in (
            "NEXT_WORKER_PROMPT",
            "[PASTE TARGET:",
            "autonomous runner",
            "external publication action",
        ):
            self.assertNotIn(forbidden, payload)

    def test_unmatched_owned_review_action_becomes_a_priority(self) -> None:
        inputs = _green_priority_inputs()
        inputs["review_actions"] = [
            {
                "action_id": "validation-orphan-001",
                "source_type": "validation_pack",
                "severity": "warning",
                "project_key": "devcockpitcore",
                "reason": "orphan warning requiring an owner",
                "evidence_path": "samples/validation.json",
                "owner_hint": "operator",
                "executable": False,
            }
        ]

        priorities = _priority_items(**inputs)

        self.assertEqual(len(priorities), 1)
        self.assertTrue(priorities[0]["condition_key"].startswith("review_action:validation_pack:"))
        self.assertEqual(
            [ref["action_id"] for ref in priorities[0]["review_action_refs"]],
            ["validation-orphan-001"],
        )

    def test_all_green_inputs_render_a_stable_success_priority(self) -> None:
        priorities = _priority_items(**_green_priority_inputs())

        self.assertEqual(len(priorities), 1)
        self.assertEqual(priorities[0]["condition_key"], "routine_observation_review")
        self.assertEqual(priorities[0]["precedence"], 5)
        self.assertEqual(priorities[0]["primary_evidence_id"], "devcockpitcore.live_status_observation")

    def test_rendered_html_uses_priority_decision_evidence_as_primary_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        html = render_dashboard(model)

        for expected in (
            'data-dashboard-variant="priority-review-console-production"',
            'data-dashboard-theme="dark"',
            'data-landmark="current-state"',
            'id="priority-lane"',
            'data-landmark="priority-lane"',
            'id="active-decision"',
            'data-landmark="active-decision"',
            'id="evidence-inspector"',
            'data-landmark="evidence-inspector"',
            'id="evidence-appendix"',
            "Priority Review Console",
            "Priority Lane",
            "Active Decision",
            "Evidence Inspector",
            "Current-claim eligible",
            "Fresh through",
            'role="option" aria-selected=',
            'data-field="review-actions"',
            "Freshness receipt ledger",
            "Non-executable review actions",
            "Validation Pack",
            "Cross-Project Smoke",
            "Locked lanes",
        ):
            self.assertIn(expected, html)
        priority_list_tag = html.split('class="priority-list"', 1)[1].split(">", 1)[0]
        self.assertNotIn("data-overflow-allowed", priority_list_tag)
        self.assertLess(html.index('id="priority-lane"'), html.index('id="active-decision"'))
        self.assertLess(html.index('id="active-decision"'), html.index('id="evidence-inspector"'))
        self.assertLess(html.index('id="evidence-inspector"'), html.index('id="evidence-appendix"'))
        self.assertNotIn('id="current-status-report"', html)
        self.assertNotIn('id="review-map"', html)
        self.assertNotIn('id="review-stack"', html)
        self.assertNotIn("NEXT_WORKER_PROMPT", html)
        self.assertNotIn("[PASTE TARGET:", html)

    def test_rendered_html_is_bilingual_without_b_or_c_production_tabs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            html = render_dashboard(
                build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")
            )

        for expected in (
            '<html lang="ja" data-language="ja">',
            'class="lang-ja"',
            'class="lang-en"',
            'data-language="ja" aria-pressed="true"',
            'data-language="en" aria-pressed="false"',
            "優先レビュー・コンソール",
            "優先事項",
            "現在の判断",
            "根拠",
            "鮮度receiptの証拠ソース",
            "確認専用action package",
            "Workerが生成したローカル確認成果物です。",
            "setLanguage",
        ):
            self.assertIn(expected, html)
        self.assertNotIn('data-direction="narrative-status-brief"', html)
        self.assertNotIn('data-direction="lane-and-project-overview"', html)
        self.assertNotIn('role="tablist"', html)
        self.assertNotIn("linear-gradient", html)
        self.assertNotIn("radial-gradient", html)

    def test_non_javascript_fallback_and_interaction_contract_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            html = render_dashboard(
                build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")
            )

        for expected in (
            "<noscript>",
            "完全な代替表示として、順位1、その判断、根拠を以下に表示します。",
            "Rank 1, its active decision, and its evidence are rendered below as the complete fallback.",
            'role="listbox"',
            'role="option" aria-selected="true"',
            'aria-controls="active-decision evidence-inspector"',
            'aria-selected="true"',
            'tabindex="0" data-landmark="priority-first"',
            "selectPriority",
            "ArrowDown",
            "ArrowUp",
            "Home",
            "End",
            "data-selected-priority-id",
        ):
            self.assertIn(expected, html)

    def test_warning_triage_and_review_actions_keep_substantive_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        triage = {group["source"]: group for group in model["warning_triage"]}
        self.assertEqual(triage["Blockers"]["count"], 0)
        self.assertGreaterEqual(triage["Validation Pack"]["count"], 1)
        self.assertGreaterEqual(triage["Project Rows"]["count"], 1)

        actions = model["review_actions"]
        self.assertGreaterEqual(len(actions), 1)
        self.assertTrue(all(action["executable"] is False for action in actions))
        self.assertTrue(all(action["evidence_path"] for action in actions))
        self.assertTrue(any(action["blocked_by_gate"] for action in actions))
        payload = json.dumps(actions)
        for forbidden in ("shell=True", "subprocess", "NEXT_WORKER_PROMPT", "[PASTE TARGET:"):
            self.assertNotIn(forbidden, payload)

    def test_review_action_package_has_expected_schema_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        package = review_action_package(model)

        self.assertEqual(package["schema_version"], "devcockpit_review_actions.v1")
        self.assertEqual(package["summary"]["total"], len(package["actions"]))
        self.assertGreaterEqual(package["summary"]["warning"], 1)
        self.assertEqual(package["package"]["access_state"], "worker_generated_not_user_opened")

    def test_priority_readback_records_selected_production_surface_and_accepted_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")
            package = priority_readback(model)
            output = root / "samples" / "dashboard" / "devcockpitcore_priority_readback.json"
            write_priority_readback(package, output, pretty=True)

            written = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(written["schema_version"], "devcockpit_priority_readback.v1")
        self.assertEqual(
            written["artifact_id"],
            "priority-review-console-production-observation-surface-v1",
        )
        self.assertEqual(written["surface"]["selected_direction"], "priority-review-console")
        self.assertIs(written["surface"]["production"], True)
        self.assertIs(written["surface"]["b_and_c_production_tabs"], False)
        self.assertEqual(written["surface"]["user_visual_acceptance"], "accepted")
        self.assertIs(written["surface"]["executable"], False)
        self.assertEqual(written["priorities"], model["priority_items"])
        self.assertEqual(
            written["freshness_receipt"]["capture_id"],
            model["evidence_freshness"]["capture_id"],
        )
        self.assertTrue(written["scope_boundary"]["locked_lanes_excluded_from_priorities"])

    def test_review_action_markdown_escapes_table_pipes(self) -> None:
        package = {
            "summary": {"total": 1, "blocker": 0, "warning": 1, "info": 0},
            "actions": [
                {
                    "action_id": "unit-001",
                    "severity": "warning",
                    "source_type": "validation_pack",
                    "project_key": "devcockpitcore",
                    "title": "Title with | pipe",
                    "evidence_path": "samples/example.json",
                    "executable": False,
                }
            ],
        }

        markdown = render_review_actions_markdown(package)

        self.assertIn("Title with \\| pipe", markdown)
        self.assertIn("Non-executable review package", markdown)
        self.assertIn("## How to review this package", markdown)

    def test_rendered_html_has_accessibility_responsive_and_print_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            html = render_dashboard(
                build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")
            )

        for expected in (
            'class="skip-link"',
            'href="#main-content"',
            '<nav class="dashboard-nav"',
            'data-aria-en="Dashboard sections"',
            '<main id="main-content"',
            '<footer class="dashboard-footer">',
            "aria-labelledby=",
            'data-aria-en="Priority review queue"',
            "@media (max-width:",
            "@media print",
            ":focus-visible",
            "prefers-reduced-motion",
            "Evidence freshness receipt sources",
            "Validation pack checks, result severity, evidence bar, and detail.",
            "Cross-project smoke rows with result, repository hint, branch, and warning summary.",
        ):
            self.assertIn(expected, html)

    def test_rendered_html_escapes_action_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            validation_path = root / "samples" / "validation_packs" / "devcockpitcore_validation_pack_result.json"
            data = json.loads(validation_path.read_text(encoding="utf-8"))
            data["health"]["warnings"].append("<script>alert(1)</script>")
            _write_json(validation_path, data)
            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        html = render_dashboard(model)

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_write_dashboard_and_machine_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")
            html_output = root / "samples" / "dashboard" / "devcockpitcore_dashboard.html"
            json_output = root / "samples" / "dashboard" / "devcockpitcore_review_actions.json"
            md_output = root / "samples" / "dashboard" / "devcockpitcore_review_actions.md"

            write_dashboard(model, html_output)
            review_package = review_action_package(model)
            write_review_actions_json(review_package, json_output, pretty=True)
            write_review_actions_markdown(review_package, md_output)

            html = html_output.read_text(encoding="utf-8")
            review_json = json.loads(json_output.read_text(encoding="utf-8"))
            review_md = md_output.read_text(encoding="utf-8")

        self.assertIn("<!doctype html>", html)
        self.assertIn("Priority Review Console", html)
        self.assertIn("local_static_file", html)
        self.assertEqual(review_json["schema_version"], "devcockpit_review_actions.v1")
        self.assertIn("Non-executable review package", review_md)

    def test_cli_writes_all_default_outputs_with_explicit_fixture_hash_skip(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = main(
                    [
                        "--repo-root",
                        str(root),
                        "--skip-freshness-hash-verification",
                    ]
                )

            output = stdout.getvalue()
            self.assertEqual(result, 0)
            for relative_path in (
                "samples/dashboard/devcockpitcore_dashboard.html",
                "samples/dashboard/devcockpitcore_review_actions.json",
                "samples/dashboard/devcockpitcore_review_actions.md",
                "samples/dashboard/devcockpitcore_priority_readback.json",
            ):
                self.assertIn(relative_path, output)
                self.assertTrue((root / relative_path).exists())
            readback = json.loads(
                (root / "samples" / "dashboard" / "devcockpitcore_priority_readback.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(readback["surface"]["selected_direction"], "priority-review-console")

    def test_missing_optional_context_is_warning_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            (root / "docs" / "project-context.md").unlink()

            model = build_dashboard_model(repo_root=root, generated_at="2026-07-12T00:00:00Z")

        self.assertEqual(model["health"]["tone"], "yellow")
        self.assertIn("project_context: missing source file", model["health"]["warnings"])


def _green_priority_inputs() -> dict[str, object]:
    live_source = {
        "project_id": "devcockpitcore",
        "source_id": "devcockpitcore.live_status_observation",
        "source_path": "git-observation:.",
        "freshness_state": "fresh",
        "temporal_state": "fresh",
        "revision_binding_state": "match",
        "current_state_claim_eligible": True,
        "assessed_at": "2026-07-13T00:00:00Z",
        "fresh_through": "2026-07-14T00:00:00Z",
        "content_sha256": "a" * 64,
        "authority_classification": "point_in_time_non_live",
        "reason_codes": ["revision_match", "timestamp_within_threshold"],
    }
    return {
        "health": {"blockers": [], "warnings": []},
        "validation": {
            "summary": {"result": "pass"},
            "health": {"blockers": [], "warnings": []},
            "checks": [
                {
                    "check_key": "required_contract",
                    "result": "pass",
                    "severity": "required",
                }
            ],
        },
        "smoke": {
            "summary": {"result": "pass"},
            "health": {"blockers": [], "warnings": []},
            "projects": [
                {
                    "project_key": "devcockpitcore",
                    "project": "DevCockpitCore",
                    "required": True,
                    "status_snapshot": {"warnings": []},
                }
            ],
        },
        "status": {"health": {"status": "green", "notes": []}},
        "receipt": {
            "assessed_at": "2026-07-13T00:00:00Z",
            "projects": [
                {
                    "project_id": "devcockpitcore",
                    "required": True,
                    "available": True,
                }
            ],
            "sources": [live_source],
        },
        "review_actions": [],
        "validation_path": "samples/validation.json",
        "smoke_path": "samples/smoke.json",
        "status_path": "samples/status.json",
    }


def _write_fixture_tree(root: Path) -> None:
    _write_json(
        root / "samples" / "validation_packs" / "devcockpitcore_validation_pack_result.json",
        {
            "schema_version": "validation_pack_result.v1",
            "generated_at": "2026-01-01T00:00:00Z",
            "summary": {
                "result": "warn",
                "done": 2,
                "total": 2,
                "meter": "#~",
                "passed": 1,
                "warnings": 1,
                "failed": 0,
            },
            "checks": [
                {
                    "check_key": "python_compile",
                    "result": "pass",
                    "severity": "required",
                    "done": 1,
                    "total": 1,
                    "meter": "#",
                    "findings": [],
                    "notes": [],
                },
                {
                    "check_key": "historical_fixture_scan",
                    "result": "warn",
                    "severity": "warning",
                    "done": 1,
                    "total": 1,
                    "meter": "~",
                    "findings": [{"path": "samples/reports/example.txt"}],
                    "notes": [],
                },
            ],
            "gate_input": {
                "recommended_gate_decision": "integrate_and_continue",
                "stop_class": "INTEGRATE_AND_CONTINUE",
                "user_work": "none",
            },
            "health": {
                "status": "yellow",
                "warnings": ["historical fixture residue"],
                "blockers": [],
                "stop_class": "INTEGRATE_AND_CONTINUE",
            },
        },
    )
    _write_json(
        root / "samples" / "cross_project_smokes" / "devcockpitcore_cross_project_smoke_result.json",
        {
            "schema_version": "cross_project_smoke_result.v1",
            "generated_at": "2026-01-01T00:00:00Z",
            "summary": {
                "result": "warn",
                "done": 1,
                "total": 1,
                "meter": "~",
                "passed": 0,
                "warnings": 1,
                "failed": 0,
            },
            "projects": [
                {
                    "project_key": "devcockpitcore",
                    "project": "DevCockpitCore",
                    "required": True,
                    "adapter_path": "adapters/devcockpitcore.json",
                    "result": "warn",
                    "done": 1,
                    "total": 1,
                    "meter": "~",
                    "repo_resolution": {"selected": "."},
                    "status_snapshot": {
                        "branch": "main",
                        "head": "abc1234",
                        "warnings": ["worktree is dirty"],
                    },
                }
            ],
            "readiness": {
                "foundation_automation_readiness": "cross_project_smoke_available",
                "execution_automation_readiness": "out_of_scope",
                "notes": ["observer only"],
            },
            "gate_input": {
                "recommended_gate_decision": "integrate_and_continue",
                "stop_class": "INTEGRATE_AND_CONTINUE",
                "user_work": "none",
            },
            "health": {
                "status": "yellow",
                "warnings": ["devcockpitcore: warn"],
                "blockers": [],
                "stop_class": "INTEGRATE_AND_CONTINUE",
            },
        },
    )
    _write_json(
        root / "samples" / "status_snapshots" / "devcockpitcore_status.json",
        {
            "schema_version": "status_snapshot.v1",
            "generated_at": "2026-01-01T00:00:00Z",
            "repo": {
                "branch": "main",
                "head": "abc1234",
                "worktree": {"state": "dirty", "short_status": [" M README.md"]},
            },
            "project_state": {
                "active_artifact": "priority-review-console-production-observation-surface-v1",
                "next_action": "review production priority console",
            },
            "health": {
                "status": "yellow",
                "stop_class": "INTEGRATE_AND_CONTINUE",
                "notes": ["worktree is dirty"],
            },
        },
    )
    _write_json(
        root / "adapters" / "devcockpitcore.json",
        {
            "schema_version": "adapter_manifest.v1",
            "project": "DevCockpitCore",
            "project_key": "devcockpitcore",
            "default_branch": "main",
            "read_only": True,
        },
    )
    _write_text(
        root / "docs" / "runtime-state.md",
        "active_artifact: priority-review-console-production-observation-surface-v1\n"
        "artifact_next: visual-acceptance-review\n",
    )
    _write_text(root / "docs" / "project-context.md", "# Project Context\n")
    receipt_target = (
        root / "samples" / "evidence_freshness" / "evidence_freshness_receipt_v1.json"
    )
    receipt_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        ROOT / "samples" / "evidence_freshness" / "evidence_freshness_receipt_v1.json",
        receipt_target,
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
