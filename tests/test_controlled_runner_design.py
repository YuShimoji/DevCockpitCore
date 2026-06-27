from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.validation_pack import scan_raw_local_paths_text


DESIGN_PATH = ROOT / "samples" / "controlled_runner_design" / "controlled_runner_design_v1.json"
REVIEW_PATH = ROOT / "samples" / "controlled_runner_design" / "controlled_runner_readiness_review_v1.json"
CONTROLLED_DOC = ROOT / "docs" / "design" / "CONTROLLED_RUNNER_DESIGN_V1.md"
COPY_DOC = ROOT / "docs" / "design" / "COPY_TRANSPORT_RESIDUE_V1.md"


class ControlledRunnerDesignTests(unittest.TestCase):
    def test_design_json_parses(self) -> None:
        data = _design()
        self.assertEqual(data["schema_version"], "controlled_runner_design.v1")

    def test_required_top_level_keys_exist(self) -> None:
        data = _design()
        for key in (
            "schema_version",
            "identity",
            "capability_ladder",
            "command_classification",
            "authority_boundaries",
            "runner_preconditions_for_future_probe",
            "evidence_contract",
            "forbidden_now",
            "future_probe_candidate",
            "report_template_corrections",
        ):
            self.assertIn(key, data)

    def test_design_status_remains_design_only_and_locked(self) -> None:
        identity = _design()["identity"]
        self.assertEqual(identity["implementation_status"], "design_only")
        self.assertEqual(identity["execution_automation_readiness"], "locked")

    def test_capability_ladder_includes_c0_through_c6(self) -> None:
        ladder = _design()["capability_ladder"]
        self.assertEqual({item["capability"] for item in ladder}, {f"C{index}" for index in range(7)})

    def test_command_classes_include_risk_and_current_allowance(self) -> None:
        for item in _design()["command_classification"]:
            self.assertIn("risk", item)
            self.assertIn("allowed_in_current_slice", item)
            self.assertIn("future_unlock_gate", item)
            self.assertIn("required_owner", item)
            self.assertIn("stop_class_if_requested_now", item)

    def test_forbidden_now_covers_required_boundaries(self) -> None:
        forbidden = " ".join(_design()["forbidden_now"]).lower()
        for term in (
            "arbitrary command execution",
            "scheduler",
            "force push",
            "credentials",
            "target repo writeback",
        ):
            self.assertIn(term, forbidden)

    def test_future_probe_not_approved_by_this_slice(self) -> None:
        candidate = _design()["future_probe_candidate"]
        self.assertEqual(candidate["status"], "not_approved_by_this_slice")
        self.assertTrue(candidate["required_supervisor_decision"])
        self.assertTrue(candidate["implementation_must_wait_for_next_supervisor_prompt"])

    def test_evidence_contract_contains_before_and_after_state(self) -> None:
        evidence = _design()["evidence_contract"]
        self.assertIn("before_state", evidence)
        self.assertIn("after_state", evidence)

    def test_report_template_corrections_include_gate_separation(self) -> None:
        corrections = _design()["report_template_corrections"]
        self.assertTrue(corrections["current_slice_gates_and_next_slice_gates_must_not_be_conflated"])
        self.assertEqual(corrections["next_slice_gates_when_not_started"], "[--------] 0/8")
        self.assertEqual(corrections["completion_matrix_meter_example"], "[#] 1/1")

    def test_copy_transport_residue_is_distinguished(self) -> None:
        data = _design()
        boundary = data["authority_boundaries"]["copy_transport_residue_handling"].lower()
        self.assertIn("transport", boundary)
        self.assertIn("agent-authored", boundary)
        copy_doc = COPY_DOC.read_text(encoding="utf-8").lower()
        self.assertIn("ui copy-transport residue", copy_doc)
        self.assertIn("agent-authored report residue", copy_doc)

    def test_no_executable_runner_module_exists(self) -> None:
        forbidden_paths = [
            ROOT / "src" / "dev_cockpit" / "runner.py",
            ROOT / "src" / "dev_cockpit" / "controlled_runner.py",
        ]
        for path in forbidden_paths:
            self.assertFalse(path.exists(), path.as_posix())

    def test_source_tree_does_not_add_controlled_runner_implementation_files(self) -> None:
        source_files = {path.name for path in (ROOT / "src" / "dev_cockpit").glob("*.py")}
        self.assertNotIn("runner.py", source_files)
        self.assertNotIn("controlled_runner.py", source_files)

    def test_design_json_has_no_unredacted_local_user_paths(self) -> None:
        text = DESIGN_PATH.read_text(encoding="utf-8")
        matches = scan_raw_local_paths_text(text)
        self.assertEqual(matches["raw"], [])

    def test_design_json_has_no_paste_ready_prompt(self) -> None:
        payload = json.dumps(_design())
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)

    def test_review_json_parses_and_keeps_probe_unapproved(self) -> None:
        data = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "controlled_runner_readiness_review.v1")
        self.assertFalse(data["readiness"]["future_probe_approved"])
        self.assertEqual(data["readiness"]["execution_automation_readiness"], "locked")

    def test_docs_do_not_contain_subprocess_shell_true_literal(self) -> None:
        combined = CONTROLLED_DOC.read_text(encoding="utf-8") + "\n" + DESIGN_PATH.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"shell\s*=\s*True", combined))

    def test_docs_explain_design_only_boundary(self) -> None:
        text = CONTROLLED_DOC.read_text(encoding="utf-8")
        self.assertIn("design-only", text)
        self.assertIn("does not implement a runner", text)
        self.assertIn("subprocess shell option remains false", text)


def _design() -> dict[str, object]:
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
