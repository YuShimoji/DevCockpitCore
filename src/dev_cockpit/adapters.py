"""Adapter manifest loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


class AdapterError(ValueError):
    """Raised when an adapter manifest cannot be used safely."""


@dataclass(frozen=True)
class AdapterConfig:
    project: str
    default_branch: str | None
    runtime_state: str | None
    project_context: str | None
    artifact_roots: tuple[str, ...]
    forbidden_stage_patterns: tuple[str, ...]
    default_validation: tuple[str, ...]
    read_only: bool
    raw: dict[str, Any]

    def to_snapshot(self, adapter_path: str) -> dict[str, Any]:
        return {
            "project": self.project,
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
    project = _required_string(data, "project")
    read_only = data.get("read_only")
    if read_only is not True:
        raise AdapterError("adapter must declare read_only: true for this slice")

    return AdapterConfig(
        project=project,
        default_branch=_optional_string(data, "default_branch"),
        runtime_state=_optional_string(data, "runtime_state"),
        project_context=_optional_string(data, "project_context"),
        artifact_roots=_string_tuple(data, "artifact_roots"),
        forbidden_stage_patterns=_string_tuple(data, "forbidden_stage_patterns"),
        default_validation=_string_tuple(data, "default_validation"),
        read_only=True,
        raw=dict(data),
    )


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AdapterError(f"adapter field {key!r} must be a non-empty string")
    return value.strip()


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise AdapterError(f"adapter field {key!r} must be a string when present")
    value = value.strip()
    return value or None


def _string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise AdapterError(f"adapter field {key!r} must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise AdapterError(f"adapter field {key!r} must contain only strings")
        items.append(item.strip())
    return tuple(items)
