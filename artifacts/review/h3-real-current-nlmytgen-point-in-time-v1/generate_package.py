from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from dev_cockpit.current_observation import load_current_observation
from dev_cockpit.report_authority_v2 import load_authority_envelope_v2
from dev_cockpit.supervision_packet import load_packet_with_manifest


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
ARTIFACT_ID = "h3-real-current-nlmytgen-point-in-time-v1"
DEVCOCKPIT_BASE_REVISION = "e7bbe331ecaa2cc21fbffede5013337bd0934c77"
SOURCE_REVISION = "21194b60f6824eaedaddacf05bb920e1a324936a"
ASSESSED_AT = "2026-07-25T03:05:47.2597223+09:00"
OBSERVATION_ARTIFACT_ID = "h3-g02-real-nlmytgen-observation-v1"
AUTHORITY_ARTIFACT_ID = "h3-g02-real-nlmytgen-authority-envelope-v2"

BOUND_PATHS = (
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/source/AGENT_REPORT_G02_NLMYTGEN_V1.md",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/receipt/current_observation_v1.json",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/manifest/task_report_manifest_v1.json",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/packet/cross_project_supervision_packet_v1.json",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/packet/cross_project_supervision_packet_v1.md",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/normalization/report_normalization_v1.json",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/authority/supervision_report_authority_envelope_v2.json",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/dashboard/devcockpitcore_dashboard.html",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/dashboard/review_actions.json",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/dashboard/review_actions.md",
    "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1/dashboard/priority_readback.json",
    "artifacts/review/h3-current-observation-safety-boundary-v1/binding_inventory_v1.json",
    "artifacts/review/h3-current-observation-safety-boundary-v1/safety_boundary_machine_readback_v1.json",
)


def generate(*, output_dir: str | Path | None = None) -> dict[str, dict[str, Any]]:
    package = _build_package()
    if output_dir is not None:
        _write_staging(Path(output_dir), package)
    return package


def _build_package() -> dict[str, dict[str, Any]]:
    bindings = {
        path: _sha256(ROOT / path)
        for path in BOUND_PATHS
    }
    observation = load_current_observation(ROOT / BOUND_PATHS[1])
    packet = load_packet_with_manifest(
        ROOT / BOUND_PATHS[3],
        ROOT / BOUND_PATHS[2],
        repo_root=ROOT,
    )
    envelope = load_authority_envelope_v2(
        ROOT / BOUND_PATHS[6],
        manifest_path=ROOT / BOUND_PATHS[2],
        packet_path=ROOT / BOUND_PATHS[3],
        current_observation_path=ROOT / BOUND_PATHS[1],
        repo_root=ROOT,
        assessed_at=ASSESSED_AT,
        expected_artifact_id=AUTHORITY_ARTIFACT_ID,
        expected_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
    )
    dashboard_readback = _strict_json(ROOT / BOUND_PATHS[10])
    manifest = _strict_json(ROOT / BOUND_PATHS[2])
    source_report_hash = _sha256(ROOT / BOUND_PATHS[0])
    if manifest["reports"][0]["content_sha256"] != source_report_hash:
        raise RuntimeError("manifest report hash does not match captured source report")

    _verify_cross_bindings(observation, packet, envelope, dashboard_readback)
    authority = dict(envelope["authority"])
    derived = observation["observation"]["derived"]
    before = observation["observation"]["before"]
    after = observation["observation"]["after"]
    readback = {
        "schema_version": "h3_real_current_nlmytgen_point_in_time_machine_readback.v1",
        "artifact_id": ARTIFACT_ID,
        "mission_id": "dcc-h3-g02-real-nlmytgen-observation",
        "devcockpitcore_base_revision": DEVCOCKPIT_BASE_REVISION,
        "transition": {
            "from": "owner_existing_dirty_nlmytgen_checkout_without_real_h3_package",
            "to": "stable_dirty_authentic_point_in_time_negative_package",
        },
        "source": {
            "project_key": observation["project_key"],
            "repository_identity": observation["repository"]["identity"],
            "source_revision": before["head_revision"],
            "report_sha256": source_report_hash,
            "report_observed_at": _report_field(
                ROOT / BOUND_PATHS[0], "observed_at"
            ),
            "source_branch": _report_field(
                ROOT / BOUND_PATHS[0], "source_branch"
            ),
            "evidence_class": "authentic_owner_authorized_point_in_time_report",
            "authority_basis": "owner_authorized_current_checkout_observation",
            "report_permission": _report_field(
                ROOT / BOUND_PATHS[0], "observer_only_permission"
            ),
            "tests_executed": False,
            "remote_freshness_established": False,
        },
        "observation": {
            "artifact_id": observation["artifact_id"],
            "first_observed_at": observation["observation"]["first_observed_at"],
            "reobserved_at": observation["observation"]["reobserved_at"],
            "before_head_revision": before["head_revision"],
            "after_head_revision": after["head_revision"],
            "before_worktree_sha256": before["worktree_sha256"],
            "after_worktree_sha256": after["worktree_sha256"],
            "before_worktree_entry_count": before["worktree_entry_count"],
            "after_worktree_entry_count": after["worktree_entry_count"],
            "actual": derived["actual"],
            "clean": derived["clean"],
            "stable": derived["stable"],
            "observation_authorization": observation["authorization"]["scope"],
        },
        "authority": {
            "report_permission": envelope["report"]["observer_permission_scope"],
            "observation_authorization": envelope["observation"]["authorization_scope"],
            "authentic_owner_attached_point_in_time_evidence": authority[
                "authentic_owner_attached_point_in_time_evidence"
            ],
            "current_claim_eligibility": authority["current_claim_eligibility"],
            "reason_codes": authority["reason_codes"],
            "live_coverage": authority["live_coverage"],
            "executable": envelope["scope_boundary"]["executable"],
            "provenance": envelope["provenance"],
            "evidence_validity": "valid",
            "observed_result": "pass",
            "decision_effect": "none",
        },
        "chronology": {
            "report_observed_at": envelope["report"]["observed_at"],
            "first_observed_at": envelope["observation"]["first_observed_at"],
            "reobserved_at": envelope["observation"]["reobserved_at"],
            "assessed_at": envelope["assessment"]["assessed_at"],
            "state": authority["chronology_state"],
        },
        "cross_binding": {
            "source_manifest_packet": "verified",
            "current_observation_receipt": "verified",
            "repository_project_revision": "verified",
            "authority_envelope_reprojection": "verified",
            "dashboard_readback_projection": "verified",
        },
        "derived_outputs": {
            "fixed_input_reprojection": True,
            "target_repository_reobserved_for_regeneration": False,
            "byte_identical_regeneration_evidence": (
                "tests.test_h3_g02_real_package.H3G02RealPackageTests.test_fixed_inputs_rebuild_derived_outputs_byte_identically"
            ),
            "paths": list(BOUND_PATHS),
        },
        "historical_invariance": {
            "safety_boundary_inventory_sha256": _sha256(
                ROOT / "artifacts/review/h3-current-observation-safety-boundary-v1/binding_inventory_v1.json"
            ),
            "safety_boundary_readback_sha256": _sha256(
                ROOT / "artifacts/review/h3-current-observation-safety-boundary-v1/safety_boundary_machine_readback_v1.json"
            ),
            "accepted_historical_and_production_baselines": "verified by safety-boundary generator",
        },
        "canonical_state": {
            "real_observation_performed": True,
            "real_current_claim_eligibility": False,
            "live_coverage": False,
            "executable": False,
            "main_integration_performed": False,
            "h4_started": False,
        },
        "scope_boundary": {
            "observer_only": True,
            "target_repository_writeback": False,
            "fetch_performed": False,
            "tests_executed_in_target": False,
            "dirty_path_names_retained": False,
            "local_absolute_paths_retained": False,
            "credentials_or_secrets_retained": False,
        },
    }
    inventory = {
        "schema_version": "h3_real_current_nlmytgen_point_in_time_binding_inventory.v1",
        "artifact_id": ARTIFACT_ID,
        "hash_basis": "repository_relative_path_and_raw_bytes_sha256_v1",
        "base_revision": DEVCOCKPIT_BASE_REVISION,
        "source_revision": SOURCE_REVISION,
        "source_tree_scope": "BOUND_PATHS only; not a repository-wide tree hash",
        "source_tree_sha256": _binding_tree_sha256(bindings),
        "bindings": bindings,
    }
    inventory_payload = _serialize(inventory)
    readback["binding_inventory_sha256"] = sha256(inventory_payload).hexdigest()
    return {
        "binding_inventory_v1.json": inventory,
        "package_readback_v1.json": readback,
    }


def _verify_cross_bindings(
    observation: dict[str, Any],
    packet: dict[str, Any],
    envelope: dict[str, Any],
    dashboard_readback: dict[str, Any],
) -> None:
    source_revision = observation["observation"]["before"]["head_revision"]
    identity = observation["repository"]["identity"]
    if observation["observation"]["after"]["head_revision"] != source_revision:
        raise RuntimeError("observation revision changed during package reprojection")
    if envelope["report"]["source_revision"] != source_revision:
        raise RuntimeError("report and observation revisions differ")
    if envelope["report"]["repository_identity"] != identity:
        raise RuntimeError("envelope repository identity differs from receipt")
    if packet["source_bindings"][0]["content_sha256"] != envelope["bindings"]["source_report"]["content_sha256"]:
        raise RuntimeError("packet and envelope source report bindings differ")
    projection = dashboard_readback["supervision_report_authority_envelope"]
    if projection["authority"] != envelope["authority"]:
        raise RuntimeError("Dashboard authority projection differs from envelope")
    if projection["observation"] != envelope["observation"]:
        raise RuntimeError("Dashboard observation projection differs from envelope")
    if projection["scope_boundary"]["executable"] is not False:
        raise RuntimeError("Dashboard executable boundary is not false")


def verify_committed_package(
    package: dict[str, dict[str, Any]] | None = None,
) -> dict[str, str]:
    expected = package if package is not None else _build_package()
    result: dict[str, str] = {}
    for name, value in expected.items():
        path = PACKAGE / name
        actual = path.read_bytes()
        encoded = _serialize(value)
        if actual != encoded:
            raise RuntimeError(
                f"committed {name} does not match fixed inputs; refusing to overwrite tracked package"
            )
        result[name] = sha256(actual).hexdigest()
    return result


def _write_staging(output_dir: Path, package: dict[str, dict[str, Any]]) -> None:
    destination = output_dir.resolve()
    if destination == PACKAGE.resolve():
        raise ValueError("staging output must not be the tracked outcome package")
    destination.mkdir(parents=True, exist_ok=True)
    for name, value in package.items():
        (destination / name).write_bytes(_serialize(value))


def _strict_json(path: Path) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise RuntimeError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain one JSON object")
    return value


def _report_field(path: Path, key: str) -> str:
    prefix = f"- {key}: `"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix) and line.endswith("`"):
            return line[len(prefix):-1]
    raise RuntimeError(f"report field {key!r} is missing")


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _binding_tree_sha256(bindings: dict[str, str]) -> str:
    digest = sha256()
    for path in sorted(bindings):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bindings[path].encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _serialize(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build or verify the fixed-input H3-G02 outcome package."
    )
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.output_dir is not None:
        package = generate(output_dir=args.output_dir)
        print(f"staged {len(package)} package files in {args.output_dir.resolve()}")
    else:
        hashes = verify_committed_package()
        for name, digest in hashes.items():
            print(f"{name}: {digest}")
