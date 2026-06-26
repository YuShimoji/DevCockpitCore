from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.adapters import AdapterError, load_adapter, validate_adapter


class AdapterTests(unittest.TestCase):
    def test_project_adapters_load(self) -> None:
        for name in ("devcockpitcore", "nlmytgen", "writingpage", "clippipegen"):
            with self.subTest(name=name):
                adapter = load_adapter(ROOT / "adapters" / f"{name}.json")
                self.assertEqual(adapter.schema_version, "adapter_manifest.v1")
                self.assertTrue(adapter.project)
                self.assertTrue(adapter.project_key)
                self.assertTrue(adapter.default_branch)
                self.assertTrue(adapter.read_only)
                self.assertIsInstance(adapter.artifact_roots, tuple)
                self.assertIsInstance(adapter.default_validation, tuple)

    def test_adapter_requires_project(self) -> None:
        with self.assertRaises(AdapterError):
            validate_adapter({"schema_version": "adapter_manifest.v1", "read_only": True})

    def test_adapter_must_be_read_only(self) -> None:
        with self.assertRaises(AdapterError):
            validate_adapter({**_valid_adapter(), "read_only": False})

    def test_adapter_rejects_missing_required_fields(self) -> None:
        adapter = _valid_adapter()
        del adapter["schema_version"]
        with self.assertRaises(AdapterError):
            validate_adapter(adapter)

    def test_adapter_rejects_absolute_user_paths(self) -> None:
        adapter = _valid_adapter()
        adapter["documents"] = {
            "runtime_state": r"C:\Users\thank\repo\docs\runtime-state.md",
            "project_context": "docs/project-context.md",
        }
        with self.assertRaises(AdapterError):
            validate_adapter(adapter)

    def test_adapter_rejects_secret_like_fields(self) -> None:
        adapter = _valid_adapter()
        adapter["token"] = "sk-proj-exampleExampleExample"
        with self.assertRaises(AdapterError):
            validate_adapter(adapter)


def _valid_adapter() -> dict[str, object]:
    return {
        "schema_version": "adapter_manifest.v1",
        "project": "Example",
        "project_key": "example",
        "default_branch": "main",
        "repo_hints": {
            "preferred_relative_paths": [
                "../Example",
            ],
        },
        "documents": {
            "runtime_state": "docs/runtime-state.md",
            "project_context": "docs/project-context.md",
        },
        "artifact_roots": ["docs"],
        "status_hints": {
            "active_artifact_patterns": ["artifact_current:"],
            "next_action_patterns": ["next:"],
            "user_work_patterns": ["user_work:"],
            "gate_patterns": ["render_gate:"],
        },
        "forbidden_stage_patterns": ["*.mp4"],
        "default_validation": ["git diff --check"],
        "read_only": True,
    }


if __name__ == "__main__":
    unittest.main()
