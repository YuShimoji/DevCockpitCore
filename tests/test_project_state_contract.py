from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _frontmatter_labels(markdown: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for line in markdown.splitlines()[1:]:
        if line.startswith("## "):
            break
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if separator and re.fullmatch(r"[a-z][a-z0-9_]*", key):
            labels[key] = value.strip()
    return labels


class ProjectStateContractTests(unittest.TestCase):
    def test_cockpit_and_runtime_projection_agree(self) -> None:
        cockpit = _frontmatter_labels(_read("docs/PROJECT_COCKPIT.md"))
        runtime = _frontmatter_labels(_read("docs/runtime-state.md"))

        self.assertEqual("this file", cockpit["status_authority"])
        self.assertEqual("docs/PROJECT_COCKPIT.md", runtime["status_authority"])
        self.assertEqual(cockpit["updated_at"], runtime["updated_at"])
        self.assertEqual(
            cockpit["active_product_checkpoint"],
            runtime["active_artifact"],
        )
        self.assertEqual(
            cockpit["blocking_issue_count"],
            runtime["blocking_issue_count"],
        )
        self.assertEqual(cockpit["external_status"], runtime["external_status"])
        self.assertEqual(
            cockpit["external_publish_state"],
            runtime["external_publish_state"],
        )
        self.assertEqual(cockpit.get("pull_request"), runtime.get("pull_request"))

    def test_readme_exposes_current_state_near_the_top(self) -> None:
        first_lines = "\n".join(_read("README.md").splitlines()[:35])
        self.assertIn(
            "[Current project state and next decisions](docs/PROJECT_COCKPIT.md)",
            first_lines,
        )

    def test_project_context_does_not_duplicate_live_state_labels(self) -> None:
        context = _read("docs/project-context.md")
        for live_label in (
            "updated_at:",
            "active_artifact:",
            "artifact_next:",
            "last_verified_base:",
        ):
            with self.subTest(live_label=live_label):
                self.assertNotIn(live_label, context)
        self.assertIn("docs/PROJECT_COCKPIT.md", context)

    def test_runtime_restart_surface_stays_bounded(self) -> None:
        runtime = _read("docs/runtime-state.md")
        restart = runtime.split("## Restart Surface", 1)[1].split(
            "## Last Live Verification", 1
        )[0]
        numbered_entries = re.findall(r"^\d+\. ", restart, flags=re.MULTILINE)

        self.assertLessEqual(len(numbered_entries), 5)
        self.assertNotIn("docs/handoffs/", restart)


if __name__ == "__main__":
    unittest.main()
