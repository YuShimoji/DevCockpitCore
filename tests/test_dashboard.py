from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.dashboard import (
    build_dashboard_model,
    main,
    render_dashboard,
    render_review_actions_markdown,
    review_action_package,
    write_dashboard,
    write_review_actions_json,
    write_review_actions_markdown,
)


class DashboardTests(unittest.TestCase):
    def test_model_loads_sources_and_aggregates_warning_health(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)

            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(model["schema_version"], "devcockpit_local_dashboard.v1")
        self.assertEqual(model["project"]["key"], "devcockpitcore")
        self.assertEqual(model["health"]["tone"], "yellow")
        self.assertEqual({source["state"] for source in model["sources"]}, {"loaded"})
        self.assertEqual(
            model["output"]["repo_relative_path"],
            "samples/dashboard/devcockpitcore_dashboard.html",
        )
        self.assertEqual(model["output"]["access_state"], "worker_generated_not_user_opened")
        self.assertIn("warning_triage", model)
        self.assertEqual(len(model["review_checkpoints"]), 3)
        self.assertEqual(model["freshness"]["loaded_count"], "6/6")
        self.assertEqual(len(model["decision_meters"]), 6)
        self.assertLessEqual(len(model["review_stack"]), 3)
        self.assertTrue(all(meter["detail_href"].startswith("#detail-") for meter in model["decision_meters"]))
        self.assertEqual(len(model["latest_brief"]), 5)
        self.assertEqual([row["label"] for row in model["latest_brief"]], ["Decision", "Blockers", "Focus", "Proof", "Next"])

    def test_rendered_html_contains_required_review_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        html = render_dashboard(model)

        for expected in (
            "Local supervision HUD",
            "Latest Brief",
            "Home-linked decision meter HUD",
            "Review Stack",
            "Linked Detail Map",
            "Detail: Stop Gate",
            "Detail: Warning Debt",
            "Detail: Evidence Freshness",
            "Detail: Review Actions",
            "Detail: Project Smoke",
            "Detail: Source Files",
            "Warnings Triage",
            "Project Cards",
            "Validation Pack",
            "Cross-Project Smoke",
            "Health, Gate, Readiness",
            "Safe Local Actions",
            "Locked Lanes",
            "Designer / Operator Notes",
            "Sources and Access",
            "samples/validation_packs/devcockpitcore_validation_pack_result.json",
            "worker_generated_not_user_opened",
        ):
            self.assertIn(expected, html)
        self.assertNotIn("NEXT_WORKER_PROMPT", html)
        self.assertNotIn("[PASTE TARGET:", html)

    def test_rendered_html_has_dark_compact_overview_and_disclosures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        html = render_dashboard(model)
        top_strip = html.split("</header>", 1)[0]

        for expected in (
            'data-dashboard-variant="home-linked-meters"',
            'data-dashboard-theme="dark"',
            "color-scheme: dark",
            "latest-brief",
            "decision-meter-board",
            "data-meter-target=\"#detail-stop-gate\"",
            "review-strip",
            "<span>Stop Gate</span>",
            "<span>Warning Debt</span>",
            "<span>Evidence Freshness</span>",
            "<span>Review Queue</span>",
            "<span>Project Smoke</span>",
            "<span>Access Readiness</span>",
            '<details class="disclosure">',
            "Evidence Snapshot",
            "Detailed Review Actions",
        ):
            self.assertIn(expected, html)
        for raw_value in (
            "INTEGRATE_AND_CONTINUE",
            "worker_generated_not_user_opened",
            "local_static_file",
            "file_generated_by_dashboard_command",
        ):
            self.assertNotIn(raw_value, top_strip)

    def test_latest_brief_is_short_and_before_meter_board(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        html = render_dashboard(model)
        top_strip = html.split("</header>", 1)[0]
        brief = top_strip.split('<section id="latest-brief"', 1)[1].split("</section>", 1)[0]

        self.assertLess(top_strip.index('id="latest-brief"'), top_strip.index('id="meter-board"'))
        self.assertEqual(brief.count("<li>"), 5)
        for expected in ("Decision", "Blockers", "Focus", "Proof", "Next"):
            self.assertIn(expected, brief)
        for duplicated_meter in ("Review Queue", "Project Smoke", "Access Readiness"):
            self.assertNotIn(duplicated_meter, brief)

    def test_home_meters_link_to_detail_panels_and_review_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        html = render_dashboard(model)

        detail_ids = (
            "detail-stop-gate",
            "detail-warning-debt",
            "detail-evidence-freshness",
            "detail-review-actions",
            "detail-project-smoke",
            "detail-source-files",
        )
        self.assertEqual(html.count('class="decision-meter '), 6)
        for detail_id in detail_ids:
            self.assertIn(f'href="#{detail_id}"', html)
            self.assertIn(f'id="{detail_id}"', html)
            self.assertIn('href="#meter-board"', html)
        self.assertIn('href="#validation-001"', html)
        self.assertIn('id="validation-001"', html)

    def test_review_stack_is_short_and_dense_evidence_stays_below_home(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        html = render_dashboard(model)
        top_strip = html.split("</header>", 1)[0]

        self.assertLessEqual(html.count("data-review-stack-item"), 3)
        self.assertLess(html.index('id="review-stack"'), html.index('id="validation-pack"'))
        self.assertLess(html.index('id="linked-detail-map"'), html.index('id="validation-pack"'))
        self.assertNotIn("Validation pack checks", top_strip)
        for forbidden in ("NEXT_WORKER_PROMPT", "[PASTE TARGET:", "shell=True", "C:\\Users\\"):
            self.assertNotIn(forbidden, html)

    def test_rendered_html_has_static_filter_affordance_and_project_cards(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        html = render_dashboard(model)

        for expected in (
            "data-dashboard-search",
            "data-filter-result=\"warn\"",
            "data-dashboard-project",
            "data-result=\"warn\"",
            "All cards remain visible without JavaScript",
        ):
            self.assertIn(expected, html)

    def test_warning_triage_keeps_blockers_separate_from_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        triage = {group["source"]: group for group in model["warning_triage"]}
        self.assertEqual(triage["Blockers"]["count"], 0)
        self.assertGreaterEqual(triage["Validation Pack"]["count"], 1)
        self.assertGreaterEqual(triage["Project Rows"]["count"], 1)

    def test_review_actions_are_non_executable_and_source_backed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

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
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        package = review_action_package(model)

        self.assertEqual(package["schema_version"], "devcockpit_review_actions.v1")
        self.assertEqual(package["summary"]["total"], len(package["actions"]))
        self.assertGreaterEqual(package["summary"]["warning"], 1)
        self.assertEqual(package["package"]["access_state"], "worker_generated_not_user_opened")

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

    def test_rendered_html_includes_review_actions_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        html = render_dashboard(model)

        for expected in (
            "Review Actions",
            "Review-only Action Package",
            "data-review-action",
            "data-action-search",
            "data-filter-action-severity=\"warning\"",
            "executable is false",
            "devcockpitcore_review_actions.json",
        ):
            self.assertIn(expected, html)

    def test_rendered_html_has_accessibility_and_print_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        html = render_dashboard(model)

        for expected in (
            'class="skip-link"',
            'href="#main-content"',
            '<nav class="dashboard-nav" aria-label="Dashboard sections">',
            '<main id="main-content"',
            '<footer class="dashboard-footer">',
            '<noscript>',
            "aria-labelledby=",
            'aria-label="Home-linked decision meters"',
            "@media print",
            ":focus-visible",
            "prefers-reduced-motion",
            "<caption>Validation pack checks",
            "<caption>Source evidence files",
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
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        html = render_dashboard(model)

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_write_dashboard_creates_static_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")
            output = root / "samples" / "dashboard" / "devcockpitcore_dashboard.html"

            write_dashboard(model, output)

            self.assertTrue(output.exists())
            text = output.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", text)
            self.assertIn("local_static_file", text)
            self.assertIn("Evidence level", text)

    def test_write_review_action_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")
            package = review_action_package(model)
            json_output = root / "samples" / "dashboard" / "devcockpitcore_review_actions.json"
            md_output = root / "samples" / "dashboard" / "devcockpitcore_review_actions.md"

            write_review_actions_json(package, json_output, pretty=True)
            write_review_actions_markdown(package, md_output)

            self.assertEqual(json.loads(json_output.read_text(encoding="utf-8"))["schema_version"], "devcockpit_review_actions.v1")
            self.assertIn("Non-executable review package", md_output.read_text(encoding="utf-8"))

    def test_cli_writes_dashboard_with_default_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = main(["--repo-root", str(root)])

            self.assertEqual(result, 0)
            self.assertIn("samples/dashboard/devcockpitcore_dashboard.html", stdout.getvalue())
            self.assertTrue((root / "samples" / "dashboard" / "devcockpitcore_dashboard.html").exists())
            self.assertTrue((root / "samples" / "dashboard" / "devcockpitcore_review_actions.json").exists())
            self.assertTrue((root / "samples" / "dashboard" / "devcockpitcore_review_actions.md").exists())

    def test_missing_optional_context_is_warning_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_fixture_tree(root)
            (root / "docs" / "project-context.md").unlink()

            model = build_dashboard_model(repo_root=root, generated_at="2026-01-01T00:00:00Z")

        self.assertEqual(model["health"]["tone"], "yellow")
        self.assertIn("project_context: missing source file", model["health"]["warnings"])


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
                "active_artifact": "dashboard-compact-dark-overview-v1",
                "next_action": "review compact dark dashboard overview",
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
        "active_artifact: dashboard-compact-dark-overview-v1\nartifact_next: japanese-display-polish-v1\n",
    )
    _write_text(root / "docs" / "project-context.md", "# Project Context\n")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
