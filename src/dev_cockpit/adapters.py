"""Adapter manifest loading and validation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from glob import glob
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import sys
from typing import Any


ADAPTER_SCHEMA_VERSION = "adapter_manifest.v1"
_PROJECT_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_SECRET_VALUE_RE = re.compile(
    r"(sk-(?:proj-)?[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{12,}|AKIA[0-9A-Z]{16})"
)
_ENDPOINT_RE = re.compile(r"https?://", re.IGNORECASE)
_SECRET_FIELD_NAMES = {
    "access_token",
    "api_key",
    "apikey",
    "client_secret",
    "credential",
    "credentials",
    "openai_api_key",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "token",
}


class AdapterError(ValueError):
    """Raised when an adapter manifest cannot be used safely."""


@dataclass(frozen=True)
class AdapterConfig:
    schema_version: str
    project: str
    project_key: str
    default_branch: str
    repo_hints: dict[str, tuple[str, ...]]
    documents: dict[str, str]
    status_hints: dict[str, tuple[str, ...]]
    artifact_roots: tuple[str, ...]
    forbidden_stage_patterns: tuple[str, ...]
    default_validation: tuple[str, ...]
    read_only: bool
    raw: dict[str, Any]

    @property
    def runtime_state(self) -> str | None:
        return self.documents.get("runtime_state")

    @property
    def project_context(self) -> str | None:
        return self.documents.get("project_context")

    def to_snapshot(self, adapter_path: str) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project": self.project,
            "project_key": self.project_key,
            "adapter_path": adapter_path,
            "default_branch": self.default_branch,
            "read_only": self.read_only,
        }


def load_adapter(path: str | Path) -> AdapterConfig:
    adapter_path = Path(path)
    try:
        data = json.loads(adapter_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AdapterError(f"adapter not found: {adapter_path}") from exc
    except json.JSONDecodeError as exc:
        raise AdapterError(f"adapter is not valid JSON: {adapter_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise AdapterError("adapter root must be a JSON object")

    return validate_adapter(data)


def validate_adapter(data: dict[str, Any]) -> AdapterConfig:
    _reject_sensitive_content(data)

    schema_version = _required_string(data, "schema_version")
    if schema_version != ADAPTER_SCHEMA_VERSION:
        raise AdapterError(
            f"adapter field 'schema_version' must be {ADAPTER_SCHEMA_VERSION!r}"
        )

    project = _required_string(data, "project")
    project_key = _required_string(data, "project_key")
    if not _PROJECT_KEY_RE.fullmatch(project_key):
        raise AdapterError(
            "adapter field 'project_key' must be a lowercase identifier "
            "matching [a-z][a-z0-9_-]*"
        )

    default_branch = _required_string(data, "default_branch")
    read_only = data.get("read_only")
    if read_only is not True:
        raise AdapterError("adapter must declare read_only: true for this slice")

    repo_hints = _validate_repo_hints(_required_object(data, "repo_hints"))
    documents = _validate_documents(_required_object(data, "documents"))
    status_hints = _validate_status_hints(_required_object(data, "status_hints"))

    artifact_roots = _required_string_tuple(data, "artifact_roots")
    for artifact_root in artifact_roots:
        _validate_relative_path(artifact_root, "artifact_roots", allow_parent=False)

    return AdapterConfig(
        schema_version=schema_version,
        project=project,
        project_key=project_key,
        default_branch=default_branch,
        repo_hints=repo_hints,
        documents=documents,
        status_hints=status_hints,
        artifact_roots=artifact_roots,
        forbidden_stage_patterns=_required_string_tuple(data, "forbidden_stage_patterns"),
        default_validation=_required_string_tuple(data, "default_validation"),
        read_only=True,
        raw=dict(data),
    )


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AdapterError(f"adapter field {key!r} must be a non-empty string")
    return value.strip()


def _required_object(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise AdapterError(f"adapter field {key!r} must be an object")
    return value


def _required_string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    if key not in data:
        raise AdapterError(f"adapter field {key!r} is required")
    return _string_tuple_value(data[key], key)


def _string_tuple_value(value: Any, key: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise AdapterError(f"adapter field {key!r} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise AdapterError(f"adapter field {key!r} must contain only strings")
        items.append(item.strip())
    return tuple(items)


def _validate_repo_hints(repo_hints: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    if "preferred_relative_paths" not in repo_hints:
        raise AdapterError("adapter field 'repo_hints.preferred_relative_paths' is required")
    paths = _string_tuple_value(
        repo_hints["preferred_relative_paths"],
        "repo_hints.preferred_relative_paths",
    )
    for path in paths:
        _validate_relative_path(
            path,
            "repo_hints.preferred_relative_paths",
            allow_parent=True,
        )
    return {"preferred_relative_paths": paths}


def _validate_documents(documents: dict[str, Any]) -> dict[str, str]:
    required = ("runtime_state", "project_context")
    cleaned: dict[str, str] = {}
    for key in required:
        value = documents.get(key)
        if not isinstance(value, str) or not value.strip():
            raise AdapterError(f"adapter field 'documents.{key}' must be a non-empty string")
        cleaned_value = value.strip()
        _validate_relative_path(cleaned_value, f"documents.{key}", allow_parent=False)
        cleaned[key] = cleaned_value

    for key, value in documents.items():
        if key in cleaned:
            continue
        if not isinstance(value, str) or not value.strip():
            raise AdapterError(f"adapter field 'documents.{key}' must be a non-empty string")
        cleaned_value = value.strip()
        _validate_relative_path(cleaned_value, f"documents.{key}", allow_parent=False)
        cleaned[key] = cleaned_value
    return cleaned


def _validate_status_hints(status_hints: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    required = (
        "active_artifact_patterns",
        "next_action_patterns",
        "user_work_patterns",
        "gate_patterns",
    )
    cleaned: dict[str, tuple[str, ...]] = {}
    for key in required:
        if key not in status_hints:
            raise AdapterError(f"adapter field 'status_hints.{key}' is required")
        cleaned[key] = _string_tuple_value(status_hints[key], f"status_hints.{key}")
    return cleaned


def _validate_relative_path(value: str, field_path: str, *, allow_parent: bool) -> None:
    normalized = value.replace("\\", "/")
    if (
        normalized.startswith("/")
        or normalized.startswith("~/")
        or normalized == "~"
        or normalized.startswith("//")
        or _WINDOWS_ABSOLUTE_RE.match(value)
        or value.startswith("\\\\")
    ):
        raise AdapterError(f"adapter field {field_path!r} must be a relative path")

    parts = PurePosixPath(normalized).parts
    if not allow_parent and ".." in parts:
        raise AdapterError(f"adapter field {field_path!r} must stay inside the target repo")


def _reject_sensitive_content(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{path}.{key}"
            key_text = str(key).lower()
            if key_text in _SECRET_FIELD_NAMES:
                raise AdapterError(f"adapter field {key_path!r} looks secret-like")
            _reject_sensitive_content(child, key_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive_content(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if _SECRET_VALUE_RE.search(value):
            raise AdapterError(f"adapter field {path!r} contains an obvious token-like value")
        if _ENDPOINT_RE.search(value):
            raise AdapterError(f"adapter field {path!r} contains an endpoint-like URL")
        if _WINDOWS_ABSOLUTE_RE.search(value) or "\\Users\\" in value or "/Users/" in value or "/home/" in value:
            raise AdapterError(f"adapter field {path!r} contains an absolute user path")


def _expand_paths(paths: list[str]) -> list[str]:
    expanded: list[str] = []
    for path in paths:
        matches = sorted(glob(path))
        expanded.extend(matches or [path])
    return expanded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate DevCockpitCore adapter manifests.")
    parser.add_argument(
        "--validate",
        nargs="+",
        metavar="ADAPTER",
        help="Adapter JSON files or glob patterns to validate.",
    )
    args = parser.parse_args(argv)

    if not args.validate:
        parser.error("--validate is required")

    ok = True
    for adapter_path in _expand_paths(args.validate):
        try:
            adapter = load_adapter(adapter_path)
        except AdapterError as exc:
            ok = False
            print(f"{adapter_path}: ERROR: {exc}", file=sys.stderr)
        else:
            print(f"{adapter_path}: OK ({adapter.project_key})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
