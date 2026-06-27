from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.report_normalizer import normalize_report, redact_absolute_user_paths


SAMPLE_REPORT = """[ROUTE: DevCockpitCore | AGENT->SUPERVISOR | slice:common-foundation-adapter-manifest-v1 | turn:T+3 | target:ChatGPT Common Foundation supervisor thread | artifact_current:adapter-manifest-v1 | artifact_next:report-normalizer-v1 | reply:User/Supervisor | confidence:high]
[PROGRESS: FOUNDATION OBSERVER READINESS [########] 8/8 | current:adapter manifest v1 committed and pushed | next:report-normalizer-v1 | blocker:none | user_work:none]
[ACTION: decision=completed | now_owner:Supervisor | deliverable:adapter-manifest-v1 | trigger:none]
[STATUS: health=green | gates=8/8 | stop_class=NONE | estimate_agent:none | estimate_user:none]

**Outcome**
Completed adapter manifest v1 and pushed commit f5aa1c2 feat: define adapter manifest v1.

**What Changed**
Adapters now validate as adapter_manifest.v1.

**Commands And Results**
- Ran 10 tests.
- Final repo state was clean.
- Final parity check returned 0 0.

**Completion Matrix**
Slice Completion 8/8.

**Continuation State**
Next artifact is report-normalizer-v1.

**Handoff Gate**
pass; no blocked handoff required.

::git-stage{cwd="C:\\Users\\<redacted>\\DevCockpitCore"}
::git-commit{cwd="C:\\Users\\<redacted>\\DevCockpitCore"}
::git-push{cwd="C:\\Users\\<redacted>\\DevCockpitCore" branch="main"}
"""


class ReportNormalizerTests(unittest.TestCase):
    def test_route_progress_action_status_parse(self) -> None:
        result = normalize_report(SAMPLE_REPORT, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["schema_version"], "report_normalization.v1")
        self.assertEqual(result["routing"]["route"], "DevCockpitCore")
        self.assertEqual(result["routing"]["direction"], "AGENT->SUPERVISOR")
        self.assertEqual(result["routing"]["slice"], "common-foundation-adapter-manifest-v1")
        self.assertEqual(result["progress"]["done"], 8)
        self.assertEqual(result["progress"]["total"], 8)
        self.assertEqual(result["action"]["decision"], "completed")
        self.assertEqual(result["status"]["gates_done"], 8)
        self.assertEqual(result["status"]["gates_total"], 8)

    def test_partial_report_does_not_crash(self) -> None:
        result = normalize_report("**Outcome**\nPartial report only.\n", generated_at="2026-01-01T00:00:00Z")
        self.assertIsNone(result["routing"]["route"])
        self.assertEqual(result["sections"]["outcome"], "Partial report only.")
        self.assertEqual(result["health"]["normalization_status"], "yellow")

    def test_markdown_sections_and_commit_reference(self) -> None:
        result = normalize_report(SAMPLE_REPORT, generated_at="2026-01-01T00:00:00Z")
        self.assertEqual(result["sections"]["outcome"].splitlines()[0], "Completed adapter manifest v1 and pushed commit f5aa1c2 feat: define adapter manifest v1.")
        self.assertIn("Ran 10 tests.", result["sections"]["commands_and_results"])
        self.assertEqual(
            result["normalized_outcome"]["commits"],
            [{"sha": "f5aa1c2", "message": "feat: define adapter manifest v1"}],
        )
        self.assertTrue(result["normalized_outcome"]["pushed"])
        self.assertEqual(result["normalized_outcome"]["worktree"], "clean")
        self.assertEqual(result["normalized_outcome"]["remote_parity"], "0 0")
        self.assertEqual(result["normalized_outcome"]["tests"], [{"count": 10}])

    def test_handoff_false_pass_extraction(self) -> None:
        result = normalize_report(SAMPLE_REPORT, generated_at="2026-01-01T00:00:00Z")
        self.assertFalse(result["handoff"]["handoff_gate"])
        self.assertFalse(result["handoff"]["supervisor_should_generate_prompt"])

    def test_pseudo_git_tag_residue_detection(self) -> None:
        result = normalize_report(SAMPLE_REPORT, generated_at="2026-01-01T00:00:00Z")
        self.assertTrue(result["residue_audit"]["contains_pseudo_git_tags"])
        self.assertEqual(
            result["residue_audit"]["pseudo_git_tags"],
            ["::git-commit", "::git-push", "::git-stage"],
        )

    def test_paste_ready_prompt_residue_detection_without_prompt_output(self) -> None:
        prompt_text = """[PASTE TARGET: Codex/Example]
[CONTRACT: v2.1 | output_type=SUPERVISOR_PROMPT]
Goal Stack:
Allowed scope:
Report format:
"""
        result = normalize_report(prompt_text, generated_at="2026-01-01T00:00:00Z")
        payload = json.dumps(result)
        self.assertTrue(result["residue_audit"]["contains_paste_ready_prompt"])
        self.assertNotIn("[PASTE TARGET:", payload)
        self.assertNotIn("Goal Stack:", payload)
        self.assertNotIn("Allowed scope:", payload)

    def test_local_absolute_path_detection_and_redaction(self) -> None:
        text = "**Outcome**\nOpened C:\\Users\\example\\DevCockpitCore\\README.md.\n"
        self.assertEqual(
            redact_absolute_user_paths(text),
            "**Outcome**\nOpened C:\\Users\\<redacted>\\DevCockpitCore\\README.md.\n",
        )
        result = normalize_report(text, generated_at="2026-01-01T00:00:00Z")
        self.assertTrue(result["residue_audit"]["contains_absolute_user_paths"])
        self.assertFalse(result["residue_audit"]["absolute_user_paths_redacted"])
        self.assertIn("C:\\Users\\<redacted>\\DevCockpitCore", result["sections"]["outcome"])
        self.assertNotIn("example", json.dumps(result))

    def test_required_top_level_keys(self) -> None:
        result = normalize_report(SAMPLE_REPORT, input_path="sample.txt", generated_at="2026-01-01T00:00:00Z")
        for key in (
            "schema_version",
            "generated_at",
            "producer",
            "source",
            "routing",
            "progress",
            "action",
            "status",
            "sections",
            "normalized_outcome",
            "handoff",
            "next",
            "residue_audit",
            "health",
        ):
            self.assertIn(key, result)

    def test_sample_input_normalizes_to_json(self) -> None:
        sample = ROOT / "samples" / "reports" / "agent_report_adapter_manifest_v1_redacted.txt"
        if not sample.exists():
            self.skipTest("sample report has not been added")
        result = normalize_report(sample.read_text(encoding="utf-8"), input_path=sample.as_posix(), generated_at="2026-01-01T00:00:00Z")
        payload = json.dumps(result)
        self.assertEqual(json.loads(payload)["schema_version"], "report_normalization.v1")
        self.assertFalse(result["residue_audit"]["contains_paste_ready_prompt"])


if __name__ == "__main__":
    unittest.main()
