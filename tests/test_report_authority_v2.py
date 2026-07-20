from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest

from dev_cockpit.current_observation import (
    AUTHORIZATION_SCOPE,
    observe_repository,
    write_current_observation,
)
from dev_cockpit.dashboard import DashboardError, build_dashboard_model, priority_readback
from dev_cockpit.report_authority import (
    AUTHENTIC_AUTHORITY_BASIS,
    AUTHENTIC_EVIDENCE_CLASS,
    H2_PERMISSION_SCOPE,
    H3_CURRENT_PERMISSION_SCOPE,
    DEFAULT_ARTIFACT_ID,
    AuthorityEnvelopeError,
)
from dev_cockpit.report_authority_v2 import (
    AUTHORITY_KEYS,
    BINDINGS_KEYS,
    OBSERVATION_KEYS,
    PROVENANCE_KEYS,
    REPORT_KEYS,
    ROOT_KEYS,
    SCHEMA_VERSION,
    build_authority_envelope_v2,
    dumps_authority_envelope_v2,
    evaluate_authority_conditions_v2,
    load_authority_envelope_v2,
    validate_authority_envelope_v2,
)
from dev_cockpit.supervision_packet import build_supervision_packet, dumps_packet
from tests.test_dashboard import _write_fixture_tree


ROOT = Path(__file__).resolve().parents[1]
SOURCE_TEMPLATE = (
    ROOT
    / "artifacts"
    / "review"
    / "h2-authentic-single-report-round-trip-v1"
    / "source"
    / "AGENT_REPORT_H2_SOURCE_V1.md"
)
ASSESSED_AT = "2026-07-20T01:02:00+00:00"
ENVELOPE_ARTIFACT_ID = "h3-current-observation-ingress-v1"
OBSERVATION_ARTIFACT_ID = "controlled-current-observation-v1"


class ReportAuthorityV2Tests(unittest.TestCase):
    def test_tracked_h3_1_package_is_deterministic_and_denies_real_promotion(self) -> None:
        package = ROOT / "artifacts" / "review" / "h3-current-observation-ingress-v1"
        generate = runpy.run_path(str(package / "generate_package.py"))["generate"]
        generate()
        first = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in package.glob("*.json")
        }
        generate()
        second = {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in package.glob("*.json")
        }
        readback = json.loads(
            (package / "current_observation_ingress_machine_readback_v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(first, second)
        self.assertTrue(readback["canonical_state"]["h3_1_ingress_operational"])
        self.assertFalse(
            readback["canonical_state"]["real_current_observation_attempted"]
        )
        self.assertFalse(readback["canonical_state"]["real_current_claim_eligibility"])
        self.assertFalse(readback["canonical_state"]["live_coverage"])
        self.assertFalse(readback["canonical_state"]["executable"])
        self.assertFalse(readback["canonical_state"]["h4_started"])

    def test_dashboard_rejects_every_partial_v2_input_set(self) -> None:
        complete = {
            "supervision_packet_path": "packet.json",
            "supervision_manifest_path": "manifest.json",
            "supervision_authority_envelope_path": "authority.json",
            "supervision_authority_assessed_at": ASSESSED_AT,
            "supervision_current_observation_path": "observation.json",
            "supervision_authority_artifact_id": ENVELOPE_ARTIFACT_ID,
            "supervision_current_observation_artifact_id": OBSERVATION_ARTIFACT_ID,
        }
        for missing in (
            "supervision_current_observation_path",
            "supervision_authority_artifact_id",
            "supervision_current_observation_artifact_id",
        ):
            with self.subTest(missing=missing), self.assertRaisesRegex(
                DashboardError, "current observation requires"
            ):
                values = dict(complete)
                values.pop(missing)
                build_dashboard_model(repo_root=ROOT, **values)

    def test_dashboard_v2_ingress_projects_current_but_never_live_or_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            _write_fixture_tree(fixture["root"])
            envelope = self._build(fixture)
            envelope_path = fixture["root"] / "authority-v2.json"
            envelope_path.write_text(
                dumps_authority_envelope_v2(envelope, pretty=True), encoding="utf-8"
            )
            model = build_dashboard_model(
                repo_root=fixture["root"],
                supervision_packet_path=fixture["packet"],
                supervision_manifest_path=fixture["manifest"],
                supervision_authority_envelope_path=envelope_path,
                supervision_authority_assessed_at=ASSESSED_AT,
                supervision_current_observation_path=fixture["observation"],
                supervision_authority_artifact_id=ENVELOPE_ARTIFACT_ID,
                supervision_current_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
                generated_at=ASSESSED_AT,
            )
            readback = priority_readback(model)

        evidence = model["priority_items"][0]["evidence_refs"][0]
        projected = readback["supervision_report_authority_envelope"]
        self.assertTrue(evidence["current_state_claim_eligible"])
        self.assertFalse(evidence["live_coverage"])
        self.assertFalse(model["priority_items"][0]["executable"])
        self.assertEqual("verified", evidence["provenance_authenticity_state"])
        self.assertEqual("satisfied", evidence["permission_state"])
        self.assertEqual("verified", projected["provenance"]["overall_current_claim_provenance_state"])
        self.assertTrue(projected["authority"]["current_claim_eligibility"])
        self.assertFalse(projected["authority"]["live_coverage"])
        self.assertFalse(projected["scope_boundary"]["executable"])

    def test_complete_sources_build_reload_and_preserve_non_live_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            envelope = self._build(fixture)
            envelope_path = fixture["root"] / "authority-v2.json"
            envelope_path.write_text(
                dumps_authority_envelope_v2(envelope, pretty=True), encoding="utf-8"
            )

            reloaded = load_authority_envelope_v2(
                envelope_path,
                manifest_path=fixture["manifest"],
                packet_path=fixture["packet"],
                current_observation_path=fixture["observation"],
                repo_root=fixture["root"],
                assessed_at=ASSESSED_AT,
                expected_artifact_id=ENVELOPE_ARTIFACT_ID,
                expected_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
            )

            self.assertEqual(SCHEMA_VERSION, reloaded["schema_version"])
            self.assertTrue(reloaded["authority"]["current_claim_eligibility"])
            self.assertFalse(reloaded["authority"]["live_coverage"])
            self.assertFalse(reloaded["scope_boundary"]["executable"])
            self.assertEqual("satisfied", reloaded["authority"]["permission_conjunction_state"])
            self.assertEqual("valid", reloaded["authority"]["chronology_state"])
            self.assertEqual(
                "verified",
                reloaded["provenance"]["overall_current_claim_provenance_state"],
            )

    def test_v2_exact_key_surfaces_include_observation_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            envelope = self._build(self._fixture(Path(temporary)))
            self.assertEqual(ROOT_KEYS, set(envelope))
            self.assertEqual(BINDINGS_KEYS, set(envelope["bindings"]))
            self.assertEqual(REPORT_KEYS, set(envelope["report"]))
            self.assertEqual(OBSERVATION_KEYS, set(envelope["observation"]))
            self.assertEqual(AUTHORITY_KEYS, set(envelope["authority"]))
            self.assertEqual(PROVENANCE_KEYS, set(envelope["provenance"]))

    def test_dual_authorization_requires_both_exact_scopes(self) -> None:
        cases = {
            "report_missing": ({"report_permission_scope": None}, "report_permission_missing"),
            "report_h2": ({"report_permission_scope": H2_PERMISSION_SCOPE}, "report_permission_scope_h2_only"),
            "report_insufficient": ({"report_permission_scope": "allowed_for_DevCockpitCore_other"}, "report_permission_insufficient_for_h3_current_claim"),
            "report_mismatch": ({"report_permission_scope": "allowed_elsewhere"}, "report_permission_mismatched"),
            "observation_missing": ({"observation_authorization_scope": None}, "observation_authorization_missing"),
            "observation_h2": ({"observation_authorization_scope": H2_PERMISSION_SCOPE}, "observation_authorization_scope_h2_only"),
            "observation_insufficient": ({"observation_authorization_scope": "allowed_for_DevCockpitCore_other"}, "observation_authorization_insufficient_for_h3_current_claim"),
            "observation_mismatch": ({"observation_authorization_scope": "allowed_elsewhere"}, "observation_authorization_mismatched"),
        }
        for name, (changes, reason) in cases.items():
            with self.subTest(name=name):
                conditions = self._positive_conditions()
                conditions.update(changes)
                result = evaluate_authority_conditions_v2(**conditions)
                self.assertFalse(result["current_claim_eligibility"])
                self.assertIn(reason, result["reason_codes"])
                self.assertEqual("unsatisfied", result["permission_conjunction_state"])

    def test_current_claim_predicate_negative_matrix(self) -> None:
        cases = {
            "source_revision_missing": (
                {"source_revision": None},
                "source_revision_missing",
            ),
            "observed_revision_missing": (
                {"observed_revision": None},
                "observed_revision_missing",
            ),
            "abbreviated_revision": (
                {"observed_revision": "a" * 12},
                "revision_abbreviation_unresolved",
            ),
            "revision_mismatch": (
                {"observed_revision": "b" * 40},
                "revision_mismatch",
            ),
            "not_actual": (
                {"observation_actual": False},
                "actual_current_observation_absent",
            ),
            "dirty": ({"observation_clean": False}, "worktree_not_clean"),
            "unstable": (
                {"observation_stable": False},
                "observation_not_stable",
            ),
            "package_binding": (
                {"package_binding_verified": False},
                "source_manifest_packet_binding_invalid",
            ),
            "receipt_provenance": (
                {"observation_receipt_verified": False},
                "current_observation_receipt_invalid",
            ),
            "cross_binding": (
                {"cross_binding_verified": False},
                "repository_project_revision_cross_binding_invalid",
            ),
            "observer_scope": (
                {"observer_only": False},
                "observer_scope_boundary_invalid",
            ),
            "executable_scope": (
                {"non_executable": False},
                "observer_scope_boundary_invalid",
            ),
        }
        for name, (changes, reason) in cases.items():
            with self.subTest(name=name):
                conditions = self._positive_conditions()
                conditions.update(changes)
                result = evaluate_authority_conditions_v2(**conditions)
                self.assertFalse(result["current_claim_eligibility"])
                self.assertFalse(result["live_coverage"])
                self.assertIn(reason, result["reason_codes"])

    def test_chronology_and_temporal_failures_are_distinguished(self) -> None:
        cases = {
            "before_report": (
                {"reobserved_at": "2026-07-20T00:59:00+00:00"},
                "reobservation_before_report",
                "reobservation_precedes_report",
            ),
            "after_assessment": (
                {"reobserved_at": "2026-07-20T01:03:00+00:00"},
                "reobservation_after_assessment",
                "reobservation_follows_assessment",
            ),
            "report_future": (
                {"report_observed_at": "2026-07-20T01:03:00+00:00"},
                "report_after_assessment",
                "report_follows_assessment",
            ),
            "report_stale": (
                {"report_observed_at": "2026-07-18T01:00:00+00:00"},
                "valid",
                "report_timestamp_threshold_exceeded",
            ),
            "timezone_missing": (
                {"reobserved_at": "2026-07-20T01:01:00"},
                "invalid_reobservation_timestamp",
                "reobservation_timestamp_timezone_missing",
            ),
            "malformed": (
                {"report_observed_at": "not-a-time"},
                "invalid_report_timestamp",
                "report_timestamp_malformed",
            ),
        }
        for name, (changes, state, reason) in cases.items():
            with self.subTest(name=name):
                conditions = self._positive_conditions()
                conditions.update(changes)
                result = evaluate_authority_conditions_v2(**conditions)
                self.assertFalse(result["current_claim_eligibility"])
                self.assertEqual(state, result["chronology_state"])
                self.assertIn(reason, result["reason_codes"])

    def test_current_observation_cross_binding_mismatch_is_separate_provenance(self) -> None:
        cases = {
            "project": ("project_key", "another-project"),
            "repository": ("repository.identity", "https://example.invalid/other.git"),
        }
        for name, (field, value) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                fixture = self._fixture(Path(temporary))
                receipt = json.loads(fixture["observation"].read_text(encoding="utf-8"))
                if field == "project_key":
                    receipt[field] = value
                else:
                    receipt["repository"]["identity"] = value
                    receipt["repository"]["identity_sha256"] = sha256(value.encode()).hexdigest()
                fixture["observation"].write_text(
                    json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
                )
                envelope = self._build(fixture)
                self.assertFalse(envelope["authority"]["current_claim_eligibility"])
                self.assertEqual(
                    "unverified",
                    envelope["provenance"][
                        "repository_project_revision_cross_binding_state"
                    ],
                )

    def test_artifact_ids_are_explicit_and_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            envelope = self._build(fixture)
            with self.assertRaisesRegex(AuthorityEnvelopeError, "artifact_id"):
                validate_authority_envelope_v2(
                    envelope,
                    expected_artifact_id="wrong-envelope-id",
                    expected_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
                )
            with self.assertRaisesRegex(AuthorityEnvelopeError, "artifact_id"):
                validate_authority_envelope_v2(
                    envelope,
                    expected_artifact_id=ENVELOPE_ARTIFACT_ID,
                    expected_observation_artifact_id="wrong-observation-id",
                )
            with self.assertRaisesRegex(AuthorityEnvelopeError, "V1 package identity"):
                build_authority_envelope_v2(
                    manifest_path=fixture["manifest"],
                    packet_path=fixture["packet"],
                    current_observation_path=fixture["observation"],
                    repo_root=fixture["root"],
                    assessed_at=ASSESSED_AT,
                    artifact_id=DEFAULT_ARTIFACT_ID,
                    expected_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
                )

    def test_loader_reprojects_receipt_package_and_serialized_claims(self) -> None:
        mutations = {
            "eligibility": lambda item: item["authority"].__setitem__("current_claim_eligibility", False),
            "provenance": lambda item: item["provenance"].__setitem__("overall_current_claim_provenance_state", "unverified"),
            "observation": lambda item: item["observation"].__setitem__("clean", False),
            "binding": lambda item: item["bindings"]["current_observation"].__setitem__("content_sha256", "a" * 64),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                fixture = self._fixture(Path(temporary))
                envelope = self._build(fixture)
                mutate(envelope)
                path = fixture["root"] / "authority-v2.json"
                path.write_text(
                    dumps_authority_envelope_v2(envelope, pretty=True), encoding="utf-8"
                )
                with self.assertRaisesRegex(
                    AuthorityEnvelopeError, "mismatch at|conflicts with components"
                ):
                    load_authority_envelope_v2(
                        path,
                        manifest_path=fixture["manifest"],
                        packet_path=fixture["packet"],
                        current_observation_path=fixture["observation"],
                        repo_root=fixture["root"],
                        assessed_at=ASSESSED_AT,
                        expected_artifact_id=ENVELOPE_ARTIFACT_ID,
                        expected_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
                    )

    def test_v2_duplicate_unknown_and_wrong_types_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._fixture(Path(temporary))
            envelope = self._build(fixture)
            path = fixture["root"] / "authority-v2.json"
            path.write_text(
                dumps_authority_envelope_v2(envelope).replace(
                    '"live_coverage":false',
                    '"live_coverage":false,"live_coverage":false',
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                AuthorityEnvelopeError,
                r"duplicate JSON key at \$\.authority\.live_coverage",
            ):
                load_authority_envelope_v2(
                    path,
                    manifest_path=fixture["manifest"],
                    packet_path=fixture["packet"],
                    current_observation_path=fixture["observation"],
                    repo_root=fixture["root"],
                    assessed_at=ASSESSED_AT,
                    expected_artifact_id=ENVELOPE_ARTIFACT_ID,
                    expected_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
                )

            mutations = {
                "unknown": lambda item: item.__setitem__("unexpected", False),
                "missing": lambda item: item["provenance"].pop(
                    "package_binding_state"
                ),
                "wrong_type": lambda item: item["authority"].__setitem__(
                    "current_claim_eligibility", 1
                ),
                "scope": lambda item: item["scope_boundary"].__setitem__(
                    "executable", True
                ),
            }
            for name, mutate in mutations.items():
                with self.subTest(name=name):
                    changed = copy.deepcopy(envelope)
                    mutate(changed)
                    with self.assertRaises(AuthorityEnvelopeError):
                        validate_authority_envelope_v2(
                            changed,
                            expected_artifact_id=ENVELOPE_ARTIFACT_ID,
                            expected_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
                        )

    def _build(self, fixture: dict[str, Path]) -> dict[str, object]:
        return build_authority_envelope_v2(
            manifest_path=fixture["manifest"],
            packet_path=fixture["packet"],
            current_observation_path=fixture["observation"],
            repo_root=fixture["root"],
            assessed_at=ASSESSED_AT,
            artifact_id=ENVELOPE_ARTIFACT_ID,
            expected_observation_artifact_id=OBSERVATION_ARTIFACT_ID,
        )

    @staticmethod
    def _positive_conditions() -> dict[str, object]:
        return {
            "report_observed_at": "2026-07-20T01:00:00+00:00",
            "reobserved_at": "2026-07-20T01:01:00+00:00",
            "assessed_at": ASSESSED_AT,
            "threshold_seconds": 86400,
            "source_revision": "a" * 40,
            "observed_revision": "a" * 40,
            "report_permission_scope": H3_CURRENT_PERMISSION_SCOPE,
            "observation_authorization_scope": AUTHORIZATION_SCOPE,
            "observation_actual": True,
            "observation_clean": True,
            "observation_stable": True,
            "package_binding_verified": True,
            "observation_receipt_verified": True,
            "cross_binding_verified": True,
            "observer_only": True,
            "non_executable": True,
            "evidence_class": AUTHENTIC_EVIDENCE_CLASS,
            "authority_basis": AUTHENTIC_AUTHORITY_BASIS,
        }

    @staticmethod
    def _fixture(temporary: Path) -> dict[str, Path]:
        root = temporary / "controller"
        target = temporary / "target"
        root.mkdir()
        target.mkdir()
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

        report_rel = Path("input") / "AGENT_REPORT.md"
        report = root / report_rel
        report.parent.mkdir()
        text = SOURCE_TEMPLATE.read_text(encoding="utf-8")
        text = text.replace(
            "d38075b97efabc99d1a23e8e0afafd5d44f1e2de", revision
        )
        text = text.replace(
            "2026-07-19T12:11:51.1904148+09:00",
            "2026-07-20T01:00:00+00:00",
        )
        text = text.replace(H2_PERMISSION_SCOPE, H3_CURRENT_PERMISSION_SCOPE)
        report.write_text(text, encoding="utf-8", newline="\n")
        canonical = report.read_text(encoding="utf-8").replace("\r\n", "\n").encode()
        manifest_value = {
            "schema_version": "task_report_manifest.v1",
            "artifact_id": "controlled-manifest-v1",
            "generated_at": ASSESSED_AT,
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
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps(manifest_value, indent=2) + "\n", encoding="utf-8")
        packet_value = build_supervision_packet(
            manifest_value,
            repo_root=root,
            manifest_path=manifest,
            generated_at=ASSESSED_AT,
        )
        packet = root / "packet.json"
        packet.write_text(dumps_packet(packet_value, pretty=True), encoding="utf-8")

        observation = root / "current-observation.json"
        start = datetime(2026, 7, 20, 1, 1, tzinfo=timezone.utc)
        times = iter((start, start + timedelta(seconds=1)))
        receipt = observe_repository(
            repository=target,
            project_key="nlmytgen",
            artifact_id=OBSERVATION_ARTIFACT_ID,
            authorization_scope=AUTHORIZATION_SCOPE,
            output_path=observation,
            clock=lambda: next(times),
        )
        write_current_observation(receipt, observation, pretty=True)
        return {
            "root": root,
            "target": target,
            "report": report,
            "manifest": manifest,
            "packet": packet,
            "observation": observation,
        }


if __name__ == "__main__":
    unittest.main()
