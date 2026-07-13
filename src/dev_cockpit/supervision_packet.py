"""Build a read-only cross-project supervision packet from explicit reports."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

from .gate_classifier import classify_gate
from .report_normalizer import ReportNormalizationError, normalize_report


MANIFEST_SCHEMA_VERSION = "task_report_manifest.v1"
PACKET_SCHEMA_VERSION = "cross_project_supervision_packet.v1"
PRODUCER = "dev_cockpit.supervision_packet"
PACKET_ARTIFACT_ID = "cross-project-supervision-packet-v1"
MANIFEST_KEYS = frozenset(
    {
        "artifact_id",
        "generated_at",
        "reports",
        "schema_version",
    }
)
MANIFEST_REPORT_KEYS = frozenset(
    {
        "authority_basis",
        "content_sha256",
        "evidence_class",
        "project_key",
        "report_path",
        "required",
    }
)
PACKET_KEYS = frozenset(
    {
        "artifact_id",
        "attention_policy",
        "closed_or_informational",
        "coverage",
        "generated_at",
        "global_attention_queue",
        "producer",
        "project_worksets",
        "schema_version",
        "scope_boundary",
        "source_bindings",
    }
)
TASK_KEYS = frozenset(
    {
        "artifact_id",
        "attention_class",
        "attention_precedence",
        "authority_basis",
        "current_state",
        "evidence_class",
        "evidence_references",
        "executable",
        "gate_decision",
        "gate_stop_class",
        "global_rank",
        "lane_id",
        "next_state",
        "outcome_summary",
        "project_key",
        "required",
        "slice_id",
        "source_report_path",
        "source_report_sha256",
        "task_id",
        "thread_id",
    }
)
NEXT_STATE_KEYS = frozenset(
    {
        "agent_work",
        "owner",
        "recommended_slice",
        "user_work",
    }
)
FIXTURE_COVERAGE_STATEMENT = (
    "Deterministic non-live fixture coverage from explicit manifest-bound reports."
)

ATTENTION_POLICY = (
    (1, "true_stop_or_required_failure", "True stop or required acceptance failure"),
    (2, "user_authorization_or_material_decision", "User action, authorization, or material decision gate"),
    (3, "awaiting_supervisor_acceptance", "Completed work awaiting supervisor acceptance or integration"),
    (4, "active_safe_continuation", "Active safe continuation"),
    (5, "unknown_requiring_review", "Unknown state requiring review"),
    (6, "closed_or_informational", "Closed or informational"),
)
ATTENTION_PRECEDENCE = {key: precedence for precedence, key, _ in ATTENTION_POLICY}
ACTIVE_ATTENTION_CLASSES = set(ATTENTION_PRECEDENCE) - {"closed_or_informational"}


class SupervisionPacketError(ValueError):
    """Raised when a manifest, report binding, or packet contract is invalid."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load and validate a task_report_manifest.v1 with nested duplicate rejection."""

    manifest_path = Path(path)
    data = _read_strict_json(manifest_path, label="manifest")
    return _validate_manifest(data)


def _validate_manifest(value: Any) -> dict[str, Any]:
    data = _require_exact_object(value, MANIFEST_KEYS, "manifest")
    reports = data.get("reports")
    if not isinstance(reports, list) or not reports:
        raise SupervisionPacketError("manifest.reports must be a non-empty array")
    entries = [
        _require_exact_object(
            raw_entry,
            MANIFEST_REPORT_KEYS,
            f"manifest.reports[{index}]",
        )
        for index, raw_entry in enumerate(reports)
    ]

    if data.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise SupervisionPacketError(
            f"manifest schema_version must be {MANIFEST_SCHEMA_VERSION!r}"
        )
    _require_nonempty_string(data, "artifact_id", "manifest")
    _require_timestamp(data.get("generated_at"), "manifest.generated_at")

    seen_paths: set[str] = set()
    for index, entry in enumerate(entries):
        label = f"manifest.reports[{index}]"
        for field in (
            "project_key",
            "report_path",
            "evidence_class",
            "authority_basis",
            "content_sha256",
        ):
            _require_nonempty_string(entry, field, label)
        if not isinstance(entry.get("required"), bool):
            raise SupervisionPacketError(f"{label}.required must be boolean")
        report_path = str(entry["report_path"])
        _validate_repo_relative_path(report_path, f"{label}.report_path")
        if report_path in seen_paths:
            raise SupervisionPacketError(f"duplicate manifest report_path: {report_path}")
        seen_paths.add(report_path)
        if not _is_sha256(str(entry["content_sha256"])):
            raise SupervisionPacketError(f"{label}.content_sha256 must be 64 lowercase hex characters")
    return data


def build_supervision_packet(
    manifest: dict[str, Any],
    *,
    repo_root: str | Path = ".",
    manifest_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Normalize, classify, rank, and project explicitly bound report tasks."""

    manifest = _validate_manifest(manifest)
    root = Path(repo_root).resolve()
    assessed_at = generated_at or str(manifest["generated_at"])
    _require_timestamp(assessed_at, "generated_at")
    manifest_display = _display_path(root, manifest_path) if manifest_path else None

    tasks: list[dict[str, Any]] = []
    source_bindings: list[dict[str, Any]] = []
    identities: set[tuple[str, str, str, str, str]] = set()

    for raw_entry in manifest["reports"]:
        entry = dict(raw_entry)
        report_path = str(entry["report_path"])
        full_path = _resolve_within(root, report_path)
        try:
            payload = full_path.read_bytes()
        except FileNotFoundError as exc:
            raise SupervisionPacketError(f"manifest report not found: {report_path}") from exc
        actual_hash = hashlib.sha256(payload).hexdigest()
        expected_hash = str(entry["content_sha256"])
        if actual_hash != expected_hash:
            raise SupervisionPacketError(
                f"report hash mismatch for {report_path}: expected {expected_hash}, got {actual_hash}"
            )
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SupervisionPacketError(f"report must be UTF-8: {report_path}") from exc

        try:
            normalization = normalize_report(
                text,
                input_path=report_path,
                input_kind="manifest_bound_agent_report",
                generated_at=assessed_at,
            )
        except ReportNormalizationError as exc:
            raise SupervisionPacketError(
                f"report identity normalization failed for {report_path}: {exc}"
            ) from exc
        classification = classify_gate(
            normalization,
            report_normalization_path=f"embedded:{report_path}",
            generated_at=assessed_at,
        )
        task = _task_from_report(entry, normalization, classification, actual_hash)
        identity = tuple(
            str(task[field])
            for field in ("project_key", "thread_id", "lane_id", "slice_id", "artifact_id")
        )
        if identity in identities:
            raise SupervisionPacketError(
                "duplicate task identity: " + "/".join(identity)
            )
        identities.add(identity)
        tasks.append(task)
        source_bindings.append(
            {
                "project_key": entry["project_key"],
                "report_path": report_path,
                "required": entry["required"],
                "evidence_class": entry["evidence_class"],
                "authority_basis": entry["authority_basis"],
                "content_sha256": actual_hash,
                "binding_status": "matched",
            }
        )

    active = [task for task in tasks if task["attention_class"] in ACTIVE_ATTENTION_CLASSES]
    closed = [task for task in tasks if task["attention_class"] == "closed_or_informational"]
    active.sort(key=_task_sort_key)
    closed.sort(key=_task_sort_key)
    for rank, task in enumerate(active, start=1):
        task["global_rank"] = rank
    for task in closed:
        task["global_rank"] = None

    worksets = _project_worksets(tasks, active, closed)
    packet = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "artifact_id": PACKET_ARTIFACT_ID,
        "generated_at": assessed_at,
        "producer": PRODUCER,
        "source_bindings": sorted(
            source_bindings,
            key=lambda item: (str(item["project_key"]), str(item["report_path"])),
        ),
        "coverage": {
            "project_count": len({str(task["project_key"]) for task in tasks}),
            "report_count": len(tasks),
            "active_task_count": len(active),
            "closed_or_informational_count": len(closed),
            "required_report_count": sum(1 for task in tasks if task["required"]),
            "manifest_path": manifest_display,
            "manifest_artifact_id": manifest["artifact_id"],
            "live_coverage": False,
            "coverage_statement": FIXTURE_COVERAGE_STATEMENT,
        },
        "attention_policy": [
            {"precedence": precedence, "key": key, "label": label}
            for precedence, key, label in ATTENTION_POLICY
        ],
        "global_attention_queue": active,
        "project_worksets": worksets,
        "closed_or_informational": closed,
        "scope_boundary": {
            "observer_first": True,
            "explicit_manifest_only": True,
            "directory_latest_report_discovery": False,
            "conversation_or_clipboard_inference": False,
            "sibling_repository_writeback": False,
            "target_repository_writeback": False,
            "execution_schedule": False,
            "executable": False,
            "global_rank_meaning": "attention_and_review_priority_only",
        },
    }
    validate_packet(packet)
    return packet


def load_packet(path: str | Path) -> dict[str, Any]:
    """Load a generated packet with strict duplicate-key and contract validation."""

    data = _read_strict_json(Path(path), label="supervision packet")
    return validate_packet(data)


def validate_packet(value: Any) -> dict[str, Any]:
    packet = _require_exact_object(value, PACKET_KEYS, "packet")
    active = _require_list(packet.get("global_attention_queue"), "packet.global_attention_queue")
    closed = _require_list(packet.get("closed_or_informational"), "packet.closed_or_informational")
    active_tasks = _task_objects(active, "global_attention_queue")
    closed_tasks = _task_objects(closed, "closed_or_informational")
    for index, task in enumerate(active_tasks):
        _validate_task_shape(task, f"packet.global_attention_queue[{index}]")
    for index, task in enumerate(closed_tasks):
        _validate_task_shape(task, f"packet.closed_or_informational[{index}]")
    for index, task in enumerate(active_tasks):
        _validate_next_state(
            task["next_state"],
            f"packet.global_attention_queue[{index}].next_state",
        )
    for index, task in enumerate(closed_tasks):
        _validate_next_state(
            task["next_state"],
            f"packet.closed_or_informational[{index}].next_state",
        )

    if packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise SupervisionPacketError(
            f"packet schema_version must be {PACKET_SCHEMA_VERSION!r}"
        )
    if packet.get("artifact_id") != PACKET_ARTIFACT_ID:
        raise SupervisionPacketError("packet artifact_id is invalid")
    if packet.get("producer") != PRODUCER:
        raise SupervisionPacketError("packet producer is invalid")
    _require_timestamp(packet.get("generated_at"), "packet.generated_at")
    all_tasks = [*active_tasks, *closed_tasks]
    if not all_tasks:
        raise SupervisionPacketError("packet must contain at least one manifest-bound task")
    task_ids: set[str] = set()
    identities: set[tuple[str, str, str, str, str]] = set()
    source_paths: set[str] = set()

    for index, task in enumerate(active_tasks):
        _validate_task(task, f"packet.global_attention_queue[{index}]", collection="active")
        if task["global_rank"] != index + 1:
            raise SupervisionPacketError("packet global ranks must be contiguous and ordered")
    for index, task in enumerate(closed_tasks):
        _validate_task(task, f"packet.closed_or_informational[{index}]", collection="closed")

    for index, task in enumerate(all_tasks):
        label = f"packet task[{index}]"
        identity = tuple(
            str(task[field])
            for field in ("project_key", "thread_id", "lane_id", "slice_id", "artifact_id")
        )
        task_id = str(task["task_id"])
        expected_task_id = _task_id_from_identity(*identity)
        if task_id != expected_task_id:
            raise SupervisionPacketError(
                f"{label}.task_id does not match identity: expected {expected_task_id}"
            )
        if identity in identities:
            raise SupervisionPacketError("duplicate packet task identity: " + "/".join(identity))
        identities.add(identity)
        if task_id in task_ids:
            raise SupervisionPacketError(f"duplicate packet task_id: {task_id}")
        task_ids.add(task_id)
        source_path = str(task["source_report_path"])
        if source_path in source_paths:
            raise SupervisionPacketError(f"duplicate packet source_report_path: {source_path}")
        source_paths.add(source_path)

    if [task["task_id"] for task in active_tasks] != [
        task["task_id"] for task in sorted(active_tasks, key=_task_sort_key)
    ]:
        raise SupervisionPacketError("packet global attention queue order is invalid")
    if [task["task_id"] for task in closed_tasks] != [
        task["task_id"] for task in sorted(closed_tasks, key=_task_sort_key)
    ]:
        raise SupervisionPacketError("packet closed collection order is invalid")

    bindings = _require_list(packet.get("source_bindings"), "packet.source_bindings")
    expected_bindings = sorted(
        [
            {
                "project_key": task["project_key"],
                "report_path": task["source_report_path"],
                "required": task["required"],
                "evidence_class": task["evidence_class"],
                "authority_basis": task["authority_basis"],
                "content_sha256": task["source_report_sha256"],
                "binding_status": "matched",
            }
            for task in all_tasks
        ],
        key=lambda item: (str(item["project_key"]), str(item["report_path"])),
    )
    if not _strict_json_equal(bindings, expected_bindings):
        raise SupervisionPacketError("packet source bindings must exactly match tasks")

    worksets = _require_list(packet.get("project_worksets"), "packet.project_worksets")
    if not _strict_json_equal(
        worksets,
        _project_worksets(all_tasks, active_tasks, closed_tasks),
    ):
        raise SupervisionPacketError("packet project worksets must exactly reproject tasks")

    coverage = _require_object(packet.get("coverage"), "packet.coverage")
    expected_coverage_keys = {
        "project_count", "report_count", "active_task_count",
        "closed_or_informational_count", "required_report_count",
        "manifest_path", "manifest_artifact_id", "live_coverage",
        "coverage_statement",
    }
    if set(coverage) != expected_coverage_keys:
        raise SupervisionPacketError("packet coverage fields are invalid")
    expected_counts = {
        "project_count": len({str(task["project_key"]) for task in all_tasks}),
        "report_count": len(all_tasks),
        "active_task_count": len(active_tasks),
        "closed_or_informational_count": len(closed_tasks),
        "required_report_count": sum(1 for task in all_tasks if task["required"] is True),
    }
    for field, expected in expected_counts.items():
        if type(coverage.get(field)) is not int or coverage.get(field) != expected:
            raise SupervisionPacketError(f"packet coverage {field} does not match tasks")
    manifest_path = coverage.get("manifest_path")
    if manifest_path is not None:
        if not isinstance(manifest_path, str) or not manifest_path:
            raise SupervisionPacketError("packet coverage manifest_path is invalid")
        _validate_repo_relative_path(manifest_path, "packet.coverage.manifest_path")
    _require_nonempty_string(coverage, "manifest_artifact_id", "packet.coverage")
    if coverage.get("live_coverage") is not False:
        raise SupervisionPacketError("packet coverage live_coverage must be false")
    if coverage.get("coverage_statement") != FIXTURE_COVERAGE_STATEMENT:
        raise SupervisionPacketError("packet coverage statement is invalid")

    expected_policy = [
        {"precedence": precedence, "key": key, "label": label}
        for precedence, key, label in ATTENTION_POLICY
    ]
    if not _strict_json_equal(packet.get("attention_policy"), expected_policy):
        raise SupervisionPacketError("packet attention policy is invalid")

    expected_scope = {
        "observer_first": True,
        "explicit_manifest_only": True,
        "directory_latest_report_discovery": False,
        "conversation_or_clipboard_inference": False,
        "sibling_repository_writeback": False,
        "target_repository_writeback": False,
        "execution_schedule": False,
        "executable": False,
        "global_rank_meaning": "attention_and_review_priority_only",
    }
    if not _strict_json_equal(packet.get("scope_boundary"), expected_scope):
        raise SupervisionPacketError("packet scope boundary is invalid")
    return packet


def _validate_task_shape(task: dict[str, Any], label: str) -> None:
    task = _require_exact_object(task, TASK_KEYS, label)
    _require_exact_object(
        task.get("next_state"),
        NEXT_STATE_KEYS,
        f"{label}.next_state",
    )


def _validate_next_state(value: Any, label: str) -> None:
    next_state = _require_object(value, label)
    _require_nonempty_string(next_state, "owner", label)
    recommended_slice = next_state.get("recommended_slice")
    if recommended_slice is not None and (
        not isinstance(recommended_slice, str) or not recommended_slice.strip()
    ):
        raise SupervisionPacketError(
            f"{label}.recommended_slice must be null or a non-empty string"
        )
    _require_nonempty_string(next_state, "user_work", label)
    _require_nonempty_string(next_state, "agent_work", label)


def _validate_task(task: dict[str, Any], label: str, *, collection: str) -> None:
    next_state = task["next_state"]
    for field in (
        "task_id", "project_key", "thread_id", "lane_id", "slice_id",
        "artifact_id", "attention_class", "outcome_summary", "current_state",
        "gate_decision", "gate_stop_class", "evidence_class", "authority_basis",
        "source_report_path", "source_report_sha256",
    ):
        _require_nonempty_string(task, field, label)
    _validate_repo_relative_path(str(task["source_report_path"]), f"{label}.source_report_path")
    if not _is_sha256(str(task["source_report_sha256"])):
        raise SupervisionPacketError(f"{label}.source_report_sha256 is invalid")
    if type(task.get("required")) is not bool:
        raise SupervisionPacketError(f"{label}.required must be boolean")
    if task.get("executable") is not False:
        raise SupervisionPacketError(f"{label}.executable must be false")
    attention_class = str(task["attention_class"])
    if attention_class not in ATTENTION_PRECEDENCE:
        raise SupervisionPacketError(f"{label}.attention_class is invalid")
    if (
        type(task.get("attention_precedence")) is not int
        or task.get("attention_precedence") != ATTENTION_PRECEDENCE[attention_class]
    ):
        raise SupervisionPacketError(f"{label}.attention_precedence does not match class")
    semantic_class = _semantic_attention_class(task, next_state)
    if semantic_class is not None and attention_class != semantic_class:
        raise SupervisionPacketError(
            f"{label}.attention_class does not match gate semantics: expected {semantic_class}"
        )
    if collection == "active":
        if attention_class not in ACTIVE_ATTENTION_CLASSES:
            raise SupervisionPacketError(f"{label} is in the wrong collection")
        if type(task.get("global_rank")) is not int or int(task["global_rank"]) < 1:
            raise SupervisionPacketError(f"{label}.global_rank must be a positive integer")
    elif attention_class != "closed_or_informational" or task.get("global_rank") is not None:
        raise SupervisionPacketError(f"{label} is in the wrong collection")

    evidence_refs = _require_list(task.get("evidence_references"), f"{label}.evidence_references")
    if len(evidence_refs) != 2:
        raise SupervisionPacketError(f"{label}.evidence_references must have two entries")
    source_ref = _require_object(evidence_refs[0], f"{label}.evidence_references[0]")
    expected_source_ref = {
        "kind": "source_report",
        "path": task["source_report_path"],
        "content_sha256": task["source_report_sha256"],
    }
    if source_ref != expected_source_ref:
        raise SupervisionPacketError(f"{label} source evidence binding is invalid")
    derived_ref = _require_object(evidence_refs[1], f"{label}.evidence_references[1]")
    expected_derived_ref = {
        "kind": "derived_contracts",
        "report_normalization_schema": "report_normalization.v1",
        "gate_classification_schema": "gate_classification.v1",
        "gate_decision": task["gate_decision"],
    }
    if derived_ref != expected_derived_ref:
        raise SupervisionPacketError(f"{label} derived evidence binding is invalid")


def _semantic_attention_class(
    task: dict[str, Any],
    next_state: dict[str, Any],
) -> str | None:
    stop_class = str(task.get("gate_stop_class") or "")
    decision = str(task.get("gate_decision") or "")
    if stop_class in {"TRUE_STOP", "VALIDATION_FAILED", "SAFETY_BOUNDARY"}:
        return "true_stop_or_required_failure"
    if stop_class in {"USER_AUTH_REQUIRED", "HANDOFF_REQUIRED"}:
        return "user_authorization_or_material_decision"
    if decision == "user_action_required":
        return "user_authorization_or_material_decision"
    if stop_class == "UNKNOWN_REVIEW_REQUIRED" or decision == "unknown_review_required":
        return "unknown_requiring_review"
    if decision == "supervisor_prompt_needed":
        return "awaiting_supervisor_acceptance"
    return None


def dumps_packet(packet: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(
        packet,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ) + "\n"


def render_packet_markdown(packet: dict[str, Any]) -> str:
    coverage = packet["coverage"]
    lines = [
        "# Cross-Project Supervision Packet V1",
        "",
        f"generated_at: {packet['generated_at']}",
        f"fixture_coverage: {coverage['project_count']} projects / {coverage['report_count']} reports",
        "authority: deterministic_non_live_manifest_bound_fixture",
        "global_rank: attention_and_review_priority_only",
        "executable: false",
        "",
        "## Global Attention Queue",
        "",
        "Global rank expresses review attention, not execution order. Safe work in different projects may continue in parallel.",
        "",
        "| Rank | Class | Required | Project | Thread / lane | Current state | Next state | Task ID |",
        "| ---: | --- | :---: | --- | --- | --- | --- | --- |",
    ]
    for task in packet["global_attention_queue"]:
        lines.append(
            "| {rank} | {attention} | {required} | {project} | {thread} / {lane} | {current} | {next_state} | `{task_id}` |".format(
                rank=task["global_rank"],
                attention=_md(task["attention_class"]),
                required="yes" if task["required"] else "no",
                project=_md(task["project_key"]),
                thread=_md(task["thread_id"]),
                lane=_md(task["lane_id"]),
                current=_md(task["current_state"]),
                next_state=_md(_next_state_text(task["next_state"])),
                task_id=task["task_id"],
            )
        )
    lines.extend(["", "## Project Worksets", ""])
    task_index = {
        task["task_id"]: task
        for task in [*packet["global_attention_queue"], *packet["closed_or_informational"]]
    }
    for workset in packet["project_worksets"]:
        first_id = workset.get("project_local_first_task_id")
        first = task_index.get(first_id) if first_id else None
        lines.extend(
            [
                f"### {workset['project_key']}",
                "",
                f"- Project-local first task: `{first_id or 'none'}`"
                + (f" — {_next_state_text(first['next_state'])}" if first else ""),
                f"- Active task IDs: {', '.join(f'`{value}`' for value in workset['active_task_ids']) or 'none'}",
                f"- User/supervisor gate: {workset['user_or_supervisor_gate']}",
                f"- Safe continuation: {workset['safe_continuation']}",
                f"- Closed/informational task IDs: {', '.join(f'`{value}`' for value in workset['closed_or_informational_task_ids']) or 'none'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Evidence Boundary",
            "",
            "Only reports explicitly named in the manifest were read. Every source is SHA-256 bound and the packet fails closed on missing, changed, duplicate-key, duplicate-identity, or projection-drift input.",
            "",
            "This tracked packet is deterministic non-live fixture evidence. It does not discover latest files, infer reports from conversation history, write to sibling repositories, schedule execution, or make any action executable.",
            "",
        ]
    )
    return "\n".join(lines)


def write_packet_json(packet: dict[str, Any], path: str | Path, *, pretty: bool = False) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps_packet(packet, pretty=pretty), encoding="utf-8", newline="\n")


def write_packet_markdown(packet: dict[str, Any], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_packet_markdown(packet), encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a read-only cross-project supervision packet from an explicit report manifest."
    )
    parser.add_argument("--manifest", required=True, help="task_report_manifest.v1 JSON path")
    parser.add_argument("--repo-root", default=".", help="Repository root used to resolve report paths")
    parser.add_argument("--output-json", required=True, help="Output packet JSON path")
    parser.add_argument("--output-markdown", required=True, help="Output packet Markdown path")
    parser.add_argument("--generated-at", help="Override deterministic packet timestamp")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print packet JSON")
    args = parser.parse_args(argv)
    root = Path(args.repo_root)
    manifest_path = _resolve_cli_path(root, args.manifest)
    try:
        manifest = load_manifest(manifest_path)
        packet = build_supervision_packet(
            manifest,
            repo_root=root,
            manifest_path=args.manifest,
            generated_at=args.generated_at,
        )
        write_packet_json(packet, _resolve_cli_path(root, args.output_json), pretty=args.pretty)
        write_packet_markdown(packet, _resolve_cli_path(root, args.output_markdown))
    except (OSError, SupervisionPacketError) as exc:
        print(f"supervision packet error: {exc}", file=sys.stderr)
        return 2
    print(_display_path(root.resolve(), args.output_json))
    print(_display_path(root.resolve(), args.output_markdown))
    return 0


def _task_from_report(
    entry: dict[str, Any],
    normalization: dict[str, Any],
    gate: dict[str, Any],
    content_sha256: str,
) -> dict[str, Any]:
    routing = _object(normalization.get("routing"))
    progress = _object(normalization.get("progress"))
    action = _object(normalization.get("action"))
    outcome = _object(normalization.get("normalized_outcome"))
    gate_classification = _object(gate.get("classification"))
    gate_next = _object(gate.get("next"))
    project_key = str(entry["project_key"])
    thread_id = str(routing.get("thread_id") or "unknown-thread")
    lane_id = str(routing.get("lane_id") or "unknown-lane")
    slice_id = str(routing.get("slice_id") or "unknown-slice")
    artifact_id = str(
        routing.get("artifact_id")
        or "unknown-artifact"
    )
    task_id = _task_id_from_identity(
        project_key,
        thread_id,
        lane_id,
        slice_id,
        artifact_id,
    )
    attention_class = _attention_class(normalization, gate)
    report_path = str(entry["report_path"])
    summary = str(
        outcome.get("summary")
        or action.get("deliverable")
        or f"Unknown outcome summary in manifest-bound report: {report_path}"
    )
    current_state = str(
        progress.get("current")
        or action.get("decision")
        or f"Unknown current state in manifest-bound report: {report_path}"
    )
    next_state = {
        "owner": gate_classification.get("next_owner") or action.get("now_owner") or "Supervisor",
        "recommended_slice": gate_next.get("recommended_next_slice") or progress.get("next"),
        "user_work": gate_next.get("user_side_work") or progress.get("user_work") or "none",
        "agent_work": gate_next.get("agent_side_work") or "review classification",
    }
    return {
        "task_id": task_id,
        "project_key": project_key,
        "thread_id": thread_id,
        "lane_id": lane_id,
        "slice_id": slice_id,
        "artifact_id": artifact_id,
        "attention_class": attention_class,
        "attention_precedence": ATTENTION_PRECEDENCE[attention_class],
        "global_rank": None,
        "required": bool(entry["required"]),
        "outcome_summary": summary,
        "current_state": current_state,
        "next_state": next_state,
        "gate_decision": str(gate_classification.get("decision") or "unknown"),
        "gate_stop_class": str(gate_classification.get("stop_class") or "UNKNOWN"),
        "evidence_class": str(entry["evidence_class"]),
        "authority_basis": str(entry["authority_basis"]),
        "evidence_references": [
            {
                "kind": "source_report",
                "path": str(entry["report_path"]),
                "content_sha256": content_sha256,
            },
            {
                "kind": "derived_contracts",
                "report_normalization_schema": normalization["schema_version"],
                "gate_classification_schema": gate["schema_version"],
                "gate_decision": gate_classification.get("decision"),
            },
        ],
        "source_report_path": str(entry["report_path"]),
        "source_report_sha256": content_sha256,
        "executable": False,
    }


def _attention_class(normalization: dict[str, Any], gate: dict[str, Any]) -> str:
    classification = _object(gate.get("classification"))
    stop_class = str(classification.get("stop_class") or "")
    decision = str(classification.get("decision") or "")
    progress = _object(normalization.get("progress"))
    next_state = _object(gate.get("next"))
    if stop_class in {"TRUE_STOP", "VALIDATION_FAILED", "SAFETY_BOUNDARY"}:
        return "true_stop_or_required_failure"
    if stop_class in {"USER_AUTH_REQUIRED", "HANDOFF_REQUIRED"} or classification.get("user_work_required") is True:
        return "user_authorization_or_material_decision"
    if decision == "user_action_required":
        return "user_authorization_or_material_decision"
    if stop_class == "UNKNOWN_REVIEW_REQUIRED" or decision == "unknown_review_required":
        return "unknown_requiring_review"
    done = progress.get("done")
    total = progress.get("total")
    complete = isinstance(done, int) and isinstance(total, int) and done >= total
    if decision == "supervisor_prompt_needed" or (
        complete and next_state.get("next_owner") == "Supervisor" and next_state.get("recommended_next_slice")
    ):
        return "awaiting_supervisor_acceptance"
    if decision == "completed_continue" and complete and not next_state.get("recommended_next_slice"):
        return "closed_or_informational"
    if classification.get("continue_allowed") is True:
        return "active_safe_continuation"
    return "unknown_requiring_review"


def _task_id_from_identity(
    project_key: str,
    thread_id: str,
    lane_id: str,
    slice_id: str,
    artifact_id: str,
) -> str:
    identity = "|".join((project_key, thread_id, lane_id, slice_id, artifact_id))
    return "task-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def _task_sort_key(task: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(task["attention_precedence"]),
        0 if task["required"] else 1,
        str(task["project_key"]),
        str(task["thread_id"]),
        str(task["lane_id"]),
        str(task["slice_id"]),
        str(task["source_report_path"]),
    )


def _project_worksets(
    tasks: list[dict[str, Any]],
    active: list[dict[str, Any]],
    closed: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    active_by_project: dict[str, list[dict[str, Any]]] = {}
    closed_by_project: dict[str, list[dict[str, Any]]] = {}
    for task in active:
        active_by_project.setdefault(str(task["project_key"]), []).append(task)
    for task in closed:
        closed_by_project.setdefault(str(task["project_key"]), []).append(task)
    projects = sorted({str(task["project_key"]) for task in tasks})
    worksets: list[dict[str, Any]] = []
    for project_key in projects:
        project_active = active_by_project.get(project_key, [])
        project_closed = closed_by_project.get(project_key, [])
        first = project_active[0] if project_active else project_closed[0] if project_closed else None
        gates = [
            task["task_id"]
            for task in project_active
            if task["attention_class"]
            in {"true_stop_or_required_failure", "user_authorization_or_material_decision", "awaiting_supervisor_acceptance"}
        ]
        safe = [
            task["task_id"]
            for task in project_active
            if task["attention_class"] == "active_safe_continuation"
        ]
        worksets.append(
            {
                "project_key": project_key,
                "project_local_first_task_id": first["task_id"] if first else None,
                "active_task_ids": [task["task_id"] for task in project_active],
                "user_or_supervisor_gate": ", ".join(gates) if gates else "none",
                "safe_continuation": ", ".join(safe) if safe else "none",
                "closed_or_informational_task_ids": [task["task_id"] for task in project_closed],
                "global_rank_references": [
                    {"task_id": task["task_id"], "global_rank": task["global_rank"]}
                    for task in project_active
                ],
            }
        )
    return worksets


def _read_strict_json(path: Path, *, label: str) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SupervisionPacketError(f"{label} not found: {path}") from exc
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except json.JSONDecodeError as exc:
        raise SupervisionPacketError(f"invalid {label} JSON {path}: {exc}") from exc


def _reject_duplicate_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SupervisionPacketError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _resolve_within(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SupervisionPacketError(f"report path escapes repository root: {value}") from exc
    return path


def _resolve_cli_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _display_path(root: Path, value: str | Path | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    full = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        return full.relative_to(root).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def _validate_repo_relative_path(value: str, label: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise SupervisionPacketError(f"{label} must be a repository-relative path without '..'")


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SupervisionPacketError(f"{label} must be an object")
    return value


def _require_exact_object(
    value: Any,
    expected_keys: frozenset[str],
    label: str,
) -> dict[str, Any]:
    result = _require_object(value, label)
    actual_keys = set(result)
    missing = sorted(expected_keys - actual_keys)
    unexpected = sorted(
        actual_keys - expected_keys,
        key=lambda key: (type(key).__name__, repr(key)),
    )
    if missing or unexpected:
        raise SupervisionPacketError(
            f"{label} keys are invalid; missing keys: {missing!r}; "
            f"unexpected keys: {unexpected!r}"
        )
    return result


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise SupervisionPacketError(f"{label} must be an array")
    return value


def _task_objects(values: list[Any], label: str) -> list[dict[str, Any]]:
    return [_require_object(value, f"{label}[{index}]") for index, value in enumerate(values)]


def _string_list(value: Any, label: str) -> list[str]:
    values = _require_list(value, label)
    if not all(isinstance(item, str) and item for item in values):
        raise SupervisionPacketError(f"{label} must contain non-empty strings")
    return values


def _require_nonempty_string(value: dict[str, Any], field: str, label: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise SupervisionPacketError(f"{label}.{field} must be a non-empty string")
    return item


def _require_timestamp(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise SupervisionPacketError(f"{label} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SupervisionPacketError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.utcoffset() is None:
        raise SupervisionPacketError(f"{label} must include a timezone")


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _next_state_text(value: Any) -> str:
    state = _object(value)
    return str(
        state.get("recommended_slice")
        or ("user work: " + str(state["user_work"]) if state.get("user_work") not in {None, "none"} else "")
        or state.get("agent_work")
        or "review classification"
    )


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _strict_json_equal(left: Any, right: Any) -> bool:
    return json.dumps(left, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == json.dumps(
        right,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


if __name__ == "__main__":
    raise SystemExit(main())
