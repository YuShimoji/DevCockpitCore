from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DOC = ROOT / "docs" / "design" / "DASHBOARD_LAYOUT_RESEARCH_V1.md"
PROTOTYPE = ROOT / "samples" / "dashboard" / "layout_research" / "devcockpitcore_layout_prototype.html"


class _PrototypeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.attrs: list[tuple[str, str]] = []
        self.headings: list[str] = []
        self._capture_heading = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.attrs.extend((name, value or "") for name, value in attrs)
        if tag in {"h1", "h2"}:
            self._capture_heading = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2"}:
            self._capture_heading = False

    def handle_data(self, data: str) -> None:
        if self._capture_heading:
            text = data.strip()
            if text:
                self.headings.append(text)


class DashboardLayoutResearchTests(unittest.TestCase):
    def test_research_doc_exists_and_selects_one_layout(self) -> None:
        text = RESEARCH_DOC.read_text(encoding="utf-8")

        self.assertIn("Dashboard Layout Research V1", text)
        self.assertIn("Choose exactly one architecture: Priority Review Console.", text)
        self.assertIn("Card-grid-first dashboard", text)
        self.assertIn("Reject as primary structure.", text)
        self.assertIn("Current Dashboard Audit", text)
        self.assertIn("Acceptance Criteria For A Future Production Redesign", text)

    def test_research_doc_compares_at_least_four_layout_models(self) -> None:
        text = RESEARCH_DOC.read_text(encoding="utf-8")
        layout_rows = [
            line
            for line in text.splitlines()
            if line.startswith("| ") and " | " in line and not line.startswith("| ---")
        ]
        compared = [line for line in layout_rows if "Reject" in line or "Keep" in line]

        self.assertGreaterEqual(len(compared), 4)
        self.assertIn("Priority Review Console", text)

    def test_prototype_exists_and_uses_selected_layout_markers(self) -> None:
        html = PROTOTYPE.read_text(encoding="utf-8")
        parser = _PrototypeParser()
        parser.feed(html)

        self.assertIn(("data-layout-prototype", "priority-review-console"), parser.attrs)
        for heading in (
            "DevCockpitCore Priority Review Console",
            "Priority Lane",
            "Active Review Workspace",
            "Evidence Inspector",
            "Ordered Project / Status List",
            "Appendix, Not Workspace",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, parser.headings)

    def test_prototype_is_static_and_not_card_grid_first(self) -> None:
        html = PROTOTYPE.read_text(encoding="utf-8")
        lower = html.lower()

        self.assertNotIn("card-grid", lower)
        self.assertNotIn("project-card", lower)
        self.assertNotIn("action-card", lower)
        self.assertNotIn("<script", lower)
        self.assertNotIn("https://", lower)
        self.assertNotIn("http://", lower)

    def test_research_artifacts_do_not_cross_safety_gates(self) -> None:
        payload = RESEARCH_DOC.read_text(encoding="utf-8") + "\n" + PROTOTYPE.read_text(encoding="utf-8")
        forbidden = (
            "NEXT" + "_WORKER_PROMPT",
            "NEXT" + "_SUPERVISOR_REVIEW_PROMPT",
            "CONTINUATION" + "_WORKER_PROMPT",
            "<" * 3,
            ">" * 3,
            "C:" + r"\Users\\",
            "C:" + "/Users/",
            "shell" + "=True",
            "executable" + ": true",
            '"executable"' + ": true",
            "scheduler/background daemon is included",
            "target repository writeback is included",
        )

        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, payload)


if __name__ == "__main__":
    unittest.main()
