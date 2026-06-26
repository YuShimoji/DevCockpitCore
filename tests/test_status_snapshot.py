from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.status_snapshot import build_status_snapshot, dumps_snapshot, write_snapshot


def _git_available() -> bool:
    return shutil.which("git") is not None


@unittest.skipUnless(_git_available(), "git is required for status snapshot tests")
class StatusSnapshotTests(unittest.TestCase):
    def test_temp_git_repo_clean_and_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = _init_repo(tmp / "repo")
            adapter = _write_adapter(tmp / "adapter.json")

            clean = build_status_snapshot(repo, adapter, generated_at="2026-01-01T00:00:00Z")
            self.assertTrue(clean["repo"]["exists"])
            self.assertTrue(clean["repo"]["is_git_repo"])
            self.assertEqual(clean["repo"]["worktree"]["state"], "clean")
            self.assertEqual(clean["repo"]["remote_parity"]["status"], "unknown")
            self.assertEqual(clean["repo"]["remote_parity"]["reason"], "missing_upstream")

            (repo / "notes.txt").write_text("dirty\n", encoding="utf-8")
            dirty = build_status_snapshot(repo, adapter, generated_at="2026-01-01T00:00:00Z")
            self.assertEqual(dirty["repo"]["worktree"]["state"], "dirty")
            self.assertIn("?? notes.txt", dirty["repo"]["worktree"]["short_status"])

    def test_missing_target_repo_is_structured_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            adapter = _write_adapter(tmp / "adapter.json")
            snapshot = build_status_snapshot(
                tmp / "missing",
                adapter,
                generated_at="2026-01-01T00:00:00Z",
            )
            self.assertFalse(snapshot["repo"]["exists"])
            self.assertFalse(snapshot["repo"]["is_git_repo"])
            self.assertEqual(snapshot["health"]["status"], "yellow")
            self.assertEqual(snapshot["health"]["stop_class"], "INTEGRATE_AND_CONTINUE")

    def test_required_top_level_keys_and_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            repo = _init_repo(tmp / "repo")
            adapter = _write_adapter(tmp / "adapter.json")
            snapshot = build_status_snapshot(repo, adapter, generated_at="2026-01-01T00:00:00Z")
            for key in (
                "schema_version",
                "generated_at",
                "producer",
                "adapter",
                "repo",
                "project_state",
                "artifacts",
                "validation",
                "health",
            ):
                self.assertIn(key, snapshot)

            payload = dumps_snapshot(snapshot, pretty=True)
            self.assertEqual(json.loads(payload)["schema_version"], "status_snapshot.v1")

            output = tmp / "out" / "status.json"
            write_snapshot(snapshot, output, pretty=True)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["producer"], "dev_cockpit.status_snapshot")


def _init_repo(path: Path) -> Path:
    path.mkdir()
    _run(["git", "init"], path)
    _run(["git", "config", "user.email", "dev-cockpit@example.invalid"], path)
    _run(["git", "config", "user.name", "Dev Cockpit Tests"], path)
    (path / "README.md").write_text("# Example\n", encoding="utf-8")
    (path / "docs").mkdir()
    (path / "docs" / "runtime-state.md").write_text("next: verify snapshot\n", encoding="utf-8")
    (path / "docs" / "project-context.md").write_text("user_work: none\n", encoding="utf-8")
    _run(["git", "add", "."], path)
    _run(["git", "commit", "-m", "init"], path)
    return path


def _write_adapter(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "project": "Example",
                "default_branch": None,
                "runtime_state": "docs/runtime-state.md",
                "project_context": "docs/project-context.md",
                "artifact_roots": ["docs"],
                "forbidden_stage_patterns": ["*.mp4"],
                "default_validation": ["git diff --check"],
                "read_only": True,
            }
        ),
        encoding="utf-8",
    )
    return path


def _run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
