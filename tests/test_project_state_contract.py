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
    "source_commit",
    "observed_at",
    "freshness_state",
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
    "resume_branch",
    "source_commit",
    "status_authority",
    "updated_at",
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

    def test_evidence_freshness_fields_have_valid_forms(self) -> None:
        for relative_path in STATE_DOCUMENTS:
            labels = _frontmatter_labels(_read(relative_path))
            with self.subTest(relative_path=relative_path):
                self.assertRegex(labels["source_commit"], r"\A[0-9a-f]{7,64}\Z")
                observed_at = datetime.fromisoformat(
                    labels["observed_at"].replace("Z", "+00:00")
                )
                self.assertIsNotNone(observed_at.utcoffset())
                self.assertIn(
                    labels["freshness_state"],
                    {"fresh", "stale", "unknown"},
                )

    def test_navigation_identifies_v2_overview_pending_choice_and_freshness_entry(self) -> None:
        cockpit = _read("docs/PROJECT_COCKPIT.md")
        runtime = _read("docs/runtime-state.md")
        pipeline = _read("docs/PROJECT_PIPELINE.mmd")
        combined = "\n".join((cockpit, runtime, pipeline))

        for document in (cockpit, runtime):
            with self.subTest(document=document.splitlines()[0]):
                self.assertIn(
                    "current_review_artifact: verified-observation-surface-intent-pack-v2",
                    document,
                )
                self.assertIn("Lane And Project Overview", document)
                self.assertRegex(document, r"(?i)user (?:direction )?selection remains\s+pending")
                self.assertRegex(document, r"(?i)production dashboard (?:and )?generator[^.]*unchanged")
                self.assertIn("python -m dev_cockpit.evidence_freshness", document)

        self.assertIn('OPTION_C["C: Lane And Project Overview"]', pipeline)
        self.assertIn('USER_REVIEW["user direction review (pending)"]', pipeline)
        self.assertIn('GEN["dev_cockpit.dashboard generator<br/>(production unchanged)"]', pipeline)
        self.assertIn('FRESH_CLI["python -m dev_cockpit.evidence_freshness"]', pipeline)
        self.assertIn("evidence_freshness_receipt.v1", pipeline)
        self.assertNotIn("verified-observation-surface-intent-pack-v1", combined)
        self.assertNotIn("Lane And Project Matrix", combined)
        self.assertIn("persisted navigation snapshot", cockpit)
        self.assertIn("not live development control", cockpit)
        self.assertIn("does not act as a development workflow controller", runtime)


if __name__ == "__main__":
    unittest.main()
