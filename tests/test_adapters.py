from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.adapters import AdapterError, load_adapter, validate_adapter


class AdapterTests(unittest.TestCase):
    def test_project_adapters_load(self) -> None:
        for name in ("nlmytgen", "writingpage", "clippipegen"):
            with self.subTest(name=name):
                adapter = load_adapter(ROOT / "adapters" / f"{name}.json")
                self.assertTrue(adapter.project)
                self.assertTrue(adapter.read_only)
                self.assertIsInstance(adapter.artifact_roots, tuple)
                self.assertIsInstance(adapter.default_validation, tuple)

    def test_adapter_requires_project(self) -> None:
        with self.assertRaises(AdapterError):
            validate_adapter({"read_only": True})

    def test_adapter_must_be_read_only(self) -> None:
        with self.assertRaises(AdapterError):
            validate_adapter({"project": "Example", "read_only": False})


if __name__ == "__main__":
    unittest.main()
