from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import runpy
import unittest

from dev_cockpit.current_observation import SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = (
    ROOT
    / "artifacts"
    / "review"
    / "h3-current-observation-safety-boundary-v1"
)
INVENTORY = PACKAGE / "binding_inventory_v1.json"
READBACK = PACKAGE / "safety_boundary_machine_readback_v1.json"


class CurrentObservationSafetyBoundaryArtifactTests(unittest.TestCase):
    def test_artifact_is_strict_bound_deterministic_and_preserves_history(
        self,
    ) -> None:
        namespace = runpy.run_path(str(PACKAGE / "generate_package.py"))
        generate = namespace["generate"]
        historical_paths = tuple(namespace["HISTORICAL_TREE_HASHES"])
        protected_paths = tuple(namespace["PROTECTED_FILE_HASHES"])
        before_trees = {
            path: namespace["_tree_sha256"](ROOT / path)
            for path in historical_paths
        }
        before_files = {
            path: sha256((ROOT / path).read_bytes()).hexdigest()
            for path in protected_paths
        }

        generate()
        first = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in (INVENTORY, READBACK)
        }
        generate()
        second = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in (INVENTORY, READBACK)
        }

        self.assertEqual(first, second)
        inventory = self._load_strict(INVENTORY)
        readback = self._load_strict(READBACK)
        self.assertEqual(
            {
                "schema_version",
                "artifact_id",
                "hash_basis",
                "base_revision",
                "source_tree_sha256",
                "bindings",
            },
            set(inventory),
        )
        self.assertEqual(
            {
                "schema_version",
                "artifact_id",
                "mission_id",
                "state_transition",
                "contracts",
                "focused_evidence",
                "historical_regeneration_handling",
                "preserved_baselines",
                "canonical_state",
                "source_tree_sha256",
                "binding_inventory_sha256",
            },
            set(readback),
        )
        self.assertEqual(SCHEMA_VERSION, "supervision_current_observation.v1")
        self.assertEqual(
            SCHEMA_VERSION,
            readback["contracts"]["current_observation_schema"],
        )
        self.assertFalse(readback["contracts"]["schema_changed"])
        self.assertEqual(set(namespace["BOUND_PATHS"]), set(inventory["bindings"]))
        for path, digest in inventory["bindings"].items():
            with self.subTest(path=path):
                self.assertEqual(sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        self.assertEqual(
            namespace["_binding_tree_sha256"](inventory["bindings"]),
            inventory["source_tree_sha256"],
        )
        self.assertEqual(
            inventory["source_tree_sha256"], readback["source_tree_sha256"]
        )
        self.assertEqual(
            sha256(INVENTORY.read_bytes()).hexdigest(),
            readback["binding_inventory_sha256"],
        )
        self.assertTrue(readback["preserved_baselines"]["all_unchanged"])
        self.assertTrue(
            readback["historical_regeneration_handling"][
                "historical_bytes_preserved"
            ]
        )
        self.assertEqual(
            before_trees,
            {
                path: namespace["_tree_sha256"](ROOT / path)
                for path in historical_paths
            },
        )
        self.assertEqual(
            before_files,
            {
                path: sha256((ROOT / path).read_bytes()).hexdigest()
                for path in protected_paths
            },
        )
        self.assertFalse(
            readback["canonical_state"][
                "real_nlmytgen_observation_performed_by_this_mission"
            ]
        )
        self.assertFalse(readback["canonical_state"]["main_integration_performed"])
        self.assertFalse(readback["canonical_state"]["h4_started"])

    @staticmethod
    def _load_strict(path: Path) -> dict[str, object]:
        def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise AssertionError(f"duplicate key {key!r} in {path}")
                result[key] = value
            return result

        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_pairs)
        if not isinstance(value, dict):
            raise AssertionError(f"{path} must contain one JSON object")
        return value


if __name__ == "__main__":
    unittest.main()
