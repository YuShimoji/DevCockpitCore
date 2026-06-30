from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.c4_scoped_runner_probe import (
    C4_CAPABILITY_LEVEL,
    C4_COMMAND_CLASS,
    C4_COMMAND_KEY,
    C4_COMMAND_KEYS,
    C4ScopedRunnerProbeError,
    default_probe,
    load_probe,
    validate_probe,
)
from dev_cockpit.controlled_runner_probe import (
    ADAPTERS_VALIDATE_HELP_KEY,
    ALLOWED_COMMAND_KEYS,
    STATUS_SNAPSHOT_HELP_KEY,
)


IMPLEMENTATION = (
    ROOT
    / "samples"
    / "c4_probe_minimal_implementation"
    / "c4_probe_minimal_implementation_v1.json"
)
RESULT = (
    ROOT
    / "samples"
    / "c4_probe_minimal_implementation"
    / "c4_probe_minimal_result_v1.json"
)
DOC = ROOT / "docs" / "design" / "C4_PROBE_MINIMAL_IMPLEMENTATION_V1.md"
PROJECT_CONTEXT = ROOT / "docs" / "project-context.md"
SOURCE_ROOT = ROOT / "src" / "dev_cockpit"
C4_SOURCE = SOURCE_ROOT / "c4_scoped_runner_probe.py"


class C4ProbeMinimalImplementationTests(unittest.TestCase):
    def test_implementation_config_loads_and_selects_only_c4_key(self) -> None:
        probe = load_probe(IMPLEMENTATION)
        self.assertEqual(probe["schema_version"], "c4_probe_minimal_implementation.v1")
        self.assertEqual(probe["command_key"], C4_COMMAND_KEY)
        self.assertEqual(probe["capability_level"], C4_CAPABILITY_LEVEL)
        self.assertEqual(probe["command_class"], C4_COMMAND_CLASS)
        self.assertEqual(C4_COMMAND_KEYS, (C4_COMMAND_KEY,))

    def test_default_probe_is_same_single_c4_key(self) -> None:
        probe = validate_probe(default_probe())
        self.assertEqual(probe["command_key"], C4_COMMAND_KEY)
        self.assertEqual(probe["command_class"], C4_COMMAND_CLASS)

    def test_c3_command_keys_remain_exactly_two(self) -> None:
        self.assertEqual(ALLOWED_COMMAND_KEYS, (STATUS_SNAPSHOT_HELP_KEY, ADAPTERS_VALIDATE_HELP_KEY))
        self.assertEqual(len(ALLOWED_COMMAND_KEYS), 2)
        self.assertNotIn(C4_COMMAND_KEY, ALLOWED_COMMAND_KEYS)

    def test_unknown_c4_command_key_is_rejected(self) -> None:
        data = default_probe()
        data["command_key"] = "not_allowed"
        with self.assertRaises(C4ScopedRunnerProbeError):
            validate_probe(data)

    def test_config_command_overrides_are_rejected(self) -> None:
        for field in ("command", "commands", "cmd"):
            with self.subTest(field=field):
                data = default_probe()
                data[field] = "python -m dev_cockpit.validation_pack --default --pretty"
                with self.assertRaises(C4ScopedRunnerProbeError):
                    validate_probe(data)

    def test_config_executable_override_is_rejected(self) -> None:
        data = default_probe()
        data["executable"] = sys.executable
        with self.assertRaises(C4ScopedRunnerProbeError):
            validate_probe(data)

    def test_config_argv_args_and_shell_overrides_are_rejected(self) -> None:
        for field, value in (("argv", ["--default"]), ("args", ["--pretty"]), ("shell", True)):
            with self.subTest(field=field):
                data = default_probe()
                data[field] = value
                with self.assertRaises(C4ScopedRunnerProbeError):
                    validate_probe(data)

    def test_timeout_is_required_and_bounded(self) -> None:
        data = default_probe()
        del data["timeout_seconds"]
        with self.assertRaises(C4ScopedRunnerProbeError):
            validate_probe(data)
        data = default_probe()
        data["timeout_seconds"] = 0
        with self.assertRaises(C4ScopedRunnerProbeError):
            validate_probe(data)

    def test_minimal_result_json_parses_and_has_required_fields(self) -> None:
        data = _result()
        required = {
            "schema_version",
            "generated_at",
            "project_key",
            "command_key",
            "capability_level",
            "command_class",
            "command_source",
            "config_command_override_allowed",
            "config_executable_override_allowed",
            "config_argv_args_override_allowed",
            "shell",
            "timeout_seconds",
            "output_truncation_present",
            "redaction_present",
            "before_repo_state",
            "after_repo_state",
            "target_repo_writeback",
            "cross_project_execution",
            "scheduler_or_autonomy",
            "credentials_required",
            "adapter_default_validation_executed",
            "adapters_validate_as_controlled_command",
            "c3_command_set",
            "c4_command_set",
            "c5_c6_locked",
            "exit_code",
            "captured_stdout_preview",
            "captured_stderr_preview",
            "known_warnings",
            "summary",
        }
        self.assertEqual(data["schema_version"], "c4_probe_minimal_result.v1")
        self.assertTrue(required.issubset(data))

    def test_minimal_result_records_exact_boundary(self) -> None:
        data = _result()
        self.assertEqual(data["command_key"], C4_COMMAND_KEY)
        self.assertEqual(data["capability_level"], C4_CAPABILITY_LEVEL)
        self.assertEqual(data["command_class"], C4_COMMAND_CLASS)
        self.assertEqual(data["command_source"], "hardcoded_allowlist")
        self.assertFalse(data["config_command_override_allowed"])
        self.assertFalse(data["config_executable_override_allowed"])
        self.assertFalse(data["config_argv_args_override_allowed"])
        self.assertFalse(data["shell"])
        self.assertTrue(data["output_truncation_present"])
        self.assertTrue(data["redaction_present"])
        self.assertEqual(data["c3_command_set"], [STATUS_SNAPSHOT_HELP_KEY, ADAPTERS_VALIDATE_HELP_KEY])
        self.assertEqual(data["c4_command_set"], [C4_COMMAND_KEY])
        self.assertTrue(data["c5_c6_locked"])

    def test_minimal_result_records_no_writeback_or_cross_project_execution(self) -> None:
        data = _result()
        self.assertFalse(data["target_repo_writeback"])
        self.assertFalse(data["cross_project_execution"])
        self.assertFalse(data["scheduler_or_autonomy"])
        self.assertFalse(data["credentials_required"])
        self.assertFalse(data["adapter_default_validation_executed"])
        self.assertFalse(data["adapters_validate_as_controlled_command"])
        self.assertIn("worktree", data["before_repo_state"])
        self.assertIn("worktree", data["after_repo_state"])

    def test_known_warnings_are_non_blocking(self) -> None:
        data = _result()
        warnings = data["known_warnings"]
        self.assertTrue(warnings["pseudo_git_tag_fixture_warning"]["present"])
        self.assertFalse(warnings["pseudo_git_tag_fixture_warning"]["blocking"])
        self.assertEqual(data["summary"]["result"], "warn")
        self.assertEqual(data["summary"]["done"], 18)
        self.assertEqual(data["summary"]["total"], 18)
        self.assertEqual(data["summary"]["unknown"], 0)
        self.assertEqual(data["summary"]["missing"], 0)

    def test_no_generalized_runner_module_or_shell_true_is_introduced(self) -> None:
        self.assertFalse((SOURCE_ROOT / "runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "controlled_runner.py").exists())
        self.assertFalse((SOURCE_ROOT / "command_registry.py").exists())
        source = C4_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("shell" + "=True", source)
        self.assertNotIn("Background" + "Scheduler", source)
        self.assertNotIn("schedule" + ".every(", source)
        self.assertNotIn("target" + "_repo_writeback = True", source)

    def test_doc_records_required_minimal_c4_boundaries(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        normalized = " ".join(doc.split())
        for phrase in (
            "minimal C4 probe",
            "`validation_pack_default_pretty`",
            "not a generalized runner",
            "C3 command keys remain exactly",
            "configuration cannot supply command text",
            "Adapter validation remains outside",
            "Target repository writeback remains forbidden",
            "C5 and C6 remain locked",
            "common-foundation-c4-probe-minimal-implementation-review-v1",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)

    def test_artifacts_do_not_use_raw_host_paths_or_prompt_text(self) -> None:
        payload = "\n".join(
            [
                IMPLEMENTATION.read_text(encoding="utf-8"),
                RESULT.read_text(encoding="utf-8"),
                DOC.read_text(encoding="utf-8"),
                PROJECT_CONTEXT.read_text(encoding="utf-8"),
            ]
        )
        for token in ("C:" + r"\Users\\", "C:" + "/Users/"):
            self.assertNotIn(token, payload)
        for marker in (
            "[" + "PASTE TARGET:",
            "Goal " + "Stack:",
            "Allowed " + "scope:",
            "BEGIN" + "_COPY_BLOCK" + "_FOR_CHATGPT",
            "next-" + "Agent Prompt",
        ):
            self.assertNotIn(marker, payload)


def _result() -> dict[str, object]:
    return json.loads(RESULT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
