from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import dev_cockpit.current_observation as current_observation_module
from dev_cockpit.current_observation import (
    AUTHORIZATION_SCOPE,
    CurrentObservationError,
    dumps_current_observation,
    load_current_observation,
    normalize_repository_identity,
    observe_repository,
    validate_current_observation,
)


class CurrentObservationTests(unittest.TestCase):
    def test_clean_repository_observation_is_actual_clean_stable_and_path_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = self._git_repo(root)
            output = root / "controller" / "observation.json"
            before_target = self._tree_state(repository)
            times = iter(
                (
                    datetime(2026, 7, 20, 1, 0, tzinfo=timezone.utc),
                    datetime(2026, 7, 20, 1, 0, 1, tzinfo=timezone.utc),
                )
            )

            receipt = observe_repository(
                repository=repository,
                project_key="controlled-project",
                artifact_id="controlled-observation-v1",
                authorization_scope=AUTHORIZATION_SCOPE,
                output_path=output,
                clock=lambda: next(times),
            )

            self.assertEqual(
                {"actual": True, "clean": True, "stable": True},
                receipt["observation"]["derived"],
            )
            self.assertEqual(
                receipt["observation"]["before"], receipt["observation"]["after"]
            )
            self.assertEqual(
                "https://example.invalid/controlled-project.git",
                receipt["repository"]["identity"],
            )
            self.assertNotIn(str(repository), dumps_current_observation(receipt, pretty=True))
            self.assertEqual(before_target, self._tree_state(repository))

    def test_dirty_repository_is_derived_dirty_not_caller_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = self._git_repo(root)
            (repository / "untracked.txt").write_text("dirty", encoding="utf-8")
            receipt = observe_repository(
                repository=repository,
                project_key="controlled-project",
                artifact_id="controlled-observation-v1",
                authorization_scope=AUTHORIZATION_SCOPE,
                output_path=root / "observation.json",
            )
            self.assertFalse(receipt["observation"]["derived"]["clean"])
            self.assertTrue(receipt["observation"]["derived"]["stable"])

    def test_tampered_derived_booleans_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = self._receipt(root)
            for field in ("actual", "clean", "stable"):
                with self.subTest(field=field):
                    changed = copy.deepcopy(receipt)
                    changed["observation"]["derived"][field] = not changed["observation"][
                        "derived"
                    ][field]
                    with self.assertRaisesRegex(
                        CurrentObservationError, "derived does not match"
                    ):
                        validate_current_observation(changed)

    def test_head_or_worktree_snapshot_tampering_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = self._receipt(root)
            cases = {
                "head": ("head_revision", "a" * 40),
                "hash": ("worktree_sha256", "b" * 64),
                "count": ("worktree_entry_count", 1),
            }
            for name, (field, value) in cases.items():
                with self.subTest(name=name):
                    changed = copy.deepcopy(receipt)
                    changed["observation"]["after"][field] = value
                    with self.assertRaises(CurrentObservationError):
                        validate_current_observation(changed)

    def test_exact_keys_types_scope_and_chronology_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = self._receipt(root)
            mutations = {
                "missing": lambda item: item.pop("authorization"),
                "unknown": lambda item: item.__setitem__("unexpected", False),
                "type": lambda item: item["observation"]["derived"].__setitem__(
                    "actual", 1
                ),
                "scope": lambda item: item["scope_boundary"].__setitem__(
                    "fetch_performed", True
                ),
                "chronology": lambda item: item["observation"].__setitem__(
                    "reobserved_at", "2026-07-19T23:59:59+00:00"
                ),
            }
            for name, mutate in mutations.items():
                with self.subTest(name=name):
                    changed = copy.deepcopy(receipt)
                    mutate(changed)
                    with self.assertRaises(CurrentObservationError):
                        validate_current_observation(changed)

    def test_duplicate_key_reports_object_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = self._receipt(root)
            path = root / "duplicate.json"
            path.write_text(
                dumps_current_observation(receipt).replace(
                    '"actual":true', '"actual":true,"actual":true'
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                CurrentObservationError,
                r"duplicate JSON key at \$\.observation\.derived\.actual",
            ):
                load_current_observation(path)

    def test_output_inside_target_repository_is_rejected_before_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = self._git_repo(root)
            with self.assertRaisesRegex(CurrentObservationError, "outside"):
                observe_repository(
                    repository=repository,
                    project_key="controlled-project",
                    artifact_id="controlled-observation-v1",
                    authorization_scope=AUTHORIZATION_SCOPE,
                    output_path=repository / "receipt.json",
                )

    def test_remote_identity_rejects_local_paths_credentials_and_query(self) -> None:
        self.assertEqual(
            "ssh://github.com/owner/repo.git",
            normalize_repository_identity("git@GitHub.com:owner/repo.git"),
        )
        for value in (
            "C:/private/repo",
            "file:///private/repo",
            "https://user:secret@example.com/repo.git",
            "https://example.com/repo.git?token=secret",
        ):
            with self.subTest(value=value), self.assertRaises(CurrentObservationError):
                normalize_repository_identity(value)

    def test_unstable_second_snapshot_is_derived_unstable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = self._git_repo(root)
            clean_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            first = {
                "head_revision": "a" * 40,
                "worktree_state": "clean",
                "worktree_sha256": clean_hash,
                "worktree_entry_count": 0,
            }
            second = {**first, "head_revision": "b" * 40}
            with mock.patch(
                "dev_cockpit.current_observation._capture_snapshot",
                side_effect=(first, second),
            ):
                receipt = observe_repository(
                    repository=repository,
                    project_key="controlled-project",
                    artifact_id="controlled-observation-v1",
                    authorization_scope=AUTHORIZATION_SCOPE,
                    output_path=root / "observation.json",
                )
            self.assertFalse(receipt["observation"]["derived"]["stable"])

    def test_target_mutation_between_snapshots_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = self._git_repo(root)
            original = current_observation_module._capture_snapshot
            calls = 0

            def capture(target: Path) -> dict[str, object]:
                nonlocal calls
                snapshot = original(target)
                calls += 1
                if calls == 1:
                    (target / "mutated-by-test-harness.txt").write_text(
                        "mutation\n", encoding="utf-8"
                    )
                return snapshot

            with mock.patch(
                "dev_cockpit.current_observation._capture_snapshot",
                side_effect=capture,
            ):
                receipt = observe_repository(
                    repository=repository,
                    project_key="controlled-project",
                    artifact_id="controlled-observation-v1",
                    authorization_scope=AUTHORIZATION_SCOPE,
                    output_path=root / "observation.json",
                )
            self.assertFalse(receipt["observation"]["derived"]["stable"])
            self.assertFalse(receipt["observation"]["derived"]["clean"])

    def _receipt(self, root: Path) -> dict[str, object]:
        repository = self._git_repo(root)
        start = datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc)
        times = iter((start, start + timedelta(seconds=1)))
        return observe_repository(
            repository=repository,
            project_key="controlled-project",
            artifact_id="controlled-observation-v1",
            authorization_scope=AUTHORIZATION_SCOPE,
            output_path=root / "observation.json",
            clock=lambda: next(times),
        )

    @staticmethod
    def _git_repo(root: Path) -> Path:
        repository = root / "target"
        repository.mkdir()
        commands = (
            ("git", "init", "-q"),
            ("git", "config", "user.name", "Controlled Test"),
            ("git", "config", "user.email", "controlled@example.invalid"),
            (
                "git",
                "remote",
                "add",
                "origin",
                "https://example.invalid/controlled-project.git",
            ),
        )
        for command in commands:
            subprocess.run(command, cwd=repository, check=True, capture_output=True)
        (repository / "tracked.txt").write_text("controlled\n", encoding="utf-8")
        subprocess.run(("git", "add", "tracked.txt"), cwd=repository, check=True)
        subprocess.run(
            ("git", "commit", "-q", "-m", "controlled fixture"),
            cwd=repository,
            check=True,
        )
        return repository

    @staticmethod
    def _tree_state(root: Path) -> dict[str, tuple[int, str]]:
        return {
            path.relative_to(root).as_posix(): (
                path.stat().st_mtime_ns,
                sha256(path.read_bytes()).hexdigest(),
            )
            for path in root.rglob("*")
            if path.is_file()
        }


if __name__ == "__main__":
    unittest.main()
