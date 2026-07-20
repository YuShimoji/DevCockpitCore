"""Build and verify observation-bound supervision authority envelopes V2."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .current_observation import (
    AUTHORIZATION_SCOPE,
    CurrentObservationError,
    load_current_observation_with_payload,
    normalize_repository_identity,
)
from .evidence_freshness import DEFAULT_THRESHOLD_SECONDS, TEMPORAL_BOUNDARY, evaluate_revision, evaluate_temporal
from .report_authority import (
    AUTHENTIC_AUTHORITY_BASIS,
    AUTHENTIC_EVIDENCE_CLASS,
    CONTENT_HASH_BASIS,
    DEFAULT_ARTIFACT_ID,
    H2_PERMISSION_SCOPE,
    H3_CURRENT_PERMISSION_SCOPE,
    SCOPE_BOUNDARY,
    SOURCE_HASH_BASIS,
    AuthorityEnvelopeError,
    _canonical_report_payload,
    _display_path,
    _first_json_difference,
    _read_strict_json,
    _require_aware_timestamp,
    _resolve_input,
    build_authority_envelope,
)
from .supervision_packet import SupervisionPacketError, load_manifest


SCHEMA_VERSION = "supervision_report_authority_envelope.v2"
PRODUCER = "dev_cockpit.report_authority"
CURRENT_OBSERVATION_HASH_BASIS = "raw_bytes_sha256_v1"

ROOT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "producer",
        "identity",
        "bindings",
        "report",
        "observation",
        "assessment",
        "authority",
        "provenance",
        "scope_boundary",
    }
)
IDENTITY_KEYS = frozenset(
    {"task_id", "project_key", "thread_id", "lane_id", "slice_id", "artifact_id"}
)
BINDINGS_KEYS = frozenset({"source_report", "manifest", "packet", "current_observation"})
BINDING_KEYS = frozenset({"path", "content_sha256", "hash_basis"})
OBSERVATION_BINDING_KEYS = frozenset(
    {"path", "content_sha256", "hash_basis", "artifact_id"}
)
REPORT_KEYS = frozenset(
    {
        "source_revision",
        "observed_at",
        "repository_identity",
        "evidence_class",
        "authority_basis",
        "observer_permission_scope",
    }
)
OBSERVATION_KEYS = frozenset(
    {
        "artifact_id",
        "project_key",
        "repository_identity",
        "authorization_scope",
        "first_observed_at",
        "reobserved_at",
        "before_head_revision",
        "after_head_revision",
        "before_worktree_sha256",
        "after_worktree_sha256",
        "actual",
        "clean",
        "stable",
    }
)
ASSESSMENT_KEYS = frozenset({"assessed_at", "threshold_seconds", "temporal_boundary"})
AUTHORITY_KEYS = frozenset(
    {
        "authentic_owner_attached_point_in_time_evidence",
        "transport_source_binding_state",
        "report_permission_state",
        "observation_authorization_state",
        "permission_conjunction_state",
        "report_temporal_state",
        "reobservation_temporal_state",
        "chronology_state",
        "revision_binding_state",
        "current_claim_eligibility",
        "live_coverage",
        "reason_codes",
    }
)
PROVENANCE_KEYS = frozenset(
    {
        "package_binding_state",
        "current_observation_receipt_state",
        "repository_project_revision_cross_binding_state",
        "overall_current_claim_provenance_state",
    }
)
SCOPE_KEYS = frozenset(SCOPE_BOUNDARY)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_FULL_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPORT_FIELD_RE = re.compile(
    r"^\s*-\s+(?P<key>[a-z][a-z0-9_]*):\s+`?(?P<value>[^`\r\n]+?)`?\s*$",
    re.MULTILINE,
)


def build_authority_envelope_v2(
    *,
    manifest_path: str | Path,
    packet_path: str | Path,
    current_observation_path: str | Path,
    repo_root: str | Path = ".",
    assessed_at: str,
    artifact_id: str,
    expected_observation_artifact_id: str,
    threshold_seconds: int = DEFAULT_THRESHOLD_SECONDS,
) -> dict[str, Any]:
    """Build V2 solely from a V1 source-bound package and a strict observation receipt."""

    root = Path(repo_root).resolve()
    _require_identifier(artifact_id, "artifact_id")
    if artifact_id == DEFAULT_ARTIFACT_ID:
        raise AuthorityEnvelopeError(
            "authority envelope v2 artifact_id must not reuse the H3 V1 package identity"
        )
    _require_identifier(
        expected_observation_artifact_id, "expected_observation_artifact_id"
    )
    if type(threshold_seconds) is not int or threshold_seconds <= 0:
        raise AuthorityEnvelopeError("threshold_seconds must be a positive integer")
    assessed_at = _require_aware_timestamp(assessed_at, "assessed_at")

    package = build_authority_envelope(
        manifest_path=manifest_path,
        packet_path=packet_path,
        repo_root=root,
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
    )
    observation_full = _resolve_input(
        root, current_observation_path, "current_observation_path"
    )
    try:
        receipt, observation_payload = load_current_observation_with_payload(
            observation_full
        )
    except (CurrentObservationError, OSError) as exc:
        raise AuthorityEnvelopeError(f"current observation verification failed: {exc}") from exc
    if receipt["artifact_id"] != expected_observation_artifact_id:
        raise AuthorityEnvelopeError("current observation artifact_id mismatch")

    manifest_full = _resolve_input(root, manifest_path, "manifest_path")
    packet_full = _resolve_input(root, packet_path, "packet_path")
    try:
        manifest = load_manifest(manifest_full)
    except (SupervisionPacketError, OSError) as exc:
        raise AuthorityEnvelopeError(f"manifest verification failed: {exc}") from exc
    if len(manifest["reports"]) != 1:
        raise AuthorityEnvelopeError("authority envelope v2 requires exactly one report")
    source_rel = str(manifest["reports"][0]["report_path"])
    source_full = _resolve_input(root, source_rel, "manifest.reports[0].report_path")
    source_text, _ = _canonical_report_payload(source_full.read_bytes(), source_rel)
    remote_values = {
        match["value"].strip()
        for match in _REPORT_FIELD_RE.finditer(source_text)
        if match["key"] == "repository_remote"
    }
    if not remote_values:
        raise AuthorityEnvelopeError("source report repository_remote is missing")
    if len(remote_values) != 1:
        raise AuthorityEnvelopeError("source report repository_remote conflicts")
    remote_value = remote_values.pop()
    try:
        report_repository_identity = normalize_repository_identity(remote_value)
    except CurrentObservationError as exc:
        raise AuthorityEnvelopeError(f"source report repository_remote is invalid: {exc}") from exc

    receipt_observation = receipt["observation"]
    before = receipt_observation["before"]
    after = receipt_observation["after"]
    derived = receipt_observation["derived"]
    report = {
        **package["report"],
        "repository_identity": report_repository_identity,
    }
    observation = {
        "artifact_id": receipt["artifact_id"],
        "project_key": receipt["project_key"],
        "repository_identity": receipt["repository"]["identity"],
        "authorization_scope": receipt["authorization"]["scope"],
        "first_observed_at": receipt_observation["first_observed_at"],
        "reobserved_at": receipt_observation["reobserved_at"],
        "before_head_revision": before["head_revision"],
        "after_head_revision": after["head_revision"],
        "before_worktree_sha256": before["worktree_sha256"],
        "after_worktree_sha256": after["worktree_sha256"],
        "actual": derived["actual"],
        "clean": derived["clean"],
        "stable": derived["stable"],
    }
    project_match = package["identity"]["project_key"] == receipt["project_key"]
    repository_match = report_repository_identity == receipt["repository"]["identity"]
    revision_match = report["source_revision"] == after["head_revision"]
    cross_binding_verified = project_match and repository_match and revision_match
    provenance = evaluate_provenance(
        package_binding_verified=True,
        current_observation_receipt_verified=True,
        repository_project_revision_cross_binding_verified=cross_binding_verified,
    )
    authority = evaluate_authority_conditions_v2(
        report_observed_at=report["observed_at"],
        reobserved_at=observation["reobserved_at"],
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
        source_revision=report["source_revision"],
        observed_revision=observation["after_head_revision"],
        report_permission_scope=report["observer_permission_scope"],
        observation_authorization_scope=observation["authorization_scope"],
        observation_actual=observation["actual"],
        observation_clean=observation["clean"],
        observation_stable=observation["stable"],
        package_binding_verified=True,
        observation_receipt_verified=True,
        cross_binding_verified=cross_binding_verified,
        observer_only=True,
        non_executable=True,
        evidence_class=report["evidence_class"],
        authority_basis=report["authority_basis"],
    )
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "producer": PRODUCER,
        "identity": dict(package["identity"]),
        "bindings": {
            **{name: dict(value) for name, value in package["bindings"].items()},
            "current_observation": {
                "path": _display_path(root, observation_full),
                "content_sha256": sha256(observation_payload).hexdigest(),
                "hash_basis": CURRENT_OBSERVATION_HASH_BASIS,
                "artifact_id": receipt["artifact_id"],
            },
        },
        "report": report,
        "observation": observation,
        "assessment": {
            "assessed_at": assessed_at,
            "threshold_seconds": threshold_seconds,
            "temporal_boundary": TEMPORAL_BOUNDARY,
        },
        "authority": authority,
        "provenance": provenance,
        "scope_boundary": dict(SCOPE_BOUNDARY),
    }
    return validate_authority_envelope_v2(
        envelope,
        expected_artifact_id=artifact_id,
        expected_observation_artifact_id=expected_observation_artifact_id,
    )


def evaluate_authority_conditions_v2(
    *,
    report_observed_at: Any,
    reobserved_at: Any,
    assessed_at: str,
    threshold_seconds: int,
    source_revision: Any,
    observed_revision: Any,
    report_permission_scope: Any,
    observation_authorization_scope: Any,
    observation_actual: bool,
    observation_clean: bool,
    observation_stable: bool,
    package_binding_verified: bool,
    observation_receipt_verified: bool,
    cross_binding_verified: bool,
    observer_only: bool,
    non_executable: bool,
    evidence_class: Any,
    authority_basis: Any,
) -> dict[str, Any]:
    """Evaluate current authority while keeping both authorization sources explicit."""

    report_temporal = evaluate_temporal(
        report_observed_at,
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
    )
    reobservation_temporal = evaluate_temporal(
        reobserved_at,
        assessed_at=assessed_at,
        threshold_seconds=threshold_seconds,
    )
    revision = evaluate_revision(source_revision, observed_revision)
    chronology_state, chronology_reasons = _evaluate_chronology(
        report_observed_at, reobserved_at, assessed_at
    )
    report_allowed = report_permission_scope == H3_CURRENT_PERMISSION_SCOPE
    observation_allowed = observation_authorization_scope == AUTHORIZATION_SCOPE
    permission_conjunction = report_allowed and observation_allowed
    overall_provenance = bool(
        package_binding_verified
        and observation_receipt_verified
        and cross_binding_verified
    )
    authentic = bool(
        package_binding_verified
        and evidence_class == AUTHENTIC_EVIDENCE_CLASS
        and authority_basis == AUTHENTIC_AUTHORITY_BASIS
    )

    reasons = [
        *(f"report_{reason}" for reason in report_temporal["reason_codes"]),
        *(f"reobservation_{reason}" for reason in reobservation_temporal["reason_codes"]),
        *revision["reason_codes"],
        *chronology_reasons,
    ]
    reasons.append(
        "source_manifest_packet_binding_valid"
        if package_binding_verified
        else "source_manifest_packet_binding_invalid"
    )
    reasons.append(
        "current_observation_receipt_valid"
        if observation_receipt_verified
        else "current_observation_receipt_invalid"
    )
    reasons.append(
        "repository_project_revision_cross_binding_valid"
        if cross_binding_verified
        else "repository_project_revision_cross_binding_invalid"
    )
    if report_allowed:
        reasons.append("report_permission_explicitly_allows_h3_current_claim")
    elif report_permission_scope == H2_PERMISSION_SCOPE:
        reasons.extend(
            ("report_permission_scope_h2_only", "report_permission_insufficient_for_h3_current_claim")
        )
    elif report_permission_scope in {None, ""}:
        reasons.append("report_permission_missing")
    else:
        reasons.append(
            "report_permission_insufficient_for_h3_current_claim"
            if _is_devcockpit_scope(report_permission_scope)
            else "report_permission_mismatched"
        )
    if observation_allowed:
        reasons.append("observation_authorization_explicitly_allows_h3_current_claim")
    elif observation_authorization_scope == H2_PERMISSION_SCOPE:
        reasons.extend(
            (
                "observation_authorization_scope_h2_only",
                "observation_authorization_insufficient_for_h3_current_claim",
            )
        )
    elif observation_authorization_scope in {None, ""}:
        reasons.append("observation_authorization_missing")
    else:
        reasons.append(
            "observation_authorization_insufficient_for_h3_current_claim"
            if _is_devcockpit_scope(observation_authorization_scope)
            else "observation_authorization_mismatched"
        )
    reasons.append(
        "dual_authorization_conjunction_satisfied"
        if permission_conjunction
        else "dual_authorization_conjunction_unsatisfied"
    )
    if not observation_actual:
        reasons.append("actual_current_observation_absent")
    if not observation_clean:
        reasons.append("worktree_not_clean")
    if not observation_stable:
        reasons.append("observation_not_stable")
    reasons.append(
        "observer_only_non_executable"
        if observer_only and non_executable
        else "observer_scope_boundary_invalid"
    )
    reasons.append("point_in_time_observation_does_not_establish_live_coverage")

    eligible = bool(
        authentic
        and permission_conjunction
        and report_temporal["temporal_state"] == "fresh"
        and reobservation_temporal["temporal_state"] == "fresh"
        and chronology_state == "valid"
        and revision["revision_binding_state"] == "match"
        and observation_actual
        and observation_clean
        and observation_stable
        and overall_provenance
        and observer_only
        and non_executable
    )
    return {
        "authentic_owner_attached_point_in_time_evidence": authentic,
        "transport_source_binding_state": "valid" if package_binding_verified else "invalid",
        "report_permission_state": _authorization_state(report_permission_scope),
        "observation_authorization_state": _authorization_state(
            observation_authorization_scope
        ),
        "permission_conjunction_state": "satisfied" if permission_conjunction else "unsatisfied",
        "report_temporal_state": report_temporal["temporal_state"],
        "reobservation_temporal_state": reobservation_temporal["temporal_state"],
        "chronology_state": chronology_state,
        "revision_binding_state": revision["revision_binding_state"],
        "current_claim_eligibility": eligible,
        "live_coverage": False,
        "reason_codes": sorted(set(reasons)),
    }


def evaluate_provenance(
    *,
    package_binding_verified: bool,
    current_observation_receipt_verified: bool,
    repository_project_revision_cross_binding_verified: bool,
) -> dict[str, str]:
    overall = bool(
        package_binding_verified
        and current_observation_receipt_verified
        and repository_project_revision_cross_binding_verified
    )
    return {
        "package_binding_state": "verified" if package_binding_verified else "unverified",
        "current_observation_receipt_state": (
            "verified" if current_observation_receipt_verified else "unverified"
        ),
        "repository_project_revision_cross_binding_state": (
            "verified" if repository_project_revision_cross_binding_verified else "unverified"
        ),
        "overall_current_claim_provenance_state": "verified" if overall else "unverified",
    }


def load_authority_envelope_v2(
    envelope_path: str | Path,
    *,
    manifest_path: str | Path,
    packet_path: str | Path,
    current_observation_path: str | Path,
    repo_root: str | Path = ".",
    assessed_at: str,
    expected_artifact_id: str,
    expected_observation_artifact_id: str,
    threshold_seconds: int = DEFAULT_THRESHOLD_SECONDS,
) -> dict[str, Any]:
    """Strictly load V2 and compare it to a full four-source reprojection."""

    root = Path(repo_root).resolve()
    envelope_full = _resolve_input(root, envelope_path, "envelope_path")
    stored = validate_authority_envelope_v2(
        _read_strict_json(envelope_full, label="authority envelope v2"),
        expected_artifact_id=expected_artifact_id,
        expected_observation_artifact_id=expected_observation_artifact_id,
    )
    expected = build_authority_envelope_v2(
        manifest_path=manifest_path,
        packet_path=packet_path,
        current_observation_path=current_observation_path,
        repo_root=root,
        assessed_at=assessed_at,
        artifact_id=expected_artifact_id,
        expected_observation_artifact_id=expected_observation_artifact_id,
        threshold_seconds=threshold_seconds,
    )
    difference = _first_json_difference(expected, stored)
    if difference is not None:
        raise AuthorityEnvelopeError(
            f"source-bound authority envelope v2 mismatch at {difference}"
        )
    return stored


def validate_authority_envelope_v2(
    value: Any,
    *,
    expected_artifact_id: str,
    expected_observation_artifact_id: str,
) -> dict[str, Any]:
    envelope = _exact(value, ROOT_KEYS, "envelope")
    identity = _exact(envelope.get("identity"), IDENTITY_KEYS, "envelope.identity")
    bindings = _exact(envelope.get("bindings"), BINDINGS_KEYS, "envelope.bindings")
    report = _exact(envelope.get("report"), REPORT_KEYS, "envelope.report")
    observation = _exact(envelope.get("observation"), OBSERVATION_KEYS, "envelope.observation")
    assessment = _exact(envelope.get("assessment"), ASSESSMENT_KEYS, "envelope.assessment")
    authority = _exact(envelope.get("authority"), AUTHORITY_KEYS, "envelope.authority")
    provenance = _exact(envelope.get("provenance"), PROVENANCE_KEYS, "envelope.provenance")
    scope = _exact(envelope.get("scope_boundary"), SCOPE_KEYS, "envelope.scope_boundary")
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise AuthorityEnvelopeError(f"envelope.schema_version must be {SCHEMA_VERSION!r}")
    _require_identifier(expected_artifact_id, "expected_artifact_id")
    if expected_artifact_id == DEFAULT_ARTIFACT_ID:
        raise AuthorityEnvelopeError(
            "authority envelope v2 must not reuse the H3 V1 package identity"
        )
    if envelope.get("artifact_id") != expected_artifact_id:
        raise AuthorityEnvelopeError("envelope.artifact_id does not match explicit expectation")
    if envelope.get("producer") != PRODUCER:
        raise AuthorityEnvelopeError("envelope.producer is invalid")
    for field in IDENTITY_KEYS:
        _nonempty(identity.get(field), f"envelope.identity.{field}")
    for name in ("source_report", "manifest", "packet"):
        binding = _exact(bindings.get(name), BINDING_KEYS, f"envelope.bindings.{name}")
        _validate_binding(binding, f"envelope.bindings.{name}", SOURCE_HASH_BASIS if name == "source_report" else CONTENT_HASH_BASIS)
    current_binding = _exact(
        bindings.get("current_observation"),
        OBSERVATION_BINDING_KEYS,
        "envelope.bindings.current_observation",
    )
    _validate_binding(
        current_binding,
        "envelope.bindings.current_observation",
        CURRENT_OBSERVATION_HASH_BASIS,
    )
    if current_binding.get("artifact_id") != expected_observation_artifact_id:
        raise AuthorityEnvelopeError(
            "envelope.bindings.current_observation.artifact_id mismatch"
        )
    for field in REPORT_KEYS:
        _nonempty(report.get(field), f"envelope.report.{field}")
    if not _FULL_REVISION_RE.fullmatch(report["source_revision"]):
        raise AuthorityEnvelopeError("envelope.report.source_revision must be a full revision")
    _require_aware_timestamp(report["observed_at"], "envelope.report.observed_at")
    try:
        if normalize_repository_identity(report["repository_identity"]) != report["repository_identity"]:
            raise AuthorityEnvelopeError("envelope.report.repository_identity is not canonical")
    except CurrentObservationError as exc:
        raise AuthorityEnvelopeError(
            f"envelope.report.repository_identity is invalid: {exc}"
        ) from exc
    for field in ("artifact_id", "project_key", "repository_identity", "authorization_scope"):
        _nonempty(observation.get(field), f"envelope.observation.{field}")
    _require_identifier(observation["artifact_id"], "envelope.observation.artifact_id")
    _require_identifier(observation["project_key"], "envelope.observation.project_key")
    if observation["artifact_id"] != expected_observation_artifact_id:
        raise AuthorityEnvelopeError("envelope.observation.artifact_id mismatch")
    try:
        if normalize_repository_identity(observation["repository_identity"]) != observation["repository_identity"]:
            raise AuthorityEnvelopeError(
                "envelope.observation.repository_identity is not canonical"
            )
    except CurrentObservationError as exc:
        raise AuthorityEnvelopeError(
            f"envelope.observation.repository_identity is invalid: {exc}"
        ) from exc
    for field in ("first_observed_at", "reobserved_at"):
        _require_aware_timestamp(observation.get(field), f"envelope.observation.{field}")
    if _parse_aware(observation["reobserved_at"]) < _parse_aware(
        observation["first_observed_at"]
    ):
        raise AuthorityEnvelopeError(
            "envelope.observation.reobserved_at precedes first_observed_at"
        )
    for field in ("before_head_revision", "after_head_revision"):
        if not isinstance(observation.get(field), str) or not _FULL_REVISION_RE.fullmatch(observation[field]):
            raise AuthorityEnvelopeError(f"envelope.observation.{field} must be a full revision")
    for field in ("before_worktree_sha256", "after_worktree_sha256"):
        if not isinstance(observation.get(field), str) or not _SHA256_RE.fullmatch(observation[field]):
            raise AuthorityEnvelopeError(f"envelope.observation.{field} must be lowercase SHA-256")
    for field in ("actual", "clean", "stable"):
        if type(observation.get(field)) is not bool:
            raise AuthorityEnvelopeError(f"envelope.observation.{field} must be boolean")
    if observation["actual"] is not True:
        raise AuthorityEnvelopeError("envelope.observation.actual must be true for a V1 receipt")
    snapshots_equal = bool(
        observation["before_head_revision"] == observation["after_head_revision"]
        and observation["before_worktree_sha256"]
        == observation["after_worktree_sha256"]
    )
    if observation["stable"] != snapshots_equal:
        raise AuthorityEnvelopeError(
            "envelope.observation.stable conflicts with projected snapshots"
        )
    _require_aware_timestamp(assessment.get("assessed_at"), "envelope.assessment.assessed_at")
    if type(assessment.get("threshold_seconds")) is not int or assessment["threshold_seconds"] <= 0:
        raise AuthorityEnvelopeError("envelope.assessment.threshold_seconds must be positive")
    if assessment.get("temporal_boundary") != TEMPORAL_BOUNDARY:
        raise AuthorityEnvelopeError("envelope.assessment.temporal_boundary is invalid")
    for field in ("authentic_owner_attached_point_in_time_evidence", "current_claim_eligibility", "live_coverage"):
        if type(authority.get(field)) is not bool:
            raise AuthorityEnvelopeError(f"envelope.authority.{field} must be boolean")
    if authority["live_coverage"]:
        raise AuthorityEnvelopeError("envelope.authority.live_coverage must remain false")
    if not isinstance(authority.get("reason_codes"), list) or not all(
        isinstance(item, str) and item for item in authority["reason_codes"]
    ):
        raise AuthorityEnvelopeError("envelope.authority.reason_codes must be strings")
    if authority["reason_codes"] != sorted(set(authority["reason_codes"])):
        raise AuthorityEnvelopeError("envelope.authority.reason_codes must be sorted and unique")
    for field in AUTHORITY_KEYS - {"reason_codes", "authentic_owner_attached_point_in_time_evidence", "current_claim_eligibility", "live_coverage"}:
        _nonempty(authority.get(field), f"envelope.authority.{field}")
    allowed_authority_states = {
        "transport_source_binding_state": {"valid", "invalid"},
        "report_permission_state": {
            "missing",
            "sufficient_for_h3_current_claim",
            "insufficient_h2_only",
            "insufficient",
            "mismatched",
        },
        "observation_authorization_state": {
            "missing",
            "sufficient_for_h3_current_claim",
            "insufficient_h2_only",
            "insufficient",
            "mismatched",
        },
        "permission_conjunction_state": {"satisfied", "unsatisfied"},
        "report_temporal_state": {"fresh", "stale", "unknown"},
        "reobservation_temporal_state": {"fresh", "stale", "unknown"},
        "chronology_state": {
            "valid",
            "invalid_report_timestamp",
            "invalid_reobservation_timestamp",
            "invalid_assessment_timestamp",
            "reobservation_before_report",
            "report_after_assessment",
            "reobservation_after_assessment",
        },
        "revision_binding_state": {"match", "mismatch", "unknown"},
    }
    for field, allowed in allowed_authority_states.items():
        if authority.get(field) not in allowed:
            raise AuthorityEnvelopeError(f"envelope.authority.{field} is invalid")
    for field in PROVENANCE_KEYS:
        if provenance.get(field) not in {"verified", "unverified"}:
            raise AuthorityEnvelopeError(f"envelope.provenance.{field} is invalid")
    expected_overall = (
        "verified"
        if all(
            provenance[field] == "verified"
            for field in PROVENANCE_KEYS
            - {"overall_current_claim_provenance_state"}
        )
        else "unverified"
    )
    if provenance["overall_current_claim_provenance_state"] != expected_overall:
        raise AuthorityEnvelopeError(
            "envelope.provenance.overall_current_claim_provenance_state conflicts with components"
        )
    if scope != SCOPE_BOUNDARY:
        raise AuthorityEnvelopeError("envelope.scope_boundary is invalid")
    return envelope


def dumps_authority_envelope_v2(envelope: dict[str, Any], *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(envelope, ensure_ascii=True, indent=2) + "\n"
    return json.dumps(envelope, ensure_ascii=True, separators=(",", ":")) + "\n"


def _evaluate_chronology(
    report_observed_at: Any, reobserved_at: Any, assessed_at: Any
) -> tuple[str, list[str]]:
    report = _parse_aware(report_observed_at)
    reobserved = _parse_aware(reobserved_at)
    assessed = _parse_aware(assessed_at)
    if report is None:
        return "invalid_report_timestamp", ["chronology_report_timestamp_invalid"]
    if reobserved is None:
        return "invalid_reobservation_timestamp", ["chronology_reobservation_timestamp_invalid"]
    if assessed is None:
        return "invalid_assessment_timestamp", ["chronology_assessment_timestamp_invalid"]
    if report > assessed:
        return "report_after_assessment", ["report_follows_assessment"]
    if reobserved > assessed:
        return "reobservation_after_assessment", ["reobservation_follows_assessment"]
    if reobserved < report:
        return "reobservation_before_report", ["reobservation_precedes_report"]
    return "valid", ["report_reobservation_assessment_chronology_valid"]


def _authorization_state(value: Any) -> str:
    if value in {None, ""}:
        return "missing"
    if value == H3_CURRENT_PERMISSION_SCOPE:
        return "sufficient_for_h3_current_claim"
    if value == H2_PERMISSION_SCOPE:
        return "insufficient_h2_only"
    if _is_devcockpit_scope(value):
        return "insufficient"
    return "mismatched"


def _is_devcockpit_scope(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("allowed_for_DevCockpitCore_")


def _parse_aware(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _validate_binding(value: dict[str, Any], label: str, basis: str) -> None:
    path = _nonempty(value.get("path"), f"{label}.path")
    path_value = Path(path)
    if path_value.is_absolute() or ".." in path_value.parts:
        raise AuthorityEnvelopeError(f"{label}.path must be repository-relative")
    digest = _nonempty(value.get("content_sha256"), f"{label}.content_sha256")
    if not _SHA256_RE.fullmatch(digest):
        raise AuthorityEnvelopeError(f"{label}.content_sha256 must be lowercase SHA-256")
    if value.get("hash_basis") != basis:
        raise AuthorityEnvelopeError(f"{label}.hash_basis is invalid")


def _exact(value: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuthorityEnvelopeError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        raise AuthorityEnvelopeError(
            f"{label} keys differ; missing={sorted(keys - actual)}, unknown={sorted(actual - keys)}"
        )
    return value


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthorityEnvelopeError(f"{label} must be a non-empty string")
    return value


def _require_identifier(value: Any, label: str) -> str:
    text = _nonempty(value, label)
    if not _IDENTIFIER_RE.fullmatch(text):
        raise AuthorityEnvelopeError(f"{label} has an invalid identifier form")
    return text
