"""Rebuild the H4-G01 authentic two-project review package from fixed inputs."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dev_cockpit.current_observation import load_current_observation
from dev_cockpit.dashboard import (
    build_dashboard_model,
    dumps_review_actions,
    priority_readback,
    render_dashboard,
    render_review_actions_markdown,
)
from dev_cockpit.gate_classifier import classify_gate, dumps_classification
from dev_cockpit.report_normalizer import dumps_normalization, normalize_report
from dev_cockpit.supervision_packet import (
    build_supervision_packet,
    dumps_packet,
    load_manifest,
    render_packet_markdown,
)


PACKAGE_REL = "artifacts/review/h4-g01-authentic-two-project-review-v1"
PACKAGE = ROOT / PACKAGE_REL
ARTIFACT_ID = "h4-g01-authentic-two-project-review-v1"
MISSION_ID = "dcc-h4-g01-authentic-two-project-review"
BASE_REVISION = "363c10d8740fd7a10a502bf926f54c8eb5aebc58"
BASE_TREE = "97a08b570ac75ad2e177edb75e9755078afd3f90"
GENERATED_AT = "2026-07-26T07:38:05.567842+00:00"
AUTHORIZATION_SCOPE = "allowed_for_DevCockpitCore_H4_point_in_time_review"

REPORT_PATHS = {
    "clippipegen": (
        f"{PACKAGE_REL}/source/AGENT_REPORT_H4_G01_CLIPPIPEGEN.md"
    ),
    "nlmytgen": f"{PACKAGE_REL}/source/AGENT_REPORT_H4_G01_NLMYTGEN.md",
}
RECEIPT_PATHS = {
    "clippipegen": (
        f"{PACKAGE_REL}/receipts/clippipegen_current_observation_v1.json"
    ),
    "nlmytgen": f"{PACKAGE_REL}/receipts/nlmytgen_current_observation_v1.json",
}
MANIFEST_PATH = f"{PACKAGE_REL}/manifest/task_report_manifest_v1.json"
FIXED_INPUTS = (
    REPORT_PATHS["clippipegen"],
    REPORT_PATHS["nlmytgen"],
    RECEIPT_PATHS["clippipegen"],
    RECEIPT_PATHS["nlmytgen"],
    MANIFEST_PATH,
)

PRODUCER_DEPENDENCIES = (
    f"{PACKAGE_REL}/generate_package.py",
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

RECONSTRUCTION_DATA = (
    "adapters/devcockpitcore.json",
    "adapters/clippipegen.json",
    "adapters/nlmytgen.json",
    "docs/project-context.md",
    "docs/runtime-state.md",
    "samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json",
    "samples/evidence_freshness/evidence_freshness_receipt_v1.json",
    "samples/status_snapshots/devcockpitcore_status.json",
    "samples/validation_packs/devcockpitcore_validation_pack_result.json",
)

NORMALIZATION_PATHS = {
    "clippipegen": "normalization/clippipegen_report_normalization_v1.json",
    "nlmytgen": "normalization/nlmytgen_report_normalization_v1.json",
}
GATE_PATHS = {
    "clippipegen": "gates/clippipegen_gate_classification_v1.json",
    "nlmytgen": "gates/nlmytgen_gate_classification_v1.json",
}
PACKET_JSON_PATH = "packet/cross_project_supervision_packet_v1.json"
PACKET_MD_PATH = "packet/cross_project_supervision_packet_v1.md"
DASHBOARD_PATH = "dashboard/devcockpitcore_dashboard.html"
REVIEW_ACTIONS_JSON_PATH = "dashboard/review_actions.json"
REVIEW_ACTIONS_MD_PATH = "dashboard/review_actions.md"
PRIORITY_READBACK_PATH = "dashboard/priority_readback.json"
PACKAGE_READBACK_PATH = "package_readback_v1.json"

BASE_DERIVED_OUTPUTS = (
    NORMALIZATION_PATHS["clippipegen"],
    NORMALIZATION_PATHS["nlmytgen"],
    GATE_PATHS["clippipegen"],
    GATE_PATHS["nlmytgen"],
    PACKET_JSON_PATH,
    PACKET_MD_PATH,
    DASHBOARD_PATH,
    REVIEW_ACTIONS_JSON_PATH,
    REVIEW_ACTIONS_MD_PATH,
    PRIORITY_READBACK_PATH,
)
DERIVED_OUTPUTS = BASE_DERIVED_OUTPUTS + (PACKAGE_READBACK_PATH,)

EXPECTED_SOURCES = {
    "clippipegen": {
        "repository_identity": "https://github.com/YuShimoji/ClipPipeGen.git",
        "revision": "a3771bc59cd58b05c00a570e1074118ace3dc15a",
        "branch": "codex/s1-two-source-common-context-probe-v1",
        "clean": True,
        "worktree_state": "clean",
        "worktree_entry_count": 0,
        "worktree_sha256": (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ),
        "next": "m6-rights-readiness-review",
    },
    "nlmytgen": {
        "repository_identity": "https://github.com/YuShimoji/NLMYTGen.git",
        "revision": "aad0043d1218cdfae8027160cd57651b04fec2ef",
        "branch": "codex/nlmytgen-third-real-topic-factory-v1",
        "clean": False,
        "worktree_state": "dirty",
        "worktree_entry_count": 21,
        "worktree_sha256": (
            "01b5f76b48bcf9304f46a93c946a924892a7e8afed7829b48defa5315e5aa306"
        ),
        "next": "factory-contract-v2-extraction-review",
    },
}

FORBIDDEN_H3_CONTROL_STRINGS = (
    "point-in-time-source-" + "report-exported",
    "devcockpitcore-h3-g02-" + "real-current-observation-v1",
)


def generate(output_dir: str | Path = PACKAGE) -> dict[str, bytes]:
    """Regenerate all derived files without reading committed derived outputs."""

    destination = Path(output_dir).resolve()
    if destination == ROOT.resolve():
        raise ValueError("output directory must not be the repository root")

    with tempfile.TemporaryDirectory(prefix="dcc-h4-g01-reconstruct-") as temp_dir:
        reconstruction_root = Path(temp_dir) / "repo"
        _prepare_reconstruction_root(reconstruction_root)
        outputs = _reconstruct(reconstruction_root)

    _write_mapping(destination, outputs)
    return outputs


def verify_committed_package() -> dict[str, str]:
    """Rebuild externally and require byte equality with committed derivatives."""

    with tempfile.TemporaryDirectory(prefix="dcc-h4-g01-verify-") as temp_dir:
        regenerated_root = Path(temp_dir) / "derived"
        outputs = generate(regenerated_root)
        for relative_path, expected in outputs.items():
            committed_path = PACKAGE / relative_path
            if not committed_path.is_file():
                raise RuntimeError(f"committed derived output is missing: {relative_path}")
            actual = committed_path.read_bytes()
            if actual != expected:
                raise RuntimeError(
                    f"committed derived output differs from regeneration: {relative_path}"
                )
    return {
        relative_path: sha256(payload).hexdigest()
        for relative_path, payload in sorted(outputs.items())
    }


def _prepare_reconstruction_root(destination: Path) -> None:
    if destination.exists():
        raise RuntimeError(f"reconstruction root must be new: {destination}")
    for relative_path in FIXED_INPUTS + RECONSTRUCTION_DATA:
        source = ROOT / relative_path
        if not source.is_file():
            raise RuntimeError(f"required reconstruction input is missing: {relative_path}")
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def _reconstruct(reconstruction_root: Path) -> dict[str, bytes]:
    manifest = load_manifest(reconstruction_root / MANIFEST_PATH)
    if manifest["artifact_id"] != ARTIFACT_ID:
        raise RuntimeError("manifest artifact id changed")
    if manifest["generated_at"] != GENERATED_AT:
        raise RuntimeError("manifest generated_at changed")
    if len(manifest["reports"]) != 2:
        raise RuntimeError("manifest must bind exactly two reports")

    observations = {
        key: load_current_observation(reconstruction_root / RECEIPT_PATHS[key])
        for key in sorted(RECEIPT_PATHS)
    }
    normalizations: dict[str, dict[str, Any]] = {}
    classifications: dict[str, dict[str, Any]] = {}
    outputs: dict[str, bytes] = {}

    for project_key in sorted(REPORT_PATHS):
        report_path = REPORT_PATHS[project_key]
        report_text = (reconstruction_root / report_path).read_text(encoding="utf-8")
        normalization = normalize_report(
            report_text,
            input_path=report_path,
            input_kind="manifest_bound_agent_report",
            generated_at=GENERATED_AT,
        )
        adapter_path = f"adapters/{project_key}.json"
        adapter = _read_json(reconstruction_root / adapter_path)
        classification = classify_gate(
            normalization,
            report_normalization_path=(
                f"{PACKAGE_REL}/{NORMALIZATION_PATHS[project_key]}"
            ),
            adapter=adapter,
            adapter_path=adapter_path,
            generated_at=GENERATED_AT,
        )
        normalizations[project_key] = normalization
        classifications[project_key] = classification
        outputs[NORMALIZATION_PATHS[project_key]] = dumps_normalization(
            normalization, pretty=True
        ).encode("utf-8")
        outputs[GATE_PATHS[project_key]] = dumps_classification(
            classification, pretty=True
        ).encode("utf-8")

    packet = build_supervision_packet(
        manifest,
        repo_root=reconstruction_root,
        manifest_path=MANIFEST_PATH,
        generated_at=GENERATED_AT,
    )
    outputs[PACKET_JSON_PATH] = dumps_packet(packet, pretty=True).encode("utf-8")
    outputs[PACKET_MD_PATH] = render_packet_markdown(packet).encode("utf-8")
    _write_bytes(
        reconstruction_root,
        f"{PACKAGE_REL}/{PACKET_JSON_PATH}",
        outputs[PACKET_JSON_PATH],
    )
    _write_bytes(
        reconstruction_root,
        f"{PACKAGE_REL}/{PACKET_MD_PATH}",
        outputs[PACKET_MD_PATH],
    )

    dashboard_model = build_dashboard_model(
        repo_root=reconstruction_root,
        validation_result_path=(
            "samples/validation_packs/devcockpitcore_validation_pack_result.json"
        ),
        cross_project_smoke_result_path=(
            "samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json"
        ),
        status_snapshot_path="samples/status_snapshots/devcockpitcore_status.json",
        adapter_path="adapters/devcockpitcore.json",
        runtime_state_path="docs/runtime-state.md",
        project_context_path="docs/project-context.md",
        freshness_receipt_path=(
            "samples/evidence_freshness/evidence_freshness_receipt_v1.json"
        ),
        output_path=f"{PACKAGE_REL}/{DASHBOARD_PATH}",
        review_actions_json_path=f"{PACKAGE_REL}/{REVIEW_ACTIONS_JSON_PATH}",
        review_actions_md_path=f"{PACKAGE_REL}/{REVIEW_ACTIONS_MD_PATH}",
        priority_readback_path=f"{PACKAGE_REL}/{PRIORITY_READBACK_PATH}",
        supervision_packet_path=f"{PACKAGE_REL}/{PACKET_JSON_PATH}",
        supervision_manifest_path=MANIFEST_PATH,
        verify_freshness_hashes=False,
        generated_at=GENERATED_AT,
    )
    outputs[DASHBOARD_PATH] = render_dashboard(dashboard_model).encode("utf-8")
    outputs[REVIEW_ACTIONS_JSON_PATH] = dumps_review_actions(
        dashboard_model, pretty=True
    ).encode("utf-8")
    outputs[REVIEW_ACTIONS_MD_PATH] = render_review_actions_markdown(
        dashboard_model
    ).encode("utf-8")
    dashboard_readback = priority_readback(dashboard_model)
    outputs[PRIORITY_READBACK_PATH] = _serialize(dashboard_readback)

    _verify_bindings(
        observations=observations,
        normalizations=normalizations,
        classifications=classifications,
        packet=packet,
        dashboard_model=dashboard_model,
        dashboard_readback=dashboard_readback,
        outputs=outputs,
    )

    fixed_bindings = _bindings(ROOT, FIXED_INPUTS)
    dependency_bindings = _bindings(ROOT, PRODUCER_DEPENDENCIES)
    data_bindings = _bindings(ROOT, RECONSTRUCTION_DATA)
    derived_bindings = {
        relative_path: sha256(outputs[relative_path]).hexdigest()
        for relative_path in BASE_DERIVED_OUTPUTS
    }
    outputs[PACKAGE_READBACK_PATH] = _serialize(
        _build_package_readback(
            observations=observations,
            normalizations=normalizations,
            classifications=classifications,
            packet=packet,
            dashboard_readback=dashboard_readback,
            fixed_bindings=fixed_bindings,
            dependency_bindings=dependency_bindings,
            data_bindings=data_bindings,
            derived_bindings=derived_bindings,
        )
    )

    if set(outputs) != set(DERIVED_OUTPUTS):
        raise RuntimeError("generated output mapping does not match declared outputs")
    return outputs


def _verify_bindings(
    *,
    observations: dict[str, dict[str, Any]],
    normalizations: dict[str, dict[str, Any]],
    classifications: dict[str, dict[str, Any]],
    packet: dict[str, Any],
    dashboard_model: dict[str, Any],
    dashboard_readback: dict[str, Any],
    outputs: dict[str, bytes],
) -> None:
    for project_key, expected in EXPECTED_SOURCES.items():
        observation = observations[project_key]
        observed = observation["observation"]
        before = observed["before"]
        after = observed["after"]
        derived = observed["derived"]
        if observation["project_key"] != project_key:
            raise RuntimeError(f"receipt project mismatch: {project_key}")
        if observation["repository"]["identity"] != expected["repository_identity"]:
            raise RuntimeError(f"receipt repository mismatch: {project_key}")
        if observation["authorization"]["scope"] != AUTHORIZATION_SCOPE:
            raise RuntimeError(f"receipt authorization mismatch: {project_key}")
        if before != after:
            raise RuntimeError(f"receipt observation is unstable: {project_key}")
        if before["head_revision"] != expected["revision"]:
            raise RuntimeError(f"receipt revision mismatch: {project_key}")
        if before["worktree_state"] != expected["worktree_state"]:
            raise RuntimeError(f"receipt worktree state mismatch: {project_key}")
        if before["worktree_entry_count"] != expected["worktree_entry_count"]:
            raise RuntimeError(f"receipt entry count mismatch: {project_key}")
        if before["worktree_sha256"] != expected["worktree_sha256"]:
            raise RuntimeError(f"receipt aggregate hash mismatch: {project_key}")
        if derived != {"actual": True, "clean": expected["clean"], "stable": True}:
            raise RuntimeError(f"receipt derived state mismatch: {project_key}")
        if observation["scope_boundary"]["write_performed"] is not False:
            raise RuntimeError(f"receipt write boundary changed: {project_key}")
        if observation["scope_boundary"]["arbitrary_command_execution"] is not False:
            raise RuntimeError(f"receipt execution boundary changed: {project_key}")

        routing = normalizations[project_key]["routing"]
        progress = normalizations[project_key]["progress"]
        if routing["route"] != (
            "ClipPipeGen" if project_key == "clippipegen" else "NLMYTGen"
        ):
            raise RuntimeError(f"report route mismatch: {project_key}")
        if progress["next"] != expected["next"]:
            raise RuntimeError(f"report next state mismatch: {project_key}")
        classification = classifications[project_key]["classification"]
        if classification["continue_allowed"] is not True:
            raise RuntimeError(f"safe continuation was suppressed: {project_key}")
        if classification["execution_automation_scope_violation"] is not False:
            raise RuntimeError(f"execution scope violation: {project_key}")

    coverage = packet["coverage"]
    if coverage["project_count"] != 2 or coverage["report_count"] != 2:
        raise RuntimeError("packet does not contain exactly two projects and reports")
    if coverage["live_coverage"] is not False:
        raise RuntimeError("packet live coverage must remain false")
    if packet["scope_boundary"]["executable"] is not False:
        raise RuntimeError("packet must remain non-executable")
    if packet["scope_boundary"]["global_rank_meaning"] != (
        "attention_and_review_priority_only"
    ):
        raise RuntimeError("global rank meaning changed")

    tasks = list(packet["global_attention_queue"]) + list(
        packet["closed_or_informational"]
    )
    if {task["project_key"] for task in tasks} != {"clippipegen", "nlmytgen"}:
        raise RuntimeError("packet project identities changed")
    if any(task["executable"] is not False for task in tasks):
        raise RuntimeError("packet contains an executable task")
    if any(task["attention_class"] != "active_safe_continuation" for task in tasks):
        raise RuntimeError("both project tasks must remain active safe continuations")

    worksets = {item["project_key"]: item for item in packet["project_worksets"]}
    if set(worksets) != {"clippipegen", "nlmytgen"}:
        raise RuntimeError("project worksets changed")
    if any(item["safe_continuation"] == "none" for item in worksets.values()):
        raise RuntimeError("a project-local safe continuation was suppressed")

    if dashboard_model["supervision_packet"] != packet:
        raise RuntimeError("dashboard packet projection changed")
    if dashboard_model["user_visual_acceptance"] != "accepted":
        raise RuntimeError("accepted Priority Review Console design changed")
    if dashboard_readback["supervision_packet"]["scope_boundary"][
        "global_rank_meaning"
    ] != (
        "attention_and_review_priority_only"
    ):
        raise RuntimeError("priority readback rank meaning changed")

    review_actions = json.loads(outputs[REVIEW_ACTIONS_JSON_PATH])
    if any(
        action.get("executable") is not False
        for action in review_actions["review_actions"]
    ):
        raise RuntimeError("review actions must remain non-executable")

    review_payload = b"\n".join(outputs.values()).decode("utf-8", errors="strict")
    for forbidden in FORBIDDEN_H3_CONTROL_STRINGS:
        if forbidden in review_payload:
            raise RuntimeError(f"historical H3 control state leaked: {forbidden}")


def _build_package_readback(
    *,
    observations: dict[str, dict[str, Any]],
    normalizations: dict[str, dict[str, Any]],
    classifications: dict[str, dict[str, Any]],
    packet: dict[str, Any],
    dashboard_readback: dict[str, Any],
    fixed_bindings: dict[str, str],
    dependency_bindings: dict[str, str],
    data_bindings: dict[str, str],
    derived_bindings: dict[str, str],
) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for project_key in sorted(observations):
        observation = observations[project_key]
        observed = observation["observation"]
        state = observed["after"]
        derived = observed["derived"]
        sources.append(
            {
                "project_key": project_key,
                "repository_identity": observation["repository"]["identity"],
                "source_revision": state["head_revision"],
                "source_branch": EXPECTED_SOURCES[project_key]["branch"],
                "actual": derived["actual"],
                "clean": derived["clean"],
                "stable": derived["stable"],
                "worktree_state": state["worktree_state"],
                "worktree_entry_count": state["worktree_entry_count"],
                "worktree_sha256": state["worktree_sha256"],
                "remote_freshness": "unknown",
                "tests_executed": False,
                "recommended_next_slice": normalizations[project_key]["progress"][
                    "next"
                ],
                "gate_decision": classifications[project_key]["classification"][
                    "decision"
                ],
                "continue_allowed": classifications[project_key]["classification"][
                    "continue_allowed"
                ],
                "live_coverage": False,
                "executable": False,
            }
        )

    return {
        "schema_version": "h4_g01_authentic_two_project_review_readback.v1",
        "artifact_id": ARTIFACT_ID,
        "mission_id": MISSION_ID,
        "generated_at": GENERATED_AT,
        "devcockpitcore_base": {
            "revision": BASE_REVISION,
            "tree": BASE_TREE,
        },
        "inputs": {
            "fixed_captured_inputs_sha256": fixed_bindings,
            "producer_dependencies_sha256": dependency_bindings,
            "reconstruction_data_sha256": data_bindings,
            "committed_derived_files_are_comparison_oracles": True,
            "producer_inputs_exclude_committed_derived_files": True,
        },
        "sources": sources,
        "warnings": [
            {
                "project_key": "clippipegen",
                "code": "optional_runtime_state_missing",
                "effect": "project context remains available; no hard stop",
            },
            {
                "project_key": "nlmytgen",
                "code": "dirty_point_in_time_observation",
                "effect": "clean claim remains false; other project worksets remain visible",
            },
            {
                "project_key": "all",
                "code": "remote_freshness_unknown",
                "effect": "no live or current-remote claim",
            },
        ],
        "packet": {
            "artifact_id": packet["artifact_id"],
            "project_count": packet["coverage"]["project_count"],
            "report_count": packet["coverage"]["report_count"],
            "active_task_count": packet["coverage"]["active_task_count"],
            "project_keys": sorted(
                item["project_key"] for item in packet["project_worksets"]
            ),
            "all_tasks_executable": False,
            "global_rank_meaning": packet["scope_boundary"]["global_rank_meaning"],
        },
        "priority_console": {
            "schema_version": dashboard_readback["schema_version"],
            "selected_priority_id": dashboard_readback["surface"][
                "selected_priority_id"
            ],
            "priority_item_count": len(dashboard_readback["priorities"]),
            "global_rank_meaning": dashboard_readback["supervision_packet"][
                "scope_boundary"
            ]["global_rank_meaning"],
            "user_visual_acceptance": dashboard_readback["surface"][
                "user_visual_acceptance"
            ],
        },
        "derived_outputs_sha256": derived_bindings,
        "scope_boundary": {
            "point_in_time": True,
            "live": False,
            "observer_only": True,
            "executable": False,
            "source_repository_writeback": False,
            "main_integration": False,
            "deployment": False,
            "human_acceptance_conferred": False,
            "rights_clearance_conferred": False,
            "production_authority_conferred": False,
            "publication_authority_conferred": False,
            "release_authority_conferred": False,
        },
    }


def _bindings(root: Path, paths: tuple[str, ...]) -> dict[str, str]:
    return {
        path: sha256((root / path).read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def _serialize(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_bytes(root: Path, relative_path: str, payload: bytes) -> None:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)


def _write_mapping(destination: Path, outputs: dict[str, bytes]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for relative_path, payload in outputs.items():
        _write_bytes(destination, relative_path, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PACKAGE,
        help="destination for regenerated derived outputs",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="rebuild externally and compare with the committed package",
    )
    args = parser.parse_args()

    hashes = (
        verify_committed_package()
        if args.verify
        else {
            path: sha256(payload).hexdigest()
            for path, payload in sorted(generate(args.output_dir).items())
        }
    )
    for relative_path, digest in hashes.items():
        print(f"{digest}  {relative_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
