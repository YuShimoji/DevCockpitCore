from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from dev_cockpit.current_observation import AUTHORIZATION_SCOPE
from dev_cockpit.report_authority import (
    AUTHENTIC_AUTHORITY_BASIS,
    AUTHENTIC_EVIDENCE_CLASS,
    H2_PERMISSION_SCOPE,
    H3_CURRENT_PERMISSION_SCOPE,
)
from tests.test_dashboard import _write_fixture_tree
from tests.test_report_authority_v2 import SOURCE_TEMPLATE


ROOT = Path(__file__).resolve().parents[1]
ENVELOPE_ARTIFACT_ID = "h3-current-observation-ingress-v1"
OBSERVATION_ARTIFACT_ID = "controlled-current-observation-v1"


class CurrentObservationIngressCliTests(unittest.TestCase):
    def test_controlled_temporary_git_public_cli_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, target, manifest, report_time = self._inputs(Path(temporary))
            observation = root / "controlled" / "current-observation.json"
            packet = root / "controlled" / "packet.json"
            packet_markdown = root / "controlled" / "packet.md"
            envelope = root / "controlled" / "authority-v2.json"
            dashboard = root / "controlled" / "dashboard.html"
            actions_json = root / "controlled" / "actions.json"
            actions_md = root / "controlled" / "actions.md"
            readback = root / "controlled" / "readback.json"

            self._run(
                "dev_cockpit.current_observation",
                "--repository",
                str(target),
                "--project-key",
                "nlmytgen",
                "--artifact-id",
                OBSERVATION_ARTIFACT_ID,
                "--authorization-scope",
                AUTHORIZATION_SCOPE,
                "--output",
                str(observation),
                "--pretty",
                cwd=root,
            )
            receipt = json.loads(observation.read_text(encoding="utf-8"))
            assessed_at = (
                datetime.fromisoformat(
                    receipt["observation"]["reobserved_at"].replace("Z", "+00:00")
                )
                + timedelta(seconds=1)
            ).isoformat()
            manifest_value = json.loads(manifest.read_text(encoding="utf-8"))
            manifest_value["generated_at"] = assessed_at
            manifest.write_text(
                json.dumps(manifest_value, indent=2) + "\n", encoding="utf-8"
            )
            self.assertLessEqual(
                report_time,
                datetime.fromisoformat(receipt["observation"]["first_observed_at"]),
            )

            self._run(
                "dev_cockpit.supervision_packet",
                "--repo-root",
                str(root),
                "--manifest",
                str(manifest),
                "--output-json",
                str(packet),
                "--output-markdown",
                str(packet_markdown),
                "--generated-at",
                assessed_at,
                "--pretty",
                cwd=root,
            )
            self._run(
                "dev_cockpit.report_authority",
                "--repo-root",
                str(root),
                "--envelope-version",
                "v2",
                "--mode",
                "current-observation-bound",
                "--manifest",
                str(manifest),
                "--packet",
                str(packet),
                "--current-observation",
                str(observation),
                "--current-observation-artifact-id",
                OBSERVATION_ARTIFACT_ID,
                "--artifact-id",
                ENVELOPE_ARTIFACT_ID,
                "--assessed-at",
                assessed_at,
                "--output",
                str(envelope),
                "--pretty",
                cwd=root,
            )
            self._run(
                "dev_cockpit.dashboard",
                "--repo-root",
                str(root),
                "--supervision-packet",
                str(packet),
                "--supervision-manifest",
                str(manifest),
                "--supervision-authority-envelope",
                str(envelope),
                "--supervision-authority-assessed-at",
                assessed_at,
                "--supervision-current-observation",
                str(observation),
                "--supervision-authority-artifact-id",
                ENVELOPE_ARTIFACT_ID,
                "--supervision-current-observation-artifact-id",
                OBSERVATION_ARTIFACT_ID,
                "--generated-at",
                assessed_at,
                "--output",
                str(dashboard),
                "--review-actions-json",
                str(actions_json),
                "--review-actions-md",
                str(actions_md),
                "--priority-readback",
                str(readback),
                "--skip-freshness-hash-verification",
                cwd=root,
            )

            result = json.loads(readback.read_text(encoding="utf-8"))
            projected = result["supervision_report_authority_envelope"]
            self.assertTrue(projected["authority"]["current_claim_eligibility"])
            self.assertFalse(projected["authority"]["live_coverage"])
            self.assertFalse(projected["scope_boundary"]["executable"])
            self.assertFalse(result["surface"]["executable"])
            self.assertEqual(
                "verified",
                projected["provenance"]["overall_current_claim_provenance_state"],
            )
            self.assertTrue(dashboard.exists())

    def test_v2_cli_rejects_missing_observation_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, _, manifest, _ = self._inputs(Path(temporary))
            result = self._run(
                "dev_cockpit.report_authority",
                "--repo-root",
                str(root),
                "--envelope-version",
                "v2",
                "--mode",
                "current-observation-bound",
                "--manifest",
                str(manifest),
                "--packet",
                str(root / "missing-packet.json"),
                "--artifact-id",
                ENVELOPE_ARTIFACT_ID,
                "--assessed-at",
                datetime.now(timezone.utc).isoformat(),
                "--output",
                str(root / "authority.json"),
                cwd=root,
                expected=2,
            )
            self.assertIn("requires --current-observation", result.stderr)

    @staticmethod
    def _run(
        module: str,
        *args: str,
        cwd: Path,
        expected: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            (sys.executable, "-m", module, *args),
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
        )
        if result.returncode != expected:
            raise AssertionError(
                f"{module} returned {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            )
        return result

    @staticmethod
    def _inputs(temporary: Path) -> tuple[Path, Path, Path, datetime]:
        root = temporary / "controller"
        target = temporary / "target"
        root.mkdir()
        target.mkdir()
        _write_fixture_tree(root)
        for command in (
            ("git", "init", "-q"),
            ("git", "config", "user.name", "Controlled Test"),
            ("git", "config", "user.email", "controlled@example.invalid"),
            (
                "git",
                "remote",
                "add",
                "origin",
                "https://github.com/YuShimoji/NLMYTGen.git",
            ),
        ):
            subprocess.run(command, cwd=target, check=True, capture_output=True)
        (target / "tracked.txt").write_text("controlled\n", encoding="utf-8")
        subprocess.run(("git", "add", "tracked.txt"), cwd=target, check=True)
        subprocess.run(
            ("git", "commit", "-q", "-m", "controlled fixture"),
            cwd=target,
            check=True,
        )
        revision = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=target,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        report_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        report_rel = Path("controlled") / "AGENT_REPORT.md"
        report = root / report_rel
        report.parent.mkdir()
        text = SOURCE_TEMPLATE.read_text(encoding="utf-8")
        text = text.replace(
            "d38075b97efabc99d1a23e8e0afafd5d44f1e2de", revision
        )
        text = text.replace(
            "2026-07-19T12:11:51.1904148+09:00", report_time.isoformat()
        )
        text = text.replace(H2_PERMISSION_SCOPE, H3_CURRENT_PERMISSION_SCOPE)
        report.write_text(text, encoding="utf-8", newline="\n")
        canonical = report.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
        manifest_value = {
            "schema_version": "task_report_manifest.v1",
            "artifact_id": "controlled-manifest-v1",
            "generated_at": report_time.isoformat(),
            "reports": [
                {
                    "project_key": "nlmytgen",
                    "report_path": report_rel.as_posix(),
                    "required": True,
                    "evidence_class": AUTHENTIC_EVIDENCE_CLASS,
                    "authority_basis": AUTHENTIC_AUTHORITY_BASIS,
                    "content_sha256": sha256(canonical).hexdigest(),
                }
            ],
        }
        manifest = root / "controlled" / "manifest.json"
        manifest.write_text(json.dumps(manifest_value, indent=2) + "\n", encoding="utf-8")
        return root, target, manifest, report_time


if __name__ == "__main__":
    unittest.main()
