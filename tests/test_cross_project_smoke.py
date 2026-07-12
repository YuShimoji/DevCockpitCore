from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.cross_project_smoke import (
    RESULT_SCHEMA_VERSION,
    CrossProjectSmokeError,
    _observation_signature,
    _observation_signature_sha256,
    default_smoke,
    run_cross_project_smoke,
    scan_weak_meter_cells_text,
    validate_smoke,
)
from dev_cockpit.validation_pack import (
    scan_forbidden_implementation_text,
    scan_mojibake_text,
    scan_pseudo_git_tags_text,
    scan_raw_local_paths_text,
)


class CrossProjectSmokeTests(unittest.TestCase):
    def test_default_smoke_validates(self) -> None:
        smoke = validate_smoke(default_smoke())
        self.assertEqual(smoke["schema_version"], "cross_project_smoke.v1")
        self.assertEqual(smoke["smoke_key"], "devcockpitcore_cross_project_observer")
        self.assertIn("adapters/devcockpitcore.json", {item["adapter_path"] for item in smoke["adapters"]})

    def test_sample_smoke_loads_and_validates(self) -> None:
        sample = ROOT / "samples" / "cross_project_smokes" / "devcockpitcore_cross_project_smoke.json"
        data = json.loads(sample.read_text(encoding="utf-8"))
        smoke = validate_smoke(data)
        self.assertEqual(smoke["project_key"], "devcockpitcore")

    def test_smoke_result_required_top_level_keys(self) -> None:
        result = run_cross_project_smoke(_self_smoke(), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        for key in (
            "schema_version",
            "generated_at",
            "producer",
            "smoke",
            "summary",
            "projects",
            "hygiene",
            "readiness",
            "gate_input",
            "health",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["schema_version"], RESULT_SCHEMA_VERSION)
        self.assertEqual(result["generated_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(
            result["projects"][0]["status_snapshot"]["observed_at"],
            result["generated_at"],
        )
        self.assertRegex(
            result["projects"][0]["status_snapshot"]["head_revision"],
            r"\A[0-9a-f]{40,64}\Z",
        )

    def test_required_devcockpitcore_self_project_is_present(self) -> None:
        result = run_cross_project_smoke(_self_smoke(), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        keys = {project["project_key"] for project in result["projects"]}
        self.assertIn("devcockpitcore", keys)
        self.assertTrue(result["projects"][0]["required"])

    def test_missing_optional_sibling_repo_is_skipped_without_crash(self) -> None:
        result = run_cross_project_smoke(
            validate_smoke(
                {
                    "schema_version": "cross_project_smoke.v1",
                    "smoke_key": "optional_missing",
                    "project_key": "devcockpitcore",
                    "description": "Unit smoke.",
                    "adapters": [
                        {
                            "adapter_path": "adapters/devcockpitcore.json",
                            "required": False,
                            "repo_path_override": "missing-sibling-repo",
                            "expected_default_branch": "main",
                            "notes": [],
                        }
                    ],
                }
            ),
            repo_path=ROOT,
            generated_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(result["projects"][0]["result"], "skipped")
        self.assertIn(result["summary"]["result"], {"warn", "pass"})

    def test_read_only_boundary_fields_are_present(self) -> None:
        result = run_cross_project_smoke(_self_smoke(), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        boundary = result["projects"][0]["scope_boundary"]
        self.assertIn("target_repo_modified", boundary)
        self.assertEqual(boundary["target_repo_commands"], "read_only_git_status_only")
        self.assertFalse(boundary["default_validation_executed"])
        observation = boundary["target_repo_observation"]
        for field in (
            "signature_before",
            "signature_after",
            "sha256_before",
            "sha256_after",
            "unchanged",
        ):
            self.assertIn(field, observation)
        self.assertTrue(observation["unchanged"])
        self.assertEqual(observation["sha256_before"], observation["sha256_after"])
        self.assertEqual(
            observation["signature_before"]["head_revision"],
            observation["signature_after"]["head_revision"],
        )
        self.assertEqual(
            observation["signature_before"]["remote_parity"]["evidence_basis"],
            "local_tracking_reference_no_fetch",
        )
        self.assertFalse(
            observation["signature_before"]["remote_parity"]["fetch_performed"]
        )

    def test_no_target_repo_writeback_is_attempted(self) -> None:
        before = _short_status(ROOT)
        result = run_cross_project_smoke(_self_smoke(), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        after = _short_status(ROOT)
        self.assertEqual(before, after)
        self.assertFalse(result["projects"][0]["scope_boundary"]["target_repo_modified"])
        self.assertTrue(
            result["projects"][0]["scope_boundary"]["target_repo_observation"]["unchanged"]
        )

    def test_observation_signature_hash_changes_with_full_head_revision(self) -> None:
        base = {
            "exists": True,
            "is_git_repo": True,
            "branch": "main",
            "head_revision": "a" * 40,
            "upstream": "origin/main",
            "remote_parity": {
                "ahead": 0,
                "behind": 0,
                "status": "in_sync",
                "tracking_ref": "origin/main",
                "evidence_basis": "local_tracking_reference_no_fetch",
                "fetch_performed": False,
            },
            "worktree": {"state": "clean", "short_status": []},
        }
        changed = {**base, "head_revision": "b" * 40}

        base_signature = _observation_signature(base)
        changed_signature = _observation_signature(changed)

        self.assertNotEqual(
            _observation_signature_sha256(base_signature),
            _observation_signature_sha256(changed_signature),
        )

    def test_branch_mismatch_is_warning_not_fail(self) -> None:
        smoke = _self_smoke(expected_default_branch="not-the-current-branch")
        result = run_cross_project_smoke(smoke, repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["projects"][0]["result"], "warn")
        self.assertNotEqual(result["summary"]["result"], "fail")

    def test_dirty_optional_target_repo_is_warning_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            adapters = temp_root / "adapters"
            adapters.mkdir()
            shutil.copyfile(ROOT / "adapters" / "devcockpitcore.json", adapters / "devcockpitcore.json")
            target = temp_root / "target"
            target.mkdir()
            subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True, text=True)
            (target / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            smoke = validate_smoke(
                {
                    "schema_version": "cross_project_smoke.v1",
                    "smoke_key": "dirty_optional",
                    "project_key": "devcockpitcore",
                    "description": "Unit smoke.",
                    "adapters": [
                        {
                            "adapter_path": "adapters/devcockpitcore.json",
                            "required": False,
                            "repo_path_override": "target",
                            "expected_default_branch": "main",
                            "notes": [],
                        }
                    ],
                }
            )
            result = run_cross_project_smoke(smoke, repo_path=temp_root, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["projects"][0]["result"], "warn")
        self.assertNotEqual(result["summary"]["result"], "fail")

    def test_meter_generation_includes_required_fields(self) -> None:
        result = run_cross_project_smoke(_self_smoke(), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        for item in (result["summary"], result["projects"][0]):
            for field in ("done", "total", "unknown", "meter", "missing"):
                self.assertIn(field, item)

    def test_weak_meter_cell_scan_detects_bare_meter(self) -> None:
        text = "| gate | meter |\n| --- | --- |\n| example | # |\n| good | [#] 1/1 |\n"
        self.assertEqual(scan_weak_meter_cells_text(text), ["#"])

    def test_pseudo_git_tag_scan_detects_synthetic_tag(self) -> None:
        self.assertIn("::git-stage", scan_pseudo_git_tags_text("historical ::git-stage{cwd=\"x\"} residue"))

    def test_mojibake_scan_detects_synthetic_text(self) -> None:
        text = "\u9a3e\uff76\u30fb\uff63\u95d6\uff6b\u30fb\uff6e"
        self.assertIn("\u9a3e\uff76", scan_mojibake_text(text))

    def test_raw_local_path_scan_detects_raw_and_allows_redacted(self) -> None:
        raw = r"C:\Users\someone\Repo"
        redacted = r"C:\Users\<redacted>\Repo"
        result = scan_raw_local_paths_text(f"{raw}\n{redacted}")
        self.assertIn(raw, result["raw"])
        self.assertIn(redacted, result["redacted"])

    def test_forbidden_implementation_scan_distinguishes_context(self) -> None:
        docs_text = "The scheduler remains out of scope for this observer slice."
        source_text = "subprocess.run(command, " + "shell=True" + ")"
        self.assertEqual(scan_forbidden_implementation_text(docs_text, source_kind="docs"), [])
        self.assertIn("shell_true", scan_forbidden_implementation_text(source_text, source_kind="src"))

    def test_cross_project_smoke_rejects_arbitrary_command_fields(self) -> None:
        data = default_smoke()
        data["adapters"][0]["command"] = "python -m unittest"
        with self.assertRaises(CrossProjectSmokeError):
            validate_smoke(data)

    def test_cross_project_smoke_does_not_emit_paste_ready_prompt(self) -> None:
        result = run_cross_project_smoke(_self_smoke(), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        payload = json.dumps(result)
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)

    def test_sample_result_json_is_valid_when_present(self) -> None:
        sample = ROOT / "samples" / "cross_project_smokes" / "devcockpitcore_cross_project_smoke_result.json"
        if not sample.exists():
            self.skipTest("sample cross-project smoke result has not been generated")
        data = json.loads(sample.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], RESULT_SCHEMA_VERSION)


def _self_smoke(expected_default_branch: str = "main") -> dict[str, object]:
    return validate_smoke(
        {
            "schema_version": "cross_project_smoke.v1",
            "smoke_key": "self_only",
            "project_key": "devcockpitcore",
            "description": "Unit smoke.",
            "adapters": [
                {
                    "adapter_path": "adapters/devcockpitcore.json",
                    "required": True,
                    "expected_default_branch": expected_default_branch,
                    "notes": [],
                }
            ],
        }
    )


def _short_status(path: Path) -> str:
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


if __name__ == "__main__":
    unittest.main()
