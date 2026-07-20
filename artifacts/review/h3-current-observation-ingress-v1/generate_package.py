from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
ARTIFACT_ID = "h3-current-observation-ingress-v1"
BOUND_PATHS = (
    "src/dev_cockpit/current_observation.py",
    "src/dev_cockpit/report_authority.py",
    "src/dev_cockpit/report_authority_v2.py",
    "src/dev_cockpit/dashboard.py",
    "tests/test_current_observation.py",
    "tests/test_current_observation_ingress_cli.py",
    "tests/test_report_authority_v2.py",
)


def generate() -> None:
    bindings = {
        path: sha256((ROOT / path).read_bytes()).hexdigest() for path in BOUND_PATHS
    }
    inventory = {
        "schema_version": "h3_current_observation_ingress_binding_inventory.v1",
        "artifact_id": ARTIFACT_ID,
        "hash_basis": "raw_bytes_sha256_v1",
        "bindings": bindings,
    }
    readback = {
        "schema_version": "h3_current_observation_ingress_machine_readback.v1",
        "artifact_id": ARTIFACT_ID,
        "state_transition": {
            "from": "h3_report_authority_envelope_contract_verified_without_live_promotion_v1",
            "to": "h3_current_observation_ingress_operationally_verified_without_real_project_promotion_v1",
        },
        "starting_gap_reproduction": {
            "D1_public_ingress_absent": True,
            "D2_observation_authorization_not_required": True,
            "D3_reobservation_before_report_eligible": True,
            "D4_explicit_artifact_and_split_provenance_absent": True,
        },
        "contracts": {
            "current_observation_schema": "supervision_current_observation.v1",
            "authority_envelope_schema": "supervision_report_authority_envelope.v2",
            "dual_authorization_scope": "allowed_for_DevCockpitCore_H3_current_claim",
            "chronology": "report_observed_at_lte_reobserved_at_lte_assessed_at",
            "observation_producer": "read_only_fixed_git_argv",
            "dashboard_partial_input_policy": "reject_before_projection",
        },
        "controlled_proof": {
            "test_id": "tests.test_current_observation_ingress_cli.CurrentObservationIngressCliTests.test_controlled_temporary_git_public_cli_end_to_end",
            "target": "ephemeral_temporary_git_repository_only",
            "public_cli_sequence": [
                "dev_cockpit.current_observation",
                "dev_cockpit.supervision_packet",
                "dev_cockpit.report_authority_v2_mode",
                "dev_cockpit.dashboard_v2_ingress",
            ],
            "expected_current_claim_eligibility": True,
            "expected_live_coverage": False,
            "expected_executable": False,
            "deterministic_regeneration": "test_recreates_all_inputs_in_a_temporary_directory",
        },
        "preserved_baselines": {
            "h2_package_tree_sha256": "bd63725b106d80cb573c27f3fadc55a07448c293b4e35a73d0a79d1dc0ac2da5",
            "h3_v1_package_tree_sha256": "d9a86453163b7db4aa1beaddb3d1483a7e8e35ad7f12ade179e3a359b5acc278",
            "canonical_packet_json_sha256": "07965839fdef3d591776804e23d94d26996b5a13a6bf380fbe4e263231f59aec",
            "canonical_packet_markdown_sha256": "d28dbfbde4d162e84843889141408972ea2946d09ba6b581e56c7c2378362fb7",
            "production_dashboard_sha256": "376521d0367ddfb2e8fa2e6f3c1020baa88f1fa5a3587f7bad9fbeabca7215e1",
            "production_priority_readback_sha256": "fb0d4ad091af5e4204c4fee15bd71231e7b3371d8399e920ca0ad0b81d85fe29",
            "production_capture_manifest_sha256": "2d9fcd3af5865391e5da3200f00086c2133b352e01674375084dcb9a61c57181",
        },
        "canonical_state": {
            "h2_complete": True,
            "h3_v1_preserved": True,
            "h3_1_ingress_operational": True,
            "real_current_observation_attempted": False,
            "real_current_claim_eligibility": False,
            "live_coverage": False,
            "executable": False,
            "h4_started": False,
        },
        "binding_inventory_sha256": sha256(
            (json.dumps(inventory, ensure_ascii=True, indent=2) + "\n").encode("utf-8")
        ).hexdigest(),
    }
    _write("binding_inventory_v1.json", inventory)
    _write("current_observation_ingress_machine_readback_v1.json", readback)


def _write(name: str, value: dict[str, object]) -> None:
    (PACKAGE / name).write_text(
        json.dumps(value, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    generate()
