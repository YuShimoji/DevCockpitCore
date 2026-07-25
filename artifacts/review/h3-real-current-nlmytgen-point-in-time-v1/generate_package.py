from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def _loaded_repo_module_paths() -> set[str]:
    paths: set[str] = set()
    for module in sys.modules.values():
        module_path = getattr(module, "__file__", None)
        if not module_path:
            continue
        path = Path(module_path).resolve()
        if path.suffix == ".py" and path.is_relative_to(ROOT):
            paths.add(path.relative_to(ROOT).as_posix())
    return paths


_MODULE_CLOSURE_BASELINE = _loaded_repo_module_paths()

from dev_cockpit.current_observation import load_current_observation
from dev_cockpit.dashboard import (
    build_dashboard_model,
    dumps_review_actions,
    priority_readback,
    render_dashboard,
    render_review_actions_markdown,
)
from dev_cockpit.report_authority_v2 import (
    build_authority_envelope_v2,
    dumps_authority_envelope_v2,
)
from dev_cockpit.report_normalizer import dumps_normalization, normalize_report
from dev_cockpit.supervision_packet import (
    SupervisionPacketError,
    build_supervision_packet,
    dumps_packet,
    load_manifest,
    render_packet_markdown,
)


class DependencyClosureError(RuntimeError):
    """Raised when the measured H3-G02 producer-module closure drifts."""


PACKAGE = Path(__file__).resolve().parent
PACKAGE_REL = "artifacts/review/h3-real-current-nlmytgen-point-in-time-v1"
ARTIFACT_ID = "h3-real-current-nlmytgen-point-in-time-v1"
DEVCOCKPIT_BASE_REVISION = "e7bbe331ecaa2cc21fbffede5013337bd0934c77"
SOURCE_REVISION = "21194b60f6824eaedaddacf05bb920e1a324936a"
ASSESSED_AT = "2026-07-25T03:05:47.2597223+09:00"
OBSERVATION_ARTIFACT_ID = "h3-g02-real-nlmytgen-observation-v1"
AUTHORITY_ARTIFACT_ID = "h3-g02-real-nlmytgen-authority-envelope-v2"

REPOSITORY_LOCAL_PRODUCER_MODULES = (
    "src/dev_cockpit/__init__.py",
    "src/dev_cockpit/current_observation.py",
    "src/dev_cockpit/dashboard.py",
    "src/dev_cockpit/evidence_freshness.py",
    "src/dev_cockpit/gate_classifier.py",
    "src/dev_cockpit/report_authority.py",
    "src/dev_cockpit/report_authority_v2.py",
    "src/dev_cockpit/report_normalizer.py",
    "src/dev_cockpit/supervision_packet.py",
)

FIXED_CAPTURED_INPUTS = (
    f"{PACKAGE_REL}/source/AGENT_REPORT_G02_NLMYTGEN_V1.md",
    f"{PACKAGE_REL}/receipt/current_observation_v1.json",
    f"{PACKAGE_REL}/manifest/task_report_manifest_v1.json",
)

IMMUTABLE_NON_MODULE_DEPENDENCIES = (
    f"{PACKAGE_REL}/README.md",
    f"{PACKAGE_REL}/generate_package.py",
    "samples/validation_packs/devcockpitcore_validation_pack_result.json",
    "samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json",
    "samples/status_snapshots/devcockpitcore_status.json",
    "adapters/devcockpitcore.json",
    "docs/runtime-state.md",
    "docs/project-context.md",
    "samples/evidence_freshness/evidence_freshness_receipt_v1.json",
)

ACCEPTED_EXTERNAL_SAFETY_DEPENDENCIES = (
    "artifacts/review/h3-current-observation-safety-boundary-v1/README.md",
    "artifacts/review/h3-current-observation-safety-boundary-v1/binding_inventory_v1.json",
    "artifacts/review/h3-current-observation-safety-boundary-v1/generate_package.py",
    "artifacts/review/h3-current-observation-safety-boundary-v1/safety_boundary_machine_readback_v1.json",
)

IMMUTABLE_PRODUCER_DEPENDENCIES = (
    REPOSITORY_LOCAL_PRODUCER_MODULES
    + IMMUTABLE_NON_MODULE_DEPENDENCIES
    + ACCEPTED_EXTERNAL_SAFETY_DEPENDENCIES
)
NORMALIZATION_PATH = f"{PACKAGE_REL}/normalization/report_normalization_v1.json"
PACKET_JSON_PATH = f"{PACKAGE_REL}/packet/cross_project_supervision_packet_v1.json"
PACKET_MD_PATH = f"{PACKAGE_REL}/packet/cross_project_supervision_packet_v1.md"
AUTHORITY_PATH = f"{PACKAGE_REL}/authority/supervision_report_authority_envelope_v2.json"
DASHBOARD_PATH = f"{PACKAGE_REL}/dashboard/devcockpitcore_dashboard.html"
REVIEW_ACTIONS_JSON_PATH = f"{PACKAGE_REL}/dashboard/review_actions.json"
REVIEW_ACTIONS_MD_PATH = f"{PACKAGE_REL}/dashboard/review_actions.md"
PRIORITY_READBACK_PATH = f"{PACKAGE_REL}/dashboard/priority_readback.json"
INVENTORY_PATH = f"{PACKAGE_REL}/binding_inventory_v2.json"
READBACK_PATH = f"{PACKAGE_REL}/package_readback_v2.json"

REGENERATED_DERIVED_OUTPUTS = (
    NORMALIZATION_PATH,
    PACKET_JSON_PATH,
    PACKET_MD_PATH,
    AUTHORITY_PATH,
    DASHBOARD_PATH,
    REVIEW_ACTIONS_JSON_PATH,
    REVIEW_ACTIONS_MD_PATH,
    PRIORITY_READBACK_PATH,
    INVENTORY_PATH,
    READBACK_PATH,
)
BASE_REGENERATED_DERIVED_OUTPUTS = REGENERATED_DERIVED_OUTPUTS[:-2]


def _assert_repository_module_closure(
    actual_paths: set[str] | None = None,
) -> tuple[str, ...]:
    if actual_paths is None:
        actual = _loaded_repo_module_paths() - _MODULE_CLOSURE_BASELINE
        declared = set(REPOSITORY_LOCAL_PRODUCER_MODULES) - _MODULE_CLOSURE_BASELINE
    else:
        actual = set(actual_paths)
        declared = set(REPOSITORY_LOCAL_PRODUCER_MODULES)
    if actual != declared:
        unexpected = sorted(actual - declared)
        missing = sorted(declared - actual)
        raise DependencyClosureError(
            "repository module dependency closure mismatch: "
            f"unexpected={unexpected}; missing={missing}"
        )
    return tuple(sorted(REPOSITORY_LOCAL_PRODUCER_MODULES))


def generate(*, output_dir: str | Path | None = None) -> dict[str, bytes]:
    """Reconstruct all declared derived outputs in a clean external staging root."""

    if output_dir is not None:
        _validate_output_destination(Path(output_dir))
    with tempfile.TemporaryDirectory(prefix="dcc-h3-g02-repro-") as temp_dir:
        reconstruction_root = Path(temp_dir) / "reconstruction-root"
        _prepare_reconstruction_root(reconstruction_root)
        outputs = _reconstruct(reconstruction_root)
    if output_dir is not None:
        _write_mapping(Path(output_dir), outputs)
    return outputs


def _prepare_reconstruction_root(destination: Path) -> None:
    if destination.exists():
        raise RuntimeError(f"reconstruction root must be new: {destination}")
    for relative_path in FIXED_CAPTURED_INPUTS + IMMUTABLE_PRODUCER_DEPENDENCIES:
        source = ROOT / relative_path
        if not source.is_file():
            raise RuntimeError(f"required reconstruction input is missing: {relative_path}")
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _reconstruct(reconstruction_root: Path) -> dict[str, bytes]:
    manifest_path = FIXED_CAPTURED_INPUTS[2]
    manifest = load_manifest(reconstruction_root / manifest_path)
    generated_at = str(manifest["generated_at"])
    if generated_at != ASSESSED_AT:
        raise RuntimeError(
            f"manifest timestamp changed: expected {ASSESSED_AT}, got {generated_at}"
        )

    source_path = FIXED_CAPTURED_INPUTS[0]
    source_text = (reconstruction_root / source_path).read_text(encoding="utf-8")
    normalization = normalize_report(
        source_text,
        input_path=source_path,
        input_kind="agent_report_text",
        generated_at=generated_at,
    )
    normalization_bytes = dumps_normalization(normalization, pretty=True).encode("utf-8")

    packet = build_supervision_packet(
        manifest,
        repo_root=reconstruction_root,
        manifest_path=manifest_path,
        generated_at=generated_at,
    )
    packet_json_bytes = dumps_packet(packet, pretty=True).encode("utf-8")
    packet_md_bytes = render_packet_markdown(packet).encode("utf-8")

    _write_bytes(reconstruction_root, NORMALIZATION_PATH, normalization_bytes)
    _write_bytes(reconstruction_root, PACKET_JSON_PATH, packet_json_bytes)
    _write_bytes(reconstruction_root, PACKET_MD_PATH, packet_md_bytes)

    authority = build_authority_envelope_v2(
        manifest_path=manifest_path,
        packet_path=PACKET_JSON_PATH,
        current_observation_path=FIXED_CAPTURED_INPUTS[1],
        repo_root=reconstruction_root,
        assessed_at=generated_at,
        artifact_id=AUTHORITY_ARTIFACT_ID,
        expected_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
    )
    authority_bytes = dumps_authority_envelope_v2(authority, pretty=True).encode("utf-8")
    _write_bytes(reconstruction_root, AUTHORITY_PATH, authority_bytes)

    dashboard_model = build_dashboard_model(
        repo_root=reconstruction_root,
        validation_result_path="samples/validation_packs/devcockpitcore_validation_pack_result.json",
        cross_project_smoke_result_path="samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json",
        status_snapshot_path="samples/status_snapshots/devcockpitcore_status.json",
        adapter_path="adapters/devcockpitcore.json",
        runtime_state_path="docs/runtime-state.md",
        project_context_path="docs/project-context.md",
        freshness_receipt_path="samples/evidence_freshness/evidence_freshness_receipt_v1.json",
        output_path=DASHBOARD_PATH,
        review_actions_json_path=REVIEW_ACTIONS_JSON_PATH,
        review_actions_md_path=REVIEW_ACTIONS_MD_PATH,
        priority_readback_path=PRIORITY_READBACK_PATH,
        supervision_packet_path=PACKET_JSON_PATH,
        supervision_manifest_path=manifest_path,
        supervision_authority_envelope_path=AUTHORITY_PATH,
        supervision_authority_assessed_at=generated_at,
        supervision_current_observation_path=FIXED_CAPTURED_INPUTS[1],
        supervision_authority_artifact_id=AUTHORITY_ARTIFACT_ID,
        supervision_current_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
        verify_freshness_hashes=False,
        generated_at=generated_at,
    )
    dashboard_html_bytes = render_dashboard(dashboard_model).encode("utf-8")
    review_actions_bytes = dumps_review_actions(dashboard_model, pretty=True).encode("utf-8")
    review_actions_md_bytes = render_review_actions_markdown(dashboard_model).encode("utf-8")
    dashboard_readback = priority_readback(dashboard_model)
    priority_bytes = _serialize(dashboard_readback)
    _write_bytes(reconstruction_root, DASHBOARD_PATH, dashboard_html_bytes)
    _write_bytes(reconstruction_root, REVIEW_ACTIONS_JSON_PATH, review_actions_bytes)
    _write_bytes(reconstruction_root, REVIEW_ACTIONS_MD_PATH, review_actions_md_bytes)
    _write_bytes(reconstruction_root, PRIORITY_READBACK_PATH, priority_bytes)

    observation = load_current_observation(
        reconstruction_root / FIXED_CAPTURED_INPUTS[1]
    )
    _verify_cross_bindings(
        observation,
        packet,
        authority,
        dashboard_readback,
        dashboard_html_bytes,
    )
    module_closure = _assert_repository_module_closure()

    fixed_bindings = _bindings(reconstruction_root, FIXED_CAPTURED_INPUTS)
    module_bindings = _bindings(
        reconstruction_root, REPOSITORY_LOCAL_PRODUCER_MODULES
    )
    data_bindings = _bindings(
        reconstruction_root, IMMUTABLE_NON_MODULE_DEPENDENCIES
    )
    safety_bindings = _bindings(
        reconstruction_root, ACCEPTED_EXTERNAL_SAFETY_DEPENDENCIES
    )
    derived_bindings = {
        path: sha256(_read_bytes(reconstruction_root, path)).hexdigest()
        for path in BASE_REGENERATED_DERIVED_OUTPUTS
    }
    inventory = _build_inventory(
        fixed_bindings=fixed_bindings,
        module_closure=module_closure,
        module_bindings=module_bindings,
        data_bindings=data_bindings,
        safety_bindings=safety_bindings,
        derived_bindings=derived_bindings,
    )
    inventory_bytes = _serialize(inventory)
    readback = _build_readback(
        observation=observation,
        packet=packet,
        authority=authority,
        manifest=manifest,
        fixed_bindings=fixed_bindings,
        module_closure=module_closure,
        module_bindings=module_bindings,
        data_bindings=data_bindings,
        safety_bindings=safety_bindings,
        derived_bindings=derived_bindings,
        inventory_bytes=inventory_bytes,
    )
    readback_bytes = _serialize(readback)
    outputs = {
        NORMALIZATION_PATH: normalization_bytes,
        PACKET_JSON_PATH: packet_json_bytes,
        PACKET_MD_PATH: packet_md_bytes,
        AUTHORITY_PATH: authority_bytes,
        DASHBOARD_PATH: dashboard_html_bytes,
        REVIEW_ACTIONS_JSON_PATH: review_actions_bytes,
        REVIEW_ACTIONS_MD_PATH: review_actions_md_bytes,
        PRIORITY_READBACK_PATH: priority_bytes,
        INVENTORY_PATH: inventory_bytes,
        READBACK_PATH: readback_bytes,
    }
    if set(outputs) != set(REGENERATED_DERIVED_OUTPUTS):
        raise RuntimeError("generated output mapping does not match declared derived outputs")
    return outputs


def _build_inventory(
    *,
    fixed_bindings: dict[str, str],
    module_closure: tuple[str, ...],
    module_bindings: dict[str, str],
    data_bindings: dict[str, str],
    safety_bindings: dict[str, str],
    derived_bindings: dict[str, str],
) -> dict[str, Any]:
    combined = {
        **fixed_bindings,
        **module_bindings,
        **data_bindings,
        **safety_bindings,
        **derived_bindings,
    }
    return {
        "schema_version": "h3_real_current_nlmytgen_point_in_time_binding_inventory.v2",
        "artifact_id": ARTIFACT_ID,
        "hash_basis": "repository_relative_path_and_raw_bytes_sha256_v1",
        "binding_set_scope": (
            "classified repository-relative paths and raw-byte SHA-256 only; "
            "not a repository-wide tree hash"
        ),
        "base_revision": DEVCOCKPIT_BASE_REVISION,
        "source_revision": SOURCE_REVISION,
        "fixed_captured_inputs": fixed_bindings,
        "immutable_producer_dependencies": {
            "repository_local_producer_modules": {
                "paths": list(module_closure),
                "raw_bytes_sha256": module_bindings,
            },
            "non_module_producer_data_and_documents": data_bindings,
            "accepted_external_safety_dependencies": safety_bindings,
        },
        "regenerated_derived_outputs": derived_bindings,
        "self_binding_exclusions": {
            "inventory": INVENTORY_PATH,
            "package_readback": READBACK_PATH,
            "reason": "generated metadata cannot hash itself without circularity",
        },
        "binding_set_sha256": _binding_set_sha256(combined),
        "bindings": combined,
    }


def _build_readback(
    *,
    observation: dict[str, Any],
    packet: dict[str, Any],
    authority: dict[str, Any],
    manifest: dict[str, Any],
    fixed_bindings: dict[str, str],
    module_closure: tuple[str, ...],
    module_bindings: dict[str, str],
    data_bindings: dict[str, str],
    safety_bindings: dict[str, str],
    derived_bindings: dict[str, str],
    inventory_bytes: bytes,
) -> dict[str, Any]:
    observation_data = observation["observation"]
    before = observation_data["before"]
    after = observation_data["after"]
    derived = observation_data["derived"]
    envelope_authority = authority["authority"]
    return {
        "schema_version": "h3_real_current_nlmytgen_point_in_time_machine_readback.v2",
        "artifact_id": ARTIFACT_ID,
        "mission_id": "dcc-h3-g02-derived-output-reproducibility",
        "devcockpitcore_base_revision": DEVCOCKPIT_BASE_REVISION,
        "transition": {
            "from": "committed-derived-files-as-reprojection-inputs",
            "to": "non_circular_fixed_input_and_dependency_reconstruction",
        },
        "package_file_classification": {
            "fixed_captured_inputs": list(FIXED_CAPTURED_INPUTS),
            "immutable_producer_dependencies": {
                "repository_local_producer_modules": list(
                    REPOSITORY_LOCAL_PRODUCER_MODULES
                ),
                "non_module_producer_data_and_documents": list(
                    IMMUTABLE_NON_MODULE_DEPENDENCIES
                ),
                "accepted_external_safety_dependencies": list(
                    ACCEPTED_EXTERNAL_SAFETY_DEPENDENCIES
                ),
            },
            "regenerated_derived_outputs": list(REGENERATED_DERIVED_OUTPUTS),
        },
        "inputs": {
            "fixed_captured": fixed_bindings,
            "immutable_dependencies": {
                "repository_local_producer_modules": module_bindings,
                "non_module_producer_data_and_documents": data_bindings,
                "accepted_external_safety_dependencies": safety_bindings,
            },
            "measured_repository_module_closure": list(module_closure),
            "declared_repository_module_closure": list(
                REPOSITORY_LOCAL_PRODUCER_MODULES
            ),
            "repository_module_closure_assertion": "exact",
            "committed_derived_files_are_comparison_oracles": True,
            "producer_inputs_exclude_committed_derived_files": True,
        },
        "source": {
            "project_key": observation["project_key"],
            "repository_identity": observation["repository"]["identity"],
            "source_revision": before["head_revision"],
            "report_sha256": fixed_bindings[FIXED_CAPTURED_INPUTS[0]],
            "report_observed_at": _report_field(
                ROOT / FIXED_CAPTURED_INPUTS[0], "observed_at"
            ),
            "source_branch": _report_field(
                ROOT / FIXED_CAPTURED_INPUTS[0], "source_branch"
            ),
            "evidence_class": "authentic_owner_authorized_point_in_time_report",
            "authority_basis": "owner_authorized_current_checkout_observation",
            "report_permission": _report_field(
                ROOT / FIXED_CAPTURED_INPUTS[0], "observer_only_permission"
            ),
            "tests_executed": False,
            "remote_freshness_established": False,
        },
        "observation": {
            "artifact_id": observation["artifact_id"],
            "first_observed_at": observation_data["first_observed_at"],
            "reobserved_at": observation_data["reobserved_at"],
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
            "report_permission": authority["report"]["observer_permission_scope"],
            "observation_authorization": authority["observation"]["authorization_scope"],
            "authentic_owner_attached_point_in_time_evidence": envelope_authority[
                "authentic_owner_attached_point_in_time_evidence"
            ],
            "current_claim_eligibility": envelope_authority["current_claim_eligibility"],
            "reason_codes": envelope_authority["reason_codes"],
            "live_coverage": envelope_authority["live_coverage"],
            "executable": authority["scope_boundary"]["executable"],
            "provenance": authority["provenance"],
            "evidence_validity": "valid",
            "observed_result": "pass",
            "decision_effect": "none",
        },
        "chronology": {
            "report_observed_at": authority["report"]["observed_at"],
            "first_observed_at": authority["observation"]["first_observed_at"],
            "reobserved_at": authority["observation"]["reobserved_at"],
            "assessed_at": authority["assessment"]["assessed_at"],
            "fixed_timestamp_source": "manifest.generated_at",
            "state": envelope_authority["chronology_state"],
        },
        "reconstruction": {
            "fixed_timestamp": manifest["generated_at"],
            "canonical_producers": [
                "report_normalizer",
                "supervision_packet",
                "report_authority_v2",
                "dashboard",
            ],
            "staging_roots_outside_repository": True,
            "output_mapping_path_set_exact": True,
            "normal_verification_writes_no_tracked_files": True,
            "repository_module_closure": list(module_closure),
            "repository_module_closure_assertion": "exact",
        },
        "cross_binding": {
            "source_manifest_packet": "verified",
            "current_observation_receipt": "verified",
            "repository_project_revision": "verified",
            "authority_envelope_reprojection": "verified",
            "dashboard_declared_authority_projection": (
                "verified_complete_priority_readback_projection"
            ),
            "dashboard_html_state_markers": "verified_structural_markers",
        },
        "derived_outputs": {
            "fixed_input_reprojection": True,
            "target_repository_reobserved_for_regeneration": False,
            "paths": list(REGENERATED_DERIVED_OUTPUTS),
            "output_sha256": derived_bindings,
            "self_binding_exclusions": {
                "binding_inventory": INVENTORY_PATH,
                "package_readback": READBACK_PATH,
            },
            "byte_identical_regeneration_evidence": (
                "tests.test_h3_g02_real_package."
                "H3G02RealPackageTests.test_two_independent_staging_builds_match"
            ),
            "comparison_oracle_scope": (
                "committed derived bytes are compared only after reconstruction"
            ),
        },
        "historical_invariance": {
            "safety_boundary_inventory_sha256": safety_bindings[
                "artifacts/review/h3-current-observation-safety-boundary-v1/"
                "binding_inventory_v1.json"
            ],
            "safety_boundary_readback_sha256": safety_bindings[
                "artifacts/review/h3-current-observation-safety-boundary-v1/"
                "safety_boundary_machine_readback_v1.json"
            ],
            "accepted_historical_and_production_baselines": (
                "verified by safety-boundary generator"
            ),
        },
        "binding_inventory_sha256": sha256(inventory_bytes).hexdigest(),
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


def _verify_cross_bindings(
    observation: dict[str, Any],
    packet: dict[str, Any],
    authority: dict[str, Any],
    dashboard_readback: dict[str, Any],
    dashboard_html: bytes,
) -> None:
    source_revision = observation["observation"]["before"]["head_revision"]
    identity = observation["repository"]["identity"]
    if observation["observation"]["after"]["head_revision"] != source_revision:
        raise RuntimeError("observation revision changed during package reconstruction")
    if observation["observation"]["after"]["worktree_sha256"] != observation["observation"]["before"]["worktree_sha256"]:
        raise RuntimeError("observation worktree changed during package reconstruction")
    if authority["report"]["source_revision"] != source_revision:
        raise RuntimeError("report and observation revisions differ")
    if authority["report"]["repository_identity"] != identity:
        raise RuntimeError("authority repository identity differs from receipt")
    if packet["source_bindings"][0]["content_sha256"] != authority["bindings"]["source_report"]["content_sha256"]:
        raise RuntimeError("packet and authority source report bindings differ")
    expected_projection = {
        "loaded": True,
        "schema_version": authority["schema_version"],
        "artifact_id": authority["artifact_id"],
        "identity": authority["identity"],
        "report": authority["report"],
        "observation": authority["observation"],
        "assessment": authority["assessment"],
        "authority": authority["authority"],
        "scope_boundary": authority["scope_boundary"],
        "provenance": authority["provenance"],
    }
    if dashboard_readback.get("supervision_report_authority_envelope") != expected_projection:
        raise RuntimeError("Dashboard authority projection is incomplete or differs from authority")
    if dashboard_readback["surface"]["executable"] is not False:
        raise RuntimeError("Dashboard executable boundary is not false")
    html_text = dashboard_html.decode("utf-8").lower()
    for marker in ("worktree_not_clean", "live coverage", "claim-ineligible"):
        if marker not in html_text:
            raise RuntimeError(f"Dashboard HTML missing state marker: {marker}")


def verify_committed_package() -> dict[str, str]:
    expected = generate()
    return _verify_committed_outputs(expected)


def _verify_committed_outputs(outputs: dict[str, bytes]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path, data in outputs.items():
        relative = path.removeprefix(f"{PACKAGE_REL}/")
        committed = PACKAGE / relative
        actual = committed.read_bytes()
        if actual != data:
            raise RuntimeError(
                f"committed {relative} does not match reconstructed bytes; "
                "refusing to overwrite tracked package"
            )
        result[relative] = sha256(actual).hexdigest()
    return result


def _write_mapping(output_dir: Path, outputs: dict[str, bytes]) -> None:
    _validate_output_destination(output_dir)
    destination = output_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for path, data in outputs.items():
        relative = path.removeprefix(f"{PACKAGE_REL}/")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    actual_paths = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    expected_paths = {
        path.removeprefix(f"{PACKAGE_REL}/") for path in outputs
    }
    if actual_paths != expected_paths:
        raise RuntimeError(
            f"staging path set differs: expected {sorted(expected_paths)}, "
            f"actual {sorted(actual_paths)}"
        )


def _validate_output_destination(output_dir: Path) -> None:
    destination = output_dir.resolve()
    root = ROOT.resolve()
    if _is_relative_to(destination, root):
        raise ValueError(
            "staging output must be outside the repository, including the tracked package"
        )


def _bindings(root: Path, paths: tuple[str, ...]) -> dict[str, str]:
    return {path: sha256(_read_bytes(root, path)).hexdigest() for path in paths}


def _read_bytes(root: Path, relative_path: str) -> bytes:
    path = root / relative_path
    if not path.is_file():
        raise RuntimeError(f"reconstruction output is missing: {relative_path}")
    return path.read_bytes()


def _write_bytes(root: Path, relative_path: str, data: bytes) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _report_field(path: Path, key: str) -> str:
    tick = chr(96)
    prefix = f"- {key}: {tick}"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix) and line.endswith(tick):
            return line[len(prefix):-1]
    raise RuntimeError(f"report field {key!r} is missing")


def _binding_set_sha256(bindings: dict[str, str]) -> str:
    digest = sha256()
    for path in sorted(bindings):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bindings[path].encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _serialize(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reconstruct or verify the fixed-input H3-G02 outcome package."
    )
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.output_dir is not None:
        outputs = generate(output_dir=args.output_dir)
        print(f"staged {len(outputs)} derived outputs in {args.output_dir.resolve()}")
    else:
        hashes = verify_committed_package()
        for name, digest in hashes.items():
            print(f"{name}: {digest}")
