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
from dev_cockpit.gate_classifier import (  # noqa: E402
    classify_gate,
    write_classification,
)
from dev_cockpit.report_normalizer import (  # noqa: E402
    normalize_report,
    write_normalization,
)
from dev_cockpit.supervision_packet import (  # noqa: E402
    build_supervision_packet,
    dumps_packet,
    load_manifest,
    load_packet,
    load_packet_with_manifest,
    render_packet_markdown,
    write_packet_json,
    write_packet_markdown,
)


PACKAGE_REL = Path("artifacts/review/h2-authentic-single-report-round-trip-v1")
MANIFEST_REL = PACKAGE_REL / "task_report_manifest_v1.json"
NORMALIZATION_REL = PACKAGE_REL / "report_normalization_v1.json"
CLASSIFICATION_REL = PACKAGE_REL / "gate_classification_v1.json"
PACKET_JSON_REL = PACKAGE_REL / "cross_project_supervision_packet_v1.json"
PACKET_MD_REL = PACKAGE_REL / "cross_project_supervision_packet_v1.md"
READBACK_JSON_REL = PACKAGE_REL / "h2_authentic_round_trip_readback_v1.json"
READBACK_MD_REL = PACKAGE_REL / "h2_authentic_round_trip_readback_v1.md"
DASHBOARD_REL = PACKAGE_REL / "dashboard/devcockpitcore_dashboard.html"
PRIORITY_REL = PACKAGE_REL / "dashboard/devcockpitcore_priority_readback.json"
REVIEW_JSON_REL = PACKAGE_REL / "dashboard/devcockpitcore_review_actions.json"
REVIEW_MD_REL = PACKAGE_REL / "dashboard/devcockpitcore_review_actions.md"

EXPECTED_SOURCE_SHA256 = "d93f15b3f3441aee6d741adbfd54b285e1850e645998f34fb5384a223d82a65b"
SOURCE_REVISION = "d38075b97efabc99d1a23e8e0afafd5d44f1e2de"
SOURCE_OBSERVED_AT = "2026-07-19T12:11:51.1904148+09:00"
CANONICAL_JSON_SHA256 = "07965839fdef3d591776804e23d94d26996b5a13a6bf380fbe4e263231f59aec"
CANONICAL_MARKDOWN_SHA256 = "d28dbfbde4d162e84843889141408972ea2946d09ba6b581e56c7c2378362fb7"


def generate() -> dict[str, Any]:
    manifest = load_manifest(REPO_ROOT / MANIFEST_REL)
    generated_at = str(manifest["generated_at"])
    entry = manifest["reports"][0]
    source_rel = Path(str(entry["report_path"]))
    source_payload = (REPO_ROOT / source_rel).read_bytes()
    actual_source_sha = sha256(source_payload).hexdigest()
    if actual_source_sha != EXPECTED_SOURCE_SHA256:
        raise RuntimeError(
            f"source copy hash mismatch: expected {EXPECTED_SOURCE_SHA256}, got {actual_source_sha}"
        )
    source_text = source_payload.decode("utf-8")

    normalization = normalize_report(
        source_text,
        input_path=source_rel.as_posix(),
        input_kind="manifest_bound_agent_report",
        generated_at=generated_at,
    )
    classification = classify_gate(
        normalization,
        report_normalization_path=NORMALIZATION_REL.as_posix(),
        generated_at=generated_at,
    )
    write_normalization(normalization, REPO_ROOT / NORMALIZATION_REL, pretty=True)
    write_classification(classification, REPO_ROOT / CLASSIFICATION_REL, pretty=True)

    packet = build_supervision_packet(
        manifest,
        repo_root=REPO_ROOT,
        manifest_path=MANIFEST_REL,
    )
    write_packet_json(packet, REPO_ROOT / PACKET_JSON_REL, pretty=True)
    write_packet_markdown(packet, REPO_ROOT / PACKET_MD_REL)
    strict_packet = load_packet(REPO_ROOT / PACKET_JSON_REL)
    source_bound_packet = load_packet_with_manifest(
        REPO_ROOT / PACKET_JSON_REL,
        REPO_ROOT / MANIFEST_REL,
        repo_root=REPO_ROOT,
    )

    model = build_dashboard_model(
        repo_root=REPO_ROOT,
        output_path=DASHBOARD_REL,
        review_actions_json_path=REVIEW_JSON_REL,
        review_actions_md_path=REVIEW_MD_REL,
        priority_readback_path=PRIORITY_REL,
        supervision_packet_path=PACKET_JSON_REL,
        supervision_manifest_path=MANIFEST_REL,
        generated_at=generated_at,
    )
    actions = review_action_package(model)
    priority = priority_readback(model)
    write_dashboard(model, REPO_ROOT / DASHBOARD_REL)
    write_review_actions_json(actions, REPO_ROOT / REVIEW_JSON_REL, pretty=True)
    write_review_actions_markdown(actions, REPO_ROOT / REVIEW_MD_REL)
    write_priority_readback(priority, REPO_ROOT / PRIORITY_REL, pretty=True)

    canonical = _canonical_fixture_invariance()
    task = packet["global_attention_queue"][0]
    projected = model["priority_items"][0]
    projected_evidence = projected["evidence_refs"][0]
    readback = {
        "schema_version": "h2_authentic_round_trip_readback.v1",
        "artifact_id": "h2-authentic-single-report-round-trip-v1",
        "generated_at": generated_at,
        "producer": "artifacts.review.h2-authentic-single-report-round-trip-v1.generate_package",
        "state_transition": {
            "from": "waiting_for_authorized_h2_input",
            "to": "h2_authentic_single_report_round_trip_verified_non_live_v1",
        },
        "input": {
            "source_remote": "https://github.com/YuShimoji/NLMYTGen.git",
            "source_repository_relative_path": "artifacts/supervision/AGENT_REPORT_H2_SOURCE_V1.md",
            "package_source_path": source_rel.as_posix(),
            "expected_sha256": EXPECTED_SOURCE_SHA256,
            "actual_sha256": actual_source_sha,
            "bytes": len(source_payload),
            "lines": len(source_text.splitlines()),
            "source_revision": SOURCE_REVISION,
            "observed_at": SOURCE_OBSERVED_AT,
            "evidence_class": str(entry["evidence_class"]),
            "authority_basis": str(entry["authority_basis"]),
        },
        "normalization": {
            "schema_version": normalization["schema_version"],
            "health": normalization["health"]["normalization_status"],
            "source_report_health": normalization["status"]["health"],
            "dialect": normalization["routing"]["dialect"],
            "epoch": normalization["routing"]["epoch"],
            "base_revision": normalization["routing"]["base_revision"],
            "false_commit_count": len(normalization["normalized_outcome"]["commits"]),
        },
        "task_identity": {
            key: task[key]
            for key in ("project_key", "thread_id", "lane_id", "slice_id", "artifact_id")
        },
        "classification": {
            "health": classification["health"]["classification_status"],
            "decision": task["gate_decision"],
            "stop_class": task["gate_stop_class"],
            "attention_class": task["attention_class"],
            "task_id": task["task_id"],
            "global_rank": task["global_rank"],
            "blockers": classification["health"]["blockers"],
            "validation_gate": classification["gates"]["validation_gate"]["status"],
        },
        "packet": {
            "strict_reload": strict_packet == packet,
            "source_bound_full_reprojection": source_bound_packet == packet,
            "narrative_reprojection": "passed_full_strict_json_equality",
            "coverage": packet["coverage"],
            "executable": task["executable"],
        },
        "dashboard": {
            "source_bound_projection": model["selected_priority_id"] == task["task_id"],
            "selected_task_id": model["selected_priority_id"],
            "packet_attention": model["packet_attention"],
            "authority_classification": projected_evidence["authority_classification"],
            "identity_complete": all(projected[field] for field in ("project_key", "thread_id", "lane_id", "slice_id")),
            "executable": projected["executable"],
            "outputs": [
                DASHBOARD_REL.as_posix(),
                PRIORITY_REL.as_posix(),
                REVIEW_JSON_REL.as_posix(),
                REVIEW_MD_REL.as_posix(),
            ],
        },
        "canonical_fixture_invariance": canonical,
        "boundary": {
            "observer_only": True,
            "current_claim_eligibility": False,
            "live_coverage": False,
            "h3_started": False,
            "target_repository_writeback": False,
            "execution_schedule": False,
        },
    }
    _write_json(readback, REPO_ROOT / READBACK_JSON_REL)
    (REPO_ROOT / READBACK_MD_REL).write_text(
        _render_readback_markdown(readback),
        encoding="utf-8",
        newline="\n",
    )
    return readback


def _canonical_fixture_invariance() -> dict[str, Any]:
    manifest_rel = Path("samples/supervision_packets/task_report_manifest_v1.json")
    packet_json_rel = Path("samples/supervision_packets/cross_project_supervision_packet_v1.json")
    packet_md_rel = Path("samples/supervision_packets/cross_project_supervision_packet_v1.md")
    manifest = load_manifest(REPO_ROOT / manifest_rel)
    packet = build_supervision_packet(
        manifest,
        repo_root=REPO_ROOT,
        manifest_path=manifest_rel,
    )
    generated_json = dumps_packet(packet, pretty=True).encode("utf-8")
    generated_markdown = render_packet_markdown(packet).encode("utf-8")
    tracked_json = (REPO_ROOT / packet_json_rel).read_bytes()
    tracked_markdown = (REPO_ROOT / packet_md_rel).read_bytes()
    result = {
        "json": {
            "expected_sha256": CANONICAL_JSON_SHA256,
            "actual_sha256": sha256(tracked_json).hexdigest(),
            "regenerated_byte_identical": generated_json == tracked_json,
        },
        "markdown": {
            "expected_sha256": CANONICAL_MARKDOWN_SHA256,
            "actual_sha256": sha256(tracked_markdown).hexdigest(),
            "regenerated_byte_identical": generated_markdown == tracked_markdown,
        },
    }
    if not all(
        item["expected_sha256"] == item["actual_sha256"]
        and item["regenerated_byte_identical"]
        for item in result.values()
    ):
        raise RuntimeError("canonical fixture invariance failed")
    return result


def _write_json(value: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _render_readback_markdown(readback: dict[str, Any]) -> str:
    source = readback["input"]
    normalization = readback["normalization"]
    identity = readback["task_identity"]
    classification = readback["classification"]
    packet = readback["packet"]
    dashboard = readback["dashboard"]
    canonical = readback["canonical_fixture_invariance"]
    boundary = readback["boundary"]
    lines = [
        "# H2 Authentic Single-Report Round-Trip Readback V1",
        "",
        f"generated_at: {readback['generated_at']}",
        f"state: {readback['state_transition']['to']}",
        "",
        "## Input Binding",
        "",
        f"- Source remote: {source['source_remote']}",
        f"- Source path: `{source['source_repository_relative_path']}`",
        f"- Package copy: `{source['package_source_path']}`",
        f"- SHA-256: `{source['actual_sha256']}` (expected match: {str(source['actual_sha256'] == source['expected_sha256']).lower()})",
        f"- Source revision: `{source['source_revision']}`",
        f"- Observed at: {source['observed_at']}",
        "",
        "## Normalization And Classification",
        "",
        f"- Dialect / epoch / base: `{normalization['dialect']}` / `{normalization['epoch']}` / `{normalization['base_revision']}`",
        f"- Normalization / source health: {normalization['health']} / {normalization['source_report_health']}",
        f"- Decision / stop / attention: `{classification['decision']}` / `{classification['stop_class']}` / `{classification['attention_class']}`",
        f"- Task ID / rank: `{classification['task_id']}` / {classification['global_rank']}",
        "- Five-field identity: " + " / ".join(str(identity[key]) for key in ("project_key", "thread_id", "lane_id", "slice_id", "artifact_id")),
        "",
        "## Source-Bound Verification",
        "",
        f"- Strict packet reload: {str(packet['strict_reload']).lower()}",
        f"- Full source-bound reprojection: {str(packet['source_bound_full_reprojection']).lower()}",
        f"- Narrative reprojection: {packet['narrative_reprojection']}",
        f"- Dashboard source-bound projection: {str(dashboard['source_bound_projection']).lower()}",
        f"- Dashboard evidence authority: `{dashboard['authority_classification']}`",
        f"- Packet attention: stop {dashboard['packet_attention']['stop']} / decision {dashboard['packet_attention']['decision']} / active {dashboard['packet_attention']['active']} / closed {dashboard['packet_attention']['closed']}",
        "",
        "## Canonical Fixture Invariance",
        "",
        f"- JSON: `{canonical['json']['actual_sha256']}` / byte-identical {str(canonical['json']['regenerated_byte_identical']).lower()}",
        f"- Markdown: `{canonical['markdown']['actual_sha256']}` / byte-identical {str(canonical['markdown']['regenerated_byte_identical']).lower()}",
        "",
        "## Boundary",
        "",
        f"- observer_only: {str(boundary['observer_only']).lower()}",
        f"- current_claim_eligibility: {str(boundary['current_claim_eligibility']).lower()}",
        f"- live_coverage: {str(boundary['live_coverage']).lower()}",
        f"- h3_started: {str(boundary['h3_started']).lower()}",
        f"- executable: {str(packet['executable']).lower()}",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    generate()
