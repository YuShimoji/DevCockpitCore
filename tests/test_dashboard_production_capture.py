from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "samples" / "dashboard" / "production_capture"
SCRIPT_PATH = PACK / "capture_priority_review_console.mjs"
MANIFEST_PATH = PACK / "production_capture_manifest.json"
READBACK_PATH = PACK / "production_capture_readback.json"
EXPECTED_ARTIFACT_ID = "priority-review-console-production-observation-surface-v1"
EXPECTED_SCREENSHOTS = {
    "ja-desktop": ("screenshots/priority-review-console-ja-desktop.png", 1440, 1200, "ja"),
    "en-desktop": ("screenshots/priority-review-console-en-desktop.png", 1440, 1200, "en"),
    "ja-narrow": ("screenshots/priority-review-console-ja-narrow.png", 390, 3100, "ja"),
}
REQUIRED_LANDMARKS = {
    "current_state",
    "priority_lane",
    "priority_first",
    "active_decision",
    "evidence_inspector",
    "freshness_status",
    "provenance",
}
AUTOMATED_STATUS_KEYS = (
    "source_binding",
    "automated_semantic_parity",
    "automated_priority_click_sync",
    "automated_priority_keyboard_sync",
    "automated_language_switch",
    "automated_visible_focus",
    "automated_no_javascript_fallback",
    "automated_overflow_check",
    "automated_narrow_order",
    "automated_geometry_check",
    "automated_browser_canvas_raster",
    "automated_ffmpeg_raster",
    "automated_decoder_agreement",
    "partial_black_negative_control",
    "browser_runtime",
)


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


def _canonical_json_digest(value: object) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"not a PNG: {path}")
    return struct.unpack(">II", data[16:24])


def _bound_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    output_candidate = PACK / path
    return output_candidate if output_candidate.exists() else ROOT / path


class ProductionCaptureScriptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = SCRIPT_PATH.read_text(encoding="utf-8")

    def test_script_is_syntax_valid_and_exposes_reproducible_cli(self) -> None:
        subprocess.run(["node", "--check", str(SCRIPT_PATH)], cwd=ROOT, check=True)
        help_result = subprocess.run(
            ["node", str(SCRIPT_PATH), "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        for option in (
            "--html",
            "--priority-readback",
            "--freshness-receipt",
            "--output-root",
            "--repo-root",
            "--captured-at",
            "--ffmpeg",
            "--validate-source-binding",
            "--validate-semantic-fixture",
            "--record-worker-inspection",
            "--inspection-at",
        ):
            self.assertIn(option, help_result.stdout)

    def test_script_requires_production_semantic_hooks_and_interactions(self) -> None:
        for landmark in (
            "current-state",
            "priority-lane",
            "priority-first",
            "active-decision",
            "evidence-inspector",
            "freshness-status",
            "provenance",
        ):
            self.assertIn(f'data-landmark="{landmark}"', self.script)
        self.assertIn("button[data-priority-id]", self.script)
        self.assertIn("data-evidence-id", self.script)
        self.assertIn('aria-selected="true"', self.script)
        self.assertIn('aria-pressed="true"', self.script)
        for key in ("ArrowDown", "ArrowUp", "Home", "End", "ArrowRight"):
            self.assertIn(key, self.script)
        self.assertIn('ids.length === 1 ? ids[0] : ids[1]', self.script)
        self.assertIn('mode: ids.length === 1 ? "single_priority_no_op"', self.script)
        self.assertNotIn("At least two priorities", self.script)
        self.assertIn("javaScriptEnabled: false", self.script)
        self.assertIn("DOCUMENT_POSITION_FOLLOWING", self.script)
        self.assertIn(":focus-visible", self.script)

    def test_script_uses_two_decoders_negative_control_and_staged_promotion(self) -> None:
        self.assertIn("browserCanvasDecode", self.script)
        self.assertIn("ffmpegDecode", self.script)
        self.assertIn('"rawvideo"', self.script)
        self.assertIn('"rgba"', self.script)
        self.assertIn('"format=rgba"', self.script)
        self.assertIn('"-compression_level"', self.script)
        self.assertIn("partialBlackNegativeControl", self.script)
        self.assertIn('fillStyle = "#000"', self.script)
        self.assertIn("mkdtemp", self.script)
        self.assertIn("await promote(", self.script)
        self.assertIn("if (!allAutomatedPass(readback)", self.script)
        self.assertIn("capture_identity_sha256", self.script)
        self.assertIn("capture_script_sha256", self.script)
        self.assertIn("Source binding rejected", self.script)
        self.assertIn("Priority semantic binding rejected before capture", self.script)
        self.assertIn("Source changed after capture", self.script)
        self.assertIn("Production generator changed after capture", self.script)
        self.assertNotIn("intent_comparison_manifest.v2", self.script)
        self.assertNotIn("previousReadback", self.script)


class ProductionCaptureSourceBindingRejectionTests(unittest.TestCase):
    def _command(
        self,
        temporary_root: Path,
        priority_path: Path,
        freshness_path: Path,
    ) -> list[str]:
        return [
            "node",
            str(SCRIPT_PATH),
            "--validate-source-binding",
            "--repo-root",
            str(ROOT),
            "--output-root",
            str(temporary_root),
            "--html",
            str(ROOT / "samples" / "dashboard" / "devcockpitcore_dashboard.html"),
            "--priority-readback",
            str(priority_path),
            "--freshness-receipt",
            str(freshness_path),
        ]

    def test_source_binding_accepts_exact_contract_and_rejects_every_fail_open_case(
        self,
    ) -> None:
        source_priority = _load(
            ROOT / "samples" / "dashboard" / "devcockpitcore_priority_readback.json"
        )
        source_freshness = _load(
            ROOT
            / "samples"
            / "evidence_freshness"
            / "evidence_freshness_receipt_v1.json"
        )
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            priority_path = temporary_root / "priority.json"
            freshness_path = temporary_root / "receipt.json"

            def write_case(
                mutate_priority=None,
                mutate_freshness=None,
            ) -> subprocess.CompletedProcess[str]:
                priority = json.loads(json.dumps(source_priority))
                freshness = json.loads(json.dumps(source_freshness))
                priority["freshness_receipt"]["path"] = "receipt.json"
                priority["freshness_receipt"]["capture_id"] = freshness["capture_id"]
                if mutate_priority is not None:
                    mutate_priority(priority)
                if mutate_freshness is not None:
                    mutate_freshness(freshness)
                priority_path.write_text(
                    json.dumps(priority, ensure_ascii=False),
                    encoding="utf-8",
                )
                freshness_path.write_text(
                    json.dumps(freshness, ensure_ascii=False),
                    encoding="utf-8",
                )
                return subprocess.run(
                    self._command(temporary_root, priority_path, freshness_path),
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )

            accepted = write_case()
            self.assertEqual(0, accepted.returncode, accepted.stderr)
            accepted_payload = json.loads(accepted.stdout)
            self.assertEqual("pass", accepted_payload["source_binding"]["status"])
            self.assertTrue(
                all(accepted_payload["source_binding"]["checks"].values())
            )

            cases = {
                "missing_declared_path": (
                    lambda value: value["freshness_receipt"].pop("path"),
                    None,
                ),
                "same_basename_wrong_path": (
                    lambda value: value["freshness_receipt"].__setitem__(
                        "path", "different/receipt.json"
                    ),
                    None,
                ),
                "missing_declared_capture_id": (
                    lambda value: value["freshness_receipt"].__setitem__(
                        "capture_id", ""
                    ),
                    None,
                ),
                "mismatched_capture_id": (
                    lambda value: value["freshness_receipt"].__setitem__(
                        "capture_id", "efr-different"
                    ),
                    None,
                ),
                "bad_priority_schema": (
                    lambda value: value.__setitem__("schema_version", "wrong.v1"),
                    None,
                ),
                "bad_priority_artifact": (
                    lambda value: value.__setitem__("artifact_id", "wrong-artifact"),
                    None,
                ),
                "bad_declared_freshness_schema": (
                    lambda value: value["freshness_receipt"].__setitem__(
                        "schema_version", "wrong.v1"
                    ),
                    None,
                ),
                "bad_actual_freshness_schema": (
                    None,
                    lambda value: value.__setitem__("schema_version", "wrong.v1"),
                ),
                "missing_actual_capture_id": (
                    None,
                    lambda value: value.__setitem__("capture_id", ""),
                ),
            }
            for name, (mutate_priority, mutate_freshness) in cases.items():
                with self.subTest(case=name):
                    rejected = write_case(mutate_priority, mutate_freshness)
                    self.assertNotEqual(0, rejected.returncode)
                    self.assertIn("Source binding rejected", rejected.stderr)


class ProductionCaptureSemanticRejectionTests(unittest.TestCase):
    def _run_fixture(
        self,
        temporary_root: Path,
        fixture: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        fixture_path = temporary_root / "semantic-fixture.json"
        fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
        return subprocess.run(
            [
                "node",
                str(SCRIPT_PATH),
                "--validate-semantic-fixture",
                str(fixture_path),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_one_priority_plan_passes_and_stale_readback_contract_is_rejected(
        self,
    ) -> None:
        visible = {
            "current-state": True,
            "priority-lane": True,
            "priority-first": True,
            "active-decision": True,
            "evidence-inspector": True,
            "freshness-status": True,
            "provenance": True,
        }
        embedded_priorities = [
            {
                "priority_id": "priority-only",
                "primary_evidence_id": "evidence-only",
                "action": {"ja": "確認する", "en": "Review"},
                "reason": {"ja": "根拠", "en": "Evidence"},
                "owner": {"id": "operator", "ja": "運用担当", "en": "Operator"},
                "evidence_refs": [
                    {
                        "fresh_through": "2026-07-13T00:00:00Z",
                        "source_id": "evidence-only",
                    }
                ],
                "review_action_refs": ["review-only"],
            }
        ]

        def snapshot(language: str) -> dict[str, object]:
            return {
                "language": language,
                "priority_ids": ["priority-only"],
                "evidence_ids": ["evidence-only"],
                "selected_priority_ids": ["priority-only"],
                "decision_priority_id": "priority-only",
                "inspector_priority_id": "priority-only",
                "inspector_evidence_id": "evidence-only",
                "embedded_priorities": embedded_priorities,
                "visible_landmarks": visible,
                "project_identity": {
                    "expected": "DevCockpitCore / supervision-fixture",
                    "rendered": {
                        "visible": True,
                        "text": "DevCockpitCore / supervision-fixture",
                    },
                },
                "lane_identity": {
                    "expected": "Foundation Observer Readiness / fixture",
                    "rendered": {
                        "visible": True,
                        "text": "Foundation Observer Readiness / fixture",
                    },
                },
                "attention_class": {
                    "expected": "active_safe_continuation",
                    "rendered": {
                        "visible": True,
                        "text": "active_safe_continuation",
                    },
                },
            }

        fixture = {
            "expected_priority_contract": {
                "priority_ids": ["priority-only"],
                "evidence_ids": ["evidence-only"],
                "selected_priority_id": "priority-only",
                "evidence_by_priority_id": {
                    "priority-only": "evidence-only",
                },
                "priorities_sha256": _canonical_json_digest(embedded_priorities),
            },
            "japanese": snapshot("ja"),
            "english": snapshot("en"),
        }
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            accepted = self._run_fixture(temporary_root, fixture)
            self.assertEqual(0, accepted.returncode, accepted.stderr)
            payload = json.loads(accepted.stdout)
            self.assertEqual(
                "pass",
                payload["priority_semantic_binding"]["status"],
            )
            plan = payload["priority_interaction_plan"]
            self.assertEqual("single_priority_no_op", plan["mode"])
            self.assertEqual("priority-only", plan["click_target"])
            self.assertEqual(
                {"priority-only"},
                set(plan["keyboard_targets"].values()),
            )
            self.assertTrue(
                payload["priority_semantic_binding"]["checks"][
                    "japanese_embedded_priority_model"
                ]
            )
            self.assertTrue(
                payload["priority_semantic_binding"]["checks"][
                    "english_embedded_priority_model"
                ]
            )

            stale = json.loads(json.dumps(fixture))
            stale["expected_priority_contract"]["priority_ids"] = ["priority-stale"]
            stale["expected_priority_contract"]["selected_priority_id"] = (
                "priority-stale"
            )
            stale["expected_priority_contract"]["evidence_by_priority_id"] = {
                "priority-stale": "evidence-only"
            }
            rejected = self._run_fixture(temporary_root, stale)
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("Priority semantic fixture rejected", rejected.stderr)
            rejected_payload = json.loads(rejected.stdout)
            self.assertEqual(
                "fail",
                rejected_payload["priority_semantic_binding"]["status"],
            )
            self.assertFalse(
                rejected_payload["priority_semantic_binding"]["checks"][
                    "japanese_priority_ids"
                ]
            )

            drift_cases = {
                "action": lambda item: item["action"].__setitem__("en", "Changed"),
                "reason": lambda item: item["reason"].__setitem__("en", "Changed"),
                "owner": lambda item: item["owner"].__setitem__("id", "changed"),
                "fresh_through": lambda item: item["evidence_refs"][0].__setitem__(
                    "fresh_through", "2099-01-01T00:00:00Z"
                ),
                "review_action_refs": lambda item: item.__setitem__(
                    "review_action_refs", ["changed"]
                ),
            }
            for field, mutate in drift_cases.items():
                with self.subTest(full_priority_drift=field):
                    drifted = json.loads(json.dumps(fixture))
                    mutate(drifted["english"]["embedded_priorities"][0])
                    drift_rejected = self._run_fixture(temporary_root, drifted)
                    self.assertNotEqual(0, drift_rejected.returncode)
                    self.assertIn(
                        "Priority semantic fixture rejected",
                        drift_rejected.stderr,
                    )
                    drift_payload = json.loads(drift_rejected.stdout)
                    checks = drift_payload["priority_semantic_binding"]["checks"]
                    self.assertTrue(checks["english_priority_ids"])
                    self.assertFalse(checks["english_embedded_priority_model"])


class ProductionCaptureTrackedPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not MANIFEST_PATH.exists() or not READBACK_PATH.exists():
            raise AssertionError(
                "Production capture package is missing. Generate it and record Worker inspection."
            )
        cls.manifest = _load(MANIFEST_PATH)
        cls.readback = _load(READBACK_PATH)

    def test_manifest_identity_is_content_derived_and_source_bound(self) -> None:
        manifest = self.manifest
        self.assertEqual("production_capture_manifest.v1", manifest["schema_version"])
        self.assertEqual(EXPECTED_ARTIFACT_ID, manifest["artifact_id"])
        identity = manifest["capture_identity"]
        canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        identity_digest = sha256(canonical.encode("utf-8")).hexdigest()
        self.assertEqual(identity_digest, manifest["capture_identity_sha256"])
        self.assertEqual(
            f"priority-review-console-{identity_digest[:24]}",
            manifest["capture_id"],
        )
        self.assertNotIn("captured_at", identity)
        binding = manifest["source_binding"]
        self.assertEqual(identity["html_sha256"], binding["html"]["sha256"])
        self.assertEqual(
            identity["priority_readback_sha256"],
            binding["priority_readback"]["sha256"],
        )
        self.assertEqual(
            identity["freshness_receipt_sha256"],
            binding["freshness_receipt"]["sha256"],
        )
        self.assertEqual(
            identity["production_generator_blob"],
            binding["production_generator"]["blob"],
        )
        self.assertEqual(
            identity["capture_script_sha256"],
            binding["capture_script"]["sha256"],
        )
        self.assertEqual(
            binding["capture_script"]["sha256"],
            manifest["capture_runtime"]["capture_script_sha256"],
        )
        self.assertEqual(
            _text_digest(_bound_path(binding["html"]["path"])),
            binding["html"]["sha256"],
        )
        self.assertEqual(
            _text_digest(_bound_path(binding["priority_readback"]["path"])),
            binding["priority_readback"]["sha256"],
        )
        self.assertEqual(
            _text_digest(_bound_path(binding["freshness_receipt"]["path"])),
            binding["freshness_receipt"]["sha256"],
        )
        self.assertEqual(
            _text_digest(_bound_path(binding["capture_script"]["path"])),
            binding["capture_script"]["sha256"],
        )
        self.assertEqual(
            binding["priority_readback"]["freshness_capture_id"],
            binding["freshness_receipt"]["capture_id"],
        )
        current_generator_blob = subprocess.run(
            ["git", "hash-object", binding["production_generator"]["path"]],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(current_generator_blob, binding["production_generator"]["blob"])

    def test_three_final_captures_have_expected_inventory_hashes_and_decoders(self) -> None:
        screenshots = self.manifest["screenshots"]
        self.assertEqual(set(EXPECTED_SCREENSHOTS), {entry["id"] for entry in screenshots})
        self.assertEqual(3, len(screenshots))
        for entry in screenshots:
            with self.subTest(capture=entry["id"]):
                expected_path, width, height, language = EXPECTED_SCREENSHOTS[entry["id"]]
                self.assertEqual(expected_path, entry["path"])
                path = PACK / entry["path"]
                self.assertTrue(path.is_file())
                self.assertEqual((width, height), _png_dimensions(path))
                self.assertEqual({"width": width, "height": height}, entry["dimensions"])
                self.assertEqual(language, entry["language"])
                self.assertEqual(self.manifest["capture_id"], entry["capture_id"])
                self.assertEqual(_digest(path), entry["normalized_png_sha256"])
                self.assertRegex(entry["decoded_pixel_sha256"], r"\A[0-9a-f]{64}\Z")
                self.assertTrue(entry["selected_priority_id"])
                self.assertTrue(entry["selected_evidence_id"])
                self.assertEqual(REQUIRED_LANDMARKS, set(entry["landmarks"]))
                self.assertTrue(all(item["pass"] for item in entry["landmarks"].values()))
                self.assertTrue(all(item["fully_visible"] for item in entry["landmarks"].values()))
                self.assertTrue(entry["browser_canvas_raster"]["pass"])
                self.assertTrue(entry["ffmpeg_raster"]["pass"])
                self.assertTrue(entry["decoder_agreement"]["pass"])
                self.assertEqual(
                    entry["browser_canvas_raster"]["rgba_sha256"],
                    entry["ffmpeg_raster"]["rgba_sha256"],
                )
                self.assertEqual(
                    entry["decoded_pixel_sha256"],
                    entry["ffmpeg_raster"]["rgba_sha256"],
                )
                self.assertTrue(entry["overflow"]["pass"])
                self.assertTrue(entry["freshness_status_present"])
                self.assertTrue(entry["provenance_present"])
                self.assertTrue(entry["pass"])

    def test_contact_sheet_is_hash_bound_and_dual_decoded(self) -> None:
        contact = self.manifest["contact_sheet"]
        self.assertEqual("contact-sheet", contact["id"])
        self.assertEqual(
            "screenshots/priority-review-console-contact-sheet.png",
            contact["path"],
        )
        path = PACK / contact["path"]
        self.assertEqual((1440, 760), _png_dimensions(path))
        self.assertEqual(contact["normalized_png_sha256"], _digest(path))
        self.assertEqual(
            {"ja-desktop", "en-desktop", "ja-narrow"},
            set(contact["source_capture_ids"]),
        )
        self.assertTrue(contact["browser_canvas_raster"]["pass"])
        self.assertTrue(contact["ffmpeg_raster"]["pass"])
        self.assertTrue(contact["decoder_agreement"]["pass"])
        self.assertTrue(contact["pass"])

    def test_readback_proves_interaction_fallback_overflow_and_decoder_contract(self) -> None:
        readback = self.readback
        self.assertEqual("production_capture_readback.v1", readback["schema_version"])
        self.assertEqual(EXPECTED_ARTIFACT_ID, readback["artifact_id"])
        self.assertEqual(self.manifest["capture_id"], readback["capture_id"])
        for key in AUTOMATED_STATUS_KEYS:
            self.assertEqual("pass", readback[key]["status"], key)
        semantic = readback["automated_semantic_parity"]
        priority_readback = _load(
            ROOT / "samples" / "dashboard" / "devcockpitcore_priority_readback.json"
        )
        expected_priority_ids = [
            item["priority_id"] for item in priority_readback["priorities"]
        ]
        expected_evidence_ids = list(
            dict.fromkeys(
                item["primary_evidence_id"]
                for item in priority_readback["priorities"]
            )
        )
        self.assertEqual(
            expected_priority_ids,
            semantic["expected_priority_contract"]["priority_ids"],
        )
        self.assertEqual(
            expected_evidence_ids,
            semantic["expected_priority_contract"]["evidence_ids"],
        )
        self.assertEqual(
            priority_readback["surface"]["selected_priority_id"],
            semantic["expected_priority_contract"]["selected_priority_id"],
        )
        self.assertEqual(
            _canonical_json_digest(priority_readback["priorities"]),
            semantic["expected_priority_contract"]["priorities_sha256"],
        )
        self.assertEqual(
            semantic["expected_priority_contract"]["priorities_sha256"],
            semantic["japanese"]["embedded_priorities_sha256"],
        )
        self.assertEqual(
            semantic["expected_priority_contract"]["priorities_sha256"],
            semantic["english"]["embedded_priorities_sha256"],
        )
        self.assertTrue(all(semantic["checks"].values()))
        self.assertEqual(
            semantic["japanese"]["priority_ids"],
            semantic["english"]["priority_ids"],
        )
        self.assertEqual(
            semantic["japanese"]["evidence_ids"],
            semantic["english"]["evidence_ids"],
        )
        self.assertGreaterEqual(len(semantic["japanese"]["priority_ids"]), 1)
        self.assertTrue(readback["automated_priority_click_sync"]["state"]["pass"])
        self.assertTrue(
            all(
                step["pass"]
                for step in readback["automated_priority_keyboard_sync"]["steps"]
            )
        )
        self.assertTrue(readback["automated_no_javascript_fallback"]["pass"])
        self.assertTrue(
            all(probe["pass"] for probe in readback["automated_overflow_check"]["probes"])
        )
        self.assertTrue(readback["automated_narrow_order"]["dom_order"])
        self.assertTrue(readback["automated_narrow_order"]["visual_order"])
        negative = readback["partial_black_negative_control"]
        self.assertEqual("priority_first", negative["blacked_landmark"])
        self.assertTrue(negative["browser_canvas"]["detector_rejected"])
        self.assertTrue(negative["ffmpeg"]["detector_rejected"])

    def test_worker_inspection_is_current_hash_bound_and_user_acceptance_is_accepted(self) -> None:
        worker = self.readback["worker_raster_inspection"]
        self.assertEqual("pass", worker["status"])
        self.assertEqual(self.manifest["capture_id"], worker["inspected_capture_id"])
        expected_hashes = {
            entry["path"]: entry["normalized_png_sha256"]
            for entry in [*self.manifest["screenshots"], self.manifest["contact_sheet"]]
        }
        inspected_hashes = {
            entry["path"]: entry["sha256"] for entry in worker["inspected_files"]
        }
        self.assertEqual(expected_hashes, inspected_hashes)
        self.assertEqual(
            {
                "html",
                "priority_readback",
                "freshness_receipt",
                "capture_script",
                "production_generator",
            },
            {entry["role"] for entry in worker["inspected_sources"]},
        )
        self.assertEqual(
            {
                "status": "accepted",
                "selected_direction": "A",
                "production_artifact": "priority-review-console",
            },
            self.readback["user_visual_acceptance"],
        )
        self.assertNotIn("human_visual_review", self.readback)


if __name__ == "__main__":
    unittest.main()
