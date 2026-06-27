"""Run read-only cross-project smoke observations for DevCockpitCore."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

from .adapters import AdapterError, load_adapter
from .git_status import inspect_repo
from .report_normalizer import redact_absolute_user_paths
from .status_snapshot import build_status_snapshot
from .validation_pack import (
    make_meter,
    scan_forbidden_implementation_text,
    scan_mojibake_text,
    scan_prompt_residue_text,
    scan_pseudo_git_tags_text,
    scan_raw_local_paths_text,
)


SMOKE_SCHEMA_VERSION = "cross_project_smoke.v1"
RESULT_SCHEMA_VERSION = "cross_project_smoke_result.v1"
PRODUCER = "dev_cockpit.cross_project_smoke"
DEFAULT_SMOKE_KEY = "devcockpitcore_cross_project_observer"
DEFAULT_PROJECT_KEY = "devcockpitcore"
DEFAULT_SMOKE_PATH = "samples/cross_project_smokes/devcockpitcore_cross_project_smoke.json"
TEXT_FILE_LIMIT_BYTES = 1024 * 1024

_COMMAND_FIELDS = {"command", "commands", "cmd", "args", "argv"}
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_WEAK_METER_CELL_RE = re.compile(r"\|\s*(?P<meter>[#?!~-]+)\s*\|")
_TEXT_SUFFIXES = {".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
_IGNORED_DIRS = {".git", ".mypy_cache", ".pytest_cache", ".serena", "__pycache__", "build", "dist"}
_DEFAULT_REPO_HINTS = {
    "devcockpitcore": ".",
    "nlmytgen": "../NLMYTGen",
    "writingpage": "../WritingPage",
    "clippipegen": "../ClipPipeGen",
}


class CrossProjectSmokeError(ValueError):
    """Raised when a cross-project smoke config cannot be used safely."""


def default_smoke() -> dict[str, Any]:
    """Return the built-in DevCockpitCore cross-project smoke config."""

    return {
        "schema_version": SMOKE_SCHEMA_VERSION,
        "smoke_key": DEFAULT_SMOKE_KEY,
        "project_key": DEFAULT_PROJECT_KEY,
        "description": "Read-only smoke observations for DevCockpitCore and configured sibling adapters.",
        "adapters": [
            _smoke_adapter("adapters/devcockpitcore.json", required=True, expected_default_branch="main"),
            _smoke_adapter("adapters/nlmytgen.json", required=False, expected_default_branch="master"),
            _smoke_adapter("adapters/writingpage.json", required=False, expected_default_branch="main"),
            _smoke_adapter("adapters/clippipegen.json", required=False, expected_default_branch="main"),
        ],
    }


def load_smoke(path: str | Path) -> dict[str, Any]:
    """Load and validate a cross_project_smoke.v1 JSON file."""

    smoke_path = Path(path)
    try:
        data = json.loads(smoke_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CrossProjectSmokeError(f"cross-project smoke not found: {smoke_path}") from exc
    except json.JSONDecodeError as exc:
        raise CrossProjectSmokeError(f"cross-project smoke is not valid JSON: {smoke_path}: {exc}") from exc
    return validate_smoke(data)


def validate_smoke(data: dict[str, Any]) -> dict[str, Any]:
    """Validate smoke config and reject executable command fields."""

    if not isinstance(data, dict):
        raise CrossProjectSmokeError("cross-project smoke root must be a JSON object")
    _reject_command_fields(data)

    schema_version = data.get("schema_version")
    if schema_version != SMOKE_SCHEMA_VERSION:
        raise CrossProjectSmokeError(f"schema_version must be {SMOKE_SCHEMA_VERSION!r}")

    smoke_key = _required_string(data, "smoke_key")
    project_key = _required_string(data, "project_key")
    description = _required_string(data, "description")
    adapters_value = data.get("adapters")
    if not isinstance(adapters_value, list) or not adapters_value:
        raise CrossProjectSmokeError("adapters must be a non-empty list")

    adapters: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(adapters_value):
        if not isinstance(item, dict):
            raise CrossProjectSmokeError(f"adapters[{index}] must be an object")
        adapter_path = _required_string(item, "adapter_path")
        _validate_relative_path(adapter_path, f"adapters[{index}].adapter_path", allow_parent=False)
        if adapter_path in seen:
            raise CrossProjectSmokeError(f"duplicate adapter_path: {adapter_path}")
        seen.add(adapter_path)

        required = item.get("required", False)
        if not isinstance(required, bool):
            raise CrossProjectSmokeError(f"adapters[{index}].required must be boolean")
        repo_path_override = item.get("repo_path_override")
        if repo_path_override is not None:
            if not isinstance(repo_path_override, str) or not repo_path_override.strip():
                raise CrossProjectSmokeError(f"adapters[{index}].repo_path_override must be a non-empty string")
            repo_path_override = repo_path_override.strip()
            _validate_relative_path(
                repo_path_override,
                f"adapters[{index}].repo_path_override",
                allow_parent=True,
            )
        expected_default_branch = item.get("expected_default_branch")
        if expected_default_branch is not None:
            if not isinstance(expected_default_branch, str) or not expected_default_branch.strip():
                raise CrossProjectSmokeError(f"adapters[{index}].expected_default_branch must be a non-empty string")
            expected_default_branch = expected_default_branch.strip()
        notes = _string_list(item.get("notes", []), f"adapters[{index}].notes")
        adapters.append(
            {
                "adapter_path": adapter_path,
                "required": required,
                "repo_path_override": repo_path_override,
                "expected_default_branch": expected_default_branch,
                "notes": notes,
            }
        )

    return {
        "schema_version": SMOKE_SCHEMA_VERSION,
        "smoke_key": smoke_key,
        "project_key": project_key,
        "description": description,
        "adapters": adapters,
    }


def run_cross_project_smoke(
    smoke: dict[str, Any],
    *,
    repo_path: str | Path = ".",
    smoke_path: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Run read-only observations for every adapter in a validated smoke config."""

    repo = Path(repo_path).resolve()
    projects = [_observe_project(repo, item) for item in smoke["adapters"]]
    hygiene = _hygiene(repo)
    summary = _summary(projects, hygiene)
    health = _health(summary, projects, hygiene)

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_iso(),
        "producer": PRODUCER,
        "smoke": {
            "smoke_key": smoke["smoke_key"],
            "smoke_path": smoke_path,
            "project_key": smoke["project_key"],
        },
        "summary": summary,
        "projects": projects,
        "hygiene": hygiene,
        "readiness": {
            "foundation_automation_readiness": "cross_project_smoke_available",
            "execution_automation_readiness": "out_of_scope",
            "notes": [
                "status producer, adapters, report normalizer, gate classifier, validation pack, and cross-project smoke are foundation tooling",
                "target repositories are observed through read-only status snapshots only",
                "controlled execution automation remains a future design slice",
            ],
        },
        "gate_input": _gate_input(summary),
        "health": health,
    }


def dumps_result(result: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(
        result,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=False,
    ) + "\n"


def write_result(result: dict[str, Any], output_path: str | Path, *, pretty: bool = False) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps_result(result, pretty=pretty), encoding="utf-8", newline="\n")


def scan_weak_meter_cells_text(text: str) -> list[str]:
    """Detect markdown table cells with bare meter glyphs and no denominator."""

    findings: list[str] = []
    for line in text.splitlines():
        if "|" not in line or re.match(r"^\s*\|?\s*:?-{3,}", line):
            continue
        for match in _WEAK_METER_CELL_RE.finditer(line):
            meter = match.group("meter")
            if meter and not _line_has_meter_denominator(line, match.end()):
                findings.append(meter)
    return sorted(set(findings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run read-only cross-project smoke observations.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--smoke", help="cross_project_smoke.v1 JSON path.")
    source.add_argument("--default", action="store_true", help="Use the built-in DevCockpitCore smoke config.")
    parser.add_argument("--output", help="Output cross_project_smoke_result.v1 JSON path. Omit to write stdout.")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON.")
    args = parser.parse_args(argv)

    try:
        if args.default:
            smoke = validate_smoke(default_smoke())
            smoke_path = "default"
        else:
            smoke = load_smoke(args.smoke)
            smoke_path = args.smoke
        result = run_cross_project_smoke(smoke, smoke_path=smoke_path)
    except CrossProjectSmokeError as exc:
        print(f"cross-project smoke error: {exc}", file=sys.stderr)
        return 2

    payload = dumps_result(result, pretty=args.pretty)
    if args.output:
        write_result(result, args.output, pretty=args.pretty)
    else:
        print(payload, end="")
    return 1 if result["summary"]["result"] == "fail" else 0


def _smoke_adapter(
    adapter_path: str,
    *,
    required: bool,
    expected_default_branch: str,
    repo_path_override: str | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "adapter_path": adapter_path,
        "required": required,
        "repo_path_override": repo_path_override,
        "expected_default_branch": expected_default_branch,
        "notes": notes or [],
    }


def _observe_project(repo: Path, config: dict[str, Any]) -> dict[str, Any]:
    adapter_path = repo / config["adapter_path"]
    required = bool(config["required"])
    base_project = {
        "project_key": None,
        "project": None,
        "adapter_path": config["adapter_path"],
        "required": required,
    }

    try:
        adapter = load_adapter(adapter_path)
    except AdapterError as exc:
        result = "fail" if required else "warn"
        return {
            **base_project,
            "repo_resolution": _empty_resolution(),
            "status_snapshot": _empty_status_snapshot(),
            "adapter_validation": {"result": result, "warnings": [str(exc)]},
            "scope_boundary": _scope_boundary(False, False),
            "result": result,
            "done": 0,
            "total": 4,
            "unknown": 0,
            "meter": make_meter(0, 4, result=result, missing=4),
            "missing": 4,
        }

    candidates = _repo_candidates(adapter.raw, config)
    resolution = _resolve_repo(repo, candidates)
    project_base = {
        "project_key": adapter.project_key,
        "project": adapter.project,
        "adapter_path": config["adapter_path"],
        "required": required,
        "repo_resolution": resolution,
        "adapter_validation": {"result": "pass", "warnings": []},
    }

    selected_path = resolution.pop("_selected_path")
    if selected_path is None:
        result = "fail" if required else "skipped"
        notes = ["required repository path is missing"] if required else ["optional repository path is missing"]
        return {
            **project_base,
            "status_snapshot": _empty_status_snapshot(notes=notes),
            "scope_boundary": _scope_boundary(False, False),
            "result": result,
            "done": 1,
            "total": 4,
            "unknown": 0,
            "meter": make_meter(1, 4, result=result, missing=3),
            "missing": 3,
        }

    before_status, before_notes = inspect_repo(selected_path)
    try:
        snapshot = build_status_snapshot(selected_path, adapter_path)
    except (AdapterError, OSError) as exc:
        result = "fail" if required else "warn"
        return {
            **project_base,
            "status_snapshot": _empty_status_snapshot(notes=[str(exc)]),
            "scope_boundary": _scope_boundary(False, False),
            "result": result,
            "done": 2,
            "total": 4,
            "unknown": 0,
            "meter": make_meter(2, 4, result=result, missing=2),
            "missing": 2,
        }
    after_status, after_notes = inspect_repo(selected_path)

    modified = before_status.get("worktree") != after_status.get("worktree")
    boundary = _scope_boundary(snapshot_generated=True, target_repo_modified=modified)
    status_summary = _status_summary(snapshot, selected_path, before_notes + after_notes)
    warnings = _project_warnings(snapshot, config, modified)
    result = "fail" if modified else "warn" if warnings else "pass"
    if result == "fail" and not required:
        result = "warn"
    done = 4 if result != "fail" else 3
    missing = 0 if result != "fail" else 1
    return {
        **project_base,
        "status_snapshot": status_summary,
        "scope_boundary": boundary,
        "result": result,
        "done": done,
        "total": 4,
        "unknown": 0,
        "meter": make_meter(done, 4, result=result, missing=missing),
        "missing": missing,
    }


def _repo_candidates(adapter_data: dict[str, Any], config: dict[str, Any]) -> list[str]:
    override = config.get("repo_path_override")
    if override:
        return [override]
    repo_hints = adapter_data.get("repo_hints")
    paths = []
    if isinstance(repo_hints, dict):
        raw_paths = repo_hints.get("preferred_relative_paths")
        if isinstance(raw_paths, list):
            paths = [path for path in raw_paths if isinstance(path, str) and path.strip()]
    project_key = adapter_data.get("project_key")
    if not paths and isinstance(project_key, str) and project_key in _DEFAULT_REPO_HINTS:
        paths = [_DEFAULT_REPO_HINTS[project_key]]
    return paths


def _resolve_repo(repo: Path, candidates: list[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    selected: str | None = None
    selected_path: Path | None = None
    for candidate in candidates:
        candidate_path = (repo / candidate).resolve()
        exists = candidate_path.exists()
        rows.append(
            {
                "candidate": candidate,
                "exists": exists,
                "redacted_path": _redact_value(str(candidate_path)),
            }
        )
        if exists and selected_path is None:
            selected = candidate
            selected_path = candidate_path
    return {
        "candidates": rows,
        "selected": selected,
        "exists": selected_path is not None,
        "redacted_selected": _redact_value(str(selected_path)) if selected_path else None,
        "_selected_path": selected_path,
    }


def _status_summary(snapshot: dict[str, Any], path: Path, notes: list[str]) -> dict[str, Any]:
    repo = snapshot.get("repo") if isinstance(snapshot.get("repo"), dict) else {}
    health = snapshot.get("health") if isinstance(snapshot.get("health"), dict) else {}
    worktree = repo.get("worktree") if isinstance(repo.get("worktree"), dict) else {}
    remote_parity = repo.get("remote_parity") if isinstance(repo.get("remote_parity"), dict) else {}
    warnings = []
    warnings.extend(str(note) for note in health.get("notes", []) if note)
    warnings.extend(str(note) for note in notes if note)
    return {
        "generated": True,
        "path": _redact_value(str(path)),
        "schema_version": snapshot.get("schema_version"),
        "branch": repo.get("branch"),
        "head": repo.get("head"),
        "worktree": worktree,
        "remote_parity": remote_parity,
        "health": health.get("status"),
        "warnings": _redact_value(warnings),
    }


def _project_warnings(snapshot: dict[str, Any], config: dict[str, Any], modified: bool) -> list[str]:
    repo = snapshot.get("repo") if isinstance(snapshot.get("repo"), dict) else {}
    health = snapshot.get("health") if isinstance(snapshot.get("health"), dict) else {}
    worktree = repo.get("worktree") if isinstance(repo.get("worktree"), dict) else {}
    warnings: list[str] = []
    if health.get("status") == "yellow":
        warnings.append("status snapshot health is yellow")
    if worktree.get("state") == "dirty":
        warnings.append("target repository worktree is dirty")
    expected_branch = config.get("expected_default_branch")
    actual_branch = repo.get("branch")
    if expected_branch and actual_branch and actual_branch != expected_branch:
        warnings.append(f"branch {actual_branch!r} differs from expected {expected_branch!r}")
    parity = repo.get("remote_parity") if isinstance(repo.get("remote_parity"), dict) else {}
    if parity.get("status") in {"unknown", "behind", "diverged"}:
        warnings.append(f"remote parity is {parity.get('status')}")
    if modified:
        warnings.append("target repository worktree changed during observation")
    return warnings


def _empty_resolution() -> dict[str, Any]:
    return {
        "candidates": [],
        "selected": None,
        "exists": False,
        "redacted_selected": None,
    }


def _empty_status_snapshot(notes: list[str] | None = None) -> dict[str, Any]:
    return {
        "generated": False,
        "path": None,
        "schema_version": None,
        "branch": None,
        "head": None,
        "worktree": None,
        "remote_parity": None,
        "health": "unknown",
        "warnings": notes or [],
    }


def _scope_boundary(snapshot_generated: bool, target_repo_modified: bool) -> dict[str, Any]:
    return {
        "target_repo_modified": target_repo_modified,
        "target_repo_commands": "read_only_git_status_only" if snapshot_generated else "none",
        "default_validation_executed": False,
    }


def _summary(projects: list[dict[str, Any]], hygiene: dict[str, Any]) -> dict[str, Any]:
    total = len(projects)
    passed = sum(1 for item in projects if item["result"] == "pass")
    warnings = sum(1 for item in projects if item["result"] == "warn")
    failed = sum(1 for item in projects if item["result"] == "fail")
    skipped = sum(1 for item in projects if item["result"] == "skipped")
    unknown = sum(1 for item in projects if item["result"] not in {"pass", "warn", "fail", "skipped"})
    hygiene_warning_count = _hygiene_warning_count(hygiene)
    hygiene_failure_count = len(hygiene["raw_local_paths"]) + len(hygiene["forbidden_implementation_terms"])
    if hygiene_warning_count and not hygiene_failure_count:
        warnings += 1
    if hygiene_failure_count:
        failed += 1
    if failed:
        result = "fail"
    elif warnings or skipped or unknown:
        result = "warn"
    else:
        result = "pass"
    meter = "".join(_summary_meter_char(item["result"]) for item in projects)
    if hygiene_failure_count:
        meter += "!"
    elif hygiene_warning_count:
        meter += "~"
    return {
        "result": result,
        "done": passed + warnings,
        "total": total + (1 if hygiene_warning_count or hygiene_failure_count else 0),
        "unknown": unknown,
        "meter": meter,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "skipped": skipped,
        "missing": failed + skipped,
    }


def _summary_meter_char(result: str) -> str:
    return {
        "pass": "#",
        "warn": "~",
        "fail": "!",
        "skipped": "-",
    }.get(result, "?")


def _hygiene(repo: Path) -> dict[str, Any]:
    report_roots = ["samples/reports"]
    sample_roots = [
        "samples/reports",
        "samples/report_normalizations",
        "samples/gate_classifications",
        "samples/validation_packs",
        "samples/cross_project_smokes",
    ]
    source_roots = ["src"]
    return {
        "pseudo_git_tags": _scan_files(repo, report_roots, scan_pseudo_git_tags_text, "pseudo_git_tag"),
        "weak_meter_cells": _scan_files(repo, report_roots, scan_weak_meter_cells_text, "weak_meter_cell"),
        "paste_ready_prompt_residue": _scan_files(repo, report_roots, scan_prompt_residue_text, "prompt_residue"),
        "raw_local_paths": _raw_local_path_findings(repo, sample_roots),
        "mojibake_tokens": _scan_files(repo, report_roots, scan_mojibake_text, "mojibake_token"),
        "forbidden_implementation_terms": _forbidden_implementation_findings(repo, source_roots),
    }


def _hygiene_warning_count(hygiene: dict[str, Any]) -> int:
    return sum(
        len(hygiene[key])
        for key in ("pseudo_git_tags", "weak_meter_cells", "paste_ready_prompt_residue", "mojibake_tokens")
    )


def _health(
    summary: dict[str, Any],
    projects: list[dict[str, Any]],
    hygiene: dict[str, Any],
) -> dict[str, Any]:
    warnings = [
        f"{item['project_key'] or item['adapter_path']}: {item['result']}"
        for item in projects
        if item["result"] in {"warn", "skipped"}
    ]
    if _hygiene_warning_count(hygiene):
        warnings.append("report hygiene warnings present")
    blockers = [
        f"{item['project_key'] or item['adapter_path']}: failed"
        for item in projects
        if item["result"] == "fail"
    ]
    if hygiene["raw_local_paths"]:
        blockers.append("raw local paths detected")
    if hygiene["forbidden_implementation_terms"]:
        blockers.append("forbidden implementation terms detected")
    status = "red" if summary["result"] == "fail" else "yellow" if summary["result"] == "warn" else "green"
    stop_class = "VALIDATION_FAILED" if blockers else "INTEGRATE_AND_CONTINUE" if warnings else "NONE"
    return {
        "status": status,
        "warnings": _redact_value(warnings),
        "blockers": _redact_value(blockers),
        "stop_class": stop_class,
    }


def _gate_input(summary: dict[str, Any]) -> dict[str, Any]:
    if summary["result"] == "fail":
        return {
            "recommended_gate_decision": "blocked_validation",
            "stop_class": "VALIDATION_FAILED",
            "user_work": "none",
            "supervisor_should_generate_prompt": False,
        }
    if summary["result"] == "warn":
        return {
            "recommended_gate_decision": "integrate_and_continue",
            "stop_class": "INTEGRATE_AND_CONTINUE",
            "user_work": "none",
            "supervisor_should_generate_prompt": False,
        }
    return {
        "recommended_gate_decision": "completed_continue",
        "stop_class": "NONE",
        "user_work": "none",
        "supervisor_should_generate_prompt": False,
    }


def _scan_files(
    repo: Path,
    roots: list[str],
    scanner: Any,
    finding_key: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in _iter_text_files(repo, roots):
        matches = scanner(_read_limited_text(path))
        if matches:
            findings.append({"path": _rel(repo, path), finding_key: matches})
    return findings


def _raw_local_path_findings(repo: Path, roots: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in _iter_text_files(repo, roots):
        matches = scan_raw_local_paths_text(_read_limited_text(path))
        if matches["raw"]:
            findings.append({"path": _rel(repo, path), "matches": matches["raw"]})
    return findings


def _forbidden_implementation_findings(repo: Path, roots: list[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in _iter_text_files(repo, roots):
        matches = scan_forbidden_implementation_text(_read_limited_text(path), source_kind="src")
        if matches:
            findings.append({"path": _rel(repo, path), "matches": matches})
    return findings


def _iter_text_files(repo: Path, roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for relative in roots:
        root = repo / relative
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if not path.is_file():
                continue
            try:
                parts = path.relative_to(repo).parts
            except ValueError:
                continue
            if any(part in _IGNORED_DIRS for part in parts):
                continue
            if path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            files.append(path)
    return sorted(files)


def _read_limited_text(path: Path) -> str:
    try:
        if path.stat().st_size > TEXT_FILE_LIMIT_BYTES:
            return path.read_text(encoding="utf-8", errors="replace")[:TEXT_FILE_LIMIT_BYTES]
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"<read error: {exc}>"


def _line_has_meter_denominator(line: str, start: int) -> bool:
    tail = line[start : start + 24]
    return bool(re.search(r"\d+\s*/\s*\d+", tail))


def _reject_command_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in _COMMAND_FIELDS:
                raise CrossProjectSmokeError(f"cross-project smoke field {path}.{key} is not allowed")
            _reject_command_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_command_fields(child, f"{path}[{index}]")


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
        raise CrossProjectSmokeError(f"{field_path} must be a relative path")
    parts = PurePosixPath(normalized).parts
    if not allow_parent and ".." in parts:
        raise CrossProjectSmokeError(f"{field_path} must stay inside the DevCockpitCore repo")


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CrossProjectSmokeError(f"{key} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise CrossProjectSmokeError(f"{field} must be a list")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise CrossProjectSmokeError(f"{field} must contain only non-empty strings")
        output.append(item.strip())
    return output


def _rel(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return str(_redact_value(path.as_posix()))


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_absolute_user_paths(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_value(child) for key, child in value.items()}
    return value


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
