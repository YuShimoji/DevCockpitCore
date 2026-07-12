from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATE_DOCUMENTS = (
    "docs/PROJECT_COCKPIT.md",
    "docs/runtime-state.md",
)
SHARED_PROJECTION_FIELDS = {
    "updated_at",
    "current_review_artifact",
    "current_review_artifact_path",
    "priority_readback_path",
    "selected_information_architecture",
    "selection_state",
    "user_visual_acceptance",
    "tracked_receipt_capture_id",
    "tracked_receipt_assessed_at",
    "tracked_receipt_authority",
    "blocking_issue_count",
}
KNOWN_LIVE_STATE_FIELDS = {
    "active_artifact",
    "artifact_current",
    "artifact_next",
    "base_branch",
    "blocking_issue_count",
    "current_review_artifact",
    "external_publish_state",
    "external_status",
    "freshness_state",
    "handoff",
    "last_verified_base",
    "observed_at",
    "pull_request",
    "priority_readback_path",
    "resume_branch",
    "selected_information_architecture",
    "selection_state",
    "source_commit",
    "status_authority",
    "tracked_receipt_assessed_at",
    "tracked_receipt_authority",
    "tracked_receipt_capture_id",
    "updated_at",
    "user_visual_acceptance",
}
STATE_LINE = re.compile(r"(?P<key>[a-z][a-z0-9_]*):\s*(?P<value>.+)")
REPOSITORY_LINK = re.compile(r"\[[^]]+\]\((?P<target>[^)]+)\)")


class DuplicateStateKeyError(ValueError):
    """Raised when a state document repeats a frontmatter-like key."""


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _frontmatter_labels(markdown: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    first_lines: dict[str, int] = {}

    for line_number, line in enumerate(markdown.splitlines()[1:], start=2):
        if line.startswith("## "):
            break
        if not line or line.startswith("#"):
            continue

        match = STATE_LINE.fullmatch(line)
        if match is None:
            raise ValueError(
                f"unparseable state metadata at line {line_number}: {line!r}"
            )

        key = match.group("key")
        if key in labels:
            raise DuplicateStateKeyError(
                f"duplicate key {key!r} at line {line_number} "
                f"(first defined at line {first_lines[key]})"
            )

        labels[key] = match.group("value").strip()
        first_lines[key] = line_number

    return labels


class ProjectStateContractTests(unittest.TestCase):
    def test_state_documents_are_strictly_parseable_with_unique_keys(self) -> None:
        for relative_path in STATE_DOCUMENTS:
            with self.subTest(relative_path=relative_path):
                labels = _frontmatter_labels(_read(relative_path))
                self.assertTrue(SHARED_PROJECTION_FIELDS <= labels.keys())
                self.assertGreaterEqual(int(labels["blocking_issue_count"]), 0)
                date.fromisoformat(labels["updated_at"])

    def test_duplicate_key_fixture_reports_key_and_line(self) -> None:
        fixture = _read("tests/fixtures/project_state_duplicate_keys.md")

        with self.assertRaisesRegex(
            DuplicateStateKeyError,
            r"duplicate key 'updated_at' at line 4 .*first defined at line 2",
        ):
            _frontmatter_labels(fixture)

    def test_declared_projection_fields_are_the_only_shared_keys(self) -> None:
        cockpit = _frontmatter_labels(_read("docs/PROJECT_COCKPIT.md"))
        runtime = _frontmatter_labels(_read("docs/runtime-state.md"))

        self.assertEqual(SHARED_PROJECTION_FIELDS, cockpit.keys() & runtime.keys())
        for field in SHARED_PROJECTION_FIELDS:
            with self.subTest(field=field):
                self.assertEqual(cockpit[field], runtime[field])

    def test_state_metadata_repository_paths_exist(self) -> None:
        for relative_path in STATE_DOCUMENTS:
            labels = _frontmatter_labels(_read(relative_path))
            for key, value in labels.items():
                if not key.endswith("_path"):
                    continue
                with self.subTest(relative_path=relative_path, key=key):
                    self.assertTrue((ROOT / value).exists(), value)

    def test_readme_exposes_resolving_human_navigation_near_the_top(self) -> None:
        first_lines = "\n".join(_read("README.md").splitlines()[:35])
        self.assertIn(
            "[Timestamped product state and review navigation]"
            "(docs/PROJECT_COCKPIT.md)",
            first_lines,
        )

        targets = REPOSITORY_LINK.findall(first_lines)
        self.assertGreaterEqual(len(targets), 3)
        for target in targets:
            if re.match(r"[a-z]+://", target):
                continue
            resolved_target = target.split("#", 1)[0]
            with self.subTest(target=target):
                self.assertTrue((ROOT / resolved_target).exists(), target)

    def test_project_context_has_no_frontmatter_like_live_state_fields(self) -> None:
        context = _read("docs/project-context.md")
        labels_found = {
            match.group("key")
            for line in context.splitlines()
            if (match := STATE_LINE.fullmatch(line)) is not None
        }

        self.assertFalse(KNOWN_LIVE_STATE_FIELDS & labels_found)

    def test_selected_surface_and_tracked_receipt_fields_have_valid_forms(self) -> None:
        for relative_path in STATE_DOCUMENTS:
            labels = _frontmatter_labels(_read(relative_path))
            with self.subTest(relative_path=relative_path):
                self.assertEqual(
                    labels["selected_information_architecture"],
                    "A_priority_review_console",
                )
                self.assertEqual(labels["selection_state"], "closed")
                self.assertEqual(labels["user_visual_acceptance"], "pending")
                self.assertRegex(
                    labels["tracked_receipt_capture_id"],
                    r"\Aefr-[0-9a-f]{20}\Z",
                )
                assessed_at = datetime.fromisoformat(
                    labels["tracked_receipt_assessed_at"].replace("Z", "+00:00")
                )
                self.assertIsNotNone(assessed_at.utcoffset())
                self.assertEqual(
                    labels["tracked_receipt_authority"],
                    "point_in_time_non_live",
                )

    def test_navigation_identifies_selected_priority_console_and_freshness_consumption(self) -> None:
        cockpit = _read("docs/PROJECT_COCKPIT.md")
        runtime = _read("docs/runtime-state.md")
        pipeline = _read("docs/PROJECT_PIPELINE.mmd")
        combined = "\n".join((cockpit, runtime, pipeline))

        for document in (cockpit, runtime):
            with self.subTest(document=document.splitlines()[0]):
                self.assertIn(
                    "current_review_artifact: priority-review-console-production-observation-surface-v1",
                    document,
                )
                self.assertIn(
                    "current_review_artifact_path: samples/dashboard/devcockpitcore_dashboard.html",
                    document,
                )
                self.assertIn("Priority Review Console", document)
                self.assertRegex(document, r"(?i)production (?:dashboard|observation surface)")
                self.assertIn("python -m dev_cockpit.evidence_freshness", document)
                self.assertIn("python -m dev_cockpit.dashboard", document)
                self.assertIn("evidence_freshness_receipt.v1", document)

        self.assertIn(
            "selected_information_architecture: A_priority_review_console",
            cockpit,
        )
        self.assertIn("selection_state: closed", cockpit)
        self.assertIn("user_visual_acceptance: pending", cockpit)
        self.assertIn("Production direction A is selected", runtime)
        self.assertRegex(runtime, r"(?i)user_visual_acceptance[^.]*pending")

        self.assertIn('OPTION_A["A: Priority Review Console<br/>selected production direction"]', pipeline)
        self.assertIn('GEN["dev_cockpit.dashboard<br/>production generator"]', pipeline)
        self.assertIn('PRIORITY_JSON["devcockpitcore_priority_readback.json"]', pipeline)
        self.assertIn('USER_REVIEW["free-form production visual review<br/>pending"]', pipeline)
        self.assertIn('FRESH_CLI["python -m dev_cockpit.evidence_freshness"]', pipeline)
        self.assertIn("evidence_freshness_receipt.v1", pipeline)
        self.assertNotIn('USER_REVIEW["user direction review (pending)"]', pipeline)
        self.assertNotIn("production unchanged", combined)
        self.assertNotIn("verified-observation-surface-intent-pack-v1", combined)
        self.assertNotIn("Lane And Project Matrix", combined)
        self.assertIn("persisted navigation snapshot", cockpit)
        self.assertIn("not live development control", cockpit)
        self.assertIn("does not act as a development workflow controller", runtime)


if __name__ == "__main__":
    unittest.main()
