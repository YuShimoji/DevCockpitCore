from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.validation_pack import (
    RESULT_SCHEMA_VERSION,
    ValidationPackError,
    default_pack,
    make_meter,
    run_validation_pack,
    scan_conflict_markers_text,
    scan_forbidden_implementation_text,
    scan_mojibake_text,
    scan_prompt_residue_text,
    scan_pseudo_git_tags_text,
    scan_raw_local_paths_text,
    validate_pack,
)


class ValidationPackTests(unittest.TestCase):
    def test_default_pack_validates(self) -> None:
        pack = validate_pack(default_pack())
        self.assertEqual(pack["schema_version"], "validation_pack.v1")
        self.assertEqual(pack["pack_key"], "devcockpitcore_default")
        self.assertTrue(pack["checks"])
        self.assertIn("python_compile", {check["check_key"] for check in pack["checks"]})

    def test_sample_pack_loads_and_validates(self) -> None:
        sample = ROOT / "samples" / "validation_packs" / "devcockpitcore_validation_pack.json"
        data = json.loads(sample.read_text(encoding="utf-8"))
        pack = validate_pack(data)
        self.assertEqual(pack["project_key"], "devcockpitcore")

    def test_validation_result_required_top_level_keys(self) -> None:
        pack = validate_pack(
            {
                "schema_version": "validation_pack.v1",
                "pack_key": "unit_json_only",
                "project_key": "devcockpitcore",
                "description": "Unit test pack.",
                "checks": [
                    {
                        "check_key": "json_parse",
                        "kind": "json",
                        "severity": "required",
                        "enabled": True,
                        "paths": ["adapters"],
                        "targets": [],
                        "allow_fixture_hits": False,
                        "notes": [],
                    }
                ],
            }
        )
        result = run_validation_pack(pack, repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        for key in (
            "schema_version",
            "generated_at",
            "producer",
            "pack",
            "repo",
            "summary",
            "checks",
            "hygiene",
            "gate_input",
            "health",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["schema_version"], RESULT_SCHEMA_VERSION)

    def test_meter_fields_are_ascii_safe(self) -> None:
        meter = make_meter(2, 4, 1, result="warn", missing=1)
        self.assertTrue(set(meter) <= set("#-?~!"))
        check = {
            "schema_version": "validation_pack.v1",
            "pack_key": "unit_json_only",
            "project_key": "devcockpitcore",
            "description": "Unit test pack.",
            "checks": [
                {
                    "check_key": "json_parse",
                    "kind": "json",
                    "severity": "required",
                    "enabled": True,
                    "paths": ["adapters"],
                    "targets": [],
                    "allow_fixture_hits": False,
                    "notes": [],
                }
            ],
        }
        result = run_validation_pack(validate_pack(check), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        for item in (result["summary"], result["checks"][0]):
            for field in ("done", "total", "unknown", "meter", "missing"):
                self.assertIn(field, item)

    def test_json_parse_check_passes_on_sample_json(self) -> None:
        pack = validate_pack(
            {
                "schema_version": "validation_pack.v1",
                "pack_key": "unit_samples_json",
                "project_key": "devcockpitcore",
                "description": "Unit test pack.",
                "checks": [
                    {
                        "check_key": "json_parse",
                        "kind": "json",
                        "severity": "required",
                        "enabled": True,
                        "paths": ["samples/status_snapshots"],
                        "targets": [],
                        "allow_fixture_hits": False,
                        "notes": [],
                    }
                ],
            }
        )
        result = run_validation_pack(pack, repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["checks"][0]["result"], "pass")

    def test_conflict_marker_scan_detects_synthetic_markers(self) -> None:
        text = "<" * 7 + " HEAD\nbody\n" + "=" * 7 + "\nbody\n" + ">" * 7 + " branch\n"
        self.assertEqual(scan_conflict_markers_text(text), ["<<<<<<<", "=======", ">>>>>>>"])

    def test_pseudo_git_tag_scan_detects_synthetic_tag(self) -> None:
        self.assertIn("::git-stage", scan_pseudo_git_tags_text("historical ::git-stage{cwd=\"x\"} residue"))

    def test_mojibake_scan_detects_synthetic_text(self) -> None:
        text = "\u9a3e\uff76\u30fb\uff63\u95d6\uff6b\u30fb\uff6e"
        self.assertIn("\u9a3e\uff76", scan_mojibake_text(text))
        self.assertIn("\u95d6\uff6b", scan_mojibake_text(text))

    def test_raw_local_path_scan_detects_raw_and_allows_redacted(self) -> None:
        raw = r"C:\Users\someone\Repo"
        redacted = r"C:\Users\<redacted>\Repo"
        result = scan_raw_local_paths_text(f"{raw}\n{redacted}")
        self.assertIn(raw, result["raw"])
        self.assertIn(redacted, result["redacted"])

    def test_prompt_residue_scan_detects_paste_target(self) -> None:
        self.assertIn("[PASTE TARGET:", scan_prompt_residue_text("[PASTE TARGET: Codex/DevCockpitCore]"))

    def test_forbidden_implementation_scan_distinguishes_context(self) -> None:
        docs_text = "The scheduler remains out of scope for this observer slice."
        source_text = "subprocess.run(command, " + "shell=True" + ")"
        self.assertEqual(scan_forbidden_implementation_text(docs_text, source_kind="docs"), [])
        self.assertIn("shell_true", scan_forbidden_implementation_text(source_text, source_kind="src"))

    def test_validation_pack_rejects_arbitrary_command_fields(self) -> None:
        data = default_pack()
        data["checks"][0]["command"] = "python -m unittest"
        with self.assertRaises(ValidationPackError):
            validate_pack(data)

    def test_invalid_pack_fails_cleanly(self) -> None:
        with self.assertRaises(ValidationPackError):
            validate_pack({"schema_version": "validation_pack.v1", "checks": []})

    def test_sample_result_json_is_valid_when_present(self) -> None:
        sample = ROOT / "samples" / "validation_packs" / "devcockpitcore_validation_pack_result.json"
        if not sample.exists():
            self.skipTest("sample validation pack result has not been generated")
        data = json.loads(sample.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], RESULT_SCHEMA_VERSION)

    def test_validation_pack_does_not_emit_paste_ready_next_agent_prompt(self) -> None:
        result = run_validation_pack(
            validate_pack(
                {
                    "schema_version": "validation_pack.v1",
                    "pack_key": "unit_json_only",
                    "project_key": "devcockpitcore",
                    "description": "Unit test pack.",
                    "checks": [
                        {
                            "check_key": "json_parse",
                            "kind": "json",
                            "severity": "required",
                            "enabled": True,
                            "paths": ["adapters"],
                            "targets": [],
                            "allow_fixture_hits": False,
                            "notes": [],
                        }
                    ],
                }
            ),
            repo_path=ROOT,
            generated_at="2026-01-01T00:00:00Z",
        )
        payload = json.dumps(result)
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)


if __name__ == "__main__":
    unittest.main()
