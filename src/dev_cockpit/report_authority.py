"""Build and verify source-bound supervision report authority envelopes."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

from .evidence_freshness import (
    DEFAULT_THRESHOLD_SECONDS,
    TEMPORAL_BOUNDARY,
    evaluate_revision,
    evaluate_temporal,
)
from .report_normalizer import normalize_report
from .supervision_packet import (
    SupervisionPacketError,
    load_manifest,
    load_packet_with_manifest,
)


SCHEMA_VERSION = "supervision_report_authority_envelope.v1"
PRODUCER = "dev_cockpit.report_authority"
DEFAULT_ARTIFACT_ID = "h3-report-authority-envelope-v1"
SOURCE_HASH_BASIS = "canonical_utf8_lf_sha256_v1"
CONTENT_HASH_BASIS = "raw_bytes_sha256_v1"
AUTHENTIC_EVIDENCE_CLASS = "authentic_owner_authorized_point_in_time_report"
AUTHENTIC_AUTHORITY_BASIS = "owner_authorized_current_checkout_observation"
H2_PERMISSION_SCOPE = "allowed_for_DevCockpitCore_H2_only"
H3_CURRENT_PERMISSION_SCOPE = "allowed_for_DevCockpitCore_H3_current_claim"

ROOT_KEYS = frozenset(
    {
        "artifact_id",
        "assessment",
        "authority",
        "bindings",
        "identity",
        "observation",
        "producer",
        "report",
        "schema_version",
        "scope_boundary",
    }
)
IDENTITY_KEYS = frozenset(
    {"task_id", "project_key", "thread_id", "lane_id", "slice_id", "artifact_id"}
)
BINDINGS_KEYS = frozenset({"source_report", "manifest", "packet"})
BINDING_KEYS = frozenset({"path", "content_sha256", "hash_basis"})
REPORT_KEYS = frozenset(
    {
        "source_revision",
        "observed_at",
        "evidence_class",
        "authority_basis",
        "observer_permission_scope",
    }
)
OBSERVATION_KEYS = frozenset(
    {
        "state",
        "observed_revision",
        "reobserved_at",
        "actual",
        "clean",
        "stable",
        "authorization_scope",
    }
)
ASSESSMENT_KEYS = frozenset(
    {"assessed_at", "threshold_seconds", "temporal_boundary"}
)
AUTHORITY_KEYS = frozenset(
    {
        "authentic_owner_attached_point_in_time_evidence",
        "transport_source_binding_state",
        "permission_state",
        "temporal_state",
        "revision_binding_state",
        "provenance_authenticity_state",
        "current_claim_eligibility",
        "live_coverage",
        "reason_codes",
    }
)
SCOPE_KEYS = frozenset(
    {
        "observer_only",
        "non_executable",
        "executable",
        "sibling_repository_writeback",
        "target_repository_writeback",
        "execution_schedule",
        "live_monitoring",
    }
)
CURRENT_OBSERVATION_INPUT_KEYS = frozenset(
    {
        "observed_revision",
        "reobserved_at",
        "actual",
        "clean",
        "stable",
        "authorization_scope",
    }
)
SCOPE_BOUNDARY = {
    "observer_only": True,
    "non_executable": True,
    "executable": False,
    "sibling_repository_writeback": False,
    "target_repository_writeback": False,
    "execution_schedule": False,
    "live_monitoring": False,
}

_REPORT_FIELD_RE = re.compile(
    r"^\s*-\s+(?P<key>[a-z][a-z0-9_]*):\s+`?(?P<value>[^`\r\n]+?)`?\s*$",
    re.MULTILINE,
)
_FULL_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AuthorityEnvelopeError(ValueError):
    """Raised when an authority envelope or its source binding is invalid."""


def build_authority_envelope(
    *,
    manifest_path: str | Path,
    packet_path: str | Path,
    repo_root: str | Path = ".",
    assessed_at: str,
    threshold_seconds: int = DEFAULT_THRESHOLD_SECONDS,
    artifact_id: str = DEFAULT_ARTIFACT_ID,
    current_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Rebuild authority solely from bound sources and trusted assessment inputs."""

    root = Path(repo_root).resolve()
    assessed_at = _require_aware_timestamp(assessed_at, "assessed_at")
    if type(threshold_seconds) is not int or threshold_seconds <= 0:
        raise AuthorityEnvelopeError("threshold_seconds must be a positive integer")
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        raise AuthorityEnvelopeError("artifact_id must be a non-empty string")

    manifest_full = _resolve_input(root, manifest_path, "manifest_path")
    packet_full = _resolve_input(root, packet_path, "packet_path")
    try:
        manifest = load_manifest(manifest_full)
        packet = load_packet_with_manifest(
            packet_full,
            manifest_full,
            repo_root=root,
        )
    except (OSError, SupervisionPacketError) as exc:
        raise AuthorityEnvelopeError(f"source-bound packet verification failed: {exc}") from exc

    entries = manifest["reports"]
    tasks = [
        *packet["global_attention_queue"],
        *packet["closed_or_informational"],
    ]
    if len(entries) != 1 or len(tasks) != 1:
        raise AuthorityEnvelopeError(
            "authority envelope v1 requires exactly one manifest report and packet task"
        )
    entry = entries[0]
    task = tasks[0]
    source_rel = str(entry["report_path"])
    source_full = _resolve_input(root, source_rel, "manifest.reports[0].report_path")
    source_payload = source_full.read_bytes()
    source_text, canonical_payload = _canonical_report_payload(source_payload, source_rel)
    source_hash = sha256(canonical_payload).hexdigest()
    if source_hash != entry["content_sha256"]:
        raise AuthorityEnvelopeError("source report canonical hash does not match manifest")

    claims = _source_report_claims(source_text)
    normalization = normalize_report(
        source_text,
        input_path=source_rel,
        input_kind="authority_envelope_bound_agent_report",
        generated_at=assessed_at,
    )
    routing = normalization["routing"]
    source_revision = claims["source_revision"].lower()
    if source_revision != str(routing.get("base_revision") or "").lower():
        raise AuthorityEnvelopeError(
            "source report revision conflicts with canonical ROUTE base_revision"
        )
    if claims["evidence_class"] != entry["evidence_class"]:
        raise AuthorityEnvelopeError("source report evidence_class conflicts with manifest")
    if claims["authority_basis"] != entry["authority_basis"]:
        raise AuthorityEnvelopeError("source report authority_basis conflicts with manifest")
    if source_rel != task["source_report_path"] or source_hash != task["source_report_sha256"]:
        raise AuthorityEnvelopeError("source report binding conflicts with packet task")

    identity = {
        field: task[field]
        for field in (
            "task_id",
            "project_key",
            "thread_id",
            "lane_id",
            "slice_id",
            "artifact_id",
        )
    }
    observation = _normalize_current_observation(current_observation)
    permission_scope = claims["observer_only_permission"]
    evaluation = evaluate_authority_conditions(
        report_observed_at=claims["observed_at"],
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
        source_revision=source_revision,
        observed_revision=observation["observed_revision"],
        reobserved_at=observation["reobserved_at"],
        permission_scope=permission_scope,
        observation_actual=observation["actual"],
        observation_clean=observation["clean"],
        observation_stable=observation["stable"],
        bindings_match=True,
        identity_match=True,
        provenance_verified=True,
        observer_only=True,
        non_executable=True,
        evidence_class=claims["evidence_class"],
        authority_basis=claims["authority_basis"],
    )

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "producer": PRODUCER,
        "identity": identity,
        "bindings": {
            "source_report": {
                "path": source_rel,
                "content_sha256": source_hash,
                "hash_basis": SOURCE_HASH_BASIS,
            },
            "manifest": {
                "path": _display_path(root, manifest_full),
                "content_sha256": sha256(manifest_full.read_bytes()).hexdigest(),
                "hash_basis": CONTENT_HASH_BASIS,
            },
            "packet": {
                "path": _display_path(root, packet_full),
                "content_sha256": sha256(packet_full.read_bytes()).hexdigest(),
                "hash_basis": CONTENT_HASH_BASIS,
            },
        },
        "report": {
            "source_revision": source_revision,
            "observed_at": claims["observed_at"],
            "evidence_class": claims["evidence_class"],
            "authority_basis": claims["authority_basis"],
            "observer_permission_scope": permission_scope,
        },
        "observation": observation,
        "assessment": {
            "assessed_at": assessed_at,
            "threshold_seconds": threshold_seconds,
            "temporal_boundary": TEMPORAL_BOUNDARY,
        },
        "authority": evaluation,
        "scope_boundary": dict(SCOPE_BOUNDARY),
    }
    return validate_authority_envelope(envelope)


def evaluate_authority_conditions(
    *,
    report_observed_at: Any,
    assessed_at: str,
    threshold_seconds: int,
    source_revision: Any,
    observed_revision: Any,
    reobserved_at: Any,
    permission_scope: Any,
    observation_actual: bool,
    observation_clean: bool,
    observation_stable: bool,
    bindings_match: bool,
    identity_match: bool,
    provenance_verified: bool,
    observer_only: bool,
    non_executable: bool,
    evidence_class: Any,
    authority_basis: Any,
) -> dict[str, Any]:
    """Pure conservative predicate separating authenticity, current use, and live use."""

    temporal = evaluate_temporal(
        report_observed_at,
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
    )
    revision = evaluate_revision(source_revision, observed_revision)
    reobservation_temporal = evaluate_temporal(
        reobserved_at,
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
    )
    permission_allows_current = permission_scope == H3_CURRENT_PERMISSION_SCOPE
    authentic = bool(
        bindings_match
        and identity_match
        and provenance_verified
        and evidence_class == AUTHENTIC_EVIDENCE_CLASS
        and authority_basis == AUTHENTIC_AUTHORITY_BASIS
    )
    reasons = [*temporal["reason_codes"], *revision["reason_codes"]]
    if bindings_match:
        reasons.append("source_manifest_packet_binding_valid")
    else:
        reasons.append("source_manifest_packet_binding_invalid")
    if identity_match:
        reasons.append("report_packet_identity_match")
    else:
        reasons.append("report_packet_identity_mismatch")
    if provenance_verified:
        reasons.append("provenance_verified")
    else:
        reasons.append("provenance_unverified")
    if permission_scope == H2_PERMISSION_SCOPE:
        reasons.extend(("permission_scope_h2_only", "permission_insufficient_for_h3_current_claim"))
    elif permission_allows_current:
        reasons.append("permission_explicitly_allows_h3_current_claim")
    else:
        reasons.append("permission_insufficient_for_h3_current_claim")
    if not observation_actual:
        reasons.append("authorized_current_source_reobservation_absent")
    else:
        reasons.extend(reobservation_temporal["reason_codes"])
    if not observation_clean:
        reasons.append("worktree_not_clean_or_unknown")
    if not observation_stable:
        reasons.append("observation_stability_unconfirmed")
    if observer_only and non_executable:
        reasons.append("observer_only_non_executable")
    else:
        reasons.append("observer_scope_boundary_invalid")
    reasons.append("point_in_time_report_does_not_establish_live_coverage")

    eligible = bool(
        bindings_match
        and identity_match
        and permission_allows_current
        and temporal["temporal_state"] == "fresh"
        and revision["revision_binding_state"] == "match"
        and observation_actual
        and reobservation_temporal["temporal_state"] == "fresh"
        and observation_clean
        and observation_stable
        and observer_only
        and non_executable
        and provenance_verified
        and authentic
    )
    permission_state = (
        "sufficient_for_h3_current_claim"
        if permission_allows_current
        else "insufficient_h2_only"
        if permission_scope == H2_PERMISSION_SCOPE
        else "insufficient"
    )
    return {
        "authentic_owner_attached_point_in_time_evidence": authentic,
        "transport_source_binding_state": "valid" if bindings_match else "invalid",
        "permission_state": permission_state,
        "temporal_state": temporal["temporal_state"],
        "revision_binding_state": revision["revision_binding_state"],
        "provenance_authenticity_state": "verified" if provenance_verified else "unverified",
        "current_claim_eligibility": eligible,
        "live_coverage": False,
        "reason_codes": sorted(set(reasons)),
    }


def load_authority_envelope(
    envelope_path: str | Path,
    *,
    manifest_path: str | Path,
    packet_path: str | Path,
    repo_root: str | Path = ".",
    assessed_at: str,
    threshold_seconds: int = DEFAULT_THRESHOLD_SECONDS,
    current_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Strictly load an envelope and compare it to a complete source reprojection."""

    root = Path(repo_root).resolve()
    envelope_full = _resolve_input(root, envelope_path, "envelope_path")
    stored = validate_authority_envelope(
        _read_strict_json(envelope_full, label="authority envelope")
    )
    expected = build_authority_envelope(
        manifest_path=manifest_path,
        packet_path=packet_path,
        repo_root=root,
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
        artifact_id=DEFAULT_ARTIFACT_ID,
        current_observation=current_observation,
    )
    difference = _first_json_difference(expected, stored)
    if difference is not None:
        raise AuthorityEnvelopeError(f"source-bound authority envelope mismatch at {difference}")
    return stored


def validate_authority_envelope(value: Any) -> dict[str, Any]:
    envelope = _require_exact_object(value, ROOT_KEYS, "envelope")
    identity = _require_exact_object(envelope.get("identity"), IDENTITY_KEYS, "envelope.identity")
    bindings = _require_exact_object(envelope.get("bindings"), BINDINGS_KEYS, "envelope.bindings")
    report = _require_exact_object(envelope.get("report"), REPORT_KEYS, "envelope.report")
    observation = _require_exact_object(
        envelope.get("observation"), OBSERVATION_KEYS, "envelope.observation"
    )
    assessment = _require_exact_object(
        envelope.get("assessment"), ASSESSMENT_KEYS, "envelope.assessment"
    )
    authority = _require_exact_object(
        envelope.get("authority"), AUTHORITY_KEYS, "envelope.authority"
    )
    scope = _require_exact_object(
        envelope.get("scope_boundary"), SCOPE_KEYS, "envelope.scope_boundary"
    )

    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise AuthorityEnvelopeError(f"envelope.schema_version must be {SCHEMA_VERSION!r}")
    if envelope.get("artifact_id") != DEFAULT_ARTIFACT_ID:
        raise AuthorityEnvelopeError("envelope.artifact_id is invalid")
    if envelope.get("producer") != PRODUCER:
        raise AuthorityEnvelopeError("envelope.producer is invalid")
    for field in IDENTITY_KEYS:
        _require_nonempty_string(identity, field, "envelope.identity")
    for name in BINDINGS_KEYS:
        binding = _require_exact_object(
            bindings.get(name), BINDING_KEYS, f"envelope.bindings.{name}"
        )
        path = _require_nonempty_string(binding, "path", f"envelope.bindings.{name}")
        _validate_repo_relative_path(path, f"envelope.bindings.{name}.path")
        content_hash = _require_nonempty_string(
            binding, "content_sha256", f"envelope.bindings.{name}"
        )
        if not _SHA256_RE.fullmatch(content_hash):
            raise AuthorityEnvelopeError(
                f"envelope.bindings.{name}.content_sha256 must be 64 lowercase hex characters"
            )
        expected_basis = SOURCE_HASH_BASIS if name == "source_report" else CONTENT_HASH_BASIS
        if binding.get("hash_basis") != expected_basis:
            raise AuthorityEnvelopeError(f"envelope.bindings.{name}.hash_basis is invalid")

    for field in REPORT_KEYS:
        _require_nonempty_string(report, field, "envelope.report")
    if not _FULL_REVISION_RE.fullmatch(report["source_revision"]):
        raise AuthorityEnvelopeError("envelope.report.source_revision must be a full revision")
    _require_aware_timestamp(report["observed_at"], "envelope.report.observed_at")

    if observation.get("state") not in {"not_reobserved", "actual_stable", "actual_unstable"}:
        raise AuthorityEnvelopeError("envelope.observation.state is invalid")
    for field in ("actual", "clean", "stable"):
        if type(observation.get(field)) is not bool:
            raise AuthorityEnvelopeError(f"envelope.observation.{field} must be boolean")
    for field in ("observed_revision", "reobserved_at", "authorization_scope"):
        item = observation.get(field)
        if item is not None and (not isinstance(item, str) or not item.strip()):
            raise AuthorityEnvelopeError(
                f"envelope.observation.{field} must be null or a non-empty string"
            )
    if observation["observed_revision"] is not None and not _FULL_REVISION_RE.fullmatch(
        observation["observed_revision"]
    ):
        raise AuthorityEnvelopeError(
            "envelope.observation.observed_revision must be null or a full revision"
        )
    if observation["reobserved_at"] is not None:
        _require_aware_timestamp(
            observation["reobserved_at"], "envelope.observation.reobserved_at"
        )

    _require_aware_timestamp(assessment.get("assessed_at"), "envelope.assessment.assessed_at")
    if type(assessment.get("threshold_seconds")) is not int or assessment["threshold_seconds"] <= 0:
        raise AuthorityEnvelopeError(
            "envelope.assessment.threshold_seconds must be a positive integer"
        )
    if assessment.get("temporal_boundary") != TEMPORAL_BOUNDARY:
        raise AuthorityEnvelopeError("envelope.assessment.temporal_boundary is invalid")

    for field in (
        "authentic_owner_attached_point_in_time_evidence",
        "current_claim_eligibility",
        "live_coverage",
    ):
        if type(authority.get(field)) is not bool:
            raise AuthorityEnvelopeError(f"envelope.authority.{field} must be boolean")
    if authority.get("transport_source_binding_state") not in {"valid", "invalid"}:
        raise AuthorityEnvelopeError(
            "envelope.authority.transport_source_binding_state is invalid"
        )
    if authority.get("permission_state") not in {
        "sufficient_for_h3_current_claim",
        "insufficient_h2_only",
        "insufficient",
    }:
        raise AuthorityEnvelopeError("envelope.authority.permission_state is invalid")
    if authority.get("temporal_state") not in {"fresh", "stale", "unknown"}:
        raise AuthorityEnvelopeError("envelope.authority.temporal_state is invalid")
    if authority.get("revision_binding_state") not in {"match", "mismatch", "unknown"}:
        raise AuthorityEnvelopeError("envelope.authority.revision_binding_state is invalid")
    if authority.get("provenance_authenticity_state") not in {"verified", "unverified"}:
        raise AuthorityEnvelopeError(
            "envelope.authority.provenance_authenticity_state is invalid"
        )
    reasons = authority.get("reason_codes")
    if (
        not isinstance(reasons, list)
        or any(not isinstance(reason, str) or not reason for reason in reasons)
        or reasons != sorted(set(reasons))
    ):
        raise AuthorityEnvelopeError(
            "envelope.authority.reason_codes must be sorted unique non-empty strings"
        )
    if authority.get("live_coverage") is not False:
        raise AuthorityEnvelopeError("envelope.authority.live_coverage must be false")
    if scope != SCOPE_BOUNDARY:
        raise AuthorityEnvelopeError("envelope.scope_boundary is invalid")
    return envelope


def dumps_authority_envelope(envelope: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(
        envelope,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ) + "\n"


def write_authority_envelope(
    envelope: dict[str, Any],
    path: str | Path,
    *,
    pretty: bool = False,
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        dumps_authority_envelope(envelope, pretty=pretty),
        encoding="utf-8",
        newline="\n",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a source-bound supervision report authority envelope."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--assessed-at", required=True)
    parser.add_argument("--threshold-seconds", type=int, default=DEFAULT_THRESHOLD_SECONDS)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        envelope = build_authority_envelope(
            manifest_path=args.manifest,
            packet_path=args.packet,
            repo_root=args.repo_root,
            assessed_at=args.assessed_at,
            threshold_seconds=args.threshold_seconds,
        )
        output = _resolve_cli_output(Path(args.repo_root), args.output)
        write_authority_envelope(envelope, output, pretty=args.pretty)
    except (OSError, AuthorityEnvelopeError) as exc:
        print(f"authority envelope error: {exc}", file=sys.stderr)
        return 2
    print(_display_path(Path(args.repo_root).resolve(), output))
    return 0


def _source_report_claims(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in _REPORT_FIELD_RE.finditer(text):
        key = match.group("key")
        if key not in {
            "source_revision",
            "observed_at",
            "evidence_class",
            "authority_basis",
            "observer_only_permission",
        }:
            continue
        value = match.group("value").strip()
        if key in found and found[key] != value:
            raise AuthorityEnvelopeError(f"conflicting source report field: {key}")
        found[key] = value
    required = {
        "source_revision",
        "observed_at",
        "evidence_class",
        "authority_basis",
        "observer_only_permission",
    }
    missing = sorted(required - set(found))
    if missing:
        raise AuthorityEnvelopeError(f"source report authority fields missing: {missing!r}")
    _require_aware_timestamp(found["observed_at"], "source report observed_at")
    if not _FULL_REVISION_RE.fullmatch(found["source_revision"].lower()):
        raise AuthorityEnvelopeError("source report source_revision must be a full revision")
    return found


def _normalize_current_observation(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {
            "state": "not_reobserved",
            "observed_revision": None,
            "reobserved_at": None,
            "actual": False,
            "clean": False,
            "stable": False,
            "authorization_scope": None,
        }
    observation = _require_exact_object(
        value,
        CURRENT_OBSERVATION_INPUT_KEYS,
        "current_observation",
    )
    for field in ("actual", "clean", "stable"):
        if type(observation.get(field)) is not bool:
            raise AuthorityEnvelopeError(f"current_observation.{field} must be boolean")
    observed_revision = observation.get("observed_revision")
    if not isinstance(observed_revision, str) or not _FULL_REVISION_RE.fullmatch(
        observed_revision.lower()
    ):
        raise AuthorityEnvelopeError(
            "current_observation.observed_revision must be a full revision"
        )
    reobserved_at = _require_aware_timestamp(
        observation.get("reobserved_at"), "current_observation.reobserved_at"
    )
    authorization_scope = observation.get("authorization_scope")
    if not isinstance(authorization_scope, str) or not authorization_scope:
        raise AuthorityEnvelopeError(
            "current_observation.authorization_scope must be a non-empty string"
        )
    actual = observation["actual"]
    stable = observation["stable"]
    return {
        "state": "actual_stable" if actual and stable else "actual_unstable",
        "observed_revision": observed_revision.lower(),
        "reobserved_at": reobserved_at,
        "actual": actual,
        "clean": observation["clean"],
        "stable": stable,
        "authorization_scope": authorization_scope,
    }


def _canonical_report_payload(payload: bytes, report_path: str) -> tuple[str, bytes]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuthorityEnvelopeError(f"source report must be UTF-8: {report_path}") from exc
    canonical = text.replace("\r\n", "\n")
    if "\r" in canonical:
        raise AuthorityEnvelopeError(
            f"source report contains unsupported bare carriage return: {report_path}"
        )
    return canonical, canonical.encode("utf-8")


def _read_strict_json(path: Path, *, label: str) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise AuthorityEnvelopeError(f"{label} not found: {path}") from exc
    try:
        value = json.loads(text, object_pairs_hook=_collect_pairs)
    except json.JSONDecodeError as exc:
        raise AuthorityEnvelopeError(f"invalid {label} JSON {path}: {exc}") from exc
    _reject_duplicate_tree(value)
    return _plain_json_value(value)


class _ParsedObject(dict[str, Any]):
    def __init__(self) -> None:
        super().__init__()
        self.duplicate_keys: list[str] = []


def _collect_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result = _ParsedObject()
    for key, value in pairs:
        if key in result:
            result.duplicate_keys.append(key)
        result[key] = value
    return result


def _reject_duplicate_tree(value: Any, path: str = "$") -> None:
    if isinstance(value, _ParsedObject):
        if value.duplicate_keys:
            key = value.duplicate_keys[0]
            raise AuthorityEnvelopeError(f"duplicate JSON key at {path}.{key}")
        for key, item in value.items():
            _reject_duplicate_tree(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_duplicate_tree(item, f"{path}[{index}]")


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain_json_value(item) for item in value]
    return value


def _require_exact_object(
    value: Any,
    expected_keys: frozenset[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuthorityEnvelopeError(f"{label} must be an object")
    actual = set(value)
    missing = sorted(expected_keys - actual)
    unexpected = sorted(actual - expected_keys)
    if missing or unexpected:
        raise AuthorityEnvelopeError(
            f"{label} keys are invalid; missing keys: {missing!r}; "
            f"unexpected keys: {unexpected!r}"
        )
    return value


def _require_nonempty_string(value: dict[str, Any], field: str, label: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise AuthorityEnvelopeError(f"{label}.{field} must be a non-empty string")
    return item


def _require_aware_timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthorityEnvelopeError(f"{label} must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthorityEnvelopeError(
            f"{label} must be a timezone-aware ISO-8601 timestamp"
        ) from exc
    if parsed.utcoffset() is None:
        raise AuthorityEnvelopeError(f"{label} must include a timezone")
    return value.strip()


def _resolve_input(root: Path, value: str | Path, label: str) -> Path:
    path = Path(value)
    full = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        full.relative_to(root)
    except ValueError as exc:
        raise AuthorityEnvelopeError(f"{label} must resolve inside repository root") from exc
    return full


def _resolve_cli_output(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _display_path(root: Path, value: str | Path) -> str:
    path = Path(value).resolve()
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise AuthorityEnvelopeError("authority binding path must be repository-relative") from exc


def _validate_repo_relative_path(value: str, label: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise AuthorityEnvelopeError(
            f"{label} must be a repository-relative path without '..'"
        )


def _first_json_difference(expected: Any, actual: Any, path: str = "$") -> str | None:
    if type(expected) is not type(actual):
        return f"{path} (expected {type(expected).__name__}, got {type(actual).__name__})"
    if isinstance(expected, dict):
        if set(expected) != set(actual):
            return f"{path} (object keys differ)"
        for key in sorted(expected):
            child = _first_json_difference(expected[key], actual[key], f"{path}.{key}")
            if child is not None:
                return child
        return None
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path} (expected {len(expected)} items, got {len(actual)})"
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            child = _first_json_difference(expected_item, actual_item, f"{path}[{index}]")
            if child is not None:
                return child
        return None
    if expected != actual:
        return f"{path} (expected {expected!r}, got {actual!r})"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
