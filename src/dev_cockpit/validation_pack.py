"""Run fixed DevCockpitCore validation packs and emit structured results."""

from __future__ import annotations

import argparse
import compileall
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Callable

from .adapters import AdapterError, load_adapter
from .git_status import inspect_repo
from .report_normalizer import redact_absolute_user_paths


PACK_SCHEMA_VERSION = "validation_pack.v1"
RESULT_SCHEMA_VERSION = "validation_pack_result.v1"
PRODUCER = "dev_cockpit.validation_pack"
DEFAULT_PACK_KEY = "devcockpitcore_default"
DEFAULT_PROJECT_KEY = "devcockpitcore"
DEFAULT_PACK_PATH = "samples/validation_packs/devcockpitcore_validation_pack.json"
SNIPPET_LIMIT = 4000
TEXT_FILE_LIMIT_BYTES = 1024 * 1024

_TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
_IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".serena",
    "__pycache__",
    "build",
    "dist",
}
_COMMAND_FIELDS = {"command", "commands", "cmd", "args", "argv"}
_PASTE_PROMPT_MARKERS = (
    "[PASTE TARGET:",
    "output_type=SUPERVISOR_PROMPT",
    "Goal Stack:",
    "Allowed scope:",
    "Report format:",
)
_PSEUDO_GIT_RE = re.compile(r"(?P<tag>::git-[A-Za-z0-9_-]+)(?:\{[^}]*\})?")
_CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
_MOJIBAKE_TOKENS = (
    "\u9a3e\uff76",
    "\u95d6\uff6b",
    "\u90e2\uff67",
    "\u90e2\uff65",
    "\u90b5\uff7a",
    "\u95d4\uff65",
    "\u96b4\uff65",
    "\u30fb\uff7d",
)
_WINDOWS_USER_PATH_RE = re.compile(
    r"(?P<path>[A-Za-z]:\\Users\\(?P<user><redacted>|[^\\\s\]\)\"']+)"
    r"(?P<rest>(?:\\[^\s\]\)\"']+)*)?)"
)
_UNIX_USER_PATH_RE = re.compile(
    r"(?P<path>/(?:home|Users)/(?P<user><redacted>|[^/\s\]\)\"']+)"
    r"(?P<rest>(?:/[^\s\]\)\"']+)*)?)"
)
_FORBIDDEN_SOURCE_PATTERNS = (
    ("shell_true", re.compile(r"shell\s*=\s*True")),
    ("os_system", re.compile(r"\bos\.system\s*\(")),
    ("popen", re.compile(r"\bsubprocess\.Popen\s*\(")),
    ("scheduler_library", re.compile(r"\b(?:APScheduler|BackgroundScheduler|import\s+sched)\b")),
    ("external_notification", re.compile(r"\b(?:smtplib|slack_send_message|webhook_url)\b")),
    ("database", re.compile(r"\b(?:sqlite3|psycopg2|sqlalchemy|create_engine)\b")),
    ("web_server", re.compile(r"\b(?:http\.server|socketserver|FastAPI|Flask|uvicorn)\b")),
    ("credential_handling", re.compile(r"\b(?:keyring|SecretStr|CredentialManager)\b")),
    ("target_repo_writeback", re.compile(r"\b(?:git\s+push|git\s+commit|git\s+reset|git\s+rebase)\b")),
    ("auto_render", re.compile(r"\b(?:auto_render|render_queue|render_worker)\b")),
    ("exec_loop", re.compile(r"\b(?:exec_loop|autonomous_runner|CommandRunner)\b")),
)


class ValidationPackError(ValueError):
    """Raised when a validation pack cannot be loaded safely."""


def default_pack() -> dict[str, Any]:
    """Return the built-in DevCockpitCore validation pack."""

    checks = [
        _pack_check("python_compile", "python", "required", paths=["src", "tests"]),
        _pack_check("unittest_discover", "python", "required"),
        _pack_check("adapter_manifest_validation", "schema", "required", paths=["adapters"]),
        _pack_check("status_snapshot_help", "cli", "required"),
        _pack_check("report_normalizer_help", "cli", "required"),
        _pack_check("gate_classifier_help", "cli", "required"),
        _pack_check("json_parse", "json", "required", paths=["adapters", "samples"]),
        _pack_check("git_diff_check", "git", "required"),
        _pack_check("git_diff_cached_check", "git", "warning"),
        _pack_check("git_status", "git", "warning"),
        _pack_check("conflict_marker_scan", "scan", "required"),
        _pack_check(
            "prompt_residue_scan",
            "scan",
            "warning",
            paths=["samples/reports"],
            allow_fixture_hits=True,
        ),
        _pack_check(
            "pseudo_git_tag_scan",
            "scan",
            "warning",
            paths=["samples/reports"],
            allow_fixture_hits=True,
        ),
        _pack_check(
            "raw_local_path_scan",
            "scan",
            "required",
            paths=["samples/reports", "samples/report_normalizations", "samples/gate_classifications"],
        ),
        _pack_check(
            "mojibake_scan",
            "scan",
            "warning",
            paths=["samples/reports"],
            allow_fixture_hits=True,
        ),
        _pack_check("forbidden_implementation_scan", "scan", "required", paths=["src"]),
    ]
    return {
        "schema_version": PACK_SCHEMA_VERSION,
        "pack_key": DEFAULT_PACK_KEY,
        "project_key": DEFAULT_PROJECT_KEY,
        "description": "Default fixed safe validation checks for DevCockpitCore.",
        "checks": checks,
    }


def load_pack(path: str | Path) -> dict[str, Any]:
    """Load and validate a validation_pack.v1 JSON file."""

    pack_path = Path(path)
    try:
        data = json.loads(pack_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationPackError(f"validation pack not found: {pack_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationPackError(f"validation pack is not valid JSON: {pack_path}: {exc}") from exc
    return validate_pack(data)


def validate_pack(data: dict[str, Any]) -> dict[str, Any]:
    """Validate pack structure without accepting executable command fields."""

    if not isinstance(data, dict):
        raise ValidationPackError("validation pack root must be a JSON object")
    _reject_command_fields(data)

    schema_version = data.get("schema_version")
    if schema_version != PACK_SCHEMA_VERSION:
        raise ValidationPackError(f"schema_version must be {PACK_SCHEMA_VERSION!r}")

    pack_key = _required_string(data, "pack_key")
    project_key = _required_string(data, "project_key")
    description = _required_string(data, "description")
    checks_value = data.get("checks")
    if not isinstance(checks_value, list) or not checks_value:
        raise ValidationPackError("checks must be a non-empty list")

    checks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(checks_value):
        if not isinstance(item, dict):
            raise ValidationPackError(f"checks[{index}] must be an object")
        check_key = _required_string(item, "check_key")
        if check_key not in _RUNNERS:
            raise ValidationPackError(f"checks[{index}].check_key is not allowlisted: {check_key}")
        if check_key in seen:
            raise ValidationPackError(f"duplicate check_key: {check_key}")
        seen.add(check_key)

        kind = _required_string(item, "kind")
        severity = _required_string(item, "severity")
        if severity not in {"required", "warning", "optional"}:
            raise ValidationPackError(f"checks[{index}].severity must be required, warning, or optional")
        enabled = item.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ValidationPackError(f"checks[{index}].enabled must be boolean")
        paths = _string_list(item.get("paths", []), f"checks[{index}].paths")
        targets = _string_list(item.get("targets", []), f"checks[{index}].targets")
        allow_fixture_hits = item.get("allow_fixture_hits", False)
        if not isinstance(allow_fixture_hits, bool):
            raise ValidationPackError(f"checks[{index}].allow_fixture_hits must be boolean")
        notes = _string_list(item.get("notes", []), f"checks[{index}].notes")
        checks.append(
            {
                "check_key": check_key,
                "kind": kind,
                "severity": severity,
                "enabled": enabled,
                "paths": paths,
                "targets": targets,
                "allow_fixture_hits": allow_fixture_hits,
                "notes": notes,
            }
        )

    return {
        "schema_version": PACK_SCHEMA_VERSION,
        "pack_key": pack_key,
        "project_key": project_key,
        "description": description,
        "checks": checks,
    }


def run_validation_pack(
    pack: dict[str, Any],
    *,
    repo_path: str | Path = ".",
    pack_path: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Run a validated pack against the current DevCockpitCore repository."""

    repo = Path(repo_path).resolve()
    checks: list[dict[str, Any]] = []
    for check in pack["checks"]:
        if not check["enabled"]:
            checks.append(_check_result(check, "skipped", 0, 1, missing=1, notes=["check disabled"]))
            continue
        runner = _RUNNERS[check["check_key"]]
        checks.append(runner(repo, check))

    summary = _summary(checks)
    repo_status, git_notes = inspect_repo(repo)
    repo_summary = _repo_result(repo_status)
    health = _health(summary, checks, git_notes)
    hygiene = _hygiene(checks)

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_iso(),
        "producer": PRODUCER,
        "pack": {
            "pack_key": pack["pack_key"],
            "pack_path": pack_path,
            "project_key": pack["project_key"],
        },
        "repo": repo_summary,
        "summary": summary,
        "checks": checks,
        "hygiene": hygiene,
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


def make_meter(
    done: int,
    total: int,
    unknown: int = 0,
    *,
    result: str | None = None,
    missing: int | None = None,
) -> str:
    """Build an ASCII-safe meter using #, -, ?, ~, and !."""

    done = max(done, 0)
    total = max(total, 0)
    unknown = max(unknown, 0)
    missing_count = max(missing if missing is not None else total - done - unknown, 0)
    width = max(total, 1)

    if result == "skipped":
        return "-" * width
    if result == "fail":
        risk_count = max(1, min(width, missing_count or width - done or 1))
        safe_done = max(0, width - risk_count - unknown)
        return "#" * safe_done + "?" * min(unknown, width - safe_done) + "!" * risk_count
    if result == "warn":
        partial_count = max(1, min(width, missing_count or width - done or 1))
        safe_done = max(0, width - partial_count - unknown)
        return "#" * safe_done + "?" * min(unknown, width - safe_done) + "~" * partial_count

    meter = "#" * min(done, width)
    remaining = width - len(meter)
    meter += "?" * min(unknown, remaining)
    remaining = width - len(meter)
    meter += "-" * remaining
    return meter


def scan_conflict_markers_text(text: str) -> list[str]:
    found: list[str] = []
    for line in text.splitlines():
        for marker in _CONFLICT_MARKERS:
            if line.startswith(marker):
                found.append(marker)
                break
    return sorted(set(found), key=_CONFLICT_MARKERS.index)


def scan_prompt_residue_text(text: str) -> list[str]:
    return [marker for marker in _PASTE_PROMPT_MARKERS if marker in text]


def scan_pseudo_git_tags_text(text: str) -> list[str]:
    return sorted({match.group("tag") for match in _PSEUDO_GIT_RE.finditer(text)})


def scan_mojibake_text(text: str) -> list[str]:
    return sorted(token for token in _MOJIBAKE_TOKENS if token in text)


def scan_raw_local_paths_text(text: str) -> dict[str, list[str]]:
    raw: list[str] = []
    redacted: list[str] = []
    for regex in (_WINDOWS_USER_PATH_RE, _UNIX_USER_PATH_RE):
        for match in regex.finditer(text):
            path = match.group("path")
            if match.group("user") == "<redacted>":
                redacted.append(path)
            else:
                raw.append(path)
    return {
        "raw": sorted(set(raw)),
        "redacted": sorted(set(redacted)),
    }


def scan_forbidden_implementation_text(text: str, *, source_kind: str) -> list[str]:
    if source_kind != "src":
        return []
    text = _strip_forbidden_detector_definitions(text)
    return [name for name, regex in _FORBIDDEN_SOURCE_PATTERNS if regex.search(text)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a fixed DevCockpitCore validation pack.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--pack", help="validation_pack.v1 JSON path.")
    source.add_argument("--default", action="store_true", help="Use the built-in DevCockpitCore pack.")
    parser.add_argument("--output", help="Output validation_pack_result.v1 JSON path. Omit to write stdout.")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON.")
    args = parser.parse_args(argv)

    try:
        if args.default:
            pack = validate_pack(default_pack())
            pack_path = "default"
        else:
            pack = load_pack(args.pack)
            pack_path = args.pack
        result = run_validation_pack(pack, pack_path=pack_path)
    except ValidationPackError as exc:
        print(f"validation pack error: {exc}", file=sys.stderr)
        return 2

    payload = dumps_result(result, pretty=args.pretty)
    if args.output:
        write_result(result, args.output, pretty=args.pretty)
    else:
        print(payload, end="")
    return 1 if result["summary"]["result"] == "fail" else 0


def _pack_check(
    check_key: str,
    kind: str,
    severity: str,
    *,
    paths: list[str] | None = None,
    targets: list[str] | None = None,
    allow_fixture_hits: bool = False,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "check_key": check_key,
        "kind": kind,
        "severity": severity,
        "enabled": True,
        "paths": paths or [],
        "targets": targets or [],
        "allow_fixture_hits": allow_fixture_hits,
        "notes": notes or [],
    }


def _run_python_compile(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    paths = check["paths"] or ["src", "tests"]
    findings: list[dict[str, Any]] = []
    passed = 0
    missing: list[str] = []
    for relative in paths:
        path = repo / relative
        if not path.exists():
            missing.append(relative)
            continue
        ok = compileall.compile_dir(str(path), quiet=1)
        if ok:
            passed += 1
        else:
            findings.append({"path": relative, "message": "compileall reported a failure"})
    result = _result_from_findings(check, findings, missing=missing)
    return _check_result(check, result, passed, len(paths), findings=findings, missing=len(findings) + len(missing))


def _run_unittest_discover(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    command = [sys.executable, "-m", "unittest", "discover"]
    completed = _run_fixed_command(repo, command)
    result = "pass" if completed["exit_code"] == 0 else _failure_result(check)
    findings = [] if result == "pass" else [{"message": "unittest discovery failed"}]
    return _check_result(
        check,
        result,
        1 if result == "pass" else 0,
        1,
        command=command,
        exit_code=completed["exit_code"],
        findings=findings,
        missing=0 if result == "pass" else 1,
        notes=[_command_note(completed)],
    )


def _run_adapter_manifest_validation(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    adapter_dir = repo / "adapters"
    paths = sorted(adapter_dir.glob("*.json"))
    findings: list[dict[str, Any]] = []
    if not adapter_dir.exists():
        return _check_result(check, _failure_result(check), 0, 1, missing=1, findings=[{"path": "adapters", "message": "directory missing"}])
    for path in paths:
        try:
            load_adapter(path)
        except AdapterError as exc:
            findings.append({"path": _rel(repo, path), "message": str(exc)})
    result = _result_from_findings(check, findings)
    passed = len(paths) - len(findings)
    return _check_result(check, result, passed, len(paths) or 1, findings=findings, missing=len(findings))


def _run_status_snapshot_help(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    return _run_help_check(repo, check, "dev_cockpit.status_snapshot")


def _run_report_normalizer_help(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    return _run_help_check(repo, check, "dev_cockpit.report_normalizer")


def _run_gate_classifier_help(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    return _run_help_check(repo, check, "dev_cockpit.gate_classifier")


def _run_help_check(repo: Path, check: dict[str, Any], module: str) -> dict[str, Any]:
    command = [sys.executable, "-m", module, "--help"]
    completed = _run_fixed_command(repo, command)
    result = "pass" if completed["exit_code"] == 0 else _failure_result(check)
    findings = [] if result == "pass" else [{"message": f"{module} --help failed"}]
    return _check_result(
        check,
        result,
        1 if result == "pass" else 0,
        1,
        command=command,
        exit_code=completed["exit_code"],
        findings=findings,
        missing=0 if result == "pass" else 1,
        notes=[_command_note(completed)],
    )


def _run_json_parse(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    files = list(_iter_text_files(repo, check["paths"] or ["adapters", "samples"], suffixes={".json"}))
    findings: list[dict[str, Any]] = []
    for path in files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append({"path": _rel(repo, path), "message": str(exc)})
    result = _result_from_findings(check, findings)
    passed = len(files) - len(findings)
    return _check_result(check, result, passed, len(files) or 1, findings=findings, missing=len(findings))


def _run_git_diff_check(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    return _run_git_check(repo, check, ["git", "diff", "--check"])


def _run_git_diff_cached_check(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    return _run_git_check(repo, check, ["git", "diff", "--cached", "--check"])


def _run_git_check(repo: Path, check: dict[str, Any], command: list[str]) -> dict[str, Any]:
    completed = _run_fixed_command(repo, command)
    result = "pass" if completed["exit_code"] == 0 else _failure_result(check)
    findings = [] if result == "pass" else [{"message": "git whitespace check failed"}]
    return _check_result(
        check,
        result,
        1 if result == "pass" else 0,
        1,
        command=command,
        exit_code=completed["exit_code"],
        findings=findings,
        missing=0 if result == "pass" else 1,
        notes=[_command_note(completed)],
    )


def _run_git_status(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    command = ["git", "status", "--short", "--branch"]
    completed = _run_fixed_command(repo, command)
    result = "pass" if completed["exit_code"] == 0 else _failure_result(check)
    findings = [] if result == "pass" else [{"message": "git status failed"}]
    notes = [_command_note(completed)]
    if completed["exit_code"] == 0 and completed["stdout_snippet"]:
        notes.append(completed["stdout_snippet"])
    return _check_result(
        check,
        result,
        1 if result == "pass" else 0,
        1,
        command=command,
        exit_code=completed["exit_code"],
        findings=findings,
        missing=0 if result == "pass" else 1,
        notes=notes,
    )


def _run_conflict_marker_scan(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    findings = _scan_files(repo, check["paths"] or ["."], scan_conflict_markers_text, "conflict_marker")
    result = _result_from_findings(check, findings)
    return _check_result(
        check,
        result,
        0 if findings else 1,
        1,
        findings=findings,
        missing=1 if findings else 0,
    )


def _run_prompt_residue_scan(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    findings = _scan_files(repo, check["paths"] or ["samples/reports"], scan_prompt_residue_text, "prompt_residue")
    result = _fixture_result(check, findings)
    return _check_result(check, result, 1, 1, findings=findings, missing=0 if result != "fail" else 1)


def _run_pseudo_git_tag_scan(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    findings = _scan_files(repo, check["paths"] or ["samples/reports"], scan_pseudo_git_tags_text, "pseudo_git_tag")
    result = _fixture_result(check, findings)
    return _check_result(check, result, 1, 1, findings=findings, missing=0 if result != "fail" else 1)


def _run_raw_local_path_scan(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    raw_findings: list[dict[str, Any]] = []
    redacted_count = 0
    for path in _iter_text_files(repo, check["paths"] or ["samples"]):
        text = _read_limited_text(path)
        matches = scan_raw_local_paths_text(text)
        redacted_count += len(matches["redacted"])
        if matches["raw"]:
            raw_findings.append({"path": _rel(repo, path), "matches": matches["raw"]})
    result = _result_from_findings(check, raw_findings)
    notes = [f"redacted local path references observed: {redacted_count}"] if redacted_count else []
    return _check_result(check, result, 1, 1, findings=raw_findings, missing=len(raw_findings), notes=notes)


def _run_mojibake_scan(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    findings = _scan_files(repo, check["paths"] or ["samples/reports"], scan_mojibake_text, "mojibake_token")
    result = _fixture_result(check, findings)
    return _check_result(check, result, 1, 1, findings=findings, missing=0 if result != "fail" else 1)


def _run_forbidden_implementation_scan(repo: Path, check: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for path in _iter_text_files(repo, check["paths"] or ["src"]):
        text = _read_limited_text(path)
        matches = scan_forbidden_implementation_text(text, source_kind="src")
        if matches:
            findings.append({"path": _rel(repo, path), "matches": matches})
    result = _result_from_findings(check, findings)
    return _check_result(check, result, 1, 1, findings=findings, missing=len(findings))


def _scan_files(
    repo: Path,
    roots: list[str],
    scanner: Callable[[str], list[str]],
    finding_key: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in _iter_text_files(repo, roots):
        matches = scanner(_read_limited_text(path))
        if matches:
            findings.append({"path": _rel(repo, path), finding_key: matches})
    return findings


def _check_result(
    check: dict[str, Any],
    result: str,
    done: int,
    total: int,
    *,
    unknown: int = 0,
    command: list[str] | None = None,
    exit_code: int | None = None,
    findings: list[dict[str, Any]] | None = None,
    missing: int = 0,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "check_key": check["check_key"],
        "kind": check["kind"],
        "result": result,
        "done": done,
        "total": total,
        "unknown": unknown,
        "meter": make_meter(done, total, unknown, result=result, missing=missing),
        "severity": check["severity"],
        "command": _redact_value(command),
        "exit_code": exit_code,
        "findings": _redact_value(findings or []),
        "missing": missing,
        "notes": _redact_value(list(check.get("notes") or []) + list(notes or [])),
    }


def _summary(checks: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(checks)
    passed = sum(1 for check in checks if check["result"] == "pass")
    warnings = sum(1 for check in checks if check["result"] == "warn")
    failed = sum(1 for check in checks if check["result"] == "fail")
    skipped = sum(1 for check in checks if check["result"] == "skipped")
    unknown = sum(1 for check in checks if check["result"] not in {"pass", "warn", "fail", "skipped"})
    if failed:
        result = "fail"
    elif warnings or skipped or unknown:
        result = "warn"
    else:
        result = "pass"
    meter = "".join(_summary_meter_char(check["result"]) for check in checks)
    return {
        "result": result,
        "done": passed + warnings,
        "total": total,
        "unknown": unknown,
        "meter": meter,
        "missing": failed + skipped,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "skipped": skipped,
    }


def _summary_meter_char(result: str) -> str:
    return {
        "pass": "#",
        "warn": "~",
        "fail": "!",
        "skipped": "-",
    }.get(result, "?")


def _repo_result(repo_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": _redact_value(repo_status.get("path")),
        "branch": repo_status.get("branch"),
        "head": repo_status.get("head"),
        "worktree": repo_status.get("worktree"),
        "remote_parity": repo_status.get("remote_parity"),
    }


def _health(
    summary: dict[str, Any],
    checks: list[dict[str, Any]],
    git_notes: list[str],
) -> dict[str, Any]:
    warnings = [
        f"{check['check_key']}: findings present"
        for check in checks
        if check["result"] == "warn"
    ]
    warnings.extend(git_notes)
    blockers = [
        f"{check['check_key']}: failed"
        for check in checks
        if check["result"] == "fail"
    ]
    status = "red" if summary["result"] == "fail" else "yellow" if summary["result"] == "warn" else "green"
    stop_class = "VALIDATION_FAILED" if blockers else "INTEGRATE_AND_CONTINUE" if warnings else "NONE"
    return {
        "status": status,
        "warnings": _redact_value(warnings),
        "blockers": _redact_value(blockers),
        "stop_class": stop_class,
    }


def _hygiene(checks: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = {check["check_key"]: check for check in checks}
    return {
        "pseudo_git_tags": by_key.get("pseudo_git_tag_scan", {}).get("findings", []),
        "paste_ready_prompt_residue": by_key.get("prompt_residue_scan", {}).get("findings", []),
        "raw_local_paths": by_key.get("raw_local_path_scan", {}).get("findings", []),
        "mojibake_tokens": by_key.get("mojibake_scan", {}).get("findings", []),
        "forbidden_implementation_terms": by_key.get("forbidden_implementation_scan", {}).get("findings", []),
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


def _run_fixed_command(repo: Path, command: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    src = str(repo / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        shell=False,
    )
    duration = round(time.perf_counter() - started, 3)
    return {
        "command": command,
        "exit_code": completed.returncode,
        "duration_seconds": duration,
        "stdout_snippet": _snippet(completed.stdout),
        "stderr_snippet": _snippet(completed.stderr),
    }


def _command_note(completed: dict[str, Any]) -> str:
    return (
        f"exit={completed['exit_code']} duration_seconds={completed['duration_seconds']} "
        f"stdout={completed['stdout_snippet']!r} stderr={completed['stderr_snippet']!r}"
    )


def _snippet(value: str) -> str:
    return str(_redact_value(value))[:SNIPPET_LIMIT]


def _failure_result(check: dict[str, Any]) -> str:
    return "warn" if check["severity"] in {"warning", "optional"} else "fail"


def _result_from_findings(
    check: dict[str, Any],
    findings: list[dict[str, Any]],
    *,
    missing: list[str] | None = None,
) -> str:
    if findings or missing:
        return _failure_result(check)
    return "pass"


def _fixture_result(check: dict[str, Any], findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "pass"
    if check.get("allow_fixture_hits") or check["severity"] in {"warning", "optional"}:
        return "warn"
    return "fail"


def _iter_text_files(
    repo: Path,
    roots: list[str],
    *,
    suffixes: set[str] | None = None,
) -> list[Path]:
    files: list[Path] = []
    allowed_suffixes = suffixes or _TEXT_SUFFIXES
    for relative in roots:
        root = repo / relative
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if not path.is_file():
                continue
            try:
                relative_parts = path.relative_to(repo).parts
            except ValueError:
                continue
            if any(part in _IGNORED_DIRS for part in relative_parts):
                continue
            if path.suffix.lower() not in allowed_suffixes:
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


def _rel(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return str(_redact_value(path.as_posix()))


def _reject_command_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in _COMMAND_FIELDS:
                raise ValidationPackError(f"validation pack field {path}.{key} is not allowed")
            _reject_command_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_command_fields(child, f"{path}[{index}]")


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationPackError(f"{key} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValidationPackError(f"{field} must be a list")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValidationPackError(f"{field} must contain only non-empty strings")
        output.append(item.strip())
    return output


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_absolute_user_paths(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_value(child) for key, child in value.items()}
    return value


def _strip_forbidden_detector_definitions(text: str) -> str:
    lines: list[str] = []
    skipping = False
    paren_depth = 0
    for line in text.splitlines():
        if not skipping and line.startswith("_FORBIDDEN_SOURCE_PATTERNS = ("):
            skipping = True
            paren_depth = line.count("(") - line.count(")")
            continue
        if skipping:
            paren_depth += line.count("(") - line.count(")")
            if paren_depth <= 0:
                skipping = False
            continue
        lines.append(line)
    return "\n".join(lines)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


_RUNNERS: dict[str, Callable[[Path, dict[str, Any]], dict[str, Any]]] = {
    "python_compile": _run_python_compile,
    "unittest_discover": _run_unittest_discover,
    "adapter_manifest_validation": _run_adapter_manifest_validation,
    "status_snapshot_help": _run_status_snapshot_help,
    "report_normalizer_help": _run_report_normalizer_help,
    "gate_classifier_help": _run_gate_classifier_help,
    "json_parse": _run_json_parse,
    "git_diff_check": _run_git_diff_check,
    "git_diff_cached_check": _run_git_diff_cached_check,
    "git_status": _run_git_status,
    "conflict_marker_scan": _run_conflict_marker_scan,
    "prompt_residue_scan": _run_prompt_residue_scan,
    "pseudo_git_tag_scan": _run_pseudo_git_tag_scan,
    "raw_local_path_scan": _run_raw_local_path_scan,
    "mojibake_scan": _run_mojibake_scan,
    "forbidden_implementation_scan": _run_forbidden_implementation_scan,
}


if __name__ == "__main__":
    raise SystemExit(main())
