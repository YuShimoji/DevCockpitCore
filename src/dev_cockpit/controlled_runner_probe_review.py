"""Review controlled runner probe evidence without running commands."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from .controlled_runner_probe import ALLOWED_COMMAND_KEY, RESULT_SCHEMA_VERSION as PROBE_RESULT_SCHEMA_VERSION
from .report_normalizer import redact_absolute_user_paths
from .validation_pack import make_meter


REVIEW_SCHEMA_VERSION = "controlled_runner_probe_review.v1"
RESULT_SCHEMA_VERSION = "controlled_runner_probe_review_result.v1"
PRODUCER = "dev_cockpit.controlled_runner_probe_review"
DEFAULT_REVIEW_KEY = "devcockpitcore_c3_probe_acceptance_review"
DEFAULT_PROJECT_KEY = "devcockpitcore"
REQUIRED_CAPABILITY_LEVEL = "C3_guarded_single_command_probe"
LOCKED_CAPABILITY_LEVELS = (
    "C4_scoped_repo_local_runner",
    "C5_cross_project_runner",
    "C6_scheduler_or_autonomy_loop",
)
REQUIRED_SAFETY_GATES = (
    "allowlist_gate",
    "arbitrary_args_gate",
    "shell_gate",
    "cwd_gate",
    "timeout_gate",
    "write_scope_gate",
    "target_repo_gate",
    "credential_gate",
    "network_gate",
    "destructive_git_gate",
)


class ControlledRunnerProbeReviewError(ValueError):
    """Raised when probe review input cannot be classified safely."""


def default_review() -> dict[str, Any]:
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "review_key": DEFAULT_REVIEW_KEY,
        "project_key": DEFAULT_PROJECT_KEY,
        "required_capability_level": REQUIRED_CAPABILITY_LEVEL,
        "accepted_command_keys": [ALLOWED_COMMAND_KEY],
        "locked_capability_levels": list(LOCKED_CAPABILITY_LEVELS),
        "required_safety_gates": list(REQUIRED_SAFETY_GATES),
        "notes": [
            "Review evidence only; do not run the controlled runner probe.",
            "C3 acceptance does not unlock C4, C5, or C6.",
        ],
    }


def load_review(path: str | Path) -> dict[str, Any]:
    return validate_review(_load_json(path, "controlled runner probe review"))


def load_probe_result(path: str | Path) -> dict[str, Any]:
    result = _load_json(path, "controlled runner probe result")
    if not isinstance(result, dict):
        raise ControlledRunnerProbeReviewError("controlled runner probe result root must be a JSON object")
    return result


def validate_review(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ControlledRunnerProbeReviewError("controlled runner probe review root must be a JSON object")
    if data.get("schema_version") != REVIEW_SCHEMA_VERSION:
        raise ControlledRunnerProbeReviewError(f"schema_version must be {REVIEW_SCHEMA_VERSION!r}")
    accepted_command_keys = _string_list(data.get("accepted_command_keys"), "accepted_command_keys")
    if accepted_command_keys != [ALLOWED_COMMAND_KEY]:
        raise ControlledRunnerProbeReviewError("accepted_command_keys must contain only status_snapshot_help")
    locked_capability_levels = tuple(_string_list(data.get("locked_capability_levels"), "locked_capability_levels"))
    missing_locks = [level for level in LOCKED_CAPABILITY_LEVELS if level not in locked_capability_levels]
    if missing_locks:
        raise ControlledRunnerProbeReviewError(f"locked_capability_levels missing: {', '.join(missing_locks)}")
    required_safety_gates = tuple(_string_list(data.get("required_safety_gates"), "required_safety_gates"))
    missing_gates = [gate for gate in REQUIRED_SAFETY_GATES if gate not in required_safety_gates]
    if missing_gates:
        raise ControlledRunnerProbeReviewError(f"required_safety_gates missing: {', '.join(missing_gates)}")
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "review_key": _required_string(data, "review_key"),
        "project_key": _required_string(data, "project_key"),
        "required_capability_level": _required_string(data, "required_capability_level"),
        "accepted_command_keys": accepted_command_keys,
        "locked_capability_levels": list(locked_capability_levels),
        "required_safety_gates": list(required_safety_gates),
        "notes": _string_list(data.get("notes", []), "notes"),
    }


def review_probe_result(
    review: dict[str, Any],
    probe_result: dict[str, Any],
    *,
    probe_result_path: str | Path | None = None,
    dirty_sample_result: dict[str, Any] | None = None,
    dirty_sample_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    source = _source(probe_result, probe_result_path)
    evidence_checks = _evidence_checks(review, probe_result)
    sample_interpretation = _sample_interpretation(probe_result, dirty_sample_result, dirty_sample_path)
    readiness = _readiness(evidence_checks, sample_interpretation)
    summary = _summary(evidence_checks, sample_interpretation)
    health = _health(summary, evidence_checks, sample_interpretation)
    acceptance = _acceptance(summary, evidence_checks, sample_interpretation)

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_iso(),
        "producer": PRODUCER,
        "review": {
            "review_key": review["review_key"],
            "project_key": review["project_key"],
            "required_capability_level": review["required_capability_level"],
            "accepted_command_keys": review["accepted_command_keys"],
            "locked_capability_levels": review["locked_capability_levels"],
        },
        "source": source,
        "acceptance": acceptance,
        "evidence_checks": evidence_checks,
        "sample_interpretation": sample_interpretation,
        "readiness": readiness,
        "summary": summary,
        "health": health,
    }


def dumps_result(result: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2 if pretty else None, sort_keys=False) + "\n"


def write_result(result: dict[str, Any], output_path: str | Path, *, pretty: bool = False) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps_result(result, pretty=pretty), encoding="utf-8", newline="\n")


def redact_review_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_absolute_user_paths(value)
    if isinstance(value, list):
        return [redact_review_value(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_review_value(child) for key, child in value.items()}
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review controlled runner probe result evidence.")
    parser.add_argument("--probe-result", required=True, help="controlled_runner_probe_result.v1 JSON path.")
    parser.add_argument("--review", help="controlled_runner_probe_review.v1 JSON path. Defaults to built-in review.")
    parser.add_argument("--dirty-sample", help="Optional during-work probe result JSON to interpret dirty warning.")
    parser.add_argument("--output", help="Output controlled_runner_probe_review_result.v1 JSON path. Omit for stdout.")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON.")
    args = parser.parse_args(argv)

    try:
        review = load_review(args.review) if args.review else validate_review(default_review())
        probe_result = load_probe_result(args.probe_result)
        dirty_sample = load_probe_result(args.dirty_sample) if args.dirty_sample else None
        result = review_probe_result(
            review,
            probe_result,
            probe_result_path=args.probe_result,
            dirty_sample_result=dirty_sample,
            dirty_sample_path=args.dirty_sample,
        )
    except ControlledRunnerProbeReviewError as exc:
        print(f"controlled runner probe review error: {exc}", file=sys.stderr)
        return 2

    payload = dumps_result(result, pretty=args.pretty)
    if args.output:
        write_result(result, args.output, pretty=args.pretty)
    else:
        print(payload, end="")
    return 1 if result["summary"]["result"] == "fail" else 0


def _source(probe_result: dict[str, Any], probe_result_path: str | Path | None) -> dict[str, Any]:
    probe = _object(probe_result.get("probe"))
    authority = _object(probe_result.get("authority"))
    return {
        "probe_result_path": redact_review_value(str(probe_result_path)) if probe_result_path else None,
        "probe_schema_version": probe_result.get("schema_version"),
        "command_key": probe.get("command_key"),
        "capability_level": authority.get("capability_level"),
    }


def _evidence_checks(review: dict[str, Any], probe_result: dict[str, Any]) -> dict[str, Any]:
    probe = _object(probe_result.get("probe"))
    authority = _object(probe_result.get("authority"))
    command = _object(probe_result.get("command"))
    repo = _object(probe_result.get("repo"))
    artifacts = _object(probe_result.get("artifacts"))
    safety_gates = _object(probe_result.get("safety_gates"))

    missing_safety_gates = [gate for gate in review["required_safety_gates"] if gate not in safety_gates]
    safety_gates_pass = all(_gate_passed(safety_gates.get(gate)) for gate in review["required_safety_gates"])
    command_key = probe.get("command_key") or command.get("command_key")
    argv = command.get("argv_redacted")
    c4_unlocked = bool(authority.get("c4_unlocked"))
    c5_unlocked = bool(authority.get("c5_unlocked"))
    c6_unlocked = bool(authority.get("c6_unlocked"))

    return {
        "probe_schema_valid": _check(
            probe_result.get("schema_version") == PROBE_RESULT_SCHEMA_VERSION,
            "probe result schema is controlled_runner_probe_result.v1",
        ),
        "command_key_fixed": _check(
            command_key in review["accepted_command_keys"] and _argv_is_status_snapshot_help(argv),
            "only status_snapshot_help is accepted and argv ends with the fixed module help call",
        ),
        "arbitrary_command_blocked": _check(
            authority.get("arbitrary_command_execution") is False and authority.get("command_source") == "hardcoded_allowlist",
            "authority reports no arbitrary command execution and a hardcoded allowlist source",
        ),
        "config_args_blocked": _check(
            authority.get("config_can_supply_args") is False and _gate_passed(safety_gates.get("arbitrary_args_gate")),
            "config cannot supply argv or args",
        ),
        "shell_false": _check(
            authority.get("shell") is False and _gate_passed(safety_gates.get("shell_gate")),
            "shell execution is false and shell gate passed",
        ),
        "timeout_present": _check(
            isinstance(command.get("timeout_seconds"), int)
            and not isinstance(command.get("timeout_seconds"), bool)
            and command.get("timeout_seconds") > 0
            and _gate_passed(safety_gates.get("timeout_gate")),
            "positive timeout is present and timeout gate passed",
        ),
        "output_truncation_present": _check(
            "stdout_truncated" in command and "stderr_truncated" in command,
            "stdout/stderr truncation flags are present",
        ),
        "redaction_present": _check(
            "redactions_applied" in command and not _contains_raw_user_path(probe_result),
            "redaction field is present and no raw local user path is visible",
        ),
        "before_after_state_present": _check(
            isinstance(repo.get("worktree_before"), dict)
            and isinstance(repo.get("worktree_after"), dict)
            and isinstance(repo.get("remote_parity_before"), dict)
            and isinstance(repo.get("remote_parity_after"), dict),
            "before/after worktree and remote parity state are present",
        ),
        "target_repo_writeback_false": _check(
            authority.get("target_repo_writeback") is False and _gate_passed(safety_gates.get("target_repo_gate")),
            "target repository writeback is false",
        ),
        "credentials_false": _check(
            authority.get("credentials_required") is False and _gate_passed(safety_gates.get("credential_gate")),
            "credentials are not required",
        ),
        "network_false": _check(
            authority.get("network_required") is False and _gate_passed(safety_gates.get("network_gate")),
            "network is not required",
        ),
        "destructive_git_false": _check(
            _gate_passed(safety_gates.get("destructive_git_gate")),
            "destructive git gate passed",
        ),
        "write_scope_explained": _check(
            artifacts.get("command_created_artifacts") is False and bool(artifacts.get("expected_write_scope")),
            "command writes no artifacts and expected write scope is explained",
        ),
        "post_commit_clean_evidence_present": _check(
            _is_clean_post_commit_probe(probe_result),
            "probe result shows clean worktree before and after with passing summary",
        ),
        "required_safety_gates_present": _check(
            not missing_safety_gates and safety_gates_pass,
            "all required safety gates are present and passing",
            details={"missing_safety_gates": missing_safety_gates},
        ),
        "c4_c5_c6_locked": _check(
            not c4_unlocked and not c5_unlocked and not c6_unlocked,
            "C4, C5, and C6 are not unlocked by the probe result",
        ),
        "paste_ready_prompt_absent": _check(
            not _contains_paste_ready_prompt(probe_result),
            "probe result contains no paste-ready next-agent prompt markers",
        ),
    }


def _sample_interpretation(
    probe_result: dict[str, Any],
    dirty_sample_result: dict[str, Any] | None,
    dirty_sample_path: str | Path | None,
) -> dict[str, Any]:
    dirty_warning = _has_dirty_warning(dirty_sample_result) if dirty_sample_result else _has_dirty_warning(probe_result)
    post_commit_clean = _is_clean_post_commit_probe(probe_result)
    if dirty_warning and post_commit_clean:
        handling = "accepted_as_expected_artifact_generation"
    elif dirty_warning:
        handling = "fix_required"
    else:
        handling = "unknown"
    return {
        "during_work_sample_path": redact_review_value(str(dirty_sample_path)) if dirty_sample_path else None,
        "during_work_sample_dirty_warning": dirty_warning,
        "post_commit_clean_probe_available": post_commit_clean,
        "dirty_warning_handling": handling,
    }


def _readiness(evidence_checks: dict[str, Any], sample_interpretation: dict[str, Any]) -> dict[str, Any]:
    c3_ok = _all_checks_pass(evidence_checks) and sample_interpretation["post_commit_clean_probe_available"]
    return {
        "c0_observer_only": "available",
        "c1_fixed_validation_pack": "available",
        "c2_command_proposal_only": "design_available",
        "c3_guarded_single_command_probe": "accepted" if c3_ok else "review_not_accepted",
        "c4_scoped_repo_local_runner": "locked",
        "c5_cross_project_runner": "locked",
        "c6_scheduler_or_autonomy_loop": "locked",
    }


def _summary(evidence_checks: dict[str, Any], sample_interpretation: dict[str, Any]) -> dict[str, Any]:
    total = len(evidence_checks)
    passed = sum(1 for item in evidence_checks.values() if item["result"] == "pass")
    failed = total - passed
    warnings = 0
    if sample_interpretation["during_work_sample_dirty_warning"] and sample_interpretation["post_commit_clean_probe_available"]:
        warnings = 1
    result = "fail" if failed else "warn" if warnings else "pass"
    missing = failed
    return {
        "result": result,
        "done": passed,
        "total": total,
        "unknown": 0,
        "meter": make_meter(passed, total, result=result, missing=missing),
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "missing": missing,
    }


def _health(
    summary: dict[str, Any],
    evidence_checks: dict[str, Any],
    sample_interpretation: dict[str, Any],
) -> dict[str, Any]:
    blockers = [name for name, item in evidence_checks.items() if item["result"] == "fail"]
    warnings: list[str] = []
    if sample_interpretation["during_work_sample_dirty_warning"] and sample_interpretation["post_commit_clean_probe_available"]:
        warnings.append("during-work sample has dirty warning but post-commit clean evidence is available")
    return {
        "status": "red" if blockers else "yellow" if warnings else "green",
        "warnings": warnings,
        "blockers": blockers,
        "stop_class": "VALIDATION_FAILED" if blockers else "INTEGRATE_AND_CONTINUE" if warnings else "NONE",
    }


def _acceptance(
    summary: dict[str, Any],
    evidence_checks: dict[str, Any],
    sample_interpretation: dict[str, Any],
) -> dict[str, Any]:
    critical_rejections = {
        "command_key_fixed",
        "arbitrary_command_blocked",
        "shell_false",
        "target_repo_writeback_false",
        "credentials_false",
        "network_false",
        "destructive_git_false",
        "c4_c5_c6_locked",
    }
    failed = {name for name, item in evidence_checks.items() if item["result"] == "fail"}
    if failed & critical_rejections:
        decision = "rejected"
    elif failed:
        decision = "fix_required"
    elif sample_interpretation["during_work_sample_dirty_warning"]:
        decision = "accepted_with_constraints"
    else:
        decision = "accepted"
    c3_accepted = decision in {"accepted", "accepted_with_constraints"}
    return {
        "decision": decision,
        "c3_accepted": c3_accepted,
        "c4_unlocked": False,
        "c5_unlocked": False,
        "c6_unlocked": False,
        "recommended_next_slice": "c3-probe-hardening-v1" if c3_accepted else "controlled-runner-stop",
        "supervisor_should_generate_prompt": True,
        "summary_result": summary["result"],
    }


def _check(passed: bool, summary: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "result": "pass" if passed else "fail",
        "done": 1 if passed else 0,
        "total": 1,
        "unknown": 0,
        "meter": make_meter(1 if passed else 0, 1, result="pass" if passed else "fail", missing=0 if passed else 1),
        "missing": 0 if passed else 1,
        "summary": summary,
        "details": redact_review_value(details or {}),
    }


def _gate_passed(value: Any) -> bool:
    return isinstance(value, dict) and value.get("result") == "pass" and value.get("passed") is True


def _argv_is_status_snapshot_help(argv: Any) -> bool:
    return isinstance(argv, list) and len(argv) >= 4 and argv[-3:] == ["-m", "dev_cockpit.status_snapshot", "--help"]


def _is_clean_post_commit_probe(probe_result: dict[str, Any]) -> bool:
    repo = _object(probe_result.get("repo"))
    before = _object(repo.get("worktree_before"))
    after = _object(repo.get("worktree_after"))
    summary = _object(probe_result.get("summary"))
    command = _object(probe_result.get("command"))
    return (
        before.get("state") == "clean"
        and after.get("state") == "clean"
        and summary.get("result") == "pass"
        and command.get("exit_code") == 0
    )


def _has_dirty_warning(probe_result: dict[str, Any] | None) -> bool:
    if not probe_result:
        return False
    repo = _object(probe_result.get("repo"))
    health = _object(probe_result.get("health"))
    warnings = health.get("warnings")
    if _object(repo.get("worktree_before")).get("state") == "dirty":
        return True
    return isinstance(warnings, list) and any("dirty" in str(item) for item in warnings)


def _contains_raw_user_path(value: Any) -> bool:
    if isinstance(value, str):
        return "<redacted>" not in value and redact_absolute_user_paths(value) != value
    if isinstance(value, dict):
        return any(_contains_raw_user_path(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_raw_user_path(child) for child in value)
    return False


def _contains_paste_ready_prompt(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, default=str)
    markers = ("[PASTE TARGET:", "Goal Stack:", "Allowed scope:", "Report format:")
    return any(marker in text for marker in markers)


def _all_checks_pass(evidence_checks: dict[str, Any]) -> bool:
    return all(item["result"] == "pass" for item in evidence_checks.values())


def _load_json(path: str | Path, label: str) -> dict[str, Any]:
    json_path = Path(path)
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ControlledRunnerProbeReviewError(f"{label} not found: {json_path}") from exc
    except json.JSONDecodeError as exc:
        raise ControlledRunnerProbeReviewError(f"{label} is not valid JSON: {json_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ControlledRunnerProbeReviewError(f"{label} root must be a JSON object")
    return data


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ControlledRunnerProbeReviewError(f"{key} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ControlledRunnerProbeReviewError(f"{field} must be a list")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ControlledRunnerProbeReviewError(f"{field} must contain only non-empty strings")
        output.append(item.strip())
    return output


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
