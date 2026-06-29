"""Run one guarded DevCockpitCore-local command probe."""

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

from .git_status import inspect_repo
from .report_normalizer import redact_absolute_user_paths
from .validation_pack import make_meter


PROBE_SCHEMA_VERSION = "controlled_runner_probe.v1"
RESULT_SCHEMA_VERSION = "controlled_runner_probe_result.v1"
PRODUCER = "dev_cockpit.controlled_runner_probe"
DEFAULT_PROBE_KEY = "devcockpitcore_status_snapshot_help_probe"
DEFAULT_PROJECT_KEY = "devcockpitcore"
STATUS_SNAPSHOT_HELP_KEY = "status_snapshot_help"
ADAPTERS_VALIDATE_HELP_KEY = "adapters_validate_help"
ALLOWED_COMMAND_KEY = STATUS_SNAPSHOT_HELP_KEY
ALLOWED_COMMAND_KEYS = (STATUS_SNAPSHOT_HELP_KEY, ADAPTERS_VALIDATE_HELP_KEY)
ALLOWED_COMMAND_CLASS = "fixed_repo_local_help"
DEFAULT_TIMEOUT_SECONDS = 10
MAX_TIMEOUT_SECONDS = 30
OUTPUT_EXCERPT_LIMIT = 4000
_FORBIDDEN_CONFIG_FIELDS = {
    "arg",
    "args",
    "argv",
    "cmd",
    "command",
    "commands",
    "executable",
    "shell",
}


class ControlledRunnerProbeError(ValueError):
    """Raised when a probe config cannot be used safely."""


def default_probe() -> dict[str, Any]:
    """Return the built-in default probe config."""

    return {
        "schema_version": PROBE_SCHEMA_VERSION,
        "probe_key": DEFAULT_PROBE_KEY,
        "project_key": DEFAULT_PROJECT_KEY,
        "command_key": ALLOWED_COMMAND_KEY,
        "command_class": ALLOWED_COMMAND_CLASS,
        "description": "Run the fixed status_snapshot --help probe with guarded evidence capture.",
        "expected_write_scope": "DevCockpitCore samples only",
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "enabled": True,
        "notes": [
            "This config selects one hardcoded command key and cannot supply argv.",
        ],
    }


def load_probe(path: str | Path) -> dict[str, Any]:
    probe_path = Path(path)
    try:
        data = json.loads(probe_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ControlledRunnerProbeError(f"controlled runner probe not found: {probe_path}") from exc
    except json.JSONDecodeError as exc:
        raise ControlledRunnerProbeError(f"controlled runner probe is not valid JSON: {probe_path}: {exc}") from exc
    return validate_probe(data)


def validate_probe(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ControlledRunnerProbeError("controlled runner probe root must be a JSON object")
    _reject_executable_fields(data)

    schema_version = data.get("schema_version")
    if schema_version != PROBE_SCHEMA_VERSION:
        raise ControlledRunnerProbeError(f"schema_version must be {PROBE_SCHEMA_VERSION!r}")

    command_key = _required_string(data, "command_key")
    if command_key not in ALLOWED_COMMAND_KEYS:
        raise ControlledRunnerProbeError(f"unsupported command_key: {command_key}")
    command_class = _required_string(data, "command_class")
    if command_class != ALLOWED_COMMAND_CLASS:
        raise ControlledRunnerProbeError(f"unsupported command_class: {command_class}")

    timeout_seconds = data.get("timeout_seconds")
    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool):
        raise ControlledRunnerProbeError("timeout_seconds must be an integer")
    if timeout_seconds <= 0 or timeout_seconds > MAX_TIMEOUT_SECONDS:
        raise ControlledRunnerProbeError(f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}")

    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise ControlledRunnerProbeError("enabled must be boolean")

    return {
        "schema_version": PROBE_SCHEMA_VERSION,
        "probe_key": _required_string(data, "probe_key"),
        "project_key": _required_string(data, "project_key"),
        "command_key": command_key,
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
        return _skipped_result(probe, repo, probe_path, output_path, generated_at)

    argv = _argv_for_command_key(probe["command_key"])
    before_status, before_notes = inspect_repo(repo)
    command_result = _run_fixed_command(repo, argv, probe["timeout_seconds"])
    after_status, after_notes = inspect_repo(repo)

    safety_gates = _safety_gates(probe, repo, command_result)
    warnings = _warnings(before_status, after_status, before_notes + after_notes)
    blockers = _blockers(safety_gates, command_result, before_status, after_status)
    summary = _summary(safety_gates, command_result, warnings, blockers)
    health = _health(summary, warnings, blockers)

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_iso(),
        "producer": PRODUCER,
        "probe": {
            "probe_key": probe["probe_key"],
            "probe_path": redact_probe_value(probe_path),
            "project_key": probe["project_key"],
            "command_key": probe["command_key"],
            "command_class": probe["command_class"],
        },
        "authority": _authority(),
        "repo": _repo_summary(repo, before_status, after_status),
        "command": {
            "command_key": probe["command_key"],
            "argv_redacted": redact_probe_value(argv),
            "cwd_redacted": redact_probe_value(str(repo)),
            "timeout_seconds": probe["timeout_seconds"],
            "exit_code": command_result["exit_code"],
            "duration_ms": command_result["duration_ms"],
            "stdout_excerpt": command_result["stdout_excerpt"],
            "stderr_excerpt": command_result["stderr_excerpt"],
            "stdout_truncated": command_result["stdout_truncated"],
            "stderr_truncated": command_result["stderr_truncated"],
            "redactions_applied": command_result["redactions_applied"],
        },
        "artifacts": {
            "written": output_path is not None,
            "paths": [redact_probe_value(str(output_path))] if output_path else [],
            "command_created_artifacts": False,
            "expected_write_scope": probe["expected_write_scope"],
        },
        "safety_gates": safety_gates,
        "summary": summary,
        "health": health,
        "next": {
            "recommended_next_slice": _recommended_next_slice(probe["command_key"]),
            "supervisor_should_generate_prompt": True,
            "execution_automation_readiness_note": "C3 probe evidence exists; C4-C6 remain locked.",
        },
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


def truncate_output(text: str, limit: int = OUTPUT_EXCERPT_LIMIT) -> tuple[str, bool]:
    safe = str(redact_probe_value(text))
    if len(safe) <= limit:
        return safe, False
    return safe[:limit], True


def redact_probe_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_absolute_user_paths(value)
    if isinstance(value, list):
        return [redact_probe_value(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_probe_value(child) for key, child in value.items()}
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the single fixed controlled runner probe.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--probe", help="controlled_runner_probe.v1 JSON path.")
    source.add_argument("--default", action="store_true", help="Use the built-in status_snapshot_help probe.")
    parser.add_argument("--output", help="Output controlled_runner_probe_result.v1 JSON path. Omit to write stdout.")
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
    except ControlledRunnerProbeError as exc:
        print(f"controlled runner probe error: {exc}", file=sys.stderr)
        return 2

    payload = dumps_result(result, pretty=args.pretty)
    if args.output:
        write_result(result, args.output, pretty=args.pretty)
    else:
        print(payload, end="")
    return 1 if result["summary"]["result"] == "fail" else 0


def _run_fixed_command(repo: Path, argv: list[str], timeout_seconds: int) -> dict[str, Any]:
    env = os.environ.copy()
    src = str(repo / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    start_time = _utc_now_iso()
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
            "start_time": start_time,
            "end_time": _utc_now_iso(),
            "duration_ms": duration_ms,
            "exit_code": completed.returncode,
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
            "start_time": start_time,
            "end_time": _utc_now_iso(),
            "duration_ms": duration_ms,
            "exit_code": None,
            "stdout_excerpt": stdout_excerpt,
            "stderr_excerpt": stderr_excerpt,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "timed_out": True,
            "redactions_applied": _redactions_applied(stdout, stderr, argv, str(repo)),
        }


def _argv_for_command_key(command_key: str) -> list[str]:
    if command_key == STATUS_SNAPSHOT_HELP_KEY:
        return [sys.executable, "-m", "dev_cockpit.status_snapshot", "--help"]
    if command_key == ADAPTERS_VALIDATE_HELP_KEY:
        return [sys.executable, "-m", "dev_cockpit.adapters", "--help"]
    raise ControlledRunnerProbeError(f"unsupported command_key: {command_key}")


def _authority() -> dict[str, Any]:
    return {
        "capability_level": "C3_guarded_single_command_probe",
        "allowed_by_design": True,
        "production_command_keys": list(ALLOWED_COMMAND_KEYS),
        "production_command_count": len(ALLOWED_COMMAND_KEYS),
        "arbitrary_command_execution": False,
        "shell": False,
        "command_source": "hardcoded_allowlist",
        "config_can_supply_command": False,
        "config_can_supply_executable": False,
        "config_can_supply_argv": False,
        "config_can_supply_args": False,
        "target_repo_writeback": False,
        "adapter_default_validation_executed": False,
        "credentials_required": False,
        "network_required": False,
        "c4_unlocked": False,
        "c5_unlocked": False,
        "c6_unlocked": False,
    }


def _repo_summary(repo: Path, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": redact_probe_value(str(repo)),
        "branch": after.get("branch") or before.get("branch"),
        "head": after.get("head") or before.get("head"),
        "worktree_before": before.get("worktree"),
        "worktree_after": after.get("worktree"),
        "remote_parity_before": before.get("remote_parity"),
        "remote_parity_after": after.get("remote_parity"),
    }


def _safety_gates(probe: dict[str, Any], repo: Path, command_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "allowlist_gate": _gate(probe["command_key"] in ALLOWED_COMMAND_KEYS, "command key is hardcoded and allowed"),
        "arbitrary_args_gate": _gate(True, "config cannot supply argv or args"),
        "shell_gate": _gate(True, "subprocess shell option is false"),
        "cwd_gate": _gate(repo.exists(), "cwd is confined to DevCockpitCore repo"),
        "timeout_gate": _gate(not command_result["timed_out"], "timeout is configured and command completed in time"),
        "write_scope_gate": _gate(True, "command writes no artifacts; CLI may write declared sample result"),
        "target_repo_gate": _gate(True, "target repository writeback is forbidden and not attempted"),
        "credential_gate": _gate(True, "credentials are not required"),
        "network_gate": _gate(True, "network and external services are not required"),
        "destructive_git_gate": _gate(True, "destructive git actions are not part of the command"),
    }


def _gate(passed: bool, summary: str) -> dict[str, Any]:
    return {
        "result": "pass" if passed else "fail",
        "passed": passed,
        "summary": summary,
        "done": 1 if passed else 0,
        "total": 1,
        "unknown": 0,
        "meter": make_meter(1 if passed else 0, 1, result="pass" if passed else "fail", missing=0 if passed else 1),
        "missing": 0 if passed else 1,
    }


def _warnings(before: dict[str, Any], after: dict[str, Any], notes: list[str]) -> list[str]:
    warnings = list(notes)
    before_state = _worktree_state(before)
    after_state = _worktree_state(after)
    if before_state != "clean":
        warnings.append(f"worktree was {before_state} before probe")
    if _remote_parity_status(after) == "unknown":
        warnings.append("remote parity is unknown")
    return warnings


def _blockers(
    safety_gates: dict[str, Any],
    command_result: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[str]:
    blockers = [name for name, gate in safety_gates.items() if gate["result"] == "fail"]
    if command_result["timed_out"]:
        blockers.append("command timed out")
    elif command_result["exit_code"] != 0:
        blockers.append("command returned non-zero exit code")
    if before.get("worktree") != after.get("worktree"):
        blockers.append("worktree changed during probe command")
    if before.get("head") != after.get("head"):
        blockers.append("HEAD changed during probe command")
    return blockers


def _summary(
    safety_gates: dict[str, Any],
    command_result: dict[str, Any],
    warnings: list[str],
    blockers: list[str],
) -> dict[str, Any]:
    gate_count = len(safety_gates)
    passed_gates = sum(1 for gate in safety_gates.values() if gate["result"] == "pass")
    command_ok = command_result["exit_code"] == 0 and not command_result["timed_out"]
    total = gate_count + 1
    passed = passed_gates + (1 if command_ok else 0)
    failed = len(blockers)
    result = "fail" if blockers else "warn" if warnings else "pass"
    warning_count = 1 if result == "warn" else 0
    missing = total - passed if result == "fail" else 0
    return {
        "result": result,
        "done": passed,
        "total": total,
        "unknown": 0,
        "meter": make_meter(passed, total, result=result, missing=missing),
        "passed": passed,
        "warnings": warning_count,
        "failed": failed,
        "missing": missing,
    }


def _health(summary: dict[str, Any], warnings: list[str], blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "red" if summary["result"] == "fail" else "yellow" if summary["result"] == "warn" else "green",
        "warnings": redact_probe_value(warnings),
        "blockers": redact_probe_value(blockers),
        "stop_class": "VALIDATION_FAILED" if blockers else "INTEGRATE_AND_CONTINUE" if warnings else "NONE",
    }


def _skipped_result(
    probe: dict[str, Any],
    repo: Path,
    probe_path: str | None,
    output_path: str | Path | None,
    generated_at: str | None,
) -> dict[str, Any]:
    status, _notes = inspect_repo(repo)
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_iso(),
        "producer": PRODUCER,
        "probe": {
            "probe_key": probe["probe_key"],
            "probe_path": redact_probe_value(probe_path),
            "project_key": probe["project_key"],
            "command_key": probe["command_key"],
            "command_class": probe["command_class"],
        },
        "authority": _authority(),
        "repo": _repo_summary(repo, status, status),
        "command": {
            "command_key": probe["command_key"],
            "argv_redacted": [],
            "cwd_redacted": redact_probe_value(str(repo)),
            "timeout_seconds": probe["timeout_seconds"],
            "exit_code": None,
            "duration_ms": 0,
            "stdout_excerpt": "",
            "stderr_excerpt": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "redactions_applied": [],
        },
        "artifacts": {
            "written": output_path is not None,
            "paths": [redact_probe_value(str(output_path))] if output_path else [],
            "command_created_artifacts": False,
            "expected_write_scope": probe["expected_write_scope"],
        },
        "safety_gates": {},
        "summary": {
            "result": "skipped",
            "done": 0,
            "total": 1,
            "unknown": 0,
            "meter": make_meter(0, 1, result="skipped", missing=1),
            "passed": 0,
            "warnings": 0,
            "failed": 0,
            "missing": 1,
        },
        "health": {"status": "yellow", "warnings": ["probe disabled"], "blockers": [], "stop_class": "INTEGRATE_AND_CONTINUE"},
        "next": {
            "recommended_next_slice": _recommended_next_slice(probe["command_key"]),
            "supervisor_should_generate_prompt": True,
            "execution_automation_readiness_note": "Probe disabled; C4-C6 remain locked.",
        },
    }


def _recommended_next_slice(command_key: str) -> str:
    if command_key == ADAPTERS_VALIDATE_HELP_KEY:
        return "c3-second-command-production-probe-review-v1"
    return "controlled-runner-probe-review-v1"


def _worktree_state(status: dict[str, Any]) -> str:
    worktree = status.get("worktree")
    if isinstance(worktree, dict):
        return str(worktree.get("state") or "unknown")
    return "unknown"


def _remote_parity_status(status: dict[str, Any]) -> str:
    parity = status.get("remote_parity")
    if isinstance(parity, dict):
        return str(parity.get("status") or "unknown")
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
                raise ControlledRunnerProbeError(f"controlled runner probe field {path}.{key} is not allowed")
            _reject_executable_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_executable_fields(child, f"{path}[{index}]")


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ControlledRunnerProbeError(f"{key} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ControlledRunnerProbeError(f"{field} must be a list")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ControlledRunnerProbeError(f"{field} must contain only non-empty strings")
        output.append(item.strip())
    return output


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
