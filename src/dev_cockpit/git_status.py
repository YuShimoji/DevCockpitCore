"""Read-only git inspection for target repositories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
from typing import Any


@dataclass(frozen=True)
class GitCommandResult:
    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def stripped_stdout(self) -> str:
        return self.stdout.strip()

    @property
    def stripped_stderr(self) -> str:
        return self.stderr.strip()


def inspect_repo(
    repo_path: str | Path,
    *,
    observed_at: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    repo = Path(repo_path)
    observation_time = observed_at or _utc_now_iso()
    notes: list[str] = []
    base = {
        "path": str(repo_path),
        "observed_at": observation_time,
        "exists": repo.exists(),
        "is_git_repo": False,
        "branch": None,
        "head": None,
        "head_revision": None,
        "upstream": None,
        "latest_commit": None,
        "remote_parity": {
            "ahead": None,
            "behind": None,
            "raw": None,
            "status": "unknown",
            "reason": "repo_not_inspected",
            "tracking_ref": None,
            "evidence_basis": "local_tracking_reference_no_fetch",
            "fetch_performed": False,
        },
        "worktree": {
            "state": "unknown",
            "short_status": [],
        },
    }

    if not repo.exists():
        notes.append("target repository path does not exist")
        base["remote_parity"]["reason"] = "repo_missing"
        return base, notes

    status = _run_git(repo, ("status", "--short", "--branch"))
    if not status.ok:
        notes.append(_git_failure_note("git status failed", status))
        base["remote_parity"]["reason"] = "not_git_repo"
        return base, notes

    short_lines = [line for line in status.stdout.splitlines() if line]
    branch_header = short_lines[0] if short_lines and short_lines[0].startswith("##") else None
    worktree_lines = short_lines[1:] if branch_header else short_lines

    base["is_git_repo"] = True
    base["worktree"] = {
        "state": "clean" if not worktree_lines else "dirty",
        "short_status": worktree_lines,
    }

    branch = _stdout_or_none(_run_git(repo, ("branch", "--show-current")))
    base["branch"] = branch or _branch_from_status_header(branch_header)

    base["head"] = _stdout_or_none(_run_git(repo, ("rev-parse", "--short", "HEAD")))
    base["head_revision"] = _stdout_or_none(_run_git(repo, ("rev-parse", "HEAD")))
    base["latest_commit"] = _stdout_or_none(_run_git(repo, ("log", "-1", "--oneline")))

    upstream_result = _run_git(repo, ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"))
    upstream = _stdout_or_none(upstream_result)
    base["upstream"] = upstream
    if not upstream:
        base["remote_parity"] = {
            "ahead": None,
            "behind": None,
            "raw": None,
            "status": "unknown",
            "reason": "missing_upstream",
            "tracking_ref": None,
            "evidence_basis": "local_tracking_reference_no_fetch",
            "fetch_performed": False,
        }
        return base, notes

    parity_result = _run_git(repo, ("rev-list", "--left-right", "--count", "HEAD...@{u}"))
    if not parity_result.ok:
        notes.append(_git_failure_note("git remote parity failed", parity_result))
        base["remote_parity"] = {
            "ahead": None,
            "behind": None,
            "raw": parity_result.stripped_stdout or None,
            "status": "unknown",
            "reason": "parity_unavailable",
            "tracking_ref": upstream,
            "evidence_basis": "local_tracking_reference_no_fetch",
            "fetch_performed": False,
        }
        return base, notes

    raw = parity_result.stripped_stdout
    base["remote_parity"] = _parse_parity(raw, tracking_ref=upstream)
    return base, notes


def _run_git(repo: Path, args: tuple[str, ...]) -> GitCommandResult:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )
    return GitCommandResult(
        args=args,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _stdout_or_none(result: GitCommandResult) -> str | None:
    if result.ok and result.stripped_stdout:
        return result.stripped_stdout
    return None


def _branch_from_status_header(header: str | None) -> str | None:
    if not header:
        return None
    branch = header[2:].strip()
    if "..." in branch:
        branch = branch.split("...", 1)[0]
    if branch.startswith("HEAD"):
        return None
    return branch or None


def _parse_parity(raw: str, *, tracking_ref: str | None = None) -> dict[str, Any]:
    parts = raw.replace("\t", " ").split()
    if len(parts) != 2:
        return {
            "ahead": None,
            "behind": None,
            "raw": raw,
            "status": "unknown",
            "reason": "unexpected_parity_output",
            "tracking_ref": tracking_ref,
            "evidence_basis": "local_tracking_reference_no_fetch",
            "fetch_performed": False,
        }

    try:
        ahead = int(parts[0])
        behind = int(parts[1])
    except ValueError:
        return {
            "ahead": None,
            "behind": None,
            "raw": raw,
            "status": "unknown",
            "reason": "unexpected_parity_output",
            "tracking_ref": tracking_ref,
            "evidence_basis": "local_tracking_reference_no_fetch",
            "fetch_performed": False,
        }

    if ahead == 0 and behind == 0:
        status = "in_sync"
    elif ahead > 0 and behind > 0:
        status = "diverged"
    elif ahead > 0:
        status = "ahead"
    else:
        status = "behind"

    return {
        "ahead": ahead,
        "behind": behind,
        "raw": raw,
        "status": status,
        "tracking_ref": tracking_ref,
        "evidence_basis": "local_tracking_reference_no_fetch",
        "fetch_performed": False,
    }


def _git_failure_note(prefix: str, result: GitCommandResult) -> str:
    detail = result.stripped_stderr or result.stripped_stdout or f"exit {result.returncode}"
    return f"{prefix}: {detail}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
