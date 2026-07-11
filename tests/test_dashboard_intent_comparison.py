from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "samples" / "dashboard" / "intent_comparison"
HTML_PATH = PACK / "verified_observation_surface_intent_pack.html"
FIXTURE_PATH = PACK / "intent_comparison_fixture.json"
MANIFEST_PATH = PACK / "intent_comparison_manifest.json"
READBACK_PATH = PACK / "intent_comparison_readback.json"


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    assert isinstance(value, dict)
    return value


class _PackParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.directions: list[str] = []
        self.panels: dict[str, set[str]] = {}
        self.languages: list[str] = []
        self.repo_paths: list[str] = []
        self.html_state: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.html_state = values
        if tag == "button" and "data-direction" in values:
            self.directions.append(values["data-direction"])
        if "data-direction-panel" in values:
            self.panels[values["data-direction-panel"]] = set(
                values["data-semantic-keys"].split(",")
            )
        if tag == "button" and "data-language" in values:
            self.languages.append(values["data-language"])
        if tag == "a" and "data-repo-path" in values:
            self.repo_paths.append(values["data-repo-path"])


class IntentComparisonPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.fixture = _load(FIXTURE_PATH)
        cls.manifest = _load(MANIFEST_PATH)
        cls.readback = _load(READBACK_PATH)
        cls.parser = _PackParser()
        cls.parser.feed(cls.html)

    def test_artifacts_parse_and_describe_point_in_time_evidence(self) -> None:
        self.assertEqual("intent_comparison_fixture.v1", self.fixture["schema_version"])
        role = self.fixture["evidence_role"]
        self.assertIsInstance(role, dict)
        self.assertIs(role["point_in_time"], True)
        self.assertIs(role["authoritative_for_live_state"], False)
        self.assertRegex(str(self.fixture["source_commit"]), r"\A[0-9a-f]{40}\Z")
        self.assertRegex(str(self.fixture["observed_at"]), r"[+-]\d\d:\d\d\Z")
        self.assertIn(self.fixture["freshness_state"], {"fresh", "stale", "unknown"})

    def test_strict_json_loader_rejects_duplicate_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key: source_commit"):
            json.loads(
                '{"source_commit":"abc","source_commit":"def"}',
                object_pairs_hook=_strict_object,
            )

    def test_three_directions_share_exact_semantic_key_set(self) -> None:
        expected_directions = {
            "priority-review-console",
            "narrative-status-brief",
            "lane-project-matrix",
        }
        semantic_contract = self.fixture["semantic_contract"]
        self.assertIsInstance(semantic_contract, dict)
        expected_keys = set(semantic_contract)
        self.assertEqual(24, len(expected_keys))
        self.assertEqual(expected_directions, set(self.parser.directions))
        self.assertEqual(expected_directions, set(self.parser.panels))
        for direction, keys in self.parser.panels.items():
            with self.subTest(direction=direction):
                self.assertEqual(expected_keys, keys)

    def test_default_language_direction_and_keyboard_contract(self) -> None:
        self.assertEqual("ja", self.parser.html_state["lang"])
        self.assertEqual("ja", self.parser.html_state["data-language"])
        self.assertEqual(
            "priority-review-console", self.parser.html_state["data-direction"]
        )
        self.assertEqual({"ja", "en"}, set(self.parser.languages))
        for key in ("ArrowLeft", "ArrowRight", "Home", "End"):
            self.assertIn(key, self.html)
        self.assertIn(":focus-visible", self.html)

    def test_embedded_fixture_matches_external_semantics(self) -> None:
        match = re.search(
            r'<script id="fixture-data" type="application/json">\s*(\{.*?\})\s*</script>',
            self.html,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        embedded = json.loads(match.group(1), object_pairs_hook=_strict_object)
        self.assertEqual(self.fixture["source_commit"], embedded["source_commit"])
        self.assertEqual(self.fixture["observed_at"], embedded["observed_at"])
        self.assertEqual(self.fixture["freshness_state"], embedded["freshness_state"])
        self.assertEqual(self.fixture["semantic_contract"], embedded["semantic_contract"])

    def test_manifest_and_readback_hold_required_machine_contract(self) -> None:
        self.assertEqual(
            "verified-observation-surface-intent-pack-v1",
            self.manifest["artifact_id"],
        )
        self.assertEqual("A", self.manifest["default_direction"])
        self.assertEqual("ja", self.manifest["default_language"])
        self.assertIs(self.manifest["production_generator_changed"], False)
        self.assertEqual({"A", "B", "C"}, set(self.manifest["screenshot_paths"]))
        for key in (
            "content_parity_across_directions",
            "language_parity",
            "screenshot_dimensions",
            "overflow_findings",
            "broken_links",
            "duplicate_key_check",
            "stale_indicator_check",
            "keyboard_switch_check",
            "human_visual_review",
            "production_generator_unchanged",
            "remaining_review_debt",
        ):
            with self.subTest(key=key):
                self.assertIn(key, self.readback)
        self.assertIs(self.readback["production_generator_unchanged"], True)
        parity = self.readback["content_parity_across_directions"]
        self.assertEqual("pass", parity["status"])
        self.assertEqual(24, parity["semantic_key_count_per_direction"])
        self.assertEqual(6, len(parity["checks"]))
        self.assertTrue(all(check["pass"] for check in parity["checks"]))
        self.assertEqual(
            {"priority-review-console", "narrative-status-brief", "lane-project-matrix"},
            {check["direction"] for check in parity["checks"]},
        )
        self.assertEqual({"ja", "en"}, {check["language"] for check in parity["checks"]})
        self.assertTrue(
            all(check["checked_key_count"] == 24 for check in parity["checks"])
        )
        self.assertEqual("pass", self.readback["human_visual_review"]["status"])

    def test_all_repo_paths_exist_and_source_links_are_exposed(self) -> None:
        self.assertEqual(6, len(self.parser.repo_paths))
        for relative_path in self.parser.repo_paths:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).exists(), relative_path)

    def test_static_boundary_and_existing_generator_are_unchanged_by_pack(self) -> None:
        self.assertNotIn("http://", self.html)
        self.assertNotIn("https://", self.html)
        self.assertNotIn("WebSocket", self.html)
        self.assertIn("production generator は未変更", self.html)
        self.assertTrue((ROOT / "src" / "dev_cockpit" / "dashboard.py").exists())


if __name__ == "__main__":
    unittest.main()
