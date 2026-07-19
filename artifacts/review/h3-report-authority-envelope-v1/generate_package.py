from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dev_cockpit.dashboard import (  # noqa: E402
    build_dashboard_model,
    priority_readback,
    review_action_package,
    write_dashboard,
    write_priority_readback,
    write_review_actions_json,
    write_review_actions_markdown,
)
from dev_cockpit.report_authority import (  # noqa: E402
    build_authority_envelope,
    load_authority_envelope,
    write_authority_envelope,
)


PACKAGE_REL = Path("artifacts/review/h3-report-authority-envelope-v1")
H2_PACKAGE_REL = Path("artifacts/review/h2-authentic-single-report-round-trip-v1")
MANIFEST_REL = H2_PACKAGE_REL / "task_report_manifest_v1.json"
PACKET_REL = H2_PACKAGE_REL / "cross_project_supervision_packet_v1.json"
ENVELOPE_REL = PACKAGE_REL / "supervision_report_authority_envelope_v1.json"
INVENTORY_REL = PACKAGE_REL / "binding_inventory_v1.json"
READBACK_JSON_REL = PACKAGE_REL / "authority_envelope_machine_readback_v1.json"
READBACK_MD_REL = PACKAGE_REL / "AUTHORITY_ENVELOPE_READBACK_V1.md"
DASHBOARD_REL = PACKAGE_REL / "dashboard/devcockpitcore_dashboard.html"
PRIORITY_REL = PACKAGE_REL / "dashboard/devcockpitcore_priority_readback.json"
REVIEW_JSON_REL = PACKAGE_REL / "dashboard/devcockpitcore_review_actions.json"
REVIEW_MD_REL = PACKAGE_REL / "dashboard/devcockpitcore_review_actions.md"

ASSESSED_AT = "2026-07-19T22:10:54.5042581+09:00"
H2_TREE_SHA256 = "bd63725b106d80cb573c27f3fadc55a07448c293b4e35a73d0a79d1dc0ac2da5"
BASELINE_HASHES = {
    "samples/supervision_packets/cross_project_supervision_packet_v1.json": (
        "07965839fdef3d591776804e23d94d26996b5a13a6bf380fbe4e263231f59aec"
    ),
    "samples/supervision_packets/cross_project_supervision_packet_v1.md": (
        "d28dbfbde4d162e84843889141408972ea2946d09ba6b581e56c7c2378362fb7"
    ),
    "samples/dashboard/devcockpitcore_dashboard.html": (
        "376521d0367ddfb2e8fa2e6f3c1020baa88f1fa5a3587f7bad9fbeabca7215e1"
    ),
    "samples/dashboard/devcockpitcore_priority_readback.json": (
        "fb0d4ad091af5e4204c4fee15bd71231e7b3371d8399e920ca0ad0b81d85fe29"
    ),
}


def generate() -> dict[str, Any]:
    invariance = _verify_baseline_invariance()
    envelope = build_authority_envelope(
        manifest_path=MANIFEST_REL,
        packet_path=PACKET_REL,
        repo_root=REPO_ROOT,
        assessed_at=ASSESSED_AT,
    )
    write_authority_envelope(envelope, REPO_ROOT / ENVELOPE_REL, pretty=True)
    reloaded = load_authority_envelope(
        REPO_ROOT / ENVELOPE_REL,
        manifest_path=MANIFEST_REL,
        packet_path=PACKET_REL,
        repo_root=REPO_ROOT,
        assessed_at=ASSESSED_AT,
    )

    envelope_sha = _file_sha256(REPO_ROOT / ENVELOPE_REL)
    inventory = {
        "schema_version": "h3_authority_binding_inventory.v1",
        "artifact_id": "h3-report-authority-envelope-v1",
        "assessed_at": ASSESSED_AT,
        "producer": (
            "artifacts.review.h3-report-authority-envelope-v1.generate_package"
        ),
        "identity": envelope["identity"],
        "bindings": envelope["bindings"],
        "authority_envelope": {
            "path": ENVELOPE_REL.as_posix(),
            "content_sha256": envelope_sha,
            "hash_basis": "raw_bytes_sha256_v1",
        },
        "scope_boundary": envelope["scope_boundary"],
    }
    _write_json(inventory, REPO_ROOT / INVENTORY_REL)
    inventory_sha = _file_sha256(REPO_ROOT / INVENTORY_REL)

    model = build_dashboard_model(
        repo_root=REPO_ROOT,
        output_path=DASHBOARD_REL,
        review_actions_json_path=REVIEW_JSON_REL,
        review_actions_md_path=REVIEW_MD_REL,
        priority_readback_path=PRIORITY_REL,
        supervision_packet_path=PACKET_REL,
        supervision_manifest_path=MANIFEST_REL,
        supervision_authority_envelope_path=ENVELOPE_REL,
        supervision_authority_assessed_at=ASSESSED_AT,
        generated_at=ASSESSED_AT,
    )
    actions = review_action_package(model)
    priority = priority_readback(model)
    write_dashboard(model, REPO_ROOT / DASHBOARD_REL)
    write_review_actions_json(actions, REPO_ROOT / REVIEW_JSON_REL, pretty=True)
    write_review_actions_markdown(actions, REPO_ROOT / REVIEW_MD_REL)
    write_priority_readback(priority, REPO_ROOT / PRIORITY_REL, pretty=True)

    projected = model["priority_items"][0]
    projected_evidence = projected["evidence_refs"][0]
    authority = envelope["authority"]
    readback = {
        "schema_version": "h3_report_authority_envelope_readback.v1",
        "artifact_id": "h3-report-authority-envelope-v1",
        "assessed_at": ASSESSED_AT,
        "producer": (
            "artifacts.review.h3-report-authority-envelope-v1.generate_package"
        ),
        "state_transition": {
            "from": "h2_authentic_single_report_round_trip_verified_non_live_v1",
            "to": (
                "h3_report_authority_envelope_contract_verified_without_live_"
                "promotion_v1"
            ),
        },
        "authority_envelope": {
            "path": ENVELOPE_REL.as_posix(),
            "content_sha256": envelope_sha,
            "strict_reload": reloaded == envelope,
            "full_source_reprojection": reloaded == envelope,
            "schema_version": envelope["schema_version"],
            "exact_key_contract": True,
        },
        "binding_inventory": {
            "path": INVENTORY_REL.as_posix(),
            "content_sha256": inventory_sha,
            "source_manifest_packet_bound": True,
        },
        "identity": envelope["identity"],
        "report": envelope["report"],
        "observation": envelope["observation"],
        "authority": authority,
        "dashboard": {
            "path": DASHBOARD_REL.as_posix(),
            "priority_readback_path": PRIORITY_REL.as_posix(),
            "review_json_path": REVIEW_JSON_REL.as_posix(),
            "review_markdown_path": REVIEW_MD_REL.as_posix(),
            "selected_task_id": model["selected_priority_id"],
            "authenticity_state": projected_evidence["authenticity_state"],
            "temporal_state": projected_evidence["temporal_state"],
            "revision_binding_state": projected_evidence[
                "revision_binding_state"
            ],
            "permission_state": projected_evidence["permission_state"],
            "current_claim_eligibility": projected_evidence[
                "current_state_claim_eligible"
            ],
            "live_coverage": projected_evidence["live_coverage"],
            "executable": projected["executable"],
        },
        "proof_boundary": {
            "isolated_positive_predicate_only": True,
            "tracked_real_evidence_promoted_to_current": False,
            "tracked_real_evidence_promoted_to_live": False,
            "any_action_executable": False,
            "h4_started": False,
        },
        "baseline_invariance": invariance,
        "scope_boundary": envelope["scope_boundary"],
    }
    _write_json(readback, REPO_ROOT / READBACK_JSON_REL)
    (REPO_ROOT / READBACK_MD_REL).write_text(
        _render_markdown(readback),
        encoding="utf-8",
        newline="\n",
    )
    return readback


def _verify_baseline_invariance() -> dict[str, Any]:
    h2_actual = _tree_sha256(REPO_ROOT / H2_PACKAGE_REL)
    files = {
        path: {
            "expected_sha256": expected,
            "actual_sha256": _file_sha256(REPO_ROOT / path),
        }
        for path, expected in BASELINE_HASHES.items()
    }
    if h2_actual != H2_TREE_SHA256 or any(
        item["actual_sha256"] != item["expected_sha256"]
        for item in files.values()
    ):
        raise RuntimeError("H2/canonical/production baseline invariance failed")
    return {
        "h2_package": {
            "path": H2_PACKAGE_REL.as_posix(),
            "expected_tree_sha256": H2_TREE_SHA256,
            "actual_tree_sha256": h2_actual,
            "unchanged": True,
        },
        "files": files,
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


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_json(value: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _render_markdown(readback: dict[str, Any]) -> str:
    envelope = readback["authority_envelope"]
    identity = readback["identity"]
    report = readback["report"]
    observation = readback["observation"]
    authority = readback["authority"]
    dashboard = readback["dashboard"]
    reasons = ", ".join(authority["reason_codes"])
    return "\n".join(
        [
            "# H3 Report Authority Envelope Readback V1",
            "",
            f"assessed_at: {readback['assessed_at']}",
            f"state: {readback['state_transition']['to']}",
            "",
            "## Envelope And Binding",
            "",
            f"- Schema: `{envelope['schema_version']}`",
            f"- Envelope: `{envelope['path']}`",
            f"- SHA-256: `{envelope['content_sha256']}`",
            f"- Strict source reprojection: {str(envelope['full_source_reprojection']).lower()}",
            f"- Binding inventory: `{readback['binding_inventory']['path']}`",
            "- Identity: "
            + " / ".join(
                str(identity[key])
                for key in (
                    "task_id",
                    "project_key",
                    "thread_id",
                    "lane_id",
                    "slice_id",
                    "artifact_id",
                )
            ),
            "",
            "## Real H2 Authority Evaluation",
            "",
            f"- Evidence class: `{report['evidence_class']}`",
            f"- Permission: `{report['observer_permission_scope']}`",
            f"- Observation: `{observation['state']}`",
            f"- Authentic point-in-time evidence: {str(authority['authentic_owner_attached_point_in_time_evidence']).lower()}",
            f"- Temporal / revision / permission: `{authority['temporal_state']}` / `{authority['revision_binding_state']}` / `{authority['permission_state']}`",
            f"- Current-claim eligibility: {str(authority['current_claim_eligibility']).lower()}",
            f"- Live coverage: {str(authority['live_coverage']).lower()}",
            f"- Reason codes: `{reasons}`",
            "",
            "## Dashboard Projection",
            "",
            f"- Dashboard: `{dashboard['path']}`",
            f"- Machine readback: `{dashboard['priority_readback_path']}`",
            f"- Authenticity / freshness / revision / permission: `{dashboard['authenticity_state']}` / `{dashboard['temporal_state']}` / `{dashboard['revision_binding_state']}` / `{dashboard['permission_state']}`",
            f"- Current / live / executable: {str(dashboard['current_claim_eligibility']).lower()} / {str(dashboard['live_coverage']).lower()} / {str(dashboard['executable']).lower()}",
            "",
            "## Boundary",
            "",
            "- The positive eligibility proof exists only in isolated unit-test input.",
            "- The tracked H2 report remains ineligible for H3/current and never establishes live coverage.",
            "- A real current claim requires a new fresh report/observation with explicit H3/current authorization.",
            "- H4 multi-project pilot is not started.",
            "",
        ]
    )


if __name__ == "__main__":
    generate()
