"""Produce and strictly verify read-only current-repository observations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Iterable
from urllib.parse import urlsplit, urlunsplit


SCHEMA_VERSION = "supervision_current_observation.v1"
PRODUCER = "dev_cockpit.current_observation"
AUTHORIZATION_SCOPE = "allowed_for_DevCockpitCore_H3_current_claim"
REPOSITORY_IDENTITY_BASIS = "sanitized_remote_origin_v1"
WORKTREE_HASH_BASIS = "git_status_porcelain_v1_z_sha256_v1"

ROOT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_id",
        "producer",
        "project_key",
        "repository",
        "authorization",
        "observation",
        "scope_boundary",
    }
)
REPOSITORY_KEYS = frozenset({"identity", "identity_sha256", "identity_basis"})
AUTHORIZATION_KEYS = frozenset({"scope"})
OBSERVATION_KEYS = frozenset(
    {"first_observed_at", "reobserved_at", "before", "after", "derived"}
)
SNAPSHOT_KEYS = frozenset(
    {"head_revision", "worktree_state", "worktree_sha256", "worktree_entry_count"}
)
DERIVED_KEYS = frozenset({"actual", "clean", "stable"})
SCOPE_KEYS = frozenset(
    {
        "read_only",
        "fetch_performed",
        "pull_performed",
        "checkout_performed",
        "merge_performed",
        "rebase_performed",
        "stash_performed",
        "reset_performed",
        "clean_performed",
        "write_performed",
        "target_repository_writeback",
        "stage_performed",
        "commit_performed",
        "push_performed",
        "arbitrary_command_execution",
    }
)
SCOPE_BOUNDARY = {
    "read_only": True,
    "fetch_performed": False,
    "pull_performed": False,
    "checkout_performed": False,
    "merge_performed": False,
    "rebase_performed": False,
    "stash_performed": False,
    "reset_performed": False,
    "clean_performed": False,
    "write_performed": False,
    "target_repository_writeback": False,
    "stage_performed": False,
    "commit_performed": False,
    "push_performed": False,
    "arbitrary_command_execution": False,
}

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_FULL_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SCP_REMOTE_RE = re.compile(
    r"^(?:(?P<user>[A-Za-z0-9._-]+)@)?(?P<host>[A-Za-z0-9.-]+):(?P<path>[^\\]+)$"
)


class CurrentObservationError(ValueError):
    """Raised when a current observation is unsafe, invalid, or forged."""


def observe_repository(
    *,
    repository: str | Path,
    project_key: str,
    artifact_id: str,
    authorization_scope: str,
    output_path: str | Path,
    clock: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Observe one explicit Git repository twice without mutating it."""

    project_key = _require_identifier(project_key, "project_key")
    artifact_id = _require_identifier(artifact_id, "artifact_id")
    authorization_scope = _require_nonempty_string(
        authorization_scope, "authorization_scope"
    )
    target = Path(repository).resolve()
    if not target.is_dir():
        raise CurrentObservationError("repository must be an existing directory")
    output = Path(output_path).resolve()
    if _is_within(output, target):
        raise CurrentObservationError("output_path must be outside the observed repository")

    top_level = Path(
        _run_git_text(target, ("rev-parse", "--show-toplevel"), "repository root")
    ).resolve()
    if top_level != target:
        raise CurrentObservationError(
            "repository must identify the exact Git top-level directory"
        )
    remote = _run_git_text(
        target, ("config", "--get", "remote.origin.url"), "remote.origin.url"
    )
    repository_identity = normalize_repository_identity(remote)
    now = clock or (lambda: datetime.now(timezone.utc))

    before = _capture_snapshot(target)
    first_observed_at = _format_timestamp(now())
    after = _capture_snapshot(target)
    reobserved_at = _format_timestamp(now())
    derived = _derive_observation(before, after)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "producer": PRODUCER,
        "project_key": project_key,
        "repository": {
            "identity": repository_identity,
            "identity_sha256": sha256(repository_identity.encode("utf-8")).hexdigest(),
            "identity_basis": REPOSITORY_IDENTITY_BASIS,
        },
        "authorization": {"scope": authorization_scope},
        "observation": {
            "first_observed_at": first_observed_at,
            "reobserved_at": reobserved_at,
            "before": before,
            "after": after,
            "derived": derived,
        },
        "scope_boundary": dict(SCOPE_BOUNDARY),
    }
    return validate_current_observation(receipt)


def load_current_observation(path: str | Path) -> dict[str, Any]:
    """Load an observation with duplicate-key and derived-field verification."""

    receipt, _ = load_current_observation_with_payload(path)
    return receipt


def load_current_observation_with_payload(
    path: str | Path,
) -> tuple[dict[str, Any], bytes]:
    """Load once and return both the verified receipt and its exact bound bytes."""

    full_path = Path(path).resolve()
    try:
        payload = full_path.read_bytes()
        text = payload.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise CurrentObservationError(f"cannot read current observation: {exc}") from exc
    try:
        value = json.loads(text, object_pairs_hook=_collect_pairs)
    except CurrentObservationError:
        raise
    except json.JSONDecodeError as exc:
        raise CurrentObservationError(f"invalid current observation JSON: {exc}") from exc
    _reject_duplicate_tree(value)
    return validate_current_observation(_plain_json_value(value)), payload


def validate_current_observation(value: Any) -> dict[str, Any]:
    receipt = _require_exact_object(value, ROOT_KEYS, "observation_receipt")
    repository = _require_exact_object(
        receipt.get("repository"), REPOSITORY_KEYS, "observation_receipt.repository"
    )
    authorization = _require_exact_object(
        receipt.get("authorization"),
        AUTHORIZATION_KEYS,
        "observation_receipt.authorization",
    )
    observation = _require_exact_object(
        receipt.get("observation"), OBSERVATION_KEYS, "observation_receipt.observation"
    )
    before = _validate_snapshot(
        observation.get("before"), "observation_receipt.observation.before"
    )
    after = _validate_snapshot(
        observation.get("after"), "observation_receipt.observation.after"
    )
    derived = _require_exact_object(
        observation.get("derived"), DERIVED_KEYS, "observation_receipt.observation.derived"
    )
    scope = _require_exact_object(
        receipt.get("scope_boundary"), SCOPE_KEYS, "observation_receipt.scope_boundary"
    )

    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise CurrentObservationError(
            f"observation_receipt.schema_version must be {SCHEMA_VERSION!r}"
        )
    if receipt.get("producer") != PRODUCER:
        raise CurrentObservationError("observation_receipt.producer is invalid")
    _require_identifier(receipt.get("artifact_id"), "observation_receipt.artifact_id")
    _require_identifier(receipt.get("project_key"), "observation_receipt.project_key")

    identity = _require_nonempty_string(
        repository.get("identity"), "observation_receipt.repository.identity"
    )
    if normalize_repository_identity(identity) != identity:
        raise CurrentObservationError(
            "observation_receipt.repository.identity is not canonical"
        )
    identity_hash = _require_nonempty_string(
        repository.get("identity_sha256"),
        "observation_receipt.repository.identity_sha256",
    )
    if not _SHA256_RE.fullmatch(identity_hash):
        raise CurrentObservationError(
            "observation_receipt.repository.identity_sha256 must be lowercase SHA-256"
        )
    if identity_hash != sha256(identity.encode("utf-8")).hexdigest():
        raise CurrentObservationError(
            "observation_receipt.repository.identity_sha256 does not match identity"
        )
    if repository.get("identity_basis") != REPOSITORY_IDENTITY_BASIS:
        raise CurrentObservationError(
            "observation_receipt.repository.identity_basis is invalid"
        )
    _require_nonempty_string(
        authorization.get("scope"), "observation_receipt.authorization.scope"
    )
    first = _require_aware_timestamp(
        observation.get("first_observed_at"),
        "observation_receipt.observation.first_observed_at",
    )
    second = _require_aware_timestamp(
        observation.get("reobserved_at"),
        "observation_receipt.observation.reobserved_at",
    )
    if _parse_timestamp(second) < _parse_timestamp(first):
        raise CurrentObservationError(
            "observation_receipt.observation.reobserved_at precedes first_observed_at"
        )
    for field in DERIVED_KEYS:
        if type(derived.get(field)) is not bool:
            raise CurrentObservationError(
                f"observation_receipt.observation.derived.{field} must be boolean"
            )
    expected_derived = _derive_observation(before, after)
    if derived != expected_derived:
        raise CurrentObservationError(
            "observation_receipt.observation.derived does not match observed snapshots"
        )
    if scope != SCOPE_BOUNDARY:
        raise CurrentObservationError("observation_receipt.scope_boundary is invalid")
    return receipt


def normalize_repository_identity(remote: str) -> str:
    """Return a credential-free canonical remote identity or fail closed."""

    value = _require_nonempty_string(remote, "repository remote").strip()
    if re.match(r"^[A-Za-z]:[\\/]", value):
        raise CurrentObservationError("repository remote must not be a local path")
    scp = _SCP_REMOTE_RE.fullmatch(value)
    if scp and "://" not in value:
        host = scp.group("host").lower()
        path = _normalize_remote_path(scp.group("path"))
        return f"ssh://{host}/{path}"

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"https", "ssh"} or not parsed.hostname:
        raise CurrentObservationError(
            "repository remote must be an https or ssh network identity"
        )
    if (
        parsed.password is not None
        or (parsed.scheme.lower() == "https" and parsed.username is not None)
        or parsed.query
        or parsed.fragment
    ):
        raise CurrentObservationError(
            "repository remote must not contain credentials, query, or fragment"
        )
    host = parsed.hostname.lower()
    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise CurrentObservationError("repository remote port is invalid") from exc
    port = f":{parsed_port}" if parsed_port is not None else ""
    path = _normalize_remote_path(parsed.path)
    return urlunsplit((parsed.scheme.lower(), f"{host}{port}", f"/{path}", "", ""))


def dumps_current_observation(receipt: dict[str, Any], *, pretty: bool = False) -> str:
    validated = validate_current_observation(receipt)
    if pretty:
        return json.dumps(validated, ensure_ascii=True, indent=2) + "\n"
    return json.dumps(validated, ensure_ascii=True, separators=(",", ":")) + "\n"


def write_current_observation(
    receipt: dict[str, Any], output_path: str | Path, *, pretty: bool = False
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps_current_observation(receipt, pretty=pretty), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a strict read-only supervision_current_observation.v1 receipt."
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--authorization-scope", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        receipt = observe_repository(
            repository=args.repository,
            project_key=args.project_key,
            artifact_id=args.artifact_id,
            authorization_scope=args.authorization_scope,
            output_path=args.output,
        )
        write_current_observation(receipt, args.output, pretty=args.pretty)
    except (CurrentObservationError, OSError) as exc:
        print(f"current observation failed: {exc}", file=sys.stderr)
        return 2
    print(Path(args.output).resolve())
    return 0


def _capture_snapshot(repository: Path) -> dict[str, Any]:
    head = _run_git_text(
        repository, ("rev-parse", "--verify", "HEAD"), "HEAD revision"
    ).lower()
    if not _FULL_REVISION_RE.fullmatch(head):
        raise CurrentObservationError("Git returned a non-full HEAD revision")
    porcelain = _run_git_bytes(
        repository,
        ("status", "--porcelain=v1", "-z", "--untracked-files=all"),
        "worktree status",
    )
    entry_count = len([entry for entry in porcelain.split(b"\0") if entry])
    return {
        "head_revision": head,
        "worktree_state": "clean" if not porcelain else "dirty",
        "worktree_sha256": sha256(porcelain).hexdigest(),
        "worktree_entry_count": entry_count,
    }


def _derive_observation(
    before: dict[str, Any], after: dict[str, Any]
) -> dict[str, bool]:
    clean = bool(
        before.get("worktree_state") == "clean"
        and after.get("worktree_state") == "clean"
        and before.get("worktree_entry_count") == 0
        and after.get("worktree_entry_count") == 0
    )
    stable = bool(before == after)
    return {"actual": True, "clean": clean, "stable": stable}


def _validate_snapshot(value: Any, label: str) -> dict[str, Any]:
    snapshot = _require_exact_object(value, SNAPSHOT_KEYS, label)
    revision = _require_nonempty_string(snapshot.get("head_revision"), f"{label}.head_revision")
    if not _FULL_REVISION_RE.fullmatch(revision):
        raise CurrentObservationError(f"{label}.head_revision must be a full revision")
    if snapshot.get("worktree_state") not in {"clean", "dirty"}:
        raise CurrentObservationError(f"{label}.worktree_state is invalid")
    status_hash = _require_nonempty_string(
        snapshot.get("worktree_sha256"), f"{label}.worktree_sha256"
    )
    if not _SHA256_RE.fullmatch(status_hash):
        raise CurrentObservationError(f"{label}.worktree_sha256 must be lowercase SHA-256")
    count = snapshot.get("worktree_entry_count")
    if type(count) is not int or count < 0:
        raise CurrentObservationError(f"{label}.worktree_entry_count must be non-negative")
    if (snapshot["worktree_state"] == "clean") != (count == 0):
        raise CurrentObservationError(f"{label} worktree state conflicts with entry count")
    if count == 0 and status_hash != sha256(b"").hexdigest():
        raise CurrentObservationError(f"{label} clean worktree hash is invalid")
    return snapshot


def _run_git_text(repository: Path, args: tuple[str, ...], label: str) -> str:
    payload = _run_git_bytes(repository, args, label)
    try:
        value = payload.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise CurrentObservationError(f"Git {label} is not UTF-8") from exc
    if not value:
        raise CurrentObservationError(f"Git {label} is empty")
    return value


def _run_git_bytes(repository: Path, args: tuple[str, ...], label: str) -> bytes:
    try:
        environment = dict(os.environ)
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        result = subprocess.run(
            ("git", "-C", str(repository), *args),
            check=False,
            capture_output=True,
            env=environment,
        )
    except OSError as exc:
        raise CurrentObservationError(f"cannot execute Git for {label}: {exc}") from exc
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise CurrentObservationError(f"Git {label} failed: {error or result.returncode}")
    return result.stdout


def _normalize_remote_path(value: str) -> str:
    path = value.replace("\\", "/").strip("/")
    if not path or any(part in {"", ".", ".."} for part in path.split("/")):
        raise CurrentObservationError("repository remote path is invalid")
    if path.endswith(".git"):
        path = path[:-4] + ".git"
    return path


def _format_timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise CurrentObservationError("clock must return a timezone-aware datetime")
    return value.isoformat(timespec="microseconds")


def _require_aware_timestamp(value: Any, label: str) -> str:
    text = _require_nonempty_string(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CurrentObservationError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CurrentObservationError(f"{label} must include a timezone offset")
    return text


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _require_identifier(value: Any, label: str) -> str:
    text = _require_nonempty_string(value, label)
    if not _IDENTIFIER_RE.fullmatch(text):
        raise CurrentObservationError(f"{label} has an invalid identifier form")
    return text


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CurrentObservationError(f"{label} must be a non-empty string")
    return value


def _require_exact_object(value: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CurrentObservationError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        unknown = sorted(actual - keys)
        raise CurrentObservationError(
            f"{label} keys differ; missing={missing}, unknown={unknown}"
        )
    return value


class _ParsedObject(dict[str, Any]):
    def __init__(self, pairs: Iterable[tuple[str, Any]]) -> None:
        super().__init__()
        self.pairs = list(pairs)


def _collect_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    return _ParsedObject(pairs)


def _reject_duplicate_tree(value: Any, path: str = "$") -> None:
    if isinstance(value, _ParsedObject):
        seen: set[str] = set()
        for key, child in value.pairs:
            if key in seen:
                raise CurrentObservationError(f"duplicate JSON key at {path}.{key}")
            seen.add(key)
            _reject_duplicate_tree(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_duplicate_tree(child, f"{path}[{index}]")


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, _ParsedObject):
        return {key: _plain_json_value(child) for key, child in value.pairs}
    if isinstance(value, list):
        return [_plain_json_value(child) for child in value]
    return value


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
