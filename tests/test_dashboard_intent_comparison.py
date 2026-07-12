from __future__ import annotations

from collections import Counter
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "samples" / "dashboard" / "intent_comparison"
HTML_PATH = PACK / "verified_observation_surface_intent_pack.html"
FIXTURE_PATH = PACK / "intent_comparison_fixture.json"
MANIFEST_PATH = PACK / "intent_comparison_manifest.json"
READBACK_PATH = PACK / "intent_comparison_readback.json"
CAPTURE_PATH = PACK / "capture_intent_comparison.mjs"
BASELINE_GENERATOR_BLOB = "8e047f50f9e9525533f5fbd6d784b27508b6d10f"
V1_B_SHA256 = "de685517421623c8eb78dc222c98ef19986577a6e0c6f3b2906af0c305959ac2"
FROZEN_CLAIM_IDS = {
    "state.summary",
    "state.change",
    "decision.question",
    "decision.recommendation",
    "metric.validation",
    "metric.projects",
    "metric.warnings",
    "metric.blockers",
    "warning.primary",
    "lane.observer",
    "lane.automation",
    "lane.execution",
    "lane.review",
    "project.devcockpitcore",
    "project.nlmytgen",
    "project.writingpage",
    "project.clippipegen",
    "source.commit",
    "source.observed_at",
    "source.freshness",
    "source.notice",
    "source.validation_path",
    "source.smoke_path",
    "source.status_path",
}


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


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _text_digest(path: Path) -> str:
    canonical = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return sha256(canonical.encode("utf-8")).hexdigest()


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"not a PNG: {path}")
    return struct.unpack(">II", data[16:24])


def _embedded_fixture(html: str) -> dict[str, object]:
    match = re.search(
        r'<script id="fixture-data" type="application/json">\s*(\{.*?\})\s*</script>',
        html,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError("embedded fixture script is missing")
    value = json.loads(match.group(1), object_pairs_hook=_strict_object)
    assert isinstance(value, dict)
    return value


def _runtime_projection(fixture: dict[str, object]) -> dict[str, object]:
    direction_fields = (
        "id",
        "slug",
        "structure_kind",
        "claim_class",
        "required_concepts",
        "labels",
        "titles",
        "descriptions",
    )
    priority_fields = (
        "rank",
        "claim_class",
        "action",
        "reason",
        "state",
        "owner",
        "evidence_route",
        "claim_ids",
    )
    claim_fields = ("claim_id", "claim_class", "labels", "values")
    return {
        "artifact_id": fixture["artifact_id"],
        "source_commit": fixture["source_commit"],
        "observed_at": fixture["observed_at"],
        "freshness_state": fixture["freshness_state"],
        "directions": [
            {key: item[key] for key in direction_fields}
            for item in fixture["directions"]
        ],
        "structural_labels": fixture["structural_labels"],
        "claim_class_labels": fixture["claim_class_labels"],
        "ui_copy": fixture["ui_copy"],
        "priority_items": [
            {key: item[key] for key in priority_fields}
            for item in fixture["priority_items"]
        ],
        "claims": [
            {key: item[key] for key in claim_fields}
            for item in fixture["claims"]
        ],
    }


class _StaticParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_state: dict[str, str] = {}
        self.direction_controls: list[dict[str, str]] = []
        self.language_controls: list[dict[str, str]] = []
        self.panels: list[dict[str, str]] = []
        self.render_modes: list[str] = []
        self.landmarks: list[str] = []
        self.repo_paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.html_state = values
        if tag == "button" and "data-direction" in values:
            self.direction_controls.append(values)
        if tag == "button" and "data-language" in values:
            self.language_controls.append(values)
        if "data-direction-panel" in values:
            self.panels.append(values)
        if "data-render-mode" in values:
            self.render_modes.append(values["data-render-mode"])
        if "data-landmark" in values:
            self.landmarks.append(values["data-landmark"])
        if tag == "a" and "data-repo-path" in values:
            self.repo_paths.append(values["data-repo-path"])


class IntentComparisonPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.capture = CAPTURE_PATH.read_text(encoding="utf-8")
        cls.fixture = _load(FIXTURE_PATH)
        cls.manifest = _load(MANIFEST_PATH)
        cls.readback = _load(READBACK_PATH)
        cls.embedded = _embedded_fixture(cls.html)
        cls.parser = _StaticParser()
        cls.parser.feed(cls.html)

    def test_strict_json_loader_rejects_duplicate_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key: source_commit"):
            json.loads(
                '{"source_commit":"abc","source_commit":"def"}',
                object_pairs_hook=_strict_object,
            )

    def test_fixture_v2_schema_evidence_role_and_direction_contract(self) -> None:
        self.assertEqual("intent_comparison_fixture.v2", self.fixture["schema_version"])
        self.assertEqual(
            "verified-observation-surface-intent-pack-v2",
            self.fixture["artifact_id"],
        )
        self.assertIs(self.fixture["evidence_role"]["point_in_time"], True)
        self.assertIs(self.fixture["evidence_role"]["authoritative_for_live_state"], False)
        self.assertEqual("stale", self.fixture["freshness_state"])
        self.assertRegex(str(self.fixture["source_commit"]), r"\A[0-9a-f]{7}\Z")
        assessment = self.fixture["freshness_assessment"]
        self.assertEqual(24, assessment["stale_after_hours"])
        self.assertIn("assessed_at", assessment)
        self.assertEqual(
            [
                ("A", "priority-review-console", "priority_console"),
                ("B", "narrative-status-brief", "narrative_brief"),
                ("C", "lane-project-overview", "overview"),
            ],
            [
                (item["id"], item["slug"], item["structure_kind"])
                for item in self.fixture["directions"]
            ],
        )
        self.assertTrue(
            all(item["claim_class"] == "editorial" for item in self.fixture["directions"])
        )

    def test_claim_and_material_copy_classification_contract(self) -> None:
        claims = self.fixture["claims"]
        ids = [claim["claim_id"] for claim in claims]
        self.assertEqual(24, len(ids))
        self.assertEqual(24, len(set(ids)))
        self.assertEqual(FROZEN_CLAIM_IDS, set(ids))
        classes = set(self.fixture["claim_classes"])
        counts = Counter(claim["claim_class"] for claim in claims)
        self.assertEqual(classes, set(counts))
        for claim in claims:
            with self.subTest(claim_id=claim["claim_id"]):
                claim_class = claim["claim_class"]
                self.assertIn(claim_class, classes)
                if claim_class == "observed":
                    self.assertTrue(claim.get("source_paths"))
                elif claim_class == "derived":
                    self.assertTrue(claim.get("source_paths"))
                    self.assertTrue(claim.get("derivation"))
                else:
                    self.assertTrue(claim.get("editorial_basis"))
                for source in claim.get("source_paths", []):
                    self.assertTrue((ROOT / source.split("#")[0]).exists(), source)
        by_id = {claim["claim_id"]: claim for claim in claims}
        self.assertEqual("editorial", by_id["decision.recommendation"]["claim_class"])
        self.assertEqual("derived", by_id["lane.execution"]["claim_class"])
        for item in self.fixture["priority_items"]:
            self.assertEqual("editorial", item["claim_class"])
            self.assertTrue(item["editorial_basis"])
        for key, contract in self.fixture["ui_copy_claims"].items():
            self.assertIn(key, self.fixture["ui_copy"])
            self.assertIn(contract["claim_class"], classes)
            if contract["claim_class"] == "derived":
                self.assertTrue(contract.get("source_paths"))
                self.assertTrue(contract.get("derivation"))
            if contract["claim_class"] == "editorial":
                self.assertTrue(contract.get("editorial_basis"))

    def test_japanese_english_and_embedded_runtime_projection(self) -> None:
        for claim in self.fixture["claims"]:
            for field in ("labels", "values"):
                self.assertTrue(claim[field]["ja"])
                self.assertTrue(claim[field]["en"])
            if claim["localization_mode"] == "translated":
                self.assertNotEqual(claim["values"]["ja"], claim["values"]["en"])
            else:
                self.assertEqual("technical_identifier", claim["localization_mode"])
                self.assertEqual(claim["values"]["ja"], claim["values"]["en"])
        for collection in (
            self.fixture["structural_labels"].values(),
            self.fixture["claim_class_labels"].values(),
            self.fixture["ui_copy"].values(),
        ):
            for item in collection:
                self.assertTrue(item["ja"])
                self.assertTrue(item["en"])
        for direction in self.fixture["directions"]:
            for field in ("labels", "titles", "descriptions"):
                self.assertTrue(direction[field]["ja"])
                self.assertTrue(direction[field]["en"])
        self.assertEqual(_runtime_projection(self.fixture), self.embedded)

    def test_ordered_priority_items_and_referenced_claims(self) -> None:
        items = self.fixture["priority_items"]
        ranks = [item["rank"] for item in items]
        self.assertEqual([1, 2, 3], ranks)
        self.assertEqual(len(ranks), len(set(ranks)))
        for item in items:
            for field in ("action", "reason", "state", "owner"):
                self.assertTrue(item[field]["ja"])
                self.assertTrue(item[field]["en"])
            self.assertTrue(item["evidence_route"])
            self.assertTrue(item["claim_ids"])
            self.assertTrue(set(item["claim_ids"]).issubset(FROZEN_CLAIM_IDS))

    def test_static_html_accessibility_routes_and_scope_boundary(self) -> None:
        slugs = {
            "priority-review-console",
            "narrative-status-brief",
            "lane-project-overview",
        }
        self.assertEqual("ja", self.parser.html_state["lang"])
        self.assertEqual("ja", self.parser.html_state["data-language"])
        self.assertEqual("priority-review-console", self.parser.html_state["data-direction"])
        self.assertEqual("common", self.parser.html_state["data-capture-mode"])
        self.assertEqual(slugs, {item["data-direction"] for item in self.parser.direction_controls})
        self.assertEqual(slugs, {item["data-direction-panel"] for item in self.parser.panels})
        self.assertEqual({"priority", "narrative", "overview"}, set(self.parser.render_modes))
        panel_ids = {item["id"] for item in self.parser.panels}
        for control in self.parser.direction_controls:
            self.assertEqual("tab", control["role"])
            self.assertIn(control["aria-controls"], panel_ids)
            self.assertNotIn("aria-pressed", control)
        for panel in self.parser.panels:
            self.assertEqual("tabpanel", panel["role"])
            self.assertEqual("0", panel["tabindex"])
        self.assertEqual({"ja", "en"}, {item["data-language"] for item in self.parser.language_controls})
        self.assertEqual({"ja", "en"}, {item["lang"] for item in self.parser.language_controls})
        self.assertTrue(
            {"common-hero", "direction-controls", "language-controls"}.issubset(
                set(self.parser.landmarks)
            )
        )
        self.assertNotIn("lane-project-matrix", self.html)
        self.assertNotIn("Lane And Project Matrix", self.html)
        self.assertNotIn("data-matrix-cell", self.html)
        self.assertIn('queue.dataset.concept = "priority-queue"', self.html)
        self.assertIn('details.dataset.concept = "progressive-evidence"', self.html)
        self.assertIn('limit.dataset.concept = "relationship-limit"', self.html)
        self.assertIn('data-panel-proof data-claim-class="derived"', self.html)
        self.assertIn('data-structural-label="artifact_kicker"', self.html)
        self.assertNotIn("http://", self.html)
        self.assertNotIn("https://", self.html)
        self.assertNotIn("WebSocket", self.html)
        self.assertEqual(6, len(self.parser.repo_paths))
        for repo_path in self.parser.repo_paths:
            self.assertTrue((ROOT / repo_path).exists(), repo_path)

    def test_capture_helper_prevents_v1_false_pass_contract(self) -> None:
        self.assertIn("page.bringToFront()", self.capture)
        self.assertIn("document.fonts?.ready", self.capture)
        self.assertIn("requestAnimationFrame", self.capture)
        self.assertIn('fullPage: false', self.capture)
        self.assertNotIn("clip:", self.capture)
        self.assertIn("uniform_black_negative_control", self.capture)
        self.assertIn("--record-worker-inspection", self.capture)
        self.assertIn('status: "pending"', self.capture)
        self.assertNotIn("previousReadback", self.capture)
        self.assertNotIn("human_visual_review", self.readback)
        v1_b = PACK / "screenshots" / "narrative-status-brief.png"
        self.assertEqual(V1_B_SHA256, _digest(v1_b))

    def test_manifest_inventory_dimensions_hashes_and_generator_boundary(self) -> None:
        manifest = self.manifest
        self.assertEqual("intent_comparison_manifest.v2", manifest["schema_version"])
        self.assertEqual(self.fixture["artifact_id"], manifest["artifact_id"])
        self.assertEqual(_text_digest(HTML_PATH), manifest["html_sha256"])
        self.assertEqual(_text_digest(FIXTURE_PATH), manifest["fixture_sha256"])
        self.assertEqual(
            "UTF-8 with CRLF normalized to LF",
            manifest["text_hash_normalization"],
        )
        common = manifest["screenshots"]["common"]
        panel = manifest["screenshots"]["panel"]
        contact = manifest["screenshots"]["contact_sheet"]
        self.assertEqual(3, len(common))
        self.assertEqual(3, len(panel))
        entries = [*common, *panel, contact]
        self.assertEqual(7, len(entries))
        for entry in entries:
            with self.subTest(path=entry["path"]):
                path = ROOT / entry["path"]
                self.assertTrue(path.exists())
                self.assertIn("screenshots/v2/", entry["path"])
                self.assertEqual(manifest["capture_id"], entry["capture_id"])
                self.assertEqual(entry["sha256"], _digest(path))
                self.assertEqual((entry["width"], entry["height"]), _png_dimensions(path))
        self.assertTrue(all(item["common_chrome"] is True for item in common))
        self.assertTrue(all(item["common_chrome"] is False for item in panel))
        self.assertTrue(all((item["width"], item["height"]) == (1440, 1200) for item in [*common, *panel]))
        self.assertEqual((1440, 620), (contact["width"], contact["height"]))
        generator = manifest["production_generator"]
        self.assertEqual(BASELINE_GENERATOR_BLOB, generator["baseline_blob"])
        self.assertEqual(BASELINE_GENERATOR_BLOB, generator["current_blob"])
        self.assertIs(generator["unchanged"], True)

    def test_v2_machine_readback_and_worker_hash_binding(self) -> None:
        readback = self.readback
        self.assertEqual("intent_comparison_readback.v2", readback["schema_version"])
        self.assertEqual(self.fixture["artifact_id"], readback["artifact_id"])
        self.assertEqual(self.manifest["capture_id"], readback["capture_id"])
        self.assertEqual(self.manifest["html_sha256"], readback["html_sha256"])
        self.assertEqual(self.manifest["fixture_sha256"], readback["fixture_sha256"])
        self.assertEqual(self.manifest["text_hash_normalization"], readback["text_hash_normalization"])
        self.assertIs(readback["evidence_scope"]["authoritative_for_live_state"], False)
        for key in (
            "automated_dom_parity",
            "automated_geometry_check",
            "automated_raster_landmark_check",
            "automated_keyboard_check",
            "automated_overflow_check",
            "automated_link_check",
            "browser_runtime",
        ):
            self.assertEqual("pass", readback[key]["status"], key)
        dom = readback["automated_dom_parity"]
        self.assertEqual(24, dom["claim_count_per_direction"])
        self.assertEqual(6, len(dom["checks"]))
        self.assertTrue(all(item["pass"] for item in dom["checks"]))
        self.assertTrue(
            all(all(count == 1 for count in item["required_concept_counts"].values()) for item in dom["checks"])
        )
        self.assertTrue(all(item["panel_proof_classes"] == ["derived"] for item in dom["checks"]))
        geometry = readback["automated_geometry_check"]
        self.assertEqual(6, len(geometry["captures"]))
        self.assertTrue(all(item["pass"] for item in geometry["captures"]))
        self.assertTrue(all(item["pass"] for item in geometry["anchor_fairness"]))
        raster = readback["automated_raster_landmark_check"]
        self.assertEqual(6, len(raster["captures"]))
        self.assertTrue(all(item["pass"] for item in raster["captures"]))
        self.assertTrue(raster["contact_sheet"]["pass"])
        negative = raster["uniform_black_negative_control"]
        self.assertEqual("fail", negative["expected_result"])
        self.assertEqual("fail", negative["observed_result"])
        self.assertIs(negative["detector_rejected_blank"], True)
        self.assertEqual(
            {"direct_query", "click_switch", "keyboard_switch"},
            {item["path"] for item in raster["narrative_state_paths"]},
        )
        self.assertTrue(all(item["pass"] for item in raster["narrative_state_paths"]))
        self.assertEqual("encoded_blank_not_reproduced", readback["v1_failure_reproduction"]["status"])
        self.assertIs(readback["v1_failure_reproduction"]["hash_preserved"], True)
        worker = readback["worker_raster_inspection"]
        self.assertEqual("pass", worker["status"])
        self.assertEqual(readback["capture_id"], worker["inspected_capture_id"])
        self.assertEqual(7, len(worker["inspected_files"]))
        inspected = {item["path"]: item["sha256"] for item in worker["inspected_files"]}
        manifest_hashes = {
            item["path"]: item["sha256"]
            for item in [
                *self.manifest["screenshots"]["common"],
                *self.manifest["screenshots"]["panel"],
                self.manifest["screenshots"]["contact_sheet"],
            ]
        }
        self.assertEqual(manifest_hashes, inspected)
        self.assertEqual(
            {"status": "pending", "selected_direction": None},
            readback["user_visual_acceptance"],
        )
        self.assertNotIn("human_visual_review", readback)


if __name__ == "__main__":
    unittest.main()
