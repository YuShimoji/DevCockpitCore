from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import (
    ADAPTERS_VALIDATE_HELP_KEY,
    ALLOWED_COMMAND_KEYS,
    ControlledRunnerProbeError,
    load_probe,
    run_probe,
    validate_probe,
)


PROBE = ROOT / "samples" / "controlled_runner_probes" / "controlled_runner_probe_adapters_validate_help_v1.json"
RESULT = ROOT / "samples" / "controlled_runner_probes" / "controlled_runner_probe_adapters_validate_help_result_v1.json"
DOC = ROOT / "docs" / "design" / "C3_SECOND_COMMAND_PRODUCTION_PROBE_V1.md"


class C3SecondCommandProductionProbeTests(unittest.TestCase):
    def test_probe_config_loads_and_selects_adapters_help(self) -> None:
        probe = load_probe(PROBE)
        self.assertEqual(probe["schema_version"], "controlled_runner_probe.v1")
        self.assertEqual(probe["command_key"], ADAPTERS_VALIDATE_HELP_KEY)
        self.assertEqual(probe["command_class"], "fixed_repo_local_help")

    def test_allowed_production_command_keys_are_exactly_two(self) -> None:
        self.assertEqual(ALLOWED_COMMAND_KEYS, ("status_snapshot_help", "adapters_validate_help"))

    def test_probe_runs_help_only_behavior(self) -> None:
        result = run_probe(load_probe(PROBE), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["probe"]["command_key"], ADAPTERS_VALIDATE_HELP_KEY)
        self.assertEqual(result["command"]["exit_code"], 0)
        self.assertEqual(result["command"]["argv_redacted"][1:], ["-m", "dev_cockpit.adapters", "--help"])
        self.assertIn("Validate DevCockpitCore adapter manifests.", result["command"]["stdout_excerpt"])
        self.assertFalse(result["authority"]["arbitrary_command_execution"])
        self.assertFalse(result["authority"]["shell"])
        self.assertEqual(result["authority"]["command_source"], "hardcoded_allowlist")

    def test_probe_does_not_execute_adapter_validation(self) -> None:
        result = run_probe(load_probe(PROBE), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        argv = result["command"]["argv_redacted"]
        self.assertNotIn("--validate", argv)
        self.assertNotIn(": OK (", result["command"]["stdout_excerpt"])
        self.assertNotIn(": ERROR:", result["command"]["stdout_excerpt"])
        self.assertFalse(result["authority"]["adapter_default_validation_executed"])

    def test_unknown_command_key_and_overrides_fail_cleanly(self) -> None:
        for key, value in (
            ("command_key", "not_allowed"),
            ("command", "python -m dev_cockpit.adapters --validate adapters/devcockpitcore.json"),
            ("executable", sys.executable),
            ("argv", ["-m", "dev_cockpit.adapters", "--validate"]),
            ("args", ["--validate"]),
            ("shell", True),
        ):
            with self.subTest(key=key):
                probe = load_probe(PROBE)
                probe[key] = value
                with self.assertRaises(ControlledRunnerProbeError):
                    validate_probe(probe)

    def test_timeout_is_required(self) -> None:
        probe = load_probe(PROBE)
        del probe["timeout_seconds"]
        with self.assertRaises(ControlledRunnerProbeError):
            validate_probe(probe)

    def test_before_after_repo_state_and_locks_are_reported(self) -> None:
        result = run_probe(load_probe(PROBE), repo_path=ROOT, generated_at="2026-01-01T00:00:00Z")
        for field in ("worktree_before", "worktree_after", "remote_parity_before", "remote_parity_after"):
            self.assertIn(field, result["repo"])
        self.assertFalse(result["authority"]["target_repo_writeback"])
        self.assertFalse(result["authority"]["credentials_required"])
        self.assertFalse(result["authority"]["network_required"])
        self.assertFalse(result["authority"]["c4_unlocked"])
        self.assertFalse(result["authority"]["c5_unlocked"])
        self.assertFalse(result["authority"]["c6_unlocked"])

    def test_sample_result_json_is_valid_when_present(self) -> None:
        if not RESULT.exists():
            self.skipTest("sample production probe result has not been generated")
        data = json.loads(RESULT.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "controlled_runner_probe_result.v1")
        self.assertEqual(data["probe"]["command_key"], ADAPTERS_VALIDATE_HELP_KEY)
        self.assertEqual(data["command"]["argv_redacted"][1:], ["-m", "dev_cockpit.adapters", "--help"])
        self.assertFalse(data["authority"]["adapter_default_validation_executed"])
        self.assertFalse(data["authority"]["target_repo_writeback"])

    def test_no_generalized_runner_shell_true_or_prompt_markers(self) -> None:
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "runner.py").exists())
        self.assertFalse((ROOT / "src" / "dev_cockpit" / "controlled_runner.py").exists())
        source = (ROOT / "src" / "dev_cockpit" / "controlled_runner_probe.py").read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)
        payload = PROBE.read_text(encoding="utf-8") + "\n" + DOC.read_text(encoding="utf-8")
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)


if __name__ == "__main__":
    unittest.main()
