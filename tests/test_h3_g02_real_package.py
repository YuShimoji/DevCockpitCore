from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "artifacts" / "review" / "h3-real-current-nlmytgen-point-in-time-v1"
SAFETY = ROOT / "artifacts" / "review" / "h3-current-observation-safety-boundary-v1"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class H3G02RealPackageTests(unittest.TestCase):
    def test_fixed_inputs_rebuild_derived_outputs_byte_identically(self) -> None:
        package_module = runpy.run_path(
            str(PACKAGE / "generate_package.py"),
            run_name="h3_g02_real_package_test_module",
        )
        build = package_module["_build_package"]
        serialize = package_module["_serialize"]
        first = build()
        second = build()
        self.assertEqual(first, second)

        committed_before = {
            name: (PACKAGE / name).read_bytes()
            for name in ("binding_inventory_v1.json", "package_readback_v1.json")
        }
        for name, value in first.items():
            self.assertEqual(committed_before[name], serialize(value), name)

        with self.assertRaises(ValueError):
            package_module["generate"](output_dir=PACKAGE)
        self.assertEqual(
            committed_before,
            {
                name: (PACKAGE / name).read_bytes()
                for name in committed_before
            },
        )
        self.assertEqual(
            package_module["verify_committed_package"](),
            {
                name: sha256(data).hexdigest()
                for name, data in committed_before.items()
            },
        )

        safety_module = runpy.run_path(
            str(SAFETY / "generate_package.py"),
            run_name="h3_g02_safety_test_module",
        )
        safety_module["verify_committed_package"]()

        receipt = _json(PACKAGE / "receipt" / "current_observation_v1.json")
        observation = receipt["observation"]
        derived = observation["derived"]
        self.assertTrue(derived["actual"])
        self.assertFalse(derived["clean"])
        self.assertTrue(derived["stable"])
        self.assertEqual(observation["before"]["head_revision"], observation["after"]["head_revision"])
        self.assertEqual(observation["before"]["worktree_sha256"], observation["after"]["worktree_sha256"])
        self.assertFalse(receipt["scope_boundary"]["target_repository_writeback"])
        self.assertFalse(receipt["scope_boundary"]["arbitrary_command_execution"])

        readback = _json(PACKAGE / "package_readback_v1.json")
        self.assertTrue(readback["authority"]["authentic_owner_attached_point_in_time_evidence"])
        self.assertFalse(readback["authority"]["current_claim_eligibility"])
        self.assertIn("worktree_not_clean", readback["authority"]["reason_codes"])
        self.assertFalse(readback["authority"]["live_coverage"])
        self.assertFalse(readback["authority"]["executable"])
        self.assertTrue(readback["cross_binding"]["current_observation_receipt"] == "verified")
        self.assertFalse(readback["scope_boundary"]["target_repository_writeback"])
        self.assertFalse(readback["scope_boundary"]["local_absolute_paths_retained"])

        safety_readback = _json(SAFETY / "safety_boundary_machine_readback_v1.json")
        self.assertEqual(
            safety_readback["source_tree_scope"],
            "BOUND_PATHS only; not a repository-wide tree hash",
        )
        self.assertEqual(
            safety_readback["focused_evidence_semantics"],
            "test names are evidence locators, not execution receipts",
        )
        self.assertEqual(
            safety_readback["canonical_state_semantics"],
            "declared package state, not an observed execution result",
        )

        package_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in PACKAGE.rglob("*")
            if path.is_file()
        )
        for forbidden in (
            "C:\\Users\\PLANNER007",
            "C:\\Users\\thank\\Storage\\Media Contents Projects\\NLMYTGen",
        ):
            self.assertNotIn(forbidden, package_text)


if __name__ == "__main__":
    unittest.main()
