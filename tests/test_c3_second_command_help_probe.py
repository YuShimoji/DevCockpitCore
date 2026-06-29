from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.controlled_runner_probe import ALLOWED_COMMAND_KEYS, default_probe, validate_probe
from dev_cockpit.controlled_runner_probe_review import default_review, validate_review


PROBE = ROOT / "samples" / "c3_second_command_probe" / "c3_second_command_help_probe_v1.json"
DOC = ROOT / "docs" / "design" / "C3_SECOND_COMMAND_HELP_PROBE_V1.md"


class C3SecondCommandHelpProbeTests(unittest.TestCase):
    def test_probe_packet_parses(self) -> None:
        data = _probe()
        self.assertEqual(data["schema_version"], "c3_second_command_help_probe.v1")
        self.assertEqual(data["probe_status"], "bounded_help_readback")
        self.assertEqual(data["implementation_status"], "probe_artifact_only")

    def test_candidate_is_help_only_and_not_accepted_command_key(self) -> None:
        candidate = _probe()["candidate"]
        self.assertEqual(candidate["command_key"], "adapters_validate_help")
        self.assertEqual(candidate["fixed_argv_suffix"], ["-m", "dev_cockpit.adapters", "--help"])
        self.assertTrue(candidate["help_only"])
        self.assertFalse(candidate["accepted_command_key"])

    def test_readback_evidence_reports_no_adapter_validation_execution(self) -> None:
        evidence = _probe()["readback_evidence"]
        self.assertEqual(evidence["exit_code"], 0)
        self.assertFalse(evidence["adapter_validation_executed"])
        self.assertFalse(evidence["target_repo_required"])
        self.assertFalse(evidence["input_file_required"])
        self.assertFalse(evidence["output_file_written"])
        self.assertFalse(evidence["credentials_required"])
        self.assertFalse(evidence["network_required"])

    def test_adapters_help_command_is_fixed_help_surface(self) -> None:
        env = os.environ.copy()
        src = str(ROOT / "src")
        env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        completed = subprocess.run(
            [sys.executable, "-m", "dev_cockpit.adapters", "--help"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            shell=False,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Validate DevCockpitCore adapter manifests.", completed.stdout)
        self.assertIn("--validate ADAPTER [ADAPTER ...]", completed.stdout)
        self.assertEqual(completed.stderr, "")
        self.assertNotIn(": OK (", completed.stdout)
        self.assertNotIn(": ERROR:", completed.stdout)

    def test_help_probe_artifact_preserves_pre_production_boundary(self) -> None:
        boundary = _probe()["current_c3_boundary"]
        self.assertEqual(boundary["accepted_command_keys"], ["status_snapshot_help"])
        self.assertFalse(boundary["production_allowlist_expanded"])
        self.assertFalse(boundary["controlled_runner_probe_changed"])
        self.assertFalse(boundary["controlled_runner_review_changed"])
        self.assertEqual(validate_probe(default_probe())["command_key"], "status_snapshot_help")
        self.assertEqual(validate_review(default_review())["accepted_command_keys"], ["status_snapshot_help"])

    def test_successor_production_probe_adds_only_adapters_validate_help(self) -> None:
        self.assertEqual(ALLOWED_COMMAND_KEYS, ("status_snapshot_help", "adapters_validate_help"))

    def test_future_requirements_keep_c4_c5_c6_locked(self) -> None:
        requirements = _probe()["future_acceptance_requirements"]
        self.assertTrue(requirements["supervisor_prompt_required"])
        self.assertTrue(requirements["hardcoded_allowlist_mapping_required"])
        self.assertFalse(requirements["adapter_validation_execution_allowed"])
        self.assertFalse(requirements["adapter_default_validation_execution_allowed"])
        self.assertFalse(requirements["target_repo_writeback"])
        self.assertFalse(requirements["c4_unlocked"])
        self.assertFalse(requirements["c5_unlocked"])
        self.assertFalse(requirements["c6_unlocked"])

    def test_probe_artifacts_do_not_contain_paste_ready_prompt(self) -> None:
        payload = PROBE.read_text(encoding="utf-8") + "\n" + DOC.read_text(encoding="utf-8")
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)


def _probe() -> dict[str, object]:
    return json.loads(PROBE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
