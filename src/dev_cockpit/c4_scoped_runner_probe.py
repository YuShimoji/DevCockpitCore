"""Run the single bounded C4 validation-pack probe."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from .controlled_runner_probe import ALLOWED_COMMAND_KEYS as C3_COMMAND_KEYS
from .controlled_runner_probe import redact_probe_value
from .git_status import inspect_repo
from .validation_pack import make_meter


PROBE_SCHEMA_VERSION = "c4_probe_minimal_implementation.v1"
RESULT_SCHEMA_VERSION = "c4_probe_minimal_result.v1"
PRODUCER = "dev_cockpit.c4_scoped_runner_probe"
DEFAULT_PROJECT_KEY = "devcockpitcore"
DEFAULT_PROBE_KEY = "devcockpitcore_validation_pack_default_pretty_probe"
C4_CAPABILITY_LEVEL = "C4_scoped_repo_local_probe"
C4_COMMAND_KEY = "validation_pack_default_pretty"
C4_COMMAND_KEYS = (C4_COMMAND_KEY,)
C4_COMMAND_CLASS = "fixed_repo_local_validation_probe"
DEFAULT_TIMEOUT_SECONDS = 60
MAX_TIMEOUT_SECONDS = 120
OUTPUT_EXCERPT_LIMIT = 4000
SUMMARY_GATE_TOTAL = 18

_FORBIDDEN_CONFIG_FIELDS = {
    "arg",
    "args",
    "argv",
    "cmd",
    "command",
    "commands",
    "cwd",
    "env",
    "environment",
    "executable",
    "retry",
    "retries",
    "shell",
}


class C4ScopedRunnerProbeError(ValueError):
    """Raised when a C4 probe config cannot be used safely."""


def default_probe() -> dict[str, Any]:
    """Return the single built-in C4 probe config."""

    return {
        "schema_version": PROBE_SCHEMA_VERSION,
        "probe_key": DEFAULT_PROBE_KEY,
        "project_key": DEFAULT_PROJECT_KEY,
        "command_key": C4_COMMAND_KEY,
        "capability_level": C4_CAPABILITY_LEVEL,
        "command_class": C4_COMMAND_CLASS,
        "description": "Run the fixed validation_pack --default --pretty probe with guarded evidence capture.",
        "expected_write_scope": "DevCockpitCore samples only",
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "enabled": True,
        "notes": [
            "This config selects one hardcoded C4 command key and cannot supply argv.",
            "The command is repo-local and writes no target repository artifacts.",
        ],
    }


def load_probe(path: str | Path) -> dict[str, Any]:
    probe_path = Path(path)
    try:
        data = json.loads(probe_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise C4ScopedRunnerProbeError(f"C4 probe config not found: {probe_path}") from exc
    except json.JSONDecodeError as exc:
        raise C4ScopedRunnerProbeError(f"C4 probe config is not valid JSON: {probe_path}: {exc}") from exc
    return validate_probe(data)


def validate_probe(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise C4ScopedRunnerProbeError("C4 probe config root must be a JSON object")
    _reject_executable_fields(data)

    schema_version = data.get("schema_version")
    if schema_version != PROBE_SCHEMA_VERSION:
        raise C4ScopedRunnerProbeError(f"schema_version must be {PROBE_SCHEMA_VERSION!r}")

    command_key = _required_string(data, "command_key")
    if command_key not in C4_COMMAND_KEYS:
        raise C4ScopedRunnerProbeError(f"unsupported C4 command_key: {command_key}")
    capability_level = _required_string(data, "capability_level")
    if capability_level != C4_CAPABILITY_LEVEL:
        raise C4ScopedRunnerProbeError(f"capability_level must be {C4_CAPABILITY_LEVEL!r}")
    command_class = _required_string(data, "command_class")
    if command_class != C4_COMMAND_CLASS:
        raise C4ScopedRunnerProbeError(f"command_class must be {C4_COMMAND_CLASS!r}")

    timeout_seconds = data.get("timeout_seconds")
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool):
        raise C4ScopedRunnerProbeError("timeout_seconds must be an integer")
    if timeout_seconds <= 0 or timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise C4ScopedRunnerProbeError(f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}")

    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise C4ScopedRunnerProbeError("enabled must be boolean")

    return {
        "schema_version": PROBE_SCHEMA_VERSION,
        "probe_key": _required_string(data, "probe_key"),
        "project_key": _required_string(data, "project_key"),
        "command_key": command_key,
        "capability_level": capability_level,
        "command_class": command_class,
        "description": _required_string(data, "description"),
        "expected_write_scope": _required_string(data, "expected_write_scope"),
        "timeout_seconds": timeout_seconds,
        "enabled": enabled,
        "notes": _string_list(data.get("notes", []), "notes"),
    }


def run_probe(
    probe: dict[str, Any],
    *,
    repo_path: str | Path = ".",
    probe_path: str | None = None,
    output_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    repo = Path(repo_path).resolve()
    if not probe["enabled"]:
        return _skipped_result(probe, repo, probe_path, generated_at)

    before_status, before_notes = inspect_repo(repo)
    command_result = _run_fixed_validation_pack(repo, probe["timeout_seconds"])
    after_status, after_notes = inspect_repo(repo)
    validation_result = _parse_validation_pack_result(command_result["stdout_raw"])

    safety = _safety_summary(before_status, after_status, command_result)
    known_warnings = _known_warnings(validation_result, before_status, after_status, before_notes + after_notes)
    summary = _summary(safety["blockers"], known_warnings)

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_iso(),
        "producer": PRODUCER,
        "project_key": probe["project_key"],
        "probe_key": probe["probe_key"],
        "probe_path": redact_probe_value(probe_path),
        "command_key": probe["command_key"],
        "capability_level": C4_CAPABILITY_LEVEL,
        "command_class": C4_COMMAND_CLASS,
        "command_source": "hardcoded_allowlist",
        "config_command_override_allowed": False,
        "config_executable_override_allowed": False,
        "config_argv_args_override_allowed": False,
        "shell": False,
        "timeout_seconds": probe["timeout_seconds"],
        "output_truncation_present": True,
        "redaction_present": True,
        "before_repo_state": redact_probe_value(before_status),
        "after_repo_state": redact_probe_value(after_status),
        "target_repo_writeback": False,
        "cross_project_execution": False,
        "scheduler_or_autonomy": False,
        "credentials_required": False,
        "adapter_default_validation_executed": False,
        "adapters_validate_as_controlled_command": False,
        "destructive_git": False,
        "force_push": False,
        "c3_command_set": list(C3_COMMAND_KEYS),
        "c4_command_set": list(C4_COMMAND_KEYS),
        "c5_c6_locked": True,
        "exit_code": command_result["exit_code"],
        "duration_ms": command_result["duration_ms"],
        "captured_stdout_preview": command_result["stdout_excerpt"],
        "captured_stderr_preview": command_result["stderr_excerpt"],
        "captured_stdout_truncated": command_result["stdout_truncated"],
        "captured_stderr_truncated": command_result["stderr_truncated"],
        "redactions_applied": command_result["redactions_applied"],
        "known_warnings": known_warnings,
        "safety": safety,
        "summary": summary,
        "next": {
            "recommended_next_slice": "common-foundation-c4-probe-minimal-implementation-review-v1",
            "supervisor_should_generate_prompt": True,
        },
    }


def dumps_result(result: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2 if pretty else None, sort_keys=False) + "\n"


def write_result(result: dict[str, Any], output_path: str | Path, *, pretty: bool = False) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps_result(result, pretty=pretty), encoding="utf-8", newline="\n")


def truncate_output(text: str, limit: int = OUTPUT_EXCERPT_LIMIT) -> tuple[str, bool]:
    safe = str(redact_probe_value(text))
    if len(safe) <= limit:
        return safe, False
    return safe[:limit], True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the single bounded C4 validation-pack probe.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--probe", help="c4_probe_minimal_implementation.v1 JSON path.")
    source.add_argument("--default", action="store_true", help="Use the built-in C4 validation-pack probe.")
    parser.add_argument("--output", help="Output c4_probe_minimal_result.v1 JSON path. Omit to write stdout.")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON.")
    args = parser.parse_args(argv)

    try:
        if args.default:
            probe = validate_probe(default_probe())
            probe_path = "default"
        else:
            probe = load_probe(args.probe)
            probe_path = args.probe
        result = run_probe(probe, probe_path=probe_path, output_path=args.output)
    except C4ScopedRunnerProbeError as exc:
        print(f"C4 scoped runner probe error: {exc}", file=sys.stderr)
        return 2

    payload = dumps_result(result, pretty=args.pretty)
    if args.output:
        write_result(result, args.output, pretty=args.pretty)
    else:
        print(payload, end="")
    return 1 if result["summary"]["result"] == "fail" else 0


def _run_fixed_validation_pack(repo: Path, timeout_seconds: int) -> dict[str, Any]:
    argv = _argv_for_command_key(C4_COMMAND_KEY)
    env = os.environ.copy()
    src = str(repo / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            argv,
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            shell=False,
            timeout=timeout_seconds,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout_excerpt, stdout_truncated = truncate_output(completed.stdout)
        stderr_excerpt, stderr_truncated = truncate_output(completed.stderr)
        return {
            "duration_ms": duration_ms,
            "exit_code": completed.returncode,
            "stdout_raw": completed.stdout,
            "stderr_raw": completed.stderr,
            "stdout_excerpt": stdout_excerpt,
            "stderr_excerpt": stderr_excerpt,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "timed_out": False,
            "redactions_applied": _redactions_applied(completed.stdout, completed.stderr, argv, str(repo)),
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        stdout_excerpt, stdout_truncated = truncate_output(stdout)
        stderr_excerpt, stderr_truncated = truncate_output(stderr)
        return {
            "duration_ms": duration_ms,
            "exit_code": None,
            "stdout_raw": stdout,
            "stderr_raw": stderr,
            "stdout_excerpt": stdout_excerpt,
            "stderr_excerpt": stderr_excerpt,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "timed_out": True,
            "redactions_applied": _redactions_applied(stdout, stderr, argv, str(repo)),
        }


def _argv_for_command_key(command_key: str) -> list[str]:
    if command_key == C4_COMMAND_KEY:
        return [sys.executable, "-m", "dev_cockpit.validation_pack", "--default", "--pretty"]
    raise C4ScopedRunnerProbeError(f"unsupported C4 command_key: {command_key}")


def _parse_validation_pack_result(stdout: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _safety_summary(
    before_status: dict[str, Any],
    after_status: dict[str, Any],
    command_result: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if command_result["timed_out"]:
        blockers.append("command timed out")
    elif command_result["exit_code"] != 0:
        blockers.append("validation_pack command returned non-zero exit code")
    if before_status.get("worktree") != after_status.get("worktree"):
        blockers.append("worktree changed during C4 probe command")
    if before_status.get("head") != after_status.get("head"):
        blockers.append("HEAD changed during C4 probe command")

    return {
        "single_c4_command_key": len(C4_COMMAND_KEYS) == 1,
        "hardcoded_allowlist_only": True,
        "config_command_override_allowed": False,
        "config_executable_override_allowed": False,
        "config_argv_args_override_allowed": False,
        "shell_false": True,
        "timeout_required": True,
        "output_truncation_present": True,
        "redaction_present": True,
        "before_after_repo_state_present": True,
        "target_repo_writeback": False,
        "cross_project_execution": False,
        "scheduler_or_autonomy": False,
        "credentials_required": False,
        "adapter_default_validation_executed": False,
        "adapters_validate_as_controlled_command": False,
        "destructive_git": False,
        "c5_c6_locked": True,
        "blockers": redact_probe_value(blockers),
    }


def _known_warnings(
    validation_result: dict[str, Any] | None,
    before_status: dict[str, Any],
    after_status: dict[str, Any],
    git_notes: list[str],
) -> dict[str, Any]:
    warnings: dict[str, Any] = {}
    pseudo_present = False
    validation_summary_result = None
    if validation_result:
        summary = validation_result.get("summary")
        if isinstance(summary, dict):
            validation_summary_result = summary.get("result")
        hygiene = validation_result.get("hygiene")
        if isinstance(hygiene, dict):
            pseudo_present = bool(hygiene.get("pseudo_git_tags"))
    warnings["validation_pack_summary_result"] = validation_summary_result or "unknown"
    warnings["pseudo_git_tag_fixture_warning"] = {
        "present": pseudo_present,
        "blocking": False,
        "interpretation": "Known validation-pack report fixture warning; not a C4 probe blocker.",
    }
    warnings["worktree_warning"] = {
        "present": _worktree_state(before_status) != "clean" or _worktree_state(after_status) != "clean",
        "blocking": False,
        "interpretation": "Worktree state is recorded as evidence and is blocking only if it changes during the command.",
    }
    warnings["git_notes"] = redact_probe_value(git_notes)
    return warnings


def _summary(blockers: list[str], known_warnings: dict[str, Any]) -> dict[str, Any]:
    warning_present = any(
        isinstance(value, dict) and bool(value.get("present"))
        for key, value in known_warnings.items()
        if key.endswith("_warning")
    )
    result = "fail" if blockers else "warn" if warning_present else "pass"
    missing = 1 if blockers else 0
    done = SUMMARY_GATE_TOTAL - missing
    return {
        "result": result,
        "done": done,
        "total": SUMMARY_GATE_TOTAL,
        "unknown": 0,
        "meter": make_meter(done, SUMMARY_GATE_TOTAL, result=result, missing=missing),
        "missing": missing,
    }


def _skipped_result(
    probe: dict[str, Any],
    repo: Path,
    probe_path: str | None,
    generated_at: str | None,
) -> dict[str, Any]:
    status, notes = inspect_repo(repo)
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_iso(),
        "producer": PRODUCER,
        "project_key": probe["project_key"],
        "probe_key": probe["probe_key"],
        "probe_path": redact_probe_value(probe_path),
        "command_key": probe["command_key"],
        "capability_level": C4_CAPABILITY_LEVEL,
        "command_class": C4_COMMAND_CLASS,
        "command_source": "hardcoded_allowlist",
        "config_command_override_allowed": False,
        "config_executable_override_allowed": False,
        "config_argv_args_override_allowed": False,
        "shell": False,
        "timeout_seconds": probe["timeout_seconds"],
        "output_truncation_present": True,
        "redaction_present": True,
        "before_repo_state": redact_probe_value(status),
        "after_repo_state": redact_probe_value(status),
        "target_repo_writeback": False,
        "cross_project_execution": False,
        "scheduler_or_autonomy": False,
        "credentials_required": False,
        "adapter_default_validation_executed": False,
        "adapters_validate_as_controlled_command": False,
        "destructive_git": False,
        "force_push": False,
        "c3_command_set": list(C3_COMMAND_KEYS),
        "c4_command_set": list(C4_COMMAND_KEYS),
        "c5_c6_locked": True,
        "exit_code": None,
        "captured_stdout_preview": "",
        "captured_stderr_preview": "",
        "known_warnings": {"git_notes": redact_probe_value(notes)},
        "summary": {
            "result": "skipped",
            "done": 0,
            "total": 1,
            "unknown": 0,
            "meter": make_meter(0, 1, result="skipped", missing=1),
            "missing": 1,
        },
        "next": {
            "recommended_next_slice": "common-foundation-c4-probe-minimal-implementation-review-v1",
            "supervisor_should_generate_prompt": True,
        },
    }


def _worktree_state(status: dict[str, Any]) -> str:
    worktree = status.get("worktree")
    if isinstance(worktree, dict):
        return str(worktree.get("state") or "unknown")
    return "unknown"


def _redactions_applied(*values: Any) -> list[str]:
    applied: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, str):
            if redact_probe_value(value) != value:
                applied.add("local_user_path")
            return
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
            return
        if isinstance(value, (list, tuple, set)):
            for child in value:
                visit(child)
            return
        if isinstance(value, Path):
            visit(str(value))

    for value in values:
        visit(value)
    return sorted(applied)


def _reject_executable_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in _FORBIDDEN_CONFIG_FIELDS:
                raise C4ScopedRunnerProbeError(f"C4 probe config field {path}.{key} is not allowed")
            _reject_executable_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_executable_fields(child, f"{path}[{index}]")


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise C4ScopedRunnerProbeError(f"{key} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise C4ScopedRunnerProbeError(f"{field} must be a list")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise C4ScopedRunnerProbeError(f"{field} must contain only non-empty strings")
        output.append(item.strip())
    return output


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
