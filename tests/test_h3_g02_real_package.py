from __future__ import annotations

import json
from hashlib import sha256
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dev_cockpit.supervision_packet import SupervisionPacketError

PACKAGE = ROOT / "artifacts" / "review" / "h3-real-current-nlmytgen-point-in-time-v1"
SAFETY = ROOT / "artifacts" / "review" / "h3-current-observation-safety-boundary-v1"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class H3G02RealPackageTests(unittest.TestCase):
    def test_clean_interpreter_module_closure_is_exact_and_lazy(self) -> None:
        code = """
import json
import runpy
import sys
import tempfile
from pathlib import Path

root = Path.cwd().resolve()
sys.path.insert(0, str(root / "src"))
module = runpy.run_path(
    str(root / "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/generate_package.py"),
    run_name="h3_g02_clean_closure_test",
)
with tempfile.TemporaryDirectory(prefix="h3-g02-clean-closure-") as output_dir:
    module["generate"](output_dir=output_dir)
    actual = sorted(
        {
            Path(path).resolve().relative_to(root).as_posix()
            for loaded in sys.modules.values()
            if (path := getattr(loaded, "__file__", None))
            and Path(path).suffix == ".py"
            and Path(path).resolve().is_relative_to(root)
        }
    )
print(
    json.dumps(
        {
            "actual": actual,
            "declared": sorted(module["REPOSITORY_LOCAL_PRODUCER_MODULES"]),
        }
    )
)
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["declared"], result["actual"])
        excluded = {
            "src/dev_cockpit/adapters.py",
            "src/dev_cockpit/cross_project_smoke.py",
            "src/dev_cockpit/git_status.py",
            "src/dev_cockpit/status_snapshot.py",
            "src/dev_cockpit/validation_pack.py",
        }
        self.assertTrue(excluded.isdisjoint(result["actual"]))

    def test_undeclared_module_closure_is_rejected(self) -> None:
        package_module = runpy.run_path(
            str(PACKAGE / "generate_package.py"),
            run_name="h3_g02_undeclared_closure_test_module",
        )
        actual = set(package_module["REPOSITORY_LOCAL_PRODUCER_MODULES"])
        actual.add("src/dev_cockpit/undeclared_test_module.py")
        with self.assertRaisesRegex(
            package_module["DependencyClosureError"],
            r"repository module dependency closure mismatch: .*undeclared_test_module\.py",
        ):
            package_module["_assert_repository_module_closure"](actual)

    def test_declared_module_drift_rejects_without_tracked_writeback(self) -> None:
        package_module = runpy.run_path(
            str(PACKAGE / "generate_package.py"),
            run_name="h3_g02_declared_module_drift_test_module",
        )
        tracked_before = {
            path.relative_to(PACKAGE).as_posix(): path.read_bytes()
            for path in PACKAGE.rglob("*")
            if path.is_file()
        }
        with tempfile.TemporaryDirectory(prefix="h3-g02-module-drift-") as temp_dir:
            reconstruction_root = Path(temp_dir) / "reconstruction-root"
            package_module["_prepare_reconstruction_root"](reconstruction_root)
            module_path = (
                reconstruction_root / "src/dev_cockpit/report_normalizer.py"
            )
            module_path.write_bytes(module_path.read_bytes() + b"\nDRIFT\n")
            outputs = package_module["_reconstruct"](reconstruction_root)
            with self.assertRaisesRegex(
                RuntimeError,
                r"committed binding_inventory_v2\.json does not match reconstructed bytes",
            ):
                package_module["_verify_committed_outputs"](outputs)
        self.assertEqual(
            tracked_before,
            {
                path.relative_to(PACKAGE).as_posix(): path.read_bytes()
                for path in PACKAGE.rglob("*")
                if path.is_file()
            },
        )

    def test_two_independent_staging_builds_match(self) -> None:
        package_module = runpy.run_path(
            str(PACKAGE / "generate_package.py"),
            run_name="h3_g02_real_package_test_module",
        )
        generated_paths = tuple(package_module["REGENERATED_DERIVED_OUTPUTS"])
        package_rel = package_module["PACKAGE_REL"] + "/"
        expected_names = {
            path.removeprefix(package_rel) for path in generated_paths
        }
        tracked_before = {
            path.relative_to(PACKAGE).as_posix(): path.read_bytes()
            for path in PACKAGE.rglob("*")
            if path.is_file()
        }
        with tempfile.TemporaryDirectory(prefix="h3-g02-stage-a-") as stage_a, \
                tempfile.TemporaryDirectory(prefix="h3-g02-stage-b-") as stage_b:
            package_module["generate"](output_dir=stage_a)
            package_module["generate"](output_dir=stage_b)
            stage_a_files = {
                path.relative_to(stage_a).as_posix(): path.read_bytes()
                for path in Path(stage_a).rglob("*")
                if path.is_file()
            }
            stage_b_files = {
                path.relative_to(stage_b).as_posix(): path.read_bytes()
                for path in Path(stage_b).rglob("*")
                if path.is_file()
            }
            self.assertEqual(set(stage_a_files), expected_names)
            self.assertEqual(set(stage_b_files), expected_names)
            self.assertEqual(stage_a_files, stage_b_files)
            self.assertEqual(
                {
                    path: (PACKAGE / path).read_bytes()
                    for path in expected_names
                },
                stage_a_files,
            )

        with self.assertRaises(ValueError):
            package_module["generate"](output_dir=PACKAGE)
        with self.assertRaises(ValueError):
            package_module["generate"](
                output_dir=PACKAGE / "temporary-output-descendant"
            )
        self.assertEqual(
            tracked_before,
            {
                path.relative_to(PACKAGE).as_posix(): path.read_bytes()
                for path in PACKAGE.rglob("*")
                if path.is_file()
            },
        )
        self.assertEqual(
            package_module["verify_committed_package"](),
            {
                path: sha256((PACKAGE / path).read_bytes()).hexdigest()
                for path in expected_names
            },
        )

    def test_mutated_fixed_input_is_rejected_without_tracked_writeback(self) -> None:
        package_module = runpy.run_path(
            str(PACKAGE / "generate_package.py"),
            run_name="h3_g02_real_package_drift_test_module",
        )
        tracked_before = {
            path.relative_to(PACKAGE).as_posix(): path.read_bytes()
            for path in PACKAGE.rglob("*")
            if path.is_file()
        }
        with tempfile.TemporaryDirectory(prefix="h3-g02-drift-") as temp_dir:
            reconstruction_root = Path(temp_dir) / "reconstruction-root"
            package_module["_prepare_reconstruction_root"](reconstruction_root)
            source_path = (
                reconstruction_root
                / package_module["FIXED_CAPTURED_INPUTS"][0]
            )
            source_path.write_bytes(source_path.read_bytes() + b"\nDRIFT\n")
            with self.assertRaises(SupervisionPacketError):
                package_module["_reconstruct"](reconstruction_root)
        self.assertEqual(
            tracked_before,
            {
                path.relative_to(PACKAGE).as_posix(): path.read_bytes()
                for path in PACKAGE.rglob("*")
                if path.is_file()
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

        readback = _json(PACKAGE / "package_readback_v2.json")
        self.assertTrue(readback["authority"]["authentic_owner_attached_point_in_time_evidence"])
        self.assertFalse(readback["authority"]["current_claim_eligibility"])
        self.assertIn("worktree_not_clean", readback["authority"]["reason_codes"])
        self.assertFalse(readback["authority"]["live_coverage"])
        self.assertFalse(readback["authority"]["executable"])
        self.assertTrue(readback["cross_binding"]["current_observation_receipt"] == "verified")
        self.assertFalse(readback["scope_boundary"]["target_repository_writeback"])
        self.assertFalse(readback["scope_boundary"]["local_absolute_paths_retained"])
        self.assertTrue(readback["inputs"]["producer_inputs_exclude_committed_derived_files"])
        self.assertEqual(
            readback["inputs"]["measured_repository_module_closure"],
            readback["inputs"]["declared_repository_module_closure"],
        )
        module_hashes = readback["inputs"]["immutable_dependencies"][
            "repository_local_producer_modules"
        ]
        self.assertEqual(
            set(module_hashes),
            set(readback["inputs"]["declared_repository_module_closure"]),
        )
        inventory = _json(PACKAGE / "binding_inventory_v2.json")
        self.assertEqual(
            set(
                inventory["immutable_producer_dependencies"][
                    "repository_local_producer_modules"
                ]["raw_bytes_sha256"]
            ),
            set(readback["inputs"]["declared_repository_module_closure"]),
        )
        self.assertEqual(
            readback["derived_outputs"]["paths"],
            list(package_module["REGENERATED_DERIVED_OUTPUTS"]),
        )
        self.assertTrue(readback["reconstruction"]["output_mapping_path_set_exact"])

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
