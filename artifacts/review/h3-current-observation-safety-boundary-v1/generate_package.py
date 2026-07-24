from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
ARTIFACT_ID = "h3-current-observation-safety-boundary-v1"
BASE_REVISION = "7b3024ab6648022396e9e915c73b54db74b75f47"

BOUND_PATHS = (
    "src/dev_cockpit/current_observation.py",
    "src/dev_cockpit/report_authority_v2.py",
    "src/dev_cockpit/dashboard.py",
    "tests/test_current_observation.py",
    "tests/test_current_observation_ingress_cli.py",
    "tests/test_current_observation_safety_boundary_artifact.py",
    "tests/test_report_authority_v2.py",
    "tests/test_project_state_contract.py",
    "README.md",
    "docs/PROJECT_COCKPIT.md",
    "docs/runtime-state.md",
    "docs/decision-log.md",
    "artifacts/review/h3-current-observation-safety-boundary-v1/README.md",
    "artifacts/review/h3-current-observation-safety-boundary-v1/generate_package.py",
)

HISTORICAL_TREE_HASHES = {
    "artifacts/review/h2-authentic-single-report-round-trip-v1":
        "bd63725b106d80cb573c27f3fadc55a07448c293b4e35a73d0a79d1dc0ac2da5",
    "artifacts/review/h3-report-authority-envelope-v1":
        "d9a86453163b7db4aa1beaddb3d1483a7e8e35ad7f12ade179e3a359b5acc278",
    "artifacts/review/h3-current-observation-ingress-v1":
        "9fda3e100cc57a39d92cd37898617f528b80f276372aef75fd43d75ffa8c331b",
}

PROTECTED_FILE_HASHES = {
    "samples/supervision_packets/cross_project_supervision_packet_v1.json":
        "07965839fdef3d591776804e23d94d26996b5a13a6bf380fbe4e263231f59aec",
    "samples/supervision_packets/cross_project_supervision_packet_v1.md":
        "d28dbfbde4d162e84843889141408972ea2946d09ba6b581e56c7c2378362fb7",
    "samples/dashboard/devcockpitcore_dashboard.html":
        "376521d0367ddfb2e8fa2e6f3c1020baa88f1fa5a3587f7bad9fbeabca7215e1",
    "samples/dashboard/devcockpitcore_priority_readback.json":
        "fb0d4ad091af5e4204c4fee15bd71231e7b3371d8399e920ca0ad0b81d85fe29",
    "samples/dashboard/production_capture/production_capture_manifest.json":
        "2d9fcd3af5865391e5da3200f00086c2133b352e01674375084dcb9a61c57181",
}


def generate() -> None:
    preserved = _verify_preserved_baselines()
    bindings = {
        path: sha256((ROOT / path).read_bytes()).hexdigest() for path in BOUND_PATHS
    }
    source_tree_sha256 = _binding_tree_sha256(bindings)
    inventory = {
        "schema_version": "h3_current_observation_safety_boundary_binding_inventory.v1",
        "artifact_id": ARTIFACT_ID,
        "hash_basis": "repository_relative_path_and_raw_bytes_sha256_v1",
        "base_revision": BASE_REVISION,
        "source_tree_sha256": source_tree_sha256,
        "bindings": bindings,
    }
    inventory_payload = json.dumps(
        inventory, ensure_ascii=True, indent=2
    ) + "\n"
    readback = {
        "schema_version": "h3_current_observation_safety_boundary_machine_readback.v1",
        "artifact_id": ARTIFACT_ID,
        "mission_id": "dcc-h3-g01-current-observation-boundary",
        "state_transition": {
            "from": "h3_current_observation_safety_hardened_dirty_source_stop_v1",
            "to": "h3_current_observation_environment_isolated_dirty_negative_contract_v1",
        },
        "contracts": {
            "current_observation_schema": "supervision_current_observation.v1",
            "schema_changed": False,
            "git_environment": {
                "inherited_git_variables_removed_case_insensitively": True,
                "optional_locks_disabled": True,
                "terminal_prompt_disabled": True,
                "credential_manager_interaction_disabled": True,
                "system_config_disabled": True,
                "global_config_target": "platform_null_device",
                "remote_identity_scope": "local_no_includes",
                "core_fsmonitor_disabled_for_every_git_call": True,
            },
            "dirty_stable_observation": {
                "actual": True,
                "clean": False,
                "stable": True,
                "authentic_point_in_time_negative_observation": True,
                "current_claim_eligibility": False,
                "live_coverage": False,
                "executable": False,
                "producer_stop_caused_only_by_dirty": False,
            },
        },
        "focused_evidence": {
            "environment_matrix": [
                "tests.test_current_observation.CurrentObservationTests.test_git_environment_removes_inherited_git_controls_case_insensitively",
                "tests.test_current_observation.CurrentObservationTests.test_inherited_redirect_trace_and_config_controls_are_inert",
                "tests.test_current_observation.CurrentObservationTests.test_fsmonitor_hook_is_disabled_for_every_observation_git_command",
                "tests.test_current_observation.CurrentObservationTests.test_output_inside_git_topology_or_linked_worktree_is_rejected",
            ],
            "dirty_public_cli_round_trip":
                "tests.test_current_observation_ingress_cli.CurrentObservationIngressCliTests.test_dirty_stable_public_cli_round_trip_is_negative_observation",
            "clean_public_cli_round_trip":
                "tests.test_current_observation_ingress_cli.CurrentObservationIngressCliTests.test_controlled_temporary_git_public_cli_end_to_end",
            "artifact_regeneration":
                "tests.test_current_observation_safety_boundary_artifact.CurrentObservationSafetyBoundaryArtifactTests.test_artifact_is_strict_bound_deterministic_and_preserves_history",
        },
        "historical_regeneration_handling": {
            "affected_identity": "h3-current-observation-ingress-v1",
            "observed_side_effect": "tracked_binding_json_refresh",
            "classification": "mission_introduced_change_not_retained_under_historical_identity",
            "final_source_binding": ARTIFACT_ID,
            "historical_bytes_preserved": True,
        },
        "preserved_baselines": preserved,
        "canonical_state": {
            "real_nlmytgen_observation_performed_by_this_mission": False,
            "real_current_claim_eligibility": False,
            "live_coverage": False,
            "executable": False,
            "main_integration_performed": False,
            "h4_started": False,
        },
        "source_tree_sha256": source_tree_sha256,
        "binding_inventory_sha256": sha256(
            inventory_payload.encode("utf-8")
        ).hexdigest(),
    }
    _write("binding_inventory_v1.json", inventory)
    _write("safety_boundary_machine_readback_v1.json", readback)


def _verify_preserved_baselines() -> dict[str, Any]:
    trees = {
        path: {
            "expected_sha256": expected,
            "actual_sha256": _tree_sha256(ROOT / path),
        }
        for path, expected in HISTORICAL_TREE_HASHES.items()
    }
    files = {
        path: {
            "expected_sha256": expected,
            "actual_sha256": sha256((ROOT / path).read_bytes()).hexdigest(),
        }
        for path, expected in PROTECTED_FILE_HASHES.items()
    }
    if any(
        item["actual_sha256"] != item["expected_sha256"]
        for item in (*trees.values(), *files.values())
    ):
        raise RuntimeError("historical or production baseline invariance failed")
    return {
        "historical_trees": trees,
        "protected_files": files,
        "all_unchanged": True,
    }


def _tree_sha256(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _binding_tree_sha256(bindings: dict[str, str]) -> str:
    digest = sha256()
    for path in sorted(bindings):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bindings[path].encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _write(name: str, value: dict[str, Any]) -> None:
    (PACKAGE / name).write_text(
        json.dumps(value, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    generate()
