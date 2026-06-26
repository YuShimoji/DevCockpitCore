"""Produce read-only status snapshots for target repositories."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fnmatch
import json
from pathlib import Path
import re
import sys
from typing import Any

from .adapters import AdapterConfig, AdapterError, load_adapter
from .git_status import inspect_repo


SCHEMA_VERSION = "status_snapshot.v1"
PRODUCER = "dev_cockpit.status_snapshot"
PROJECT_TEXT_LIMIT = 64 * 1024
ARTIFACT_SCAN_LIMIT = 1000
ARTIFACT_CANDIDATE_LIMIT = 10

_LABEL_RE = re.compile(
    r"^\s*(?:[-*]\s*)?"
    r"(?P<label>active_artifact|artifact_current|artifact_next|next_action|next|user_work|render_gate)"
    r"\s*[:=]\s*(?P<value>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def build_status_snapshot(
    repo_path: str | Path,
    adapter_path: str | Path,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    adapter = load_adapter(adapter_path)
    repo_status, git_notes = inspect_repo(repo_path)
    repo = Path(repo_path)

    project_state = inspect_project_state(repo, adapter)
    artifacts = inspect_artifacts(repo, adapter)
    validation = {
        "default_commands": list(adapter.default_validation),
        "not_run_reason": "observer_only_slice",
    }
    health = classify_health(adapter, repo_status, project_state, git_notes)

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_iso(),
        "producer": PRODUCER,
        "adapter": adapter.to_snapshot(str(adapter_path)),
        "repo": repo_status,
        "project_state": project_state,
        "artifacts": artifacts,
        "validation": validation,
        "health": health,
    }


def inspect_project_state(repo: Path, adapter: AdapterConfig) -> dict[str, Any]:
    runtime_path = adapter.runtime_state
    context_path = adapter.project_context
    runtime_file = repo / runtime_path if runtime_path else None
    context_file = repo / context_path if context_path else None

    labels: dict[str, str] = {}
    for candidate in (runtime_file, context_file):
        if candidate and candidate.is_file():
            labels.update(_extract_labels(candidate))

    active_artifact = (
        labels.get("active_artifact")
        or labels.get("artifact_current")
        or labels.get("artifact_next")
    )
    next_action = labels.get("next_action") or labels.get("next") or labels.get("artifact_next")

    return {
        "runtime_state_path": runtime_path,
        "runtime_state_exists": bool(runtime_file and runtime_file.is_file()),
        "project_context_path": context_path,
        "project_context_exists": bool(context_file and context_file.is_file()),
        "active_artifact": active_artifact,
        "next_action": next_action,
        "user_work": labels.get("user_work") or "unknown",
        "render_gate": labels.get("render_gate") or "unknown",
    }


def inspect_artifacts(repo: Path, adapter: AdapterConfig) -> dict[str, Any]:
    roots: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    if not repo.exists():
        return {
            "roots": [
                {
                    "path": root,
                    "exists": False,
                    "latest_candidate_count": 0,
                }
                for root in adapter.artifact_roots
            ],
            "latest_candidates": [],
        }

    for root in adapter.artifact_roots:
        root_path = repo / root
        root_candidates = _latest_candidates(repo, root_path)
        roots.append(
            {
                "path": root,
                "exists": root_path.exists(),
                "latest_candidate_count": len(root_candidates),
            }
        )
        candidates.extend(root_candidates)

    candidates.sort(key=lambda item: item["modified_at"], reverse=True)
    return {
        "roots": roots,
        "latest_candidates": candidates[:ARTIFACT_CANDIDATE_LIMIT],
    }


def classify_health(
    adapter: AdapterConfig,
    repo_status: dict[str, Any],
    project_state: dict[str, Any],
    git_notes: list[str],
) -> dict[str, Any]:
    notes = list(git_notes)
    health = "green"
    stop_class = "NONE"

    if not adapter.read_only:
        notes.append("adapter is not read-only")
        return {
            "status": "red",
            "stop_class": "TRUE_STOP",
            "notes": notes,
        }

    if not repo_status["exists"]:
        notes.append("target repository is absent; snapshot contains adapter-only context")
        health = "yellow"
        stop_class = "INTEGRATE_AND_CONTINUE"
    elif not repo_status["is_git_repo"]:
        notes.append("target path exists but is not a git repository")
        health = "yellow"
        stop_class = "INTEGRATE_AND_CONTINUE"
    else:
        worktree_state = repo_status["worktree"]["state"]
        if worktree_state != "clean":
            notes.append(f"worktree is {worktree_state}")
            health = "yellow"
            stop_class = "INTEGRATE_AND_CONTINUE"

        parity_status = repo_status["remote_parity"]["status"]
        if parity_status == "unknown":
            notes.append("remote parity is unknown")
            health = "yellow"
            stop_class = "INTEGRATE_AND_CONTINUE"
        elif parity_status in {"behind", "diverged"}:
            notes.append(f"remote parity is {parity_status}")
            health = "yellow"
            stop_class = "INTEGRATE_AND_CONTINUE"

        default_branch = adapter.default_branch
        branch = repo_status.get("branch")
        if default_branch and branch and branch != default_branch:
            notes.append(f"current branch {branch!r} differs from adapter default {default_branch!r}")
            health = "yellow"
            stop_class = "INTEGRATE_AND_CONTINUE"

        forbidden = _forbidden_staged_matches(
            repo_status["worktree"]["short_status"],
            adapter.forbidden_stage_patterns,
        )
        if forbidden:
            notes.append(f"forbidden staged artifact patterns matched: {', '.join(forbidden)}")
            health = "red"
            stop_class = "TRUE_STOP"

    if not project_state["runtime_state_exists"]:
        notes.append("runtime state document is absent")
        if health == "green":
            health = "yellow"
            stop_class = "INTEGRATE_AND_CONTINUE"

    if not project_state["project_context_exists"]:
        notes.append("project context document is absent")
        if health == "green":
            health = "yellow"
            stop_class = "INTEGRATE_AND_CONTINUE"

    return {
        "status": health,
        "stop_class": stop_class,
        "notes": notes,
    }


def dumps_snapshot(snapshot: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(
        snapshot,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=False,
    ) + "\n"


def write_snapshot(snapshot: dict[str, Any], output_path: str | Path, *, pretty: bool = False) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps_snapshot(snapshot, pretty=pretty), encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Produce a read-only repository status snapshot.")
    parser.add_argument("--repo", required=True, help="Target repository path to inspect.")
    parser.add_argument("--adapter", required=True, help="Adapter JSON path.")
    parser.add_argument("--output", help="Output JSON path. Required unless --no-write is used.")
    parser.add_argument("--pretty", action="store_true", help="Write indented JSON.")
    parser.add_argument("--no-write", action="store_true", help="Print JSON and skip output file writes.")
    args = parser.parse_args(argv)

    if not args.output and not args.no_write:
        parser.error("--output is required unless --no-write is used")

    try:
        snapshot = build_status_snapshot(args.repo, args.adapter)
    except AdapterError as exc:
        print(f"adapter error: {exc}", file=sys.stderr)
        return 2

    payload = dumps_snapshot(snapshot, pretty=args.pretty)
    if args.no_write:
        print(payload, end="")
    else:
        write_snapshot(snapshot, args.output, pretty=args.pretty)
    return 0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _extract_labels(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")[:PROJECT_TEXT_LIMIT]
    labels: dict[str, str] = {}
    for match in _LABEL_RE.finditer(text):
        value = _normalize_label_value(match.group("value"))
        if value is not None:
            labels[match.group("label").lower()] = value
    return labels


def _normalize_label_value(value: str) -> str | None:
    cleaned = value.strip().strip("`'\"")
    if not cleaned:
        return None
    if cleaned.lower() in {"none", "null", "n/a", "unknown", "-"}:
        return None
    return cleaned


def _latest_candidates(repo: Path, root: Path) -> list[dict[str, Any]]:
    if not root.exists() or not root.is_dir():
        return []

    found: list[dict[str, Any]] = []
    seen = 0
    for path in root.rglob("*"):
        seen += 1
        if seen > ARTIFACT_SCAN_LIMIT:
            break
        if not path.is_file():
            continue
        stat = path.stat()
        found.append(
            {
                "path": _relative_posix(repo, path),
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z"),
                "size_bytes": stat.st_size,
            }
        )

    found.sort(key=lambda item: item["modified_at"], reverse=True)
    return found[:ARTIFACT_CANDIDATE_LIMIT]


def _relative_posix(base: Path, path: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _forbidden_staged_matches(short_status: list[str], patterns: tuple[str, ...]) -> list[str]:
    if not patterns:
        return []
    matches: list[str] = []
    for line in short_status:
        if len(line) < 3:
            continue
        staged_code = line[0]
        if staged_code in {" ", "?"}:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern):
                matches.append(path)
                break
    return matches


if __name__ == "__main__":
    raise SystemExit(main())
