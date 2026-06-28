from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import (
    ALLOWED_COMMAND_KEY,
    RESULT_SCHEMA_VERSION,
    ControlledRunnerProbeError,
    default_probe,
    load_probe,
    redact_probe_value,
    run_probe,
    truncate_output,
    validate_probe,
)


SAMPLE_PROBE = ROOT / "samples" / "controlled_runner_probes" / "controlled_runner_probe_v1.json"
SAMPLE_RESULT = ROOT / "samples" / "controlled_runner_probes" / "controlled_runner_probe_result_v1.json"


class ControlledRunnerProbeTests(unittest.TestCase):
    def test_probe_config_loads_and_validates(self) -> None:
        probe = load_probe(SAMPLE_PROBE)
        self.assertEqual(probe["schema_version"], "controlled_runner_probe.v1")
        self.assertEqual(probe["command_key"], ALLOWED_COMMAND_KEY)

    def test_default_probe_can_be_built(self) -> None:
        probe = validate_probe(default_probe())
        self.assertEqual(probe["probe_key"], "devcockpitcore_status_snapshot_help_probe")
        self.assertEqual(probe["command_class"], "fixed_repo_local_help")

    def test_result_contains_required_top_level_keys(self) -> None:
        result = run_probe(validate_probe(default_probe()), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        for key in (
            "schema_version",
            "generated_at",
            "producer",
            "probe",
            "authority",
            "repo",
            "command",
            "artifacts",
            "safety_gates",
            "summary",
            "health",
            "next",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["schema_version"], RESULT_SCHEMA_VERSION)

    def test_status_snapshot_help_command_key_is_accepted(self) -> None:
        result = run_probe(validate_probe(default_probe()), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["probe"]["command_key"], ALLOWED_COMMAND_KEY)
        self.assertEqual(result["command"]["exit_code"], 0)

    def test_unknown_command_key_fails_cleanly(self) -> None:
        data = default_probe()
        data["command_key"] = "not_allowed"
        with self.assertRaises(ControlledRunnerProbeError):
            validate_probe(data)

    def test_executable_command_fields_are_rejected(self) -> None:
        for field in ("command", "commands", "cmd", "executable"):
            with self.subTest(field=field):
                data = default_probe()
                data[field] = "python -m dev_cockpit.status_snapshot --help"
                with self.assertRaises(ControlledRunnerProbeError):
                    validate_probe(data)

    def test_argv_and_args_overrides_are_rejected(self) -> None:
        for field in ("argv", "args"):
            with self.subTest(field=field):
                data = default_probe()
                data[field] = ["--help"]
                with self.assertRaises(ControlledRunnerProbeError):
                    validate_probe(data)

    def test_shell_flag_cannot_be_enabled(self) -> None:
        data = default_probe()
        data["shell"] = True
        with self.assertRaises(ControlledRunnerProbeError):
            validate_probe(data)

    def test_timeout_is_required(self) -> None:
        data = default_probe()
        del data["timeout_seconds"]
        with self.assertRaises(ControlledRunnerProbeError):
            validate_probe(data)
        data = default_probe()
        data["timeout_seconds"] = 0
        with self.assertRaises(ControlledRunnerProbeError):
            validate_probe(data)

    def test_stdout_stderr_truncation_helpers(self) -> None:
        excerpt, truncated = truncate_output("a" * 20, limit=5)
        self.assertEqual(excerpt, "aaaaa")
        self.assertTrue(truncated)

    def test_local_user_paths_are_redacted(self) -> None:
        redacted = redact_probe_value(r"C:\Users\someone\Repo")
        self.assertEqual(redacted, r"C:\Users\<redacted>\Repo")

    def test_redactions_applied_records_local_path_redaction(self) -> None:
        result = run_probe(validate_probe(default_probe()), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        if "<redacted>" not in result["command"]["cwd_redacted"]:
            self.skipTest("repository path did not require local user path redaction")
        self.assertIn("local_user_path", result["command"]["redactions_applied"])

    def test_probe_path_is_redacted_when_absolute(self) -> None:
        absolute_probe_path = str(ROOT / "samples" / "controlled_runner_probes" / "controlled_runner_probe_v1.json")
        result = run_probe(
            validate_probe(default_probe()),
            repo_path=ROOT,
            probe_path=absolute_probe_path,
            generated_at="2026-01-01T00:00:00Z",
        )
        if "<redacted>" not in result["probe"]["probe_path"]:
            self.skipTest("probe path did not require local user path redaction")
        self.assertNotIn(r"C:\Users\thank", result["probe"]["probe_path"])

    def test_before_and_after_repo_state_fields_exist(self) -> None:
        result = run_probe(validate_probe(default_probe()), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        repo = result["repo"]
        for field in ("worktree_before", "worktree_after", "remote_parity_before", "remote_parity_after"):
            self.assertIn(field, repo)

    def test_safety_gates_are_present(self) -> None:
        result = run_probe(validate_probe(default_probe()), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        for gate in (
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
        ):
            self.assertIn(gate, result["safety_gates"])

    def test_summary_includes_meter_fields(self) -> None:
        result = run_probe(validate_probe(default_probe()), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        for field in ("done", "total", "unknown", "meter", "missing"):
            self.assertIn(field, result["summary"])

    def test_no_arbitrary_command_execution_from_config(self) -> None:
        data = default_probe()
        data["notes"] = ["try to run: python -m unittest"]
        probe = validate_probe(data)
        result = run_probe(probe, repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["command"]["argv_redacted"][1:], ["-m", "dev_cockpit.status_snapshot", "--help"])

    def test_no_target_repo_writeback_is_attempted(self) -> None:
        before = _short_status(ROOT)
        result = run_probe(validate_probe(default_probe()), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        after = _short_status(ROOT)
        self.assertEqual(before, after)
        self.assertFalse(result["authority"]["target_repo_writeback"])

    def test_no_paste_ready_prompt_is_emitted(self) -> None:
        result = run_probe(validate_probe(default_probe()), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        payload = json.dumps(result)
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)

    def test_no_scheduler_notification_or_database_implementation_is_introduced(self) -> None:
        source = (ROOT / "src" / "dev_cockpit" / "controlled_runner_probe.py").read_text(encoding="utf-8")
        for token in ("smtplib", "sqlite3", "auto_render", "BackgroundScheduler"):
            self.assertNotIn(token, source)

    def test_no_general_runner_module_exists(self) -> None:
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "controlled_runner.py").exists())

    def test_sample_result_json_is_valid_when_present(self) -> None:
        if not SAMPLE_RESULT.exists():
            self.skipTest("sample probe result has not been generated")
        data = json.loads(SAMPLE_RESULT.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], RESULT_SCHEMA_VERSION)


def _short_status(path: Path) -> str:
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


if __name__ == "__main__":
    unittest.main()
