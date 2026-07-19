"""Classify normalized AGENT_REPORT readbacks into gate decisions."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any


SCHEMA_VERSION = "gate_classification.v1"
PRODUCER = "dev_cockpit.gate_classifier"

DECISION_COMPLETED_CONTINUE = "completed_continue"
DECISION_SUPERVISOR_PROMPT_NEEDED = "supervisor_prompt_needed"
DECISION_USER_ACTION_REQUIRED = "user_action_required"
DECISION_HANDOFF_REQUIRED = "handoff_required"
DECISION_INTEGRATE_AND_CONTINUE = "integrate_and_continue"
DECISION_BLOCKED_TRUE_STOP = "blocked_true_stop"
DECISION_BLOCKED_AUTH = "blocked_auth"
DECISION_BLOCKED_VALIDATION = "blocked_validation"
DECISION_BLOCKED_SAFETY_BOUNDARY = "blocked_safety_boundary"
DECISION_UNKNOWN_REVIEW_REQUIRED = "unknown_review_required"

STOP_NONE = "NONE"
STOP_INTEGRATE = "INTEGRATE_AND_CONTINUE"
STOP_USER_AUTH = "USER_AUTH_REQUIRED"
STOP_HANDOFF = "HANDOFF_REQUIRED"
STOP_VALIDATION_FAILED = "VALIDATION_FAILED"
STOP_REPO_STATE_CONFLICT = "REPO_STATE_CONFLICT"
STOP_SAFETY_BOUNDARY = "SAFETY_BOUNDARY"
STOP_TRUE_STOP = "TRUE_STOP"
STOP_UNKNOWN_REVIEW = "UNKNOWN_REVIEW_REQUIRED"

_AUTOMATION_TERMS = (
    "codex exec loop",
    "subprocess runner",
    "command executor",
    "subprocess orchestrator",
    "scheduler",
    "external notification",
    "auto-render",
    "credential handling",
)
_DESTRUCTIVE_TERMS = (
    "force push",
    "reset",
    "rebase",
    "stash",
    "auto-merge",
    "destructive",
)
_USER_ACTION_TERMS = (
    "auth",
    "authorization",
    "credential",
    "manual",
    "decision",
    "review",
    "local operation",
    "blocked setup",
)
_AUTH_TERMS = ("auth", "authorization", "credential", "permission")
_NEGATION_HINTS = (
    "do not",
    "does not",
    "did not",
    "no ",
    "not ",
    "without ",
    "out of scope",
    "must not",
    "remains out of scope",
)


def classify_gate(
    report_normalization: dict[str, Any],
    *,
    report_normalization_path: str | None = None,
    status_snapshot: dict[str, Any] | None = None,
    status_snapshot_path: str | None = None,
    adapter: dict[str, Any] | None = None,
    adapter_path: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    routing = _routing(report_normalization)
    input_summary = _input_summary(report_normalization)
    source_warnings = _source_warnings(status_snapshot, adapter)
    scan_text = _scan_text(report_normalization)
    gates = {
        "push_gate": _push_gate(report_normalization, input_summary),
        "handoff_gate": _handoff_gate(input_summary),
        "user_work_gate": _user_work_gate(input_summary),
        "residue_gate": _residue_gate(report_normalization),
        "validation_gate": _validation_gate(report_normalization),
        "readiness_gate": _readiness_gate(report_normalization, scan_text),
        "execution_automation_gate": _execution_automation_gate(report_normalization, scan_text),
        "production_public_gate": _production_public_gate(report_normalization, scan_text),
        "destructive_action_gate": _destructive_action_gate(scan_text),
        "form_burden_gate": _form_burden_gate(report_normalization, scan_text),
    }
    residue_findings = _residue_findings(report_normalization, gates["residue_gate"])
    classification = _classification(report_normalization, input_summary, gates)
    readiness = _readiness(report_normalization, status_snapshot, adapter, gates)
    next_state = _next_state(report_normalization, classification)
    health = _health(gates, source_warnings, classification)

    return {
        "schema_version": SCHEMA_VERSION,
        "producer": PRODUCER,
        "generated_at": generated_at or _utc_now_iso(),
        "source": {
            "report_normalization_path": report_normalization_path,
            "status_snapshot_path": status_snapshot_path,
            "adapter_path": adapter_path,
            "input_kind": "report_normalization_json",
            "warnings": source_warnings,
        },
        "routing": routing,
        "input_summary": input_summary,
        "classification": classification,
        "gates": gates,
        "residue_findings": residue_findings,
        "readiness": readiness,
        "next": next_state,
        "health": health,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    json_path = Path(path)
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"JSON file not found: {json_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON file is invalid: {json_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {json_path}")
    return data


def dumps_classification(classification: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(
        classification,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=False,
    ) + "\n"


def write_classification(
    classification: dict[str, Any],
    output_path: str | Path,
    *,
    pretty: bool = False,
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps_classification(classification, pretty=pretty), encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify a report_normalization.v1 JSON readback.")
    parser.add_argument("--report-normalization", required=True, help="Required report normalization JSON path.")
    parser.add_argument("--status-snapshot", help="Optional status_snapshot.v1 JSON path.")
    parser.add_argument("--adapter", help="Optional adapter_manifest.v1 JSON path.")
    parser.add_argument("--output", help="Output JSON path. Omit to write to stdout.")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON.")
    args = parser.parse_args(argv)

    try:
        report_normalization = load_json(args.report_normalization)
    except ValueError as exc:
        print(f"report normalization error: {exc}", file=sys.stderr)
        return 2

    status_snapshot, adapter = None, None
    optional_errors: list[str] = []
    if args.status_snapshot:
        try:
            status_snapshot = load_json(args.status_snapshot)
        except ValueError as exc:
            optional_errors.append(str(exc))
    if args.adapter:
        try:
            adapter = load_json(args.adapter)
        except ValueError as exc:
            optional_errors.append(str(exc))

    classification = classify_gate(
        report_normalization,
        report_normalization_path=args.report_normalization,
        status_snapshot=status_snapshot,
        status_snapshot_path=args.status_snapshot,
        adapter=adapter,
        adapter_path=args.adapter,
    )
    classification["source"]["warnings"].extend(optional_errors)

    payload = dumps_classification(classification, pretty=args.pretty)
    if args.output:
        write_classification(classification, args.output, pretty=args.pretty)
    else:
        print(payload, end="")
    return 0


def _routing(report: dict[str, Any]) -> dict[str, Any]:
    source = _object(report.get("routing"))
    return {
        "route": source.get("route"),
        "thread": source.get("thread"),
        "lane": source.get("lane"),
        "slice": source.get("slice"),
        "artifact": source.get("artifact"),
        "thread_id": source.get("thread_id"),
        "lane_id": source.get("lane_id"),
        "slice_id": source.get("slice_id"),
        "artifact_id": source.get("artifact_id"),
        "dialect": source.get("dialect"),
        "artifact_current": source.get("artifact_current"),
        "artifact_next": source.get("artifact_next"),
        "confidence": source.get("confidence"),
        "direction": source.get("direction"),
    }


def _input_summary(report: dict[str, Any]) -> dict[str, Any]:
    action = _object(report.get("action"))
    report_health = _object(report.get("health"))
    outcome = _object(report.get("normalized_outcome"))
    progress = _object(report.get("progress"))
    status = _object(report.get("status"))
    handoff = _object(report.get("handoff"))
    sections = _object(report.get("sections"))

    return {
        "agent_decision": action.get("decision") or outcome.get("decision"),
        "report_health": report_health.get("normalization_status"),
        "normalized_outcome_decision": outcome.get("decision"),
        "pushed": outcome.get("pushed"),
        "worktree": outcome.get("worktree"),
        "remote_parity": outcome.get("remote_parity"),
        "tests_summary": _tests_summary(outcome.get("tests")),
        "handoff_gate": handoff.get("handoff_gate"),
        "user_work": progress.get("user_work") or sections.get("user_side_work"),
        "blocker": progress.get("blocker"),
        "stop_class": status.get("stop_class") or report_health.get("stop_class"),
    }


def _source_warnings(status_snapshot: dict[str, Any] | None, adapter: dict[str, Any] | None) -> list[str]:
    warnings: list[str] = []
    if status_snapshot is None:
        warnings.append("optional status snapshot not provided")
    if adapter is None:
        warnings.append("optional adapter manifest not provided")
    return warnings


def _push_gate(report: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    commits = _object(report.get("normalized_outcome")).get("commits") or []
    pushed = summary.get("pushed")
    worktree = summary.get("worktree")
    parity = _normalize_parity(summary.get("remote_parity"))

    if pushed is True and worktree == "clean" and parity == "0 0":
        return _gate("green", True, "committed, pushed, clean, and in sync")
    if commits and pushed is not False:
        return _gate("yellow", False, "commit evidence exists but push/worktree/parity is incomplete")
    if pushed is False:
        return _gate("yellow", False, "push is missing or reported blocked")
    return _gate("yellow", False, "commit and push evidence is incomplete")


def _handoff_gate(summary: dict[str, Any]) -> dict[str, Any]:
    value = summary.get("handoff_gate")
    if value is False:
        return _gate("green", True, "handoff gate passed")
    if value is True:
        return _gate("red", False, "handoff is required")
    return _gate("yellow", False, "handoff gate is unknown")


def _user_work_gate(summary: dict[str, Any]) -> dict[str, Any]:
    user_work = _lower_text(summary.get("user_work"))
    blocker = _lower_text(summary.get("blocker"))
    combined = f"{user_work} {blocker}".strip()
    if not combined or combined in {"unknown", "none", "null"}:
        if user_work == "unknown":
            return _gate("yellow", False, "user work is unknown")
        return _gate("green", True, "no user work required")
    if any(term in combined for term in _USER_ACTION_TERMS):
        status = "red" if any(term in combined for term in _AUTH_TERMS) else "yellow"
        return _gate(status, False, f"user work required: {combined}")
    return _gate("green", True, "no user action required by classification terms")


def _residue_gate(report: dict[str, Any]) -> dict[str, Any]:
    audit = _object(report.get("residue_audit"))
    notes: list[str] = []
    if audit.get("contains_paste_ready_prompt"):
        notes.append("paste-ready prompt residue violates report/prompt separation")
    if audit.get("contains_pseudo_git_tags"):
        notes.append("pseudo git tags are present as hygiene residue")
    if audit.get("contains_absolute_user_paths"):
        redacted = audit.get("absolute_user_paths_redacted")
        notes.append("local user paths are redacted" if redacted else "raw local user paths are present")
    if audit.get("contains_runner_or_scheduler_instruction"):
        notes.append("runner or scheduler instruction residue is present")
    if audit.get("contains_execution_automation_overclaim"):
        notes.append("execution automation readiness overclaim is present")
    if audit.get("contains_production_readiness_overclaim"):
        notes.append("production readiness overclaim is present")

    red = (
        audit.get("contains_runner_or_scheduler_instruction")
        or audit.get("contains_execution_automation_overclaim")
        or (audit.get("contains_absolute_user_paths") and not audit.get("absolute_user_paths_redacted"))
    )
    if red:
        return _gate("red", False, "; ".join(notes) or "red residue present")
    if audit.get("contains_paste_ready_prompt") or notes:
        return _gate("yellow", False, "; ".join(notes))
    return _gate("green", True, "no blocking residue")


def _validation_gate(report: dict[str, Any]) -> dict[str, Any]:
    sections = _object(report.get("sections"))
    commands = _list(sections.get("commands_and_results"))
    validation = _list(sections.get("validation"))
    outcome = _object(report.get("normalized_outcome"))
    text = _lower_text(" ".join(commands + validation))

    if re.search(r"\b(fail|failed|failure|error)\b", text):
        return _gate("red", False, "validation failure reported")
    if outcome.get("tests") or "passed" in text or "ok" in text:
        return _gate("green", True, "validation reported passing")
    return _gate("yellow", False, "validation evidence is missing or partial")


def _readiness_gate(report: dict[str, Any], scan_text: str) -> dict[str, Any]:
    audit = _object(report.get("residue_audit"))
    if audit.get("contains_execution_automation_overclaim") or _execution_readiness_overclaim(scan_text):
        return _gate("red", False, "execution automation readiness overclaim detected")
    return _gate("green", True, "readiness lanes remain separated")


def _execution_automation_gate(report: dict[str, Any], scan_text: str) -> dict[str, Any]:
    audit = _object(report.get("residue_audit"))
    if audit.get("contains_runner_or_scheduler_instruction") or _contains_unnegated(scan_text, _AUTOMATION_TERMS):
        return _gate("red", False, "execution automation instruction is out of scope")
    return _gate("green", True, "no execution automation instruction")


def _production_public_gate(report: dict[str, Any], scan_text: str) -> dict[str, Any]:
    audit = _object(report.get("residue_audit"))
    if audit.get("contains_production_readiness_overclaim"):
        return _gate("yellow", False, "production readiness overclaim reported")
    if re.search(r"\bproduction[- ]ready\b|\bpublic action\b", scan_text, re.IGNORECASE):
        return _gate("yellow", False, "production/public readiness wording needs review")
    return _gate("green", True, "no production/public readiness claim")


def _destructive_action_gate(scan_text: str) -> dict[str, Any]:
    if _contains_unnegated(scan_text, _DESTRUCTIVE_TERMS):
        return _gate("red", False, "destructive action wording detected")
    return _gate("green", True, "no destructive action required")


def _form_burden_gate(report: dict[str, Any], scan_text: str) -> dict[str, Any]:
    audit = _object(report.get("residue_audit"))
    if audit.get("contains_paste_ready_prompt"):
        return _gate("yellow", False, "paste-ready prompt residue creates form burden")
    if re.search(r"\bfixed form\b|\bform_required=true\b", scan_text, re.IGNORECASE):
        return _gate("yellow", False, "fixed-form burden wording detected")
    return _gate("green", True, "freeform user input remains acceptable")


def _residue_findings(report: dict[str, Any], residue_gate: dict[str, Any]) -> dict[str, Any]:
    audit = _object(report.get("residue_audit"))
    severity = residue_gate["status"]
    if audit.get("contains_paste_ready_prompt") and severity == "green":
        severity = "yellow"
    return {
        "contains_paste_ready_prompt": bool(audit.get("contains_paste_ready_prompt")),
        "contains_pseudo_git_tags": bool(audit.get("contains_pseudo_git_tags")),
        "contains_absolute_user_paths": bool(audit.get("contains_absolute_user_paths")),
        "contains_runner_or_scheduler_instruction": bool(audit.get("contains_runner_or_scheduler_instruction")),
        "readiness_overclaim": bool(
            audit.get("contains_execution_automation_overclaim")
            or audit.get("contains_production_readiness_overclaim")
        ),
        "severity": severity,
        "recommended_handling": _residue_handling(audit, severity),
    }


def _classification(
    report: dict[str, Any],
    summary: dict[str, Any],
    gates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    gate_statuses = {name: gate["status"] for name, gate in gates.items()}
    red_gates = [name for name, status in gate_statuses.items() if status == "red"]
    yellow_gates = [name for name, status in gate_statuses.items() if status == "yellow"]
    next_obj = _object(report.get("next"))
    next_owner = next_obj.get("next_owner") or "Supervisor"

    decision = DECISION_COMPLETED_CONTINUE
    stop_class = STOP_NONE
    if "execution_automation_gate" in red_gates or "readiness_gate" in red_gates:
        decision, stop_class = DECISION_BLOCKED_SAFETY_BOUNDARY, STOP_SAFETY_BOUNDARY
    elif "destructive_action_gate" in red_gates:
        decision, stop_class = DECISION_BLOCKED_TRUE_STOP, STOP_TRUE_STOP
    elif "validation_gate" in red_gates:
        decision, stop_class = DECISION_BLOCKED_VALIDATION, STOP_VALIDATION_FAILED
    elif gates["user_work_gate"]["status"] == "red":
        decision, stop_class = DECISION_BLOCKED_AUTH, STOP_USER_AUTH
    elif gates["handoff_gate"]["status"] == "red":
        decision, stop_class = DECISION_HANDOFF_REQUIRED, STOP_HANDOFF
    elif gates["user_work_gate"]["status"] == "yellow":
        decision, stop_class = DECISION_USER_ACTION_REQUIRED, STOP_INTEGRATE
    elif gates["push_gate"]["status"] == "yellow":
        decision, stop_class = DECISION_INTEGRATE_AND_CONTINUE, STOP_INTEGRATE
    elif gates["handoff_gate"]["status"] == "yellow" or summary.get("agent_decision") is None:
        decision, stop_class = DECISION_UNKNOWN_REVIEW_REQUIRED, STOP_UNKNOWN_REVIEW
    elif next_owner == "Supervisor" and next_obj.get("recommended_next_slice"):
        decision, stop_class = DECISION_SUPERVISOR_PROMPT_NEEDED, STOP_NONE

    health = "red" if stop_class in {STOP_USER_AUTH, STOP_HANDOFF, STOP_VALIDATION_FAILED, STOP_SAFETY_BOUNDARY, STOP_TRUE_STOP} else "yellow" if yellow_gates else "green"
    user_work_required = decision in {DECISION_USER_ACTION_REQUIRED, DECISION_BLOCKED_AUTH}
    handoff_required = decision == DECISION_HANDOFF_REQUIRED
    scope_violation = "execution_automation_gate" in red_gates or "readiness_gate" in red_gates

    return {
        "decision": decision,
        "health": health,
        "stop_class": stop_class,
        "next_owner": next_owner,
        "user_work_required": user_work_required,
        "supervisor_should_generate_prompt": decision == DECISION_SUPERVISOR_PROMPT_NEEDED,
        "handoff_required": handoff_required,
        "continue_allowed": stop_class in {STOP_NONE, STOP_INTEGRATE, STOP_UNKNOWN_REVIEW},
        "commit_push_accepted": gates["push_gate"]["status"] == "green",
        "review_required": bool(yellow_gates) or decision == DECISION_UNKNOWN_REVIEW_REQUIRED,
        "execution_automation_scope_violation": scope_violation,
    }


def _readiness(
    report: dict[str, Any],
    status_snapshot: dict[str, Any] | None,
    adapter: dict[str, Any] | None,
    gates: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "foundation_observer_readiness": "available" if status_snapshot or adapter else "not_evaluated",
        "foundation_automation_readiness": "gate_classifier_available",
        "execution_automation_readiness": "out_of_scope",
        "project_product_readiness": "not_evaluated",
        "notes": [
            "status producer, adapter manifest, report normalizer, and gate classifier are foundation tooling",
            "execution automation readiness is not advanced by this classification",
            gates["readiness_gate"]["summary"],
        ],
    }


def _next_state(report: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    next_obj = _object(report.get("next"))
    recommended = next_obj.get("recommended_next_slice") or next_obj.get("artifact_next")
    if recommended == "gate-classifier-v1":
        recommended = "validation-pack-v1"
    return {
        "recommended_next_slice": recommended,
        "minimal_next_task": next_obj.get("minimal_next_task"),
        "next_owner": classification["next_owner"],
        "supervisor_should_generate_prompt": classification["supervisor_should_generate_prompt"],
        "user_side_work": "required" if classification["user_work_required"] else "none",
        "agent_side_work": "none" if classification["supervisor_should_generate_prompt"] else "review classification",
    }


def _health(
    gates: dict[str, dict[str, Any]],
    source_warnings: list[str],
    classification: dict[str, Any],
) -> dict[str, Any]:
    warnings = [gate["summary"] for gate in gates.values() if gate["status"] == "yellow"]
    blockers = [gate["summary"] for gate in gates.values() if gate["status"] == "red"]
    return {
        "classification_status": classification["health"],
        "warnings": warnings + source_warnings,
        "blockers": blockers,
        "stop_class": classification["stop_class"],
    }


def _tests_summary(tests: Any) -> dict[str, Any]:
    rows = _list(tests)
    counts = [item.get("count") for item in rows if isinstance(item, dict) and isinstance(item.get("count"), int)]
    return {
        "reported": bool(rows),
        "counts": counts,
        "total": sum(counts) if counts else None,
    }


def _gate(status: str, passed: bool, summary: str, notes: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "passed": passed,
        "summary": summary,
        "notes": notes or [],
    }


def _residue_handling(audit: dict[str, Any], severity: str) -> str:
    if audit.get("contains_runner_or_scheduler_instruction") or audit.get("contains_execution_automation_overclaim"):
        return "stop and keep execution automation out of scope"
    if audit.get("contains_paste_ready_prompt"):
        return "contract warning; remove prompt residue before supervisor handoff"
    if audit.get("contains_absolute_user_paths") and not audit.get("absolute_user_paths_redacted"):
        return "redact local user paths before committing or sharing"
    if audit.get("contains_pseudo_git_tags"):
        return "hygiene warning; do not treat pseudo tags as a true blocker"
    return "no residue handling required"


def _scan_text(report: dict[str, Any]) -> str:
    sections = _object(report.get("sections"))
    values: list[str] = []
    for key in ("outcome", "what_changed", "completion_matrix", "continuation_state", "user_side_work", "agent_side_work", "handoff_gate"):
        value = sections.get(key)
        if isinstance(value, str):
            values.append(value)
    for key in ("commands_and_results", "validation", "artifacts"):
        values.extend(str(item) for item in _list(sections.get(key)))
    extra = _object(sections.get("extra"))
    values.extend(str(item) for item in extra.values())
    health = _object(report.get("health"))
    values.extend(str(item) for item in _list(health.get("warnings")))
    return "\n".join(values)


def _contains_unnegated(text: str, terms: tuple[str, ...]) -> bool:
    for line in text.lower().splitlines():
        for term in terms:
            for match in re.finditer(re.escape(term), line):
                if _term_is_locally_negated(line, match.start(), match.end()):
                    continue
                return True
    return False


def _term_is_locally_negated(line: str, start: int, end: int) -> bool:
    prefix = line[max(0, start - 80) : start]
    prefix_clause = re.split(r"[.;:,]|\b(?:but|however)\b", prefix)[-1]
    if re.search(
        r"\b(?:no|without|never)\b[^.;:]{0,48}$"
        r"|\b(?:do|does|did|must|should|will|is|are|was|were)?\s*not\b[^.;:]{0,40}$",
        prefix_clause,
    ):
        return True

    postfix = line[end : min(len(line), end + 96)]
    negated_action = (
        r"`?(?:not|never)\s+"
        r"(?:performed|used|run|executed|done|applied|requested|required|attempted|"
        r"allowed|authorized|needed)\b"
    )
    if re.match(
        rf"\s+(?:(?:was|were|is|are|has been|have been)\s+)?{negated_action}",
        postfix,
    ):
        return True
    if re.match(rf"[a-z0-9_-]{{0,64}}\s*[:=]\s*{negated_action}", postfix):
        return True
    return bool(
        re.match(
            r"\s+(?:(?:is|are|remains?|stays?)\s+)?out of scope\b",
            postfix,
        )
    )


def _execution_readiness_overclaim(text: str) -> bool:
    for line in text.splitlines():
        lowered = line.lower()
        if "execution automation readiness" not in lowered:
            continue
        if any(hint in lowered for hint in _NEGATION_HINTS) or "out of scope" in lowered:
            continue
        if re.search(r"\[[#]+\]|\badvanced\b|\bcomplete\b|\bready\b", lowered):
            return True
    return False


def _normalize_parity(value: Any) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", str(value)).strip()


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _lower_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
