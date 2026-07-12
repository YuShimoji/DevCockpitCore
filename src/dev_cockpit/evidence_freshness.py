"""Build read-only evidence freshness and provenance receipts.

The receipt is deliberately point-in-time and non-live.  It separates the
age of an evidence item from its binding to an observed repository revision,
then derives current-state claim eligibility conservatively.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
from typing import Any, Iterable

from .cross_project_smoke import load_smoke, run_cross_project_smoke


POLICY_SCHEMA_VERSION = "evidence_freshness_policy.v1"
OBSERVATIONS_SCHEMA_VERSION = "evidence_freshness_observations.v1"
RECEIPT_SCHEMA_VERSION = "evidence_freshness_receipt.v1"
PRODUCER = "dev_cockpit.evidence_freshness"
DEFAULT_POLICY_PATH = "samples/evidence_freshness/evidence_freshness_policy_v1.json"
DEFAULT_THRESHOLD_SECONDS = 24 * 60 * 60
TEMPORAL_BOUNDARY = "age_seconds <= threshold_seconds"
HASH_BASIS = "canonical_json_utf8_v1"
RAW_HASH_BASIS = "raw_bytes_sha256_v1"
AUTHORITY_CLASSIFICATION = "point_in_time_non_live"
REMOTE_PARITY_BASIS = "local_tracking_reference_no_fetch"

_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]*$")
_FULL_REVISION_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_HEX_REVISION_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_WINDOWS_USER_RE = re.compile(r"(?i)([A-Za-z]:[\\/]Users[\\/])([^\\/]+)")
_POSIX_USER_RE = re.compile(r"(/(?:home|Users)/)([^/]+)")


class EvidenceFreshnessError(ValueError):
    """Raised when a freshness policy or evidence contract is unsafe."""


def load_policy(path: str | Path) -> dict[str, Any]:
    """Load and validate an evidence_freshness_policy.v1 JSON file."""

    policy_path = Path(path)
    data = _read_strict_json(policy_path, contract="policy")
    return validate_policy(data)


def validate_policy(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise EvidenceFreshnessError("policy root must be a JSON object")
    if data.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise EvidenceFreshnessError(
            f"policy schema_version must be {POLICY_SCHEMA_VERSION!r}"
        )

    policy_id = _required_id(data, "policy_id", context="policy")
    threshold_seconds = data.get("threshold_seconds", DEFAULT_THRESHOLD_SECONDS)
    if isinstance(threshold_seconds, bool) or not isinstance(threshold_seconds, int):
        raise EvidenceFreshnessError("policy threshold_seconds must be an integer")
    if threshold_seconds <= 0:
        raise EvidenceFreshnessError("policy threshold_seconds must be greater than zero")

    boundary = data.get("temporal_boundary", TEMPORAL_BOUNDARY)
    if boundary != TEMPORAL_BOUNDARY:
        raise EvidenceFreshnessError(
            f"policy temporal_boundary must be {TEMPORAL_BOUNDARY!r}"
        )

    smoke_path = _required_relative_path(
        data,
        "cross_project_smoke_path",
        context="policy",
    )
    raw_sources = data.get("tracked_sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise EvidenceFreshnessError("policy tracked_sources must be a non-empty list")

    sources: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, value in enumerate(raw_sources):
        context = f"policy tracked_sources[{index}]"
        if not isinstance(value, dict):
            raise EvidenceFreshnessError(f"{context} must be an object")
        project_id = _required_id(value, "project_id", context=context)
        source_id = _required_id(value, "source_id", context=context)
        key = (project_id, source_id)
        if key in seen:
            raise EvidenceFreshnessError(
                f"policy contains duplicate project/source ID: {project_id}/{source_id}"
            )
        seen.add(key)
        required = value.get("required")
        if not isinstance(required, bool):
            raise EvidenceFreshnessError(f"{context}.required must be boolean")
        source_path = _required_relative_path(value, "path", context=context)
        timestamp_kind = value.get("timestamp_kind")
        if timestamp_kind not in {"generated_at", "observed_at"}:
            raise EvidenceFreshnessError(
                f"{context}.timestamp_kind must be 'generated_at' or 'observed_at'"
            )
        source_kind = _optional_id(
            value.get("source_kind"),
            default="tracked_point_in_time_artifact",
            context=f"{context}.source_kind",
        )
        if source_kind == "live_project_observation":
            raise EvidenceFreshnessError(
                f"{context}.source_kind uses a reserved observer source kind"
            )
        sources.append(
            {
                "project_id": project_id,
                "source_id": source_id,
                "required": required,
                "path": source_path,
                "source_kind": source_kind,
                "schema_path": _validate_locator(
                    value.get("schema_path", ["schema_version"]),
                    f"{context}.schema_path",
                ),
                "timestamp_kind": timestamp_kind,
                "timestamp_path": _validate_locator(
                    value.get("timestamp_path"),
                    f"{context}.timestamp_path",
                ),
                "revision_path": _validate_locator(
                    value.get("revision_path"),
                    f"{context}.revision_path",
                ),
            }
        )

    sources.sort(key=lambda item: (item["project_id"], item["source_id"], item["path"]))
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "policy_id": policy_id,
        "threshold_seconds": threshold_seconds,
        "temporal_boundary": boundary,
        "cross_project_smoke_path": smoke_path,
        "tracked_sources": sources,
    }


def load_observations(path: str | Path) -> dict[str, Any]:
    """Load deterministic injected observations using the strict JSON loader."""

    data = _read_strict_json(Path(path), contract="observations")
    return validate_observations(data)


def load_source_contract(path: str | Path) -> Any:
    """Load a source JSON contract while rejecting duplicate keys at any depth."""

    return _read_strict_json(Path(path), contract="source")


def load_receipt(
    path: str | Path,
    *,
    repo_root: str | Path | None = None,
    verify_hashes: bool = False,
) -> dict[str, Any]:
    """Strictly load and validate an evidence_freshness_receipt.v1 file."""

    receipt = validate_receipt(_read_strict_json(Path(path), contract="receipt"))
    if verify_hashes:
        if repo_root is None:
            raise EvidenceFreshnessError("repo_root is required when verify_hashes is true")
        verify_receipt_hashes(receipt, repo_root=repo_root)
    return receipt


def validate_observations(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise EvidenceFreshnessError("observations root must be a JSON object")
    if data.get("schema_version") != OBSERVATIONS_SCHEMA_VERSION:
        raise EvidenceFreshnessError(
            f"observations schema_version must be {OBSERVATIONS_SCHEMA_VERSION!r}"
        )
    observed_at = data.get("observed_at")
    _parse_assessment_time(observed_at, field="observations observed_at")
    projects_value = data.get("projects")
    if not isinstance(projects_value, list) or not projects_value:
        raise EvidenceFreshnessError("observations projects must be a non-empty list")

    projects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(projects_value):
        context = f"observations projects[{index}]"
        if not isinstance(value, dict):
            raise EvidenceFreshnessError(f"{context} must be an object")
        project_id = _required_id(value, "project_id", context=context)
        if project_id in seen:
            raise EvidenceFreshnessError(f"observations duplicate project_id: {project_id}")
        seen.add(project_id)
        required = value.get("required")
        available = value.get("available")
        if not isinstance(required, bool) or not isinstance(available, bool):
            raise EvidenceFreshnessError(
                f"{context}.required and .available must be boolean"
            )
        path = value.get("path")
        if path is not None and not isinstance(path, str):
            raise EvidenceFreshnessError(f"{context}.path must be string or null")
        worktree_state = value.get("worktree_state")
        if worktree_state not in {"clean", "dirty", "unknown", None}:
            raise EvidenceFreshnessError(f"{context}.worktree_state is unsupported")
        observation_unchanged = value.get("observation_unchanged")
        target_repo_modified = value.get("target_repo_modified")
        if observation_unchanged not in {True, False, None}:
            raise EvidenceFreshnessError(
                f"{context}.observation_unchanged must be boolean or null"
            )
        if target_repo_modified not in {True, False, None}:
            raise EvidenceFreshnessError(
                f"{context}.target_repo_modified must be boolean or null"
            )
        remote_parity = value.get("remote_parity")
        if remote_parity is not None and not isinstance(remote_parity, dict):
            raise EvidenceFreshnessError(f"{context}.remote_parity must be object or null")
        projects.append(
            {
                "project_id": project_id,
                "required": required,
                "available": available,
                "path": redact_path(path) if path else None,
                "schema_version": _optional_string(value.get("schema_version")),
                "observed_at": _optional_string(value.get("observed_at")) or observed_at,
                "branch": _optional_string(value.get("branch")),
                "head_revision": _optional_string(value.get("head_revision")),
                "worktree_state": worktree_state or "unknown",
                "before_head_revision": _optional_string(value.get("before_head_revision")),
                "after_head_revision": _optional_string(value.get("after_head_revision")),
                "before_worktree_state": _optional_string(value.get("before_worktree_state")),
                "after_worktree_state": _optional_string(value.get("after_worktree_state")),
                "upstream": _optional_string(value.get("upstream")),
                "remote_parity": _normalize_remote_parity(remote_parity),
                "observation_unchanged": observation_unchanged,
                "target_repo_modified": target_repo_modified,
                "before_sha256": _optional_string(value.get("before_sha256")),
                "after_sha256": _optional_string(value.get("after_sha256")),
                "reason_codes": _string_list(value.get("reason_codes", []), context),
            }
        )
    projects.sort(key=lambda item: item["project_id"])
    return {
        "schema_version": OBSERVATIONS_SCHEMA_VERSION,
        "observed_at": observed_at,
        "projects": projects,
    }


def validate_receipt(data: Any) -> dict[str, Any]:
    """Validate receipt structure, deterministic ordering, counts, and capture ID."""

    if not isinstance(data, dict):
        raise EvidenceFreshnessError("receipt root must be a JSON object")
    if data.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise EvidenceFreshnessError(
            f"receipt schema_version must be {RECEIPT_SCHEMA_VERSION!r}"
        )
    capture_id = data.get("capture_id")
    if not isinstance(capture_id, str) or not re.fullmatch(r"efr-[0-9a-f]{20}", capture_id):
        raise EvidenceFreshnessError("receipt capture_id is invalid")
    _parse_assessment_time(data.get("assessed_at"), field="receipt assessed_at")
    policy = data.get("policy")
    authority = data.get("authority")
    projects = data.get("projects")
    sources = data.get("sources")
    if not isinstance(policy, dict) or policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise EvidenceFreshnessError("receipt policy contract is invalid")
    policy_contract = {
        "schema_version": policy.get("schema_version"),
        "policy_id": policy.get("policy_id"),
        "threshold_seconds": policy.get("threshold_seconds"),
        "temporal_boundary": policy.get("temporal_boundary"),
        "cross_project_smoke_path": policy.get("cross_project_smoke_path"),
        "tracked_sources": policy.get("tracked_sources"),
    }
    validated_policy = validate_policy(policy_contract)
    if policy.get("policy_content_sha256") != canonical_sha256(validated_policy):
        raise EvidenceFreshnessError("receipt policy hash does not match its contract")
    if policy.get("threshold_hours") != validated_policy["threshold_seconds"] / 3600:
        raise EvidenceFreshnessError("receipt policy threshold projection is invalid")
    if (
        policy.get("future_timestamp_state") != "unknown"
        or policy.get("missing_or_invalid_timestamp_state") != "unknown"
        or policy.get("revision_mismatch_state") != "stale"
    ):
        raise EvidenceFreshnessError("receipt policy state composition is invalid")
    if not isinstance(authority, dict) or authority.get("classification") != AUTHORITY_CLASSIFICATION:
        raise EvidenceFreshnessError("receipt authority classification is invalid")
    if authority.get("point_in_time") is not True or authority.get("live") is not False:
        raise EvidenceFreshnessError("receipt must be point-in-time and non-live")
    observation_mode = data.get("observation_mode")
    if observation_mode not in {
        "live_read_only_capture",
        "injected_deterministic_observations",
    }:
        raise EvidenceFreshnessError("receipt observation_mode is invalid")
    if not isinstance(authority.get("tracked_example"), bool):
        raise EvidenceFreshnessError("receipt tracked_example authority is invalid")
    tracked_example = authority["tracked_example"]
    if observation_mode == "injected_deterministic_observations" and not tracked_example:
        raise EvidenceFreshnessError("injected observations must be a tracked/non-authoritative example")
    authority_allows_current_claim = (
        observation_mode == "live_read_only_capture" and not tracked_example
    )
    if authority.get("may_support_current_state_at_assessed_at") is not authority_allows_current_claim:
        raise EvidenceFreshnessError("receipt current-state authority is inconsistent")
    if authority.get("authoritative_for_live_state") is not False:
        raise EvidenceFreshnessError("a point-in-time receipt cannot claim live-state authority")
    if not isinstance(projects, list) or not isinstance(sources, list):
        raise EvidenceFreshnessError("receipt projects and sources must be lists")

    project_ids: list[str] = []
    for index, project in enumerate(projects):
        if not isinstance(project, dict):
            raise EvidenceFreshnessError(f"receipt projects[{index}] must be an object")
        project_id = project.get("project_id")
        if not isinstance(project_id, str) or not _ID_RE.fullmatch(project_id):
            raise EvidenceFreshnessError(f"receipt projects[{index}].project_id is invalid")
        if not isinstance(project.get("required"), bool) or not isinstance(project.get("available"), bool):
            raise EvidenceFreshnessError(
                f"receipt projects[{index}] required/available flags are invalid"
            )
        project_reasons = project.get("reason_codes")
        if (
            not isinstance(project_reasons, list)
            or any(not isinstance(item, str) for item in project_reasons)
            or project_reasons != sorted(set(project_reasons))
        ):
            raise EvidenceFreshnessError(f"receipt projects[{index}].reason_codes are invalid")
        project_path = project.get("path")
        if isinstance(project_path, str) and _is_unredacted_absolute_path(project_path):
            raise EvidenceFreshnessError(f"receipt projects[{index}].path is not redacted")
        project_parity = project.get("remote_parity")
        if (
            not isinstance(project_parity, dict)
            or project_parity.get("evidence_basis") != REMOTE_PARITY_BASIS
            or project_parity.get("fetch_performed") is not False
        ):
            raise EvidenceFreshnessError(
                f"receipt projects[{index}].remote_parity evidence scope is invalid"
            )
        if project["available"]:
            before_hash = project.get("before_sha256")
            after_hash = project.get("after_sha256")
            if (
                not isinstance(project.get("observation_unchanged"), bool)
                or not isinstance(project.get("target_repo_modified"), bool)
                or not isinstance(before_hash, str)
                or not re.fullmatch(r"[0-9a-f]{64}", before_hash)
                or not isinstance(after_hash, str)
                or not re.fullmatch(r"[0-9a-f]{64}", after_hash)
            ):
                raise EvidenceFreshnessError(
                    f"receipt projects[{index}] before/after observation proof is invalid"
                )
            if project["observation_unchanged"] and (
                before_hash != after_hash
                or project.get("before_head_revision") != project.get("after_head_revision")
                or project.get("before_worktree_state") != project.get("after_worktree_state")
            ):
                raise EvidenceFreshnessError(
                    f"receipt projects[{index}] stable observation proof is contradictory"
                )
        project_ids.append(project_id)
    if project_ids != sorted(project_ids) or len(set(project_ids)) != len(project_ids):
        raise EvidenceFreshnessError("receipt projects must have unique deterministic ordering")
    project_map = {item["project_id"]: item for item in projects}
    configured_sources = {
        (item["project_id"], item["source_id"]): item
        for item in validated_policy["tracked_sources"]
    }
    remote_parity_evidence = data.get("remote_parity_evidence")
    if (
        not isinstance(remote_parity_evidence, dict)
        or remote_parity_evidence.get("basis") != REMOTE_PARITY_BASIS
        or remote_parity_evidence.get("fetch_performed") is not False
        or remote_parity_evidence.get("live_remote_state_claimed") is not False
    ):
        raise EvidenceFreshnessError("receipt remote-parity evidence scope is invalid")
    scope_boundary = data.get("scope_boundary")
    if not isinstance(scope_boundary, dict):
        raise EvidenceFreshnessError("receipt scope_boundary is invalid")
    expected_target_observations = [
        {
            "project_id": item["project_id"],
            "required": item["required"],
            "available": item["available"],
            "before_sha256": item.get("before_sha256"),
            "after_sha256": item.get("after_sha256"),
            "before_head_revision": item.get("before_head_revision"),
            "after_head_revision": item.get("after_head_revision"),
            "before_worktree_state": item.get("before_worktree_state"),
            "after_worktree_state": item.get("after_worktree_state"),
            "observation_unchanged": item.get("observation_unchanged"),
            "target_repo_modified": item.get("target_repo_modified"),
        }
        for item in projects
    ]
    if (
        scope_boundary.get("target_repositories_observed_read_only") is not True
        or scope_boundary.get("fetch_performed") is not False
        or scope_boundary.get("default_validation_executed") is not False
        or scope_boundary.get("target_repo_modified")
        is not any(item.get("target_repo_modified") is True for item in projects)
        or scope_boundary.get("all_available_observations_unchanged")
        is not all(
            item.get("observation_unchanged") is True
            for item in projects
            if item.get("available")
        )
        or scope_boundary.get("target_observations") != expected_target_observations
    ):
        raise EvidenceFreshnessError("receipt scope boundary disagrees with project observations")

    source_keys: list[tuple[str, str, str]] = []
    source_ids: list[tuple[str, str]] = []
    allowed_freshness = {"fresh", "stale", "unknown"}
    allowed_revision = {"match", "mismatch", "unknown"}
    required_fields = {
        "project_id",
        "source_id",
        "source_kind",
        "required",
        "availability",
        "schema_version",
        "source_path",
        "content_sha256",
        "hash_basis",
        "generated_at",
        "observed_at",
        "timestamp_field",
        "assessed_at",
        "age_seconds",
        "fresh_through",
        "temporal_state",
        "source_revision",
        "observed_revision",
        "revision_binding_state",
        "freshness_state",
        "reason_codes",
        "current_state_claim_eligible",
        "authority_classification",
    }
    for index, source in enumerate(sources):
        if not isinstance(source, dict) or not required_fields.issubset(source):
            raise EvidenceFreshnessError(f"receipt sources[{index}] is missing required fields")
        project_id = source.get("project_id")
        source_id = source.get("source_id")
        source_path = source.get("source_path") or ""
        if project_id not in project_ids:
            raise EvidenceFreshnessError(f"receipt sources[{index}] references unknown project")
        if not isinstance(source_id, str) or not _ID_RE.fullmatch(source_id):
            raise EvidenceFreshnessError(f"receipt sources[{index}].source_id is invalid")
        if not isinstance(source.get("required"), bool):
            raise EvidenceFreshnessError(f"receipt sources[{index}].required is invalid")
        if not isinstance(source.get("current_state_claim_eligible"), bool):
            raise EvidenceFreshnessError(
                f"receipt sources[{index}].current_state_claim_eligible is invalid"
            )
        if source.get("temporal_state") not in allowed_freshness:
            raise EvidenceFreshnessError(f"receipt sources[{index}].temporal_state is invalid")
        if source.get("freshness_state") not in allowed_freshness:
            raise EvidenceFreshnessError(f"receipt sources[{index}].freshness_state is invalid")
        if source.get("revision_binding_state") not in allowed_revision:
            raise EvidenceFreshnessError(
                f"receipt sources[{index}].revision_binding_state is invalid"
            )
        if source.get("authority_classification") != AUTHORITY_CLASSIFICATION:
            raise EvidenceFreshnessError(
                f"receipt sources[{index}].authority_classification is invalid"
            )
        reason_codes = source.get("reason_codes")
        if (
            not isinstance(reason_codes, list)
            or any(not isinstance(item, str) for item in reason_codes)
            or reason_codes != sorted(set(reason_codes))
        ):
            raise EvidenceFreshnessError(f"receipt sources[{index}].reason_codes are invalid")
        content_hash = source.get("content_sha256")
        availability = source.get("availability")
        if availability == "available":
            if source.get("hash_basis") != HASH_BASIS:
                raise EvidenceFreshnessError(f"receipt sources[{index}].hash_basis is invalid")
            if not isinstance(content_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", content_hash):
                raise EvidenceFreshnessError(
                    f"receipt sources[{index}].content_sha256 is invalid"
                )
        elif availability == "invalid_contract":
            if source.get("hash_basis") != RAW_HASH_BASIS:
                raise EvidenceFreshnessError(f"receipt sources[{index}].hash_basis is invalid")
            if not isinstance(content_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", content_hash):
                raise EvidenceFreshnessError(
                    f"receipt sources[{index}].content_sha256 is invalid"
                )
        elif availability == "missing":
            if source.get("hash_basis") != HASH_BASIS or content_hash is not None:
                raise EvidenceFreshnessError(f"receipt sources[{index}].missing hash contract is invalid")
        else:
            raise EvidenceFreshnessError(f"receipt sources[{index}].availability is invalid")

        if source.get("assessed_at") != data["assessed_at"]:
            raise EvidenceFreshnessError(f"receipt sources[{index}].assessed_at is inconsistent")
        if isinstance(source_path, str) and _is_unredacted_absolute_path(source_path):
            raise EvidenceFreshnessError(f"receipt sources[{index}].source_path is not redacted")

        project = project_map[str(project_id)]
        if source.get("observed_revision") != project.get("head_revision"):
            raise EvidenceFreshnessError(
                f"receipt sources[{index}].observed_revision is inconsistent"
            )
        if source.get("source_kind") == "live_project_observation":
            if source_id != f"{project_id}.live_status_observation":
                raise EvidenceFreshnessError(f"receipt sources[{index}] live source ID is invalid")
            if source.get("required") is not project["required"]:
                raise EvidenceFreshnessError(f"receipt sources[{index}] required flag is inconsistent")
            expected_live_path = f"git-observation:{project.get('path') or '<redacted>'}"
            if source.get("source_path") != expected_live_path:
                raise EvidenceFreshnessError(
                    f"receipt sources[{index}] live provenance projection is inconsistent"
                )
            if availability == "available" and (
                source.get("schema_version") != project.get("schema_version")
                or source.get("generated_at") is not None
                or source.get("observed_at") != project.get("observed_at")
                or source.get("timestamp_field") != "observed_at"
                or source.get("source_revision") != project.get("head_revision")
            ):
                raise EvidenceFreshnessError(
                    f"receipt sources[{index}] live provenance projection is inconsistent"
                )
            extra_reasons = project["reason_codes"]
            expected_source_revision = project.get("head_revision")
        else:
            config = configured_sources.get((str(project_id), source_id))
            if config is None:
                raise EvidenceFreshnessError(f"receipt sources[{index}] is absent from policy")
            if (
                source.get("source_kind") != config["source_kind"]
                or source.get("required") is not config["required"]
                or source.get("source_path") != config["path"]
            ):
                raise EvidenceFreshnessError(f"receipt sources[{index}] disagrees with policy")
            extra_reasons = []
            expected_source_revision = source.get("source_revision")

        if availability == "available":
            expected = _evaluated_source_row(
                project_id=str(project_id),
                source_id=source_id,
                source_kind=source["source_kind"],
                required=source["required"],
                availability="available",
                schema_version=source.get("schema_version"),
                source_path=source.get("source_path"),
                content_sha256=source.get("content_sha256"),
                generated_at=source.get("generated_at"),
                observed_at=source.get("observed_at"),
                timestamp_field=source.get("timestamp_field"),
                source_revision=expected_source_revision,
                observed_revision=project.get("head_revision"),
                assessed_at=data["assessed_at"],
                threshold_seconds=validated_policy["threshold_seconds"],
                authority_allows_current_claim=authority_allows_current_claim,
                observation_clean=project.get("worktree_state") == "clean",
                observation_stable=(
                    project.get("observation_unchanged") is True
                    and project.get("target_repo_modified") is False
                ),
                extra_reason_codes=extra_reasons,
            )
            semantic_fields = {
                "age_seconds",
                "fresh_through",
                "temporal_state",
                "source_revision",
                "observed_revision",
                "revision_binding_state",
                "freshness_state",
                "reason_codes",
                "current_state_claim_eligible",
            }
            if any(source.get(field) != expected.get(field) for field in semantic_fields):
                raise EvidenceFreshnessError(
                    f"receipt sources[{index}] semantic freshness projection is inconsistent"
                )
        else:
            if (
                source.get("temporal_state") != "unknown"
                or source.get("revision_binding_state") != "unknown"
                or source.get("freshness_state") != "unknown"
                or source.get("current_state_claim_eligible") is not False
                or source.get("schema_version") is not None
                or source.get("generated_at") is not None
                or source.get("observed_at") is not None
                or source.get("timestamp_field") is not None
                or source.get("age_seconds") is not None
                or source.get("fresh_through") is not None
                or source.get("source_revision") is not None
                or not reason_codes
            ):
                raise EvidenceFreshnessError(
                    f"receipt sources[{index}] unusable-source projection is inconsistent"
                )
        source_keys.append((str(project_id), source_id, str(source_path)))
        source_ids.append((str(project_id), source_id))
    if source_keys != sorted(source_keys):
        raise EvidenceFreshnessError("receipt sources must have unique deterministic ordering")
    if len(set(source_ids)) != len(source_ids):
        raise EvidenceFreshnessError("receipt source IDs must be unique within each project")
    observed_configured_sources = {
        pair
        for pair, source in zip(source_ids, sources)
        if source.get("source_kind") != "live_project_observation"
    }
    if observed_configured_sources != set(configured_sources):
        raise EvidenceFreshnessError("receipt tracked-source set does not match policy")

    expected_summary = _summary(projects, sources)
    if data.get("summary") != expected_summary:
        raise EvidenceFreshnessError("receipt summary does not match project/source rows")
    expected_capture_id = _capture_id(
        policy_id=policy.get("policy_id"),
        policy_sha256=policy.get("policy_content_sha256"),
        assessed_at=data["assessed_at"],
        observation_mode=data.get("observation_mode"),
        tracked_example=authority.get("tracked_example") is True,
        projects=projects,
        sources=sources,
    )
    if capture_id != expected_capture_id:
        raise EvidenceFreshnessError("receipt capture_id does not match its content")
    return data


def verify_receipt_hashes(
    receipt: dict[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, int]:
    """Recompute every available source hash from its declared provenance."""

    validated = validate_receipt(receipt)
    root = Path(repo_root).resolve()
    projects = {item["project_id"]: item for item in validated["projects"]}
    configs = {
        (item["project_id"], item["source_id"]): item
        for item in validated["policy"]["tracked_sources"]
    }
    verified = 0
    skipped_missing = 0
    for source in validated["sources"]:
        if source["availability"] == "missing":
            skipped_missing += 1
            continue
        if source["source_kind"] == "live_project_observation":
            expected = canonical_sha256(_live_source_payload(projects[source["project_id"]]))
        else:
            config = configs[(source["project_id"], source["source_id"])]
            path = _resolve_contained_file(root, config["path"], contract="source")
            payload = path.read_bytes()
            if source["availability"] == "invalid_contract":
                try:
                    _parse_strict_json_bytes(
                        payload,
                        path=path,
                        contract=f"source {source['source_id']}",
                    )
                except EvidenceFreshnessError:
                    expected = hashlib.sha256(payload).hexdigest()
                else:
                    raise EvidenceFreshnessError(
                        f"source is no longer an invalid contract: {source['source_id']}"
                    )
            else:
                source_data = _parse_strict_json_bytes(
                    payload,
                    path=path,
                    contract=f"source {source['source_id']}",
                )
                expected = canonical_sha256(source_data)
                timestamp = _nested(source_data, config["timestamp_path"])
                expected_generated_at = (
                    timestamp if config["timestamp_kind"] == "generated_at" else None
                )
                expected_observed_at = (
                    timestamp if config["timestamp_kind"] == "observed_at" else None
                )
                projection = {
                    "schema_version": _nested(source_data, config["schema_path"]),
                    "generated_at": expected_generated_at,
                    "observed_at": expected_observed_at,
                    "timestamp_field": config["timestamp_kind"],
                    "source_revision": _nested(source_data, config["revision_path"]),
                }
                if any(source.get(key) != value for key, value in projection.items()):
                    raise EvidenceFreshnessError(
                        f"source provenance projection mismatch: "
                        f"{source['project_id']}/{source['source_id']}"
                    )
        if expected != source["content_sha256"]:
            raise EvidenceFreshnessError(
                f"source content hash mismatch: {source['project_id']}/{source['source_id']}"
            )
        verified += 1
    return {"verified": verified, "skipped_missing": skipped_missing}


def build_receipt(
    policy: dict[str, Any],
    *,
    repo_root: str | Path,
    assessed_at: str | None = None,
    observations: dict[str, Any] | None = None,
    tracked_example: bool = False,
) -> dict[str, Any]:
    """Build one deterministic point-in-time receipt from policy and observations."""

    validated_policy = validate_policy(policy)
    assessment_time = assessed_at or _utc_now_iso()
    _parse_assessment_time(assessment_time, field="assessed_at")
    root = Path(repo_root).resolve()
    if observations is None:
        project_rows = _collect_live_observations(
            validated_policy,
            repo_root=root,
            observed_at=assessment_time,
        )
        observation_mode = "live_read_only_capture"
    else:
        validated_observations = validate_observations(observations)
        project_rows = validated_observations["projects"]
        observation_mode = "injected_deterministic_observations"

    project_rows = sorted(project_rows, key=lambda item: item["project_id"])
    project_map = {item["project_id"]: item for item in project_rows}
    effective_tracked_example = tracked_example or observations is not None
    authority_allows_current_claim = not effective_tracked_example and observations is None

    sources: list[dict[str, Any]] = []
    for project in project_rows:
        sources.append(
            _live_observation_source(
                project,
                assessed_at=assessment_time,
                threshold_seconds=validated_policy["threshold_seconds"],
                authority_allows_current_claim=authority_allows_current_claim,
            )
        )
    for source_config in validated_policy["tracked_sources"]:
        sources.append(
            _tracked_source(
                source_config,
                repo_root=root,
                project=project_map.get(source_config["project_id"]),
                assessed_at=assessment_time,
                threshold_seconds=validated_policy["threshold_seconds"],
                authority_allows_current_claim=authority_allows_current_claim,
            )
        )
    sources.sort(key=lambda item: (item["project_id"], item["source_id"], item["source_path"] or ""))

    summary = _summary(project_rows, sources)
    target_observations = [
        {
            "project_id": item["project_id"],
            "required": item["required"],
            "available": item["available"],
            "before_sha256": item.get("before_sha256"),
            "after_sha256": item.get("after_sha256"),
            "before_head_revision": item.get("before_head_revision"),
            "after_head_revision": item.get("after_head_revision"),
            "before_worktree_state": item.get("before_worktree_state"),
            "after_worktree_state": item.get("after_worktree_state"),
            "observation_unchanged": item.get("observation_unchanged"),
            "target_repo_modified": item.get("target_repo_modified"),
        }
        for item in project_rows
    ]
    scope_boundary = {
        "target_repositories_observed_read_only": True,
        "target_repo_commands": "read_only_git_status_rev_parse_log_and_local_tracking_parity",
        "fetch_performed": False,
        "default_validation_executed": False,
        "target_repo_modified": any(
            item.get("target_repo_modified") is True for item in project_rows
        ),
        "all_available_observations_unchanged": all(
            item.get("observation_unchanged") is True
            for item in project_rows
            if item.get("available")
        ),
        "target_observations": target_observations,
    }

    capture_id = _capture_id(
        policy_id=validated_policy["policy_id"],
        policy_sha256=canonical_sha256(validated_policy),
        assessed_at=assessment_time,
        observation_mode=observation_mode,
        tracked_example=effective_tracked_example,
        projects=project_rows,
        sources=sources,
    )

    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "capture_id": capture_id,
        "assessed_at": assessment_time,
        "producer": PRODUCER,
        "policy": {
            "schema_version": validated_policy["schema_version"],
            "policy_id": validated_policy["policy_id"],
            "threshold_seconds": validated_policy["threshold_seconds"],
            "threshold_hours": validated_policy["threshold_seconds"] / 3600,
            "temporal_boundary": validated_policy["temporal_boundary"],
            "cross_project_smoke_path": validated_policy["cross_project_smoke_path"],
            "tracked_sources": validated_policy["tracked_sources"],
            "policy_content_sha256": canonical_sha256(validated_policy),
            "future_timestamp_state": "unknown",
            "missing_or_invalid_timestamp_state": "unknown",
            "revision_mismatch_state": "stale",
        },
        "authority": {
            "classification": AUTHORITY_CLASSIFICATION,
            "point_in_time": True,
            "live": False,
            "tracked_example": effective_tracked_example,
            "authoritative_for_live_state": False,
            "may_support_current_state_at_assessed_at": authority_allows_current_claim,
            "statement": (
                "Tracked deterministic example; never authoritative for live state."
                if effective_tracked_example
                else "Local read-only capture; valid only for the recorded assessment and policy window."
            ),
        },
        "observation_mode": observation_mode,
        "remote_parity_evidence": {
            "basis": REMOTE_PARITY_BASIS,
            "fetch_performed": False,
            "live_remote_state_claimed": False,
        },
        "projects": project_rows,
        "sources": sources,
        "summary": summary,
        "scope_boundary": scope_boundary,
    }


def evaluate_temporal(
    timestamp: Any,
    *,
    assessed_at: str,
    threshold_seconds: int,
) -> dict[str, Any]:
    """Evaluate age using the inclusive boundary mandated by policy."""

    assessed = _parse_assessment_time(assessed_at, field="assessed_at")
    if timestamp is None or (isinstance(timestamp, str) and not timestamp.strip()):
        return _temporal_unknown("timestamp_missing")
    if not isinstance(timestamp, str):
        return _temporal_unknown("timestamp_malformed")
    try:
        parsed = datetime.fromisoformat(timestamp.strip().replace("Z", "+00:00"))
    except ValueError:
        return _temporal_unknown("timestamp_malformed")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return _temporal_unknown("timestamp_timezone_missing")
    parsed = parsed.astimezone(timezone.utc)
    if parsed > assessed:
        return _temporal_unknown("timestamp_in_future")
    age = (assessed - parsed).total_seconds()
    age_value: int | float = int(age) if age.is_integer() else age
    fresh_through = _format_datetime(parsed + timedelta(seconds=threshold_seconds))
    if age <= threshold_seconds:
        return {
            "temporal_state": "fresh",
            "age_seconds": age_value,
            "fresh_through": fresh_through,
            "reason_codes": ["timestamp_within_threshold"],
        }
    return {
        "temporal_state": "stale",
        "age_seconds": age_value,
        "fresh_through": fresh_through,
        "reason_codes": ["timestamp_threshold_exceeded"],
    }


def evaluate_revision(
    source_revision: Any,
    observed_revision: Any,
) -> dict[str, Any]:
    """Compare revisions without treating an unresolved abbreviation as exact."""

    source = source_revision.strip().lower() if isinstance(source_revision, str) else None
    observed = observed_revision.strip().lower() if isinstance(observed_revision, str) else None
    if not source:
        return {
            "revision_binding_state": "unknown",
            "source_revision": None,
            "observed_revision": observed or None,
            "reason_codes": ["source_revision_missing"],
        }
    if not observed:
        return {
            "revision_binding_state": "unknown",
            "source_revision": source,
            "observed_revision": None,
            "reason_codes": ["observed_revision_missing"],
        }
    if not _HEX_REVISION_RE.fullmatch(source) or not _HEX_REVISION_RE.fullmatch(observed):
        return {
            "revision_binding_state": "unknown",
            "source_revision": source,
            "observed_revision": observed,
            "reason_codes": ["revision_format_unsupported"],
        }
    if _FULL_REVISION_RE.fullmatch(source) and _FULL_REVISION_RE.fullmatch(observed):
        if source == observed:
            return {
                "revision_binding_state": "match",
                "source_revision": source,
                "observed_revision": observed,
                "reason_codes": ["revision_match"],
            }
        return {
            "revision_binding_state": "mismatch",
            "source_revision": source,
            "observed_revision": observed,
            "reason_codes": ["revision_mismatch"],
        }
    if source.startswith(observed) or observed.startswith(source):
        return {
            "revision_binding_state": "unknown",
            "source_revision": source,
            "observed_revision": observed,
            "reason_codes": ["revision_abbreviation_unresolved"],
        }
    return {
        "revision_binding_state": "mismatch",
        "source_revision": source,
        "observed_revision": observed,
        "reason_codes": ["revision_mismatch"],
    }


def render_markdown(receipt: dict[str, Any]) -> str:
    """Render a concise human projection from the receipt model only."""

    summary = receipt["summary"]
    lines = [
        "# Evidence Freshness / Provenance Receipt",
        "",
        f"- Schema: `{receipt['schema_version']}`",
        f"- Capture ID: `{receipt['capture_id']}`",
        f"- Assessed at: `{receipt['assessed_at']}`",
        f"- Authority: `{receipt['authority']['classification']}` (live: `false`)",
        f"- Policy: `{receipt['policy']['policy_id']}`; `{receipt['policy']['temporal_boundary']}`",
        f"- Remote parity basis: `{receipt['remote_parity_evidence']['basis']}`; fetch performed: `false`",
        "",
        receipt["authority"]["statement"],
        "",
        "## Summary",
        "",
        (
            f"Sources: fresh `{summary['source_counts']['fresh']}`, "
            f"stale `{summary['source_counts']['stale']}`, "
            f"unknown `{summary['source_counts']['unknown']}`; "
            f"current-state eligible `{summary['current_state_claim_eligible']['eligible']}`."
        ),
        "",
        "## Projects",
        "",
        "| Project | Required | State | HEAD before -> after | Worktree before -> after | Stable | Before hash | After hash | Reasons |",
        "| --- | ---: | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for project in receipt["projects"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(project["project_id"]),
                    str(project["required"]).lower(),
                    _md("observed" if project["available"] else "skipped"),
                    _md(
                        f"{_short_hash(project.get('before_head_revision'))} -> "
                        f"{_short_hash(project.get('after_head_revision'))}"
                    ),
                    _md(
                        f"{project.get('before_worktree_state') or 'unknown'} -> "
                        f"{project.get('after_worktree_state') or 'unknown'}"
                    ),
                    _bool_text(project.get("observation_unchanged")),
                    _md(_short_hash(project.get("before_sha256"))),
                    _md(_short_hash(project.get("after_sha256"))),
                    _md(", ".join(project.get("reason_codes", [])) or "none"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Sources",
            "",
            "| Project / source | Kind | Path | Time | Fresh through | Temporal | Revision | Freshness | Eligible | SHA-256 | Reasons |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for source in receipt["sources"]:
        timestamp = source.get("observed_at") or source.get("generated_at") or "unknown"
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(f"{source['project_id']} / {source['source_id']}"),
                    _md(source["source_kind"]),
                    _md(source.get("source_path")),
                    _md(timestamp),
                    _md(source.get("fresh_through")),
                    _md(source["temporal_state"]),
                    _md(source["revision_binding_state"]),
                    _md(source["freshness_state"]),
                    str(source["current_state_claim_eligible"]).lower(),
                    _md(source.get("content_sha256")),
                    _md(", ".join(source["reason_codes"])),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "This receipt is a point-in-time observation, not a continuously live control plane. "
            "Reassess after the listed `fresh_through` time or after repository state changes.",
            "",
        ]
    )
    return "\n".join(lines)


def dumps_receipt(receipt: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(
        receipt,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        sort_keys=False,
    ) + "\n"


def write_receipt(
    receipt: dict[str, Any],
    output_json: str | Path,
    *,
    output_markdown: str | Path | None = None,
    pretty: bool = False,
) -> None:
    json_path = Path(output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        dumps_receipt(receipt, pretty=pretty),
        encoding="utf-8",
        newline="\n",
    )
    if output_markdown is not None:
        markdown_path = Path(output_markdown)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(receipt), encoding="utf-8", newline="\n")


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def redact_path(value: str | None, repo_root: str | Path | None = None) -> str | None:
    """Return a repo-relative path where possible, otherwise redact user segments."""

    if value is None:
        return None
    if value.startswith("git-observation:"):
        inner = value.split(":", 1)[1]
        return "git-observation:" + str(redact_path(inner, repo_root=repo_root))
    if repo_root is not None:
        try:
            candidate = Path(value).resolve()
            root = Path(repo_root).resolve()
            relative = candidate.relative_to(root)
        except (OSError, ValueError):
            pass
        else:
            text = relative.as_posix()
            return text or "."
    if _WINDOWS_ABSOLUTE_RE.match(value) or value.startswith("\\\\"):
        name = PureWindowsPath(value).name or "<root>"
        return f"<redacted-absolute>/{name}"
    if value.startswith("/"):
        name = PurePosixPath(value).name or "<root>"
        return f"<redacted-absolute>/{name}"
    redacted = _WINDOWS_USER_RE.sub(r"\1<redacted>", value)
    redacted = _POSIX_USER_RE.sub(r"\1<redacted>", redacted)
    return redacted.replace("\\", "/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a read-only evidence_freshness_receipt.v1."
    )
    parser.add_argument("--policy", default=DEFAULT_POLICY_PATH, help="Policy JSON path.")
    parser.add_argument("--repo-root", default=".", help="DevCockpitCore repository root.")
    parser.add_argument(
        "--observations",
        help="Optional deterministic evidence_freshness_observations.v1 input.",
    )
    parser.add_argument("--assessed-at", help="Inject an RFC 3339 assessment time.")
    parser.add_argument("--output-json", help="Receipt JSON path. Omit to write stdout.")
    parser.add_argument("--output-markdown", help="Optional generated Markdown path.")
    parser.add_argument("--tracked-example", action="store_true", help="Mark output non-authoritative.")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON.")
    args = parser.parse_args(argv)

    if args.output_markdown and not args.output_json:
        parser.error("--output-markdown requires --output-json")
    try:
        policy = load_policy(args.policy)
        observations = load_observations(args.observations) if args.observations else None
        receipt = validate_receipt(
            build_receipt(
                policy,
                repo_root=args.repo_root,
                assessed_at=args.assessed_at,
                observations=observations,
                tracked_example=args.tracked_example,
            )
        )
        verify_receipt_hashes(receipt, repo_root=args.repo_root)
    except EvidenceFreshnessError as exc:
        print(f"evidence freshness error: {exc}", file=sys.stderr)
        return 2

    payload = dumps_receipt(receipt, pretty=args.pretty)
    if args.output_json:
        write_receipt(
            receipt,
            args.output_json,
            output_markdown=args.output_markdown,
            pretty=args.pretty,
        )
    else:
        print(payload, end="")
    return 1 if (
        receipt["summary"]["required_missing"]
        or receipt["summary"]["required_invalid"]
    ) else 0


def _collect_live_observations(
    policy: dict[str, Any],
    *,
    repo_root: Path,
    observed_at: str,
) -> list[dict[str, Any]]:
    smoke_path = _resolve_contained_file(
        repo_root,
        policy["cross_project_smoke_path"],
        contract="cross-project smoke",
    )
    smoke = load_smoke(smoke_path)
    result = run_cross_project_smoke(
        smoke,
        repo_path=repo_root,
        smoke_path=policy["cross_project_smoke_path"],
        generated_at=observed_at,
    )
    rows: list[dict[str, Any]] = []
    for index, project in enumerate(result["projects"]):
        status = project.get("status_snapshot")
        status = status if isinstance(status, dict) else {}
        resolution = project.get("repo_resolution")
        resolution = resolution if isinstance(resolution, dict) else {}
        boundary = project.get("scope_boundary")
        boundary = boundary if isinstance(boundary, dict) else {}
        target_observation = boundary.get("target_repo_observation")
        target_observation = target_observation if isinstance(target_observation, dict) else {}
        signature_before = target_observation.get("signature_before")
        signature_before = signature_before if isinstance(signature_before, dict) else {}
        signature_after = target_observation.get("signature_after")
        signature_after = signature_after if isinstance(signature_after, dict) else {}
        project_id = project.get("project_key") or _fallback_project_id(project, index)
        available = status.get("generated") is True
        required = project.get("required") is True
        reasons = []
        if not available:
            reasons.append("required_project_missing" if required else "optional_project_missing")
        if target_observation.get("unchanged") is False:
            reasons.append("observation_changed_during_capture")
        if boundary.get("target_repo_modified") is True:
            reasons.append("target_repo_worktree_changed_during_capture")
        rows.append(
            {
                "project_id": project_id,
                "required": required,
                "available": available,
                "path": _selected_relative_path(resolution),
                "schema_version": status.get("schema_version"),
                "observed_at": status.get("observed_at") or observed_at,
                "branch": status.get("branch"),
                "head_revision": status.get("head_revision"),
                "worktree_state": _nested(status, ["worktree", "state"]) or "unknown",
                "before_head_revision": signature_before.get("head_revision"),
                "after_head_revision": signature_after.get("head_revision"),
                "before_worktree_state": _nested(signature_before, ["worktree", "state"]),
                "after_worktree_state": _nested(signature_after, ["worktree", "state"]),
                "upstream": _nested(status, ["remote_parity", "tracking_ref"]),
                "remote_parity": _normalize_remote_parity(status.get("remote_parity")),
                "observation_unchanged": target_observation.get("unchanged"),
                "target_repo_modified": boundary.get("target_repo_modified"),
                "before_sha256": target_observation.get("sha256_before"),
                "after_sha256": target_observation.get("sha256_after"),
                "reason_codes": sorted(set(reasons)),
            }
        )
    return sorted(rows, key=lambda item: item["project_id"])


def _live_observation_source(
    project: dict[str, Any],
    *,
    assessed_at: str,
    threshold_seconds: int,
    authority_allows_current_claim: bool,
) -> dict[str, Any]:
    available = project["available"]
    if not available:
        reason = "required_project_missing" if project["required"] else "optional_project_missing"
        return _missing_source_row(
            project_id=project["project_id"],
            source_id=f"{project['project_id']}.live_status_observation",
            source_kind="live_project_observation",
            required=project["required"],
            source_path=f"git-observation:{project.get('path') or '<redacted>'}",
            assessed_at=assessed_at,
            reason_code=reason,
            observed_revision=None,
        )

    source_payload = _live_source_payload(project)
    return _evaluated_source_row(
        project_id=project["project_id"],
        source_id=f"{project['project_id']}.live_status_observation",
        source_kind="live_project_observation",
        required=project["required"],
        availability="available",
        schema_version=project.get("schema_version"),
        source_path=f"git-observation:{project.get('path') or '<redacted>'}",
        content_sha256=canonical_sha256(source_payload),
        generated_at=None,
        observed_at=project.get("observed_at"),
        timestamp_field="observed_at",
        source_revision=project.get("head_revision"),
        observed_revision=project.get("head_revision"),
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
        authority_allows_current_claim=authority_allows_current_claim,
        observation_clean=project.get("worktree_state") == "clean",
        observation_stable=(
            project.get("observation_unchanged") is True
            and project.get("target_repo_modified") is False
        ),
        extra_reason_codes=project.get("reason_codes", []),
    )


def _tracked_source(
    config: dict[str, Any],
    *,
    repo_root: Path,
    project: dict[str, Any] | None,
    assessed_at: str,
    threshold_seconds: int,
    authority_allows_current_claim: bool,
) -> dict[str, Any]:
    observed_revision = project.get("head_revision") if project else None
    try:
        path = _resolve_contained_file(repo_root, config["path"], contract="source")
    except EvidenceFreshnessError as exc:
        reason = "required_source_missing" if config["required"] else "optional_source_missing"
        if "escapes repository root" in str(exc):
            reason = "source_path_outside_repository"
        return _missing_source_row(
            project_id=config["project_id"],
            source_id=config["source_id"],
            source_kind=config["source_kind"],
            required=config["required"],
            source_path=config["path"],
            assessed_at=assessed_at,
            reason_code=reason,
            observed_revision=observed_revision,
        )
    payload = path.read_bytes()
    try:
        data = _parse_strict_json_bytes(
            payload,
            path=path,
            contract=f"source {config['source_id']}",
        )
    except EvidenceFreshnessError as exc:
        reason = "source_json_duplicate_key" if "duplicate JSON key" in str(exc) else "source_json_invalid"
        return _invalid_source_row(
            project_id=config["project_id"],
            source_id=config["source_id"],
            source_kind=config["source_kind"],
            required=config["required"],
            source_path=config["path"],
            content_sha256=hashlib.sha256(payload).hexdigest(),
            assessed_at=assessed_at,
            reason_code=reason,
            observed_revision=observed_revision,
        )
    schema_version = _nested(data, config["schema_path"])
    timestamp = _nested(data, config["timestamp_path"])
    source_revision = _nested(data, config["revision_path"])
    generated_at = timestamp if config["timestamp_kind"] == "generated_at" else None
    observed_at = timestamp if config["timestamp_kind"] == "observed_at" else None
    observation_clean = bool(project and project.get("worktree_state") == "clean")
    observation_stable = bool(
        project
        and project.get("observation_unchanged") is True
        and project.get("target_repo_modified") is False
    )
    return _evaluated_source_row(
        project_id=config["project_id"],
        source_id=config["source_id"],
        source_kind=config["source_kind"],
        required=config["required"],
        availability="available",
        schema_version=schema_version if isinstance(schema_version, str) else None,
        source_path=config["path"],
        content_sha256=canonical_sha256(data),
        generated_at=generated_at,
        observed_at=observed_at,
        timestamp_field=config["timestamp_kind"],
        source_revision=source_revision,
        observed_revision=observed_revision,
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
        authority_allows_current_claim=authority_allows_current_claim,
        observation_clean=observation_clean,
        observation_stable=observation_stable,
        extra_reason_codes=[] if project else ["project_observation_missing"],
    )


def _evaluated_source_row(
    *,
    project_id: str,
    source_id: str,
    source_kind: str,
    required: bool,
    availability: str,
    schema_version: str | None,
    source_path: str | None,
    content_sha256: str | None,
    generated_at: Any,
    observed_at: Any,
    timestamp_field: str,
    source_revision: Any,
    observed_revision: Any,
    assessed_at: str,
    threshold_seconds: int,
    authority_allows_current_claim: bool,
    observation_clean: bool,
    observation_stable: bool,
    extra_reason_codes: Iterable[str],
) -> dict[str, Any]:
    timestamp = observed_at if timestamp_field == "observed_at" else generated_at
    temporal = evaluate_temporal(
        timestamp,
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
    )
    revision = evaluate_revision(source_revision, observed_revision)
    if temporal["temporal_state"] == "stale" or revision["revision_binding_state"] == "mismatch":
        freshness_state = "stale"
    elif temporal["temporal_state"] == "fresh" and revision["revision_binding_state"] == "match":
        freshness_state = "fresh"
    else:
        freshness_state = "unknown"

    reasons = list(temporal["reason_codes"]) + list(revision["reason_codes"])
    reasons.extend(extra_reason_codes)
    if not isinstance(schema_version, str) or not schema_version:
        reasons.append("source_schema_missing")
    if not observation_clean:
        reasons.append("worktree_not_clean_or_unknown")
    if not observation_stable:
        reasons.append("observation_stability_unconfirmed")
    if not authority_allows_current_claim:
        reasons.append("receipt_not_authoritative_for_live_state")
    eligible = bool(
        availability == "available"
        and freshness_state == "fresh"
        and revision["revision_binding_state"] == "match"
        and isinstance(schema_version, str)
        and bool(schema_version)
        and observation_clean
        and observation_stable
        and authority_allows_current_claim
    )
    return {
        "project_id": project_id,
        "source_id": source_id,
        "source_kind": source_kind,
        "required": required,
        "availability": availability,
        "schema_version": schema_version,
        "source_path": redact_path(source_path),
        "content_sha256": content_sha256,
        "hash_basis": HASH_BASIS,
        "generated_at": generated_at if isinstance(generated_at, str) else None,
        "observed_at": observed_at if isinstance(observed_at, str) else None,
        "timestamp_field": timestamp_field,
        "assessed_at": assessed_at,
        "age_seconds": temporal["age_seconds"],
        "fresh_through": temporal["fresh_through"],
        "temporal_state": temporal["temporal_state"],
        "source_revision": revision["source_revision"],
        "observed_revision": revision["observed_revision"],
        "revision_binding_state": revision["revision_binding_state"],
        "freshness_state": freshness_state,
        "reason_codes": sorted(set(reasons)),
        "current_state_claim_eligible": eligible,
        "authority_classification": AUTHORITY_CLASSIFICATION,
    }


def _missing_source_row(
    *,
    project_id: str,
    source_id: str,
    source_kind: str,
    required: bool,
    source_path: str | None,
    assessed_at: str,
    reason_code: str,
    observed_revision: str | None,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "source_id": source_id,
        "source_kind": source_kind,
        "required": required,
        "availability": "missing",
        "schema_version": None,
        "source_path": redact_path(source_path),
        "content_sha256": None,
        "hash_basis": HASH_BASIS,
        "generated_at": None,
        "observed_at": None,
        "timestamp_field": None,
        "assessed_at": assessed_at,
        "age_seconds": None,
        "fresh_through": None,
        "temporal_state": "unknown",
        "source_revision": None,
        "observed_revision": observed_revision,
        "revision_binding_state": "unknown",
        "freshness_state": "unknown",
        "reason_codes": [reason_code],
        "current_state_claim_eligible": False,
        "authority_classification": AUTHORITY_CLASSIFICATION,
    }


def _invalid_source_row(
    *,
    project_id: str,
    source_id: str,
    source_kind: str,
    required: bool,
    source_path: str | None,
    content_sha256: str,
    assessed_at: str,
    reason_code: str,
    observed_revision: str | None,
) -> dict[str, Any]:
    row = _missing_source_row(
        project_id=project_id,
        source_id=source_id,
        source_kind=source_kind,
        required=required,
        source_path=source_path,
        assessed_at=assessed_at,
        reason_code=reason_code,
        observed_revision=observed_revision,
    )
    row["availability"] = "invalid_contract"
    row["content_sha256"] = content_sha256
    row["hash_basis"] = RAW_HASH_BASIS
    return row


def _summary(projects: list[dict[str, Any]], sources: list[dict[str, Any]]) -> dict[str, Any]:
    project_counts = {
        "observed": sum(1 for item in projects if item["available"]),
        "missing_required": sum(
            1 for item in projects if item["required"] and not item["available"]
        ),
        "missing_optional": sum(
            1 for item in projects if not item["required"] and not item["available"]
        ),
        "total": len(projects),
    }
    source_counts = {
        state: sum(1 for item in sources if item["freshness_state"] == state)
        for state in ("fresh", "stale", "unknown")
    }
    source_counts["total"] = len(sources)
    eligible = sum(1 for item in sources if item["current_state_claim_eligible"])
    required_missing = sum(
        1
        for item in sources
        if item["required"] and item["availability"] == "missing"
    )
    required_invalid = sum(
        1
        for item in sources
        if item["required"] and item["availability"] == "invalid_contract"
    )
    return {
        "project_counts": project_counts,
        "source_counts": source_counts,
        "current_state_claim_eligible": {
            "eligible": eligible,
            "ineligible": len(sources) - eligible,
        },
        "required_missing": required_missing,
        "required_invalid": required_invalid,
    }


def _live_source_payload(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": project.get("schema_version"),
        "project_id": project["project_id"],
        "observed_at": project.get("observed_at"),
        "branch": project.get("branch"),
        "head_revision": project.get("head_revision"),
        "worktree_state": project.get("worktree_state"),
        "before_head_revision": project.get("before_head_revision"),
        "after_head_revision": project.get("after_head_revision"),
        "before_worktree_state": project.get("before_worktree_state"),
        "after_worktree_state": project.get("after_worktree_state"),
        "upstream": project.get("upstream"),
        "remote_parity": project.get("remote_parity"),
        "observation_unchanged": project.get("observation_unchanged"),
        "target_repo_modified": project.get("target_repo_modified"),
        "before_sha256": project.get("before_sha256"),
        "after_sha256": project.get("after_sha256"),
    }


def _capture_id(
    *,
    policy_id: Any,
    policy_sha256: Any,
    assessed_at: Any,
    observation_mode: Any,
    tracked_example: bool,
    projects: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> str:
    capture_seed = {
        "policy_id": policy_id,
        "policy_sha256": policy_sha256,
        "assessed_at": assessed_at,
        "observation_mode": observation_mode,
        "tracked_example": tracked_example,
        "projects": projects,
        "sources": sources,
    }
    return "efr-" + canonical_sha256(capture_seed)[:20]


def _read_strict_json(path: Path, *, contract: str) -> Any:
    try:
        payload = path.read_bytes()
    except FileNotFoundError as exc:
        raise EvidenceFreshnessError(f"{contract} not found: {path}") from exc
    return _parse_strict_json_bytes(payload, path=path, contract=contract)


def _parse_strict_json_bytes(payload: bytes, *, path: Path, contract: str) -> Any:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise EvidenceFreshnessError(f"{contract} is not UTF-8: {path}") from exc
    try:
        return json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except json.JSONDecodeError as exc:
        raise EvidenceFreshnessError(f"{contract} is not valid JSON: {path}: {exc}") from exc


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceFreshnessError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _resolve_contained_file(root: Path, relative_path: str, *, contract: str) -> Path:
    candidate = root / relative_path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise EvidenceFreshnessError(
            f"{contract} path escapes repository root: {relative_path}"
        ) from exc
    if not resolved.is_file():
        raise EvidenceFreshnessError(f"{contract} not found: {relative_path}")
    return resolved


def _parse_assessment_time(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceFreshnessError(f"{field} must be a timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceFreshnessError(f"{field} is malformed: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceFreshnessError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _temporal_unknown(reason: str) -> dict[str, Any]:
    return {
        "temporal_state": "unknown",
        "age_seconds": None,
        "fresh_through": None,
        "reason_codes": [reason],
    }


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _utc_now_iso() -> str:
    return _format_datetime(datetime.now(timezone.utc))


def _required_id(data: dict[str, Any], key: str, *, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise EvidenceFreshnessError(f"{context}.{key} must be a stable lowercase ID")
    return value


def _optional_id(value: Any, *, default: str, context: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise EvidenceFreshnessError(f"{context} must be a stable lowercase ID")
    return value


def _required_relative_path(data: dict[str, Any], key: str, *, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceFreshnessError(f"{context}.{key} must be a relative path")
    normalized = value.strip().replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if (
        normalized.startswith(("/", "~/", "//"))
        or _WINDOWS_ABSOLUTE_RE.match(value)
        or ".." in parts
    ):
        raise EvidenceFreshnessError(f"{context}.{key} must stay inside the repository")
    return normalized


def _validate_locator(value: Any, context: str) -> list[str | int]:
    if not isinstance(value, list) or not value:
        raise EvidenceFreshnessError(f"{context} must be a non-empty list")
    result: list[str | int] = []
    for part in value:
        if isinstance(part, bool) or not isinstance(part, (str, int)):
            raise EvidenceFreshnessError(f"{context} contains an invalid path component")
        if isinstance(part, str) and not part:
            raise EvidenceFreshnessError(f"{context} contains an empty path component")
        if isinstance(part, int) and part < 0:
            raise EvidenceFreshnessError(f"{context} contains a negative list index")
        result.append(part)
    return result


def _nested(value: Any, path: Iterable[str | int]) -> Any:
    current = value
    for part in path:
        if isinstance(part, int):
            if not isinstance(current, list) or part >= len(current):
                return None
            current = current[part]
        else:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
    return current


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _string_list(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise EvidenceFreshnessError(f"{context}.reason_codes must be a list of strings")
    return sorted(set(value))


def _normalize_remote_parity(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    return {
        "status": source.get("status", "unknown"),
        "ahead": source.get("ahead"),
        "behind": source.get("behind"),
        "tracking_ref": source.get("tracking_ref"),
        "evidence_basis": REMOTE_PARITY_BASIS,
        "fetch_performed": False,
    }


def _selected_relative_path(resolution: dict[str, Any]) -> str | None:
    selected = resolution.get("selected")
    if isinstance(selected, str):
        return selected.replace("\\", "/")
    candidates = resolution.get("candidates")
    if isinstance(candidates, list) and candidates:
        candidate = candidates[0]
        if isinstance(candidate, dict) and isinstance(candidate.get("candidate"), str):
            return candidate["candidate"].replace("\\", "/")
    return None


def _is_unredacted_absolute_path(value: str) -> bool:
    candidate = value.split(":", 1)[1] if value.startswith("git-observation:") else value
    if candidate.startswith("<redacted-absolute>/"):
        return False
    return bool(
        _WINDOWS_ABSOLUTE_RE.match(candidate)
        or candidate.startswith("\\\\")
        or candidate.startswith("/")
    )


def _fallback_project_id(project: dict[str, Any], index: int) -> str:
    adapter_path = project.get("adapter_path")
    if isinstance(adapter_path, str):
        stem = Path(adapter_path).stem.lower()
        if _ID_RE.fullmatch(stem):
            return stem
    return f"unknown-project-{index}"


def _short_hash(value: Any) -> str:
    return value[:12] if isinstance(value, str) else "unknown"


def _bool_text(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return "unknown"


def _md(value: Any) -> str:
    if value is None:
        return "unknown"
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
