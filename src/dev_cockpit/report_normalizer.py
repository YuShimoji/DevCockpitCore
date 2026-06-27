"""Normalize AGENT_REPORT-like text into structured readback JSON."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any


SCHEMA_VERSION = "report_normalization.v1"
PRODUCER = "dev_cockpit.report_normalizer"

_HEADER_RE = re.compile(r"^\[(ROUTE|PROGRESS|ACTION|STATUS):\s*(.*?)\]\s*$", re.MULTILINE)
_PROGRESS_RE = re.compile(
    r"^(?P<lane>.+?)\s+\[(?P<meter>[#-]+)\]\s+"
    r"(?P<done>\d+)\s*/\s*(?P<total>\d+)\s*(?:\|\s*(?P<rest>.*))?$"
)
_SHA_RE = re.compile(r"\b(?P<sha>[0-9a-f]{7,40})\s+(?P<message>[^\r\n`]+)")
_PSEUDO_GIT_RE = re.compile(r"::(?P<tag>git-[A-Za-z0-9_-]+)(?:\{[^}]*\})?")
_WINDOWS_USER_PATH_RE = re.compile(
    r"(?P<prefix>[A-Za-z]:\\Users\\)(?P<user><redacted>|[^\\\s\]\)]+)"
    r"(?P<rest>(?:\\[^\s\]\)]+)*)"
)
_UNIX_HOME_PATH_RE = re.compile(
    r"(?P<prefix>/(?:home|Users)/)(?P<user><redacted>|[^/\s\]\)]+)"
    r"(?P<rest>(?:/[^\s\]\)]+)*)"
)
_PARITY_RE = re.compile(r"(?:remote\s+)?parity[^0-9]*(?P<parity>\d+\s+\d+)", re.IGNORECASE)
_TEST_COUNT_RE = re.compile(r"\b(?P<count>\d+)\s+tests?\b", re.IGNORECASE)

_PASTE_PROMPT_MARKERS = (
    "[PASTE TARGET:",
    "[CONTRACT: v2.1 | output_type=SUPERVISOR_PROMPT",
    "Goal Stack:",
    "Allowed scope:",
    "Report format:",
)
_RISKY_AUTOMATION_TERMS = (
    "Codex exec loop",
    "subprocess runner",
    "scheduler",
    "external notification",
    "auto-render",
    "force push",
    "credential handling",
)
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
_SECTION_ALIASES = {
    "outcome": "outcome",
    "what_changed": "what_changed",
    "artifacts": "artifacts",
    "artifacts_and_repo_relative_paths": "artifacts",
    "commands_and_results": "commands_and_results",
    "commands_executed_and_results": "commands_and_results",
    "report_normalization_v1_summary": "report_normalization_v1_summary",
    "adapter_manifest_v1_summary": "adapter_manifest_v1_summary",
    "residue_audit_behavior": "residue_audit_behavior",
    "sample_normalization_result": "sample_normalization_result",
    "validation": "validation",
    "completion_matrix": "completion_matrix",
    "user_side_work": "user_side_work",
    "agent_side_work": "agent_side_work",
    "continuation_state": "continuation_state",
    "handoff_gate": "handoff_gate",
    "handoff_gate_result": "handoff_gate",
}


def normalize_report(
    text: str,
    *,
    input_path: str | None = None,
    input_kind: str = "agent_report_text",
    generated_at: str | None = None,
) -> dict[str, Any]:
    audit = audit_residue(text)
    safe_text = redact_absolute_user_paths(text)
    headers = _parse_headers(safe_text)
    section_text = _extract_sections(safe_text)
    routing = _parse_route(headers.get("ROUTE"))
    progress = _parse_progress(headers.get("PROGRESS"))
    action = _parse_action(headers.get("ACTION"))
    status = _parse_status(headers.get("STATUS"))
    sections = _build_sections(section_text)
    outcome = _build_normalized_outcome(safe_text, sections, action)
    handoff = _build_handoff(sections, safe_text)
    next_state = _build_next(routing, progress, action, sections)
    health = _build_health(routing, progress, action, status, audit)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_iso(),
        "producer": PRODUCER,
        "source": {
            "input_path": redact_absolute_user_paths(input_path) if input_path else None,
            "input_kind": input_kind,
            "bytes": len(text.encode("utf-8")),
            "lines": len(text.splitlines()),
        },
        "routing": routing,
        "progress": progress,
        "action": action,
        "status": status,
        "sections": sections,
        "normalized_outcome": outcome,
        "handoff": handoff,
        "next": next_state,
        "residue_audit": audit,
        "health": health,
    }


def audit_residue(text: str) -> dict[str, Any]:
    pseudo_tags = sorted({f"::{match.group('tag')}" for match in _PSEUDO_GIT_RE.finditer(text)})
    path_matches = _absolute_user_path_matches(text)
    paste_ready_prompt = any(marker in text for marker in _PASTE_PROMPT_MARKERS)
    risky_terms = _risky_automation_residues(text)
    execution_overclaim = _contains_execution_automation_overclaim(text)
    production_overclaim = bool(re.search(r"\bproduction[- ]ready\b|\bpublic action\b", text, re.IGNORECASE))

    notes: list[str] = []
    if paste_ready_prompt:
        notes.append("paste-ready supervisor prompt residue detected")
    if pseudo_tags:
        notes.append("pseudo git tags detected")
    if path_matches and not _all_paths_redacted(path_matches):
        notes.append("unredacted local user path detected")
    if risky_terms:
        notes.append("risky automation instruction residue detected")
    if execution_overclaim or production_overclaim:
        notes.append("readiness overclaim residue detected")

    return {
        "contains_paste_ready_prompt": paste_ready_prompt,
        "contains_pseudo_git_tags": bool(pseudo_tags),
        "pseudo_git_tags": pseudo_tags,
        "contains_absolute_user_paths": bool(path_matches),
        "absolute_user_paths_redacted": _all_paths_redacted(path_matches) if path_matches else False,
        "absolute_user_path_count": len(path_matches),
        "contains_runner_or_scheduler_instruction": bool(risky_terms),
        "risky_automation_residues": risky_terms,
        "contains_execution_automation_overclaim": execution_overclaim,
        "contains_production_readiness_overclaim": production_overclaim,
        "notes": notes,
    }


def redact_absolute_user_paths(text: str | None) -> str | None:
    if text is None:
        return None
    text = _WINDOWS_USER_PATH_RE.sub(r"\g<prefix><redacted>\g<rest>", text)
    return _UNIX_HOME_PATH_RE.sub(r"\g<prefix><redacted>\g<rest>", text)


def dumps_normalization(normalization: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(
        normalization,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=False,
    ) + "\n"


def write_normalization(
    normalization: dict[str, Any],
    output_path: str | Path,
    *,
    pretty: bool = False,
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps_normalization(normalization, pretty=pretty), encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize an AGENT_REPORT-like text report.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Input report text path.")
    source.add_argument("--stdin", action="store_true", help="Read report text from stdin.")
    parser.add_argument("--output", help="Output JSON path. Omit to write to stdout.")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON.")
    args = parser.parse_args(argv)

    if args.stdin:
        text = sys.stdin.read()
        input_path = None
    else:
        input_path = args.input
        try:
            text = Path(args.input).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"input error: {exc}", file=sys.stderr)
            return 2

    normalization = normalize_report(text, input_path=input_path)
    payload = dumps_normalization(normalization, pretty=args.pretty)
    if args.output:
        write_normalization(normalization, args.output, pretty=args.pretty)
    else:
        print(payload, end="")
    return 0


def _parse_headers(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in _HEADER_RE.finditer(text)}


def _parse_route(header: str | None) -> dict[str, Any]:
    result = {
        "route": None,
        "direction": None,
        "slice": None,
        "turn": None,
        "target": None,
        "artifact_current": None,
        "artifact_next": None,
        "reply": None,
        "confidence": None,
    }
    if not header:
        return result

    segments = _pipe_segments(header)
    if segments:
        result["route"] = segments[0]
    for segment in segments[1:]:
        if "->" in segment and ":" not in segment:
            result["direction"] = segment
            continue
        key, value = _split_key_value(segment)
        if key in result:
            result[key] = value
    return result


def _parse_progress(header: str | None) -> dict[str, Any]:
    result = {
        "lane": None,
        "meter": None,
        "done": None,
        "total": None,
        "current": None,
        "next": None,
        "blocker": None,
        "user_work": None,
    }
    if not header:
        return result

    match = _PROGRESS_RE.match(header.strip())
    if match:
        result.update(
            {
                "lane": match.group("lane").strip(),
                "meter": match.group("meter"),
                "done": int(match.group("done")),
                "total": int(match.group("total")),
            }
        )
        for segment in _pipe_segments(match.group("rest") or ""):
            key, value = _split_key_value(segment)
            if key in result:
                result[key] = value
    else:
        result["lane"] = header.strip() or None
    return result


def _parse_action(header: str | None) -> dict[str, Any]:
    result = {"decision": None, "now_owner": None, "deliverable": None, "trigger": None}
    if header:
        result.update(_known_key_values(header, result.keys()))
    return result


def _parse_status(header: str | None) -> dict[str, Any]:
    result = {
        "health": None,
        "gates_done": None,
        "gates_total": None,
        "stop_class": None,
        "estimate_agent": None,
        "estimate_user": None,
    }
    if not header:
        return result

    for segment in _pipe_segments(header):
        key, value = _split_key_value(segment)
        if key == "gates":
            counts = _parse_count_pair(value)
            result["gates_done"], result["gates_total"] = counts
        elif key in result:
            result[key] = value
    return result


def _extract_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    extra_index = 0

    for line in text.splitlines():
        if _is_prompt_instruction_line(line):
            current = None
            continue
        if line.strip().startswith("::git-"):
            continue
        heading = _section_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
        elif line.strip() and not line.startswith("["):
            extra_index += 1
            key = f"preamble_{extra_index}"
            sections.setdefault(key, []).append(line)

    return {key: _clean_section_body(lines) for key, lines in sections.items()}


def _is_prompt_instruction_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if any(marker in stripped for marker in _PASTE_PROMPT_MARKERS):
        return True
    return stripped in {"Task:", "Goal Stack:", "Allowed scope:", "Report format:"}


def _build_sections(section_text: dict[str, str]) -> dict[str, Any]:
    known = {
        "outcome": section_text.get("outcome"),
        "what_changed": section_text.get("what_changed"),
        "artifacts": _section_items(section_text.get("artifacts")),
        "commands_and_results": _section_items(section_text.get("commands_and_results")),
        "validation": _section_items(section_text.get("validation")),
        "completion_matrix": section_text.get("completion_matrix"),
        "continuation_state": section_text.get("continuation_state"),
        "user_side_work": section_text.get("user_side_work"),
        "agent_side_work": section_text.get("agent_side_work"),
        "handoff_gate": section_text.get("handoff_gate"),
        "extra": {},
    }
    for key, value in section_text.items():
        if key not in known:
            known["extra"][key] = value
    return known


def _build_normalized_outcome(
    text: str,
    sections: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    commits = _extract_commits(text)
    return {
        "decision": action.get("decision") or _infer_decision(text),
        "summary": _first_sentence(sections.get("outcome")),
        "commits": commits,
        "pushed": _infer_pushed(text),
        "worktree": _infer_worktree(text),
        "remote_parity": _infer_remote_parity(text),
        "tests": _extract_test_counts(text),
    }


def _build_handoff(sections: dict[str, Any], text: str) -> dict[str, Any]:
    handoff_text = sections.get("handoff_gate") or ""
    combined = f"{handoff_text}\n{text}".lower()
    gate = None
    reason = None
    if re.search(r"handoff gate[:\s-]*(pass|false)|no blocked handoff|required:?\s*no", combined):
        gate = False
    elif re.search(r"handoff gate[:\s-]*(fail|true)|handoff required|required:?\s*yes", combined):
        gate = True
        reason = _first_sentence(handoff_text) or "handoff requested by report"

    supervisor_prompt = bool(
        re.search(r"supervisor_should_generate_prompt\s*[:=]\s*true", text, re.IGNORECASE)
    )
    return {
        "handoff_gate": gate,
        "handoff_reason": reason,
        "supervisor_should_generate_prompt": supervisor_prompt,
    }


def _build_next(
    routing: dict[str, Any],
    progress: dict[str, Any],
    action: dict[str, Any],
    sections: dict[str, Any],
) -> dict[str, Any]:
    artifact_next = routing.get("artifact_next") or progress.get("next")
    return {
        "artifact_next": artifact_next,
        "recommended_next_slice": artifact_next,
        "next_owner": action.get("now_owner"),
        "minimal_next_task": _first_sentence(sections.get("continuation_state")),
    }


def _build_health(
    routing: dict[str, Any],
    progress: dict[str, Any],
    action: dict[str, Any],
    status: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    if not routing.get("route"):
        warnings.append("route header missing")
    if not progress.get("lane"):
        warnings.append("progress header missing")
    if not action.get("decision"):
        warnings.append("action header missing")
    if not status.get("health"):
        warnings.append("status header missing")
    warnings.extend(audit["notes"])

    red_flags = (
        audit["contains_paste_ready_prompt"]
        or (audit["contains_absolute_user_paths"] and not audit["absolute_user_paths_redacted"])
        or audit["contains_runner_or_scheduler_instruction"]
        or audit["contains_execution_automation_overclaim"]
        or audit["contains_production_readiness_overclaim"]
    )
    if red_flags:
        normalization_status = "red"
        stop_class = "UNKNOWN"
    elif warnings:
        normalization_status = "yellow"
        stop_class = "INTEGRATE_AND_CONTINUE"
    else:
        normalization_status = "green"
        stop_class = "NONE"

    return {
        "normalization_status": normalization_status,
        "warnings": warnings,
        "stop_class": stop_class,
    }


def _pipe_segments(text: str) -> list[str]:
    return [segment.strip() for segment in text.split("|") if segment.strip()]


def _split_key_value(segment: str) -> tuple[str, str | None]:
    if ":" in segment:
        key, value = segment.split(":", 1)
    elif "=" in segment:
        key, value = segment.split("=", 1)
    else:
        return _key(segment), None
    return _key(key), value.strip() or None


def _known_key_values(text: str, keys: Any) -> dict[str, str | None]:
    known = set(keys)
    parsed: dict[str, str | None] = {}
    for segment in _pipe_segments(text):
        key, value = _split_key_value(segment)
        if key in known:
            parsed[key] = value
    return parsed


def _parse_count_pair(value: str | None) -> tuple[int | None, int | None]:
    if not value or "/" not in value:
        return None, None
    left, right = value.split("/", 1)
    try:
        return int(left.strip()), int(right.strip())
    except ValueError:
        return None, None


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _section_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("["):
        return None

    match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
    if match:
        return _SECTION_ALIASES.get(_key(match.group(1)))

    match = re.match(r"^\*\*(.+?)\*\*$", stripped)
    if match:
        return _SECTION_ALIASES.get(_key(match.group(1)))

    if len(stripped) <= 80:
        return _SECTION_ALIASES.get(_key(stripped.rstrip(":")))
    return None


def _clean_section_body(lines: list[str]) -> str | None:
    body = "\n".join(lines).strip()
    return body or None


def _section_items(body: str | None) -> list[str]:
    if not body:
        return []
    bullets = []
    for line in body.splitlines():
        stripped = line.strip()
        match = re.match(r"^[-*]\s+(.+)$", stripped)
        if match:
            bullets.append(match.group(1).strip())
    if bullets:
        return bullets
    if "\n" not in body and "," in body:
        return [item.strip() for item in body.split(",") if item.strip()]
    return [body]


def _extract_commits(text: str) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in _SHA_RE.finditer(text):
        sha = match.group("sha")
        message = _clean_commit_message(match.group("message"))
        if sha in seen or _looks_like_path_fragment(message):
            continue
        seen.add(sha)
        commits.append({"sha": sha, "message": message})
    return commits


def _looks_like_path_fragment(value: str) -> bool:
    return "/" in value[:20] or "\\" in value[:20]


def _clean_commit_message(value: str) -> str:
    message = value.strip()
    message = re.split(
        r"(?:,\s+and\s+pushed\b|\s+and\s+pushed\b|\. Final\b|\. Push\b)",
        message,
        maxsplit=1,
    )[0]
    return message.strip().rstrip(".,;")


def _infer_decision(text: str) -> str | None:
    lowered = text.lower()
    for value in ("completed", "partial", "blocked", "needs_decision"):
        if value in lowered:
            return value
    return None


def _infer_pushed(text: str) -> bool | None:
    lowered = text.lower()
    if "not pushed" in lowered or "push blocked" in lowered:
        return False
    if "pushed" in lowered or "push completed" in lowered or "::git-push" in lowered:
        return True
    return None


def _infer_worktree(text: str) -> str | None:
    lowered = text.lower()
    if re.search(
        r"\bclean worktree\b|\bworktree clean\b|\bclean state\b|\brepo state was clean\b",
        lowered,
    ):
        return "clean"
    if re.search(r"\bdirty worktree\b|\bworktree is dirty\b", lowered):
        return "dirty"
    return None


def _infer_remote_parity(text: str) -> str | None:
    match = _PARITY_RE.search(text)
    if match:
        return re.sub(r"\s+", " ", match.group("parity")).strip()
    return None


def _extract_test_counts(text: str) -> list[dict[str, int]]:
    return [{"count": int(match.group("count"))} for match in _TEST_COUNT_RE.finditer(text)]


def _first_sentence(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return None
    match = re.match(r"(.+?[.!?])(?:\s|$)", cleaned)
    return (match.group(1) if match else cleaned)[:500]


def _absolute_user_path_matches(text: str) -> list[str]:
    matches = [match.group(0) for match in _WINDOWS_USER_PATH_RE.finditer(text)]
    matches.extend(match.group(0) for match in _UNIX_HOME_PATH_RE.finditer(text))
    return matches


def _all_paths_redacted(paths: list[str]) -> bool:
    return bool(paths) and all("<redacted>" in path for path in paths)


def _risky_automation_residues(text: str) -> list[str]:
    lowered = text.lower()
    residues: list[str] = []
    for term in _RISKY_AUTOMATION_TERMS:
        term_lower = term.lower()
        for match in re.finditer(re.escape(term_lower), lowered):
            window = lowered[max(0, match.start() - 80) : match.start()]
            if any(hint in window for hint in _NEGATION_HINTS):
                continue
            residues.append(term)
            break
    return residues


def _contains_execution_automation_overclaim(text: str) -> bool:
    for line in text.splitlines():
        lowered = line.lower()
        if "execution automation readiness" not in lowered:
            continue
        if any(hint in lowered for hint in _NEGATION_HINTS) or "0/" in lowered:
            continue
        if re.search(r"\[[#]+\]|\badvanced\b|\bcompleted\b|\bready\b", lowered):
            return True
    return False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
