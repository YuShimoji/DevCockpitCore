from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest

from dev_cockpit.report_authority import (
    AUTHENTIC_AUTHORITY_BASIS,
    AUTHENTIC_EVIDENCE_CLASS,
    AUTHORITY_KEYS,
    BINDING_KEYS,
    BINDINGS_KEYS,
    H2_PERMISSION_SCOPE,
    H3_CURRENT_PERMISSION_SCOPE,
    IDENTITY_KEYS,
    OBSERVATION_KEYS,
    REPORT_KEYS,
    ROOT_KEYS,
    SCOPE_KEYS,
    AuthorityEnvelopeError,
    build_authority_envelope,
    dumps_authority_envelope,
    evaluate_authority_conditions,
    load_authority_envelope,
    validate_authority_envelope,
)


ROOT = Path(__file__).resolve().parents[1]
H2_RELATIVE = Path("artifacts/review/h2-authentic-single-report-round-trip-v1")
H2_PACKAGE = ROOT / H2_RELATIVE
H2_MANIFEST = H2_PACKAGE / "task_report_manifest_v1.json"
H2_PACKET = H2_PACKAGE / "cross_project_supervision_packet_v1.json"
H2_SOURCE_RELATIVE = H2_RELATIVE / "source" / "AGENT_REPORT_H2_SOURCE_V1.md"
H3_PACKAGE = ROOT / "artifacts" / "review" / "h3-report-authority-envelope-v1"
H3_ENVELOPE = H3_PACKAGE / "supervision_report_authority_envelope_v1.json"
H3_READBACK = H3_PACKAGE / "authority_envelope_machine_readback_v1.json"
H3_INVENTORY = H3_PACKAGE / "binding_inventory_v1.json"
ASSESSED_AT = "2026-07-19T22:10:54.5042581+09:00"
SOURCE_REVISION = "d38075b97efabc99d1a23e8e0afafd5d44f1e2de"


class ReportAuthorityTests(unittest.TestCase):
    def test_tracked_h3_package_reloads_and_matches_machine_readback(self) -> None:
        envelope = load_authority_envelope(
            H3_ENVELOPE,
            manifest_path=H2_MANIFEST,
            packet_path=H2_PACKET,
            repo_root=ROOT,
            assessed_at=ASSESSED_AT,
        )
        readback = json.loads(H3_READBACK.read_text(encoding="utf-8"))
        inventory = json.loads(H3_INVENTORY.read_text(encoding="utf-8"))

        self.assertEqual(envelope["identity"], readback["identity"])
        self.assertEqual(envelope["authority"], readback["authority"])
        self.assertEqual(envelope["bindings"], inventory["bindings"])
        self.assertTrue(readback["authority_envelope"]["strict_reload"])
        self.assertTrue(readback["authority_envelope"]["full_source_reprojection"])
        self.assertFalse(readback["dashboard"]["current_claim_eligibility"])
        self.assertFalse(readback["dashboard"]["live_coverage"])
        self.assertFalse(readback["dashboard"]["executable"])
        self.assertFalse(readback["proof_boundary"]["h4_started"])

    def test_h3_package_generator_is_byte_deterministic_across_two_passes(self) -> None:
        namespace = runpy.run_path(str(H3_PACKAGE / "generate_package.py"))
        generate = namespace["generate"]

        generate()
        first = self._package_hashes()
        generate()
        second = self._package_hashes()

        self.assertEqual(first, second)

    def test_real_h2_package_is_authentic_but_not_current_or_live(self) -> None:
        envelope = self._build()
        authority = envelope["authority"]

        self.assertTrue(authority["authentic_owner_attached_point_in_time_evidence"])
        self.assertEqual("valid", authority["transport_source_binding_state"])
        self.assertEqual("insufficient_h2_only", authority["permission_state"])
        self.assertEqual("fresh", authority["temporal_state"])
        self.assertEqual("unknown", authority["revision_binding_state"])
        self.assertEqual("verified", authority["provenance_authenticity_state"])
        self.assertFalse(authority["current_claim_eligibility"])
        self.assertFalse(authority["live_coverage"])
        self.assertFalse(envelope["scope_boundary"]["executable"])
        self.assertEqual("not_reobserved", envelope["observation"]["state"])
        self.assertIsNone(envelope["observation"]["observed_revision"])
        self.assertEqual(H2_PERMISSION_SCOPE, envelope["report"]["observer_permission_scope"])
        self.assertEqual(
            [
                "authorized_current_source_reobservation_absent",
                "observation_stability_unconfirmed",
                "observed_revision_missing",
                "observer_only_non_executable",
                "permission_insufficient_for_h3_current_claim",
                "permission_scope_h2_only",
                "point_in_time_report_does_not_establish_live_coverage",
                "provenance_verified",
                "report_packet_identity_match",
                "source_manifest_packet_binding_valid",
                "timestamp_within_threshold",
                "worktree_not_clean_or_unknown",
            ],
            authority["reason_codes"],
        )
        self.assertNotIn("f611aac", json.dumps(envelope))

    def test_envelope_has_exact_root_and_nested_key_surfaces(self) -> None:
        envelope = self._build()

        self.assertEqual(ROOT_KEYS, set(envelope))
        self.assertEqual(IDENTITY_KEYS, set(envelope["identity"]))
        self.assertEqual(BINDINGS_KEYS, set(envelope["bindings"]))
        self.assertTrue(
            all(set(binding) == BINDING_KEYS for binding in envelope["bindings"].values())
        )
        self.assertEqual(REPORT_KEYS, set(envelope["report"]))
        self.assertEqual(OBSERVATION_KEYS, set(envelope["observation"]))
        self.assertEqual(AUTHORITY_KEYS, set(envelope["authority"]))
        self.assertEqual(SCOPE_KEYS, set(envelope["scope_boundary"]))

    def test_pure_predicate_is_true_only_for_complete_authorized_observation(self) -> None:
        evaluation = evaluate_authority_conditions(**self._positive_conditions())

        self.assertTrue(evaluation["authentic_owner_attached_point_in_time_evidence"])
        self.assertEqual("fresh", evaluation["temporal_state"])
        self.assertEqual("match", evaluation["revision_binding_state"])
        self.assertEqual("sufficient_for_h3_current_claim", evaluation["permission_state"])
        self.assertTrue(evaluation["current_claim_eligibility"])
        self.assertFalse(evaluation["live_coverage"])

    def test_pure_predicate_negative_matrix(self) -> None:
        cases = {
            "timestamp_missing": ({"report_observed_at": None}, "timestamp_missing"),
            "timestamp_stale": (
                {"report_observed_at": "2026-07-17T20:00:00+09:00"},
                "timestamp_threshold_exceeded",
            ),
            "timestamp_future": (
                {"report_observed_at": "2026-07-20T20:00:00+09:00"},
                "timestamp_in_future",
            ),
            "timestamp_timezone_missing": (
                {"report_observed_at": "2026-07-19T20:00:00"},
                "timestamp_timezone_missing",
            ),
            "timestamp_malformed": (
                {"report_observed_at": "not-a-time"},
                "timestamp_malformed",
            ),
            "source_revision_missing": (
                {"source_revision": None},
                "source_revision_missing",
            ),
            "observed_revision_missing": (
                {"observed_revision": None},
                "observed_revision_missing",
            ),
            "revision_short": (
                {"observed_revision": SOURCE_REVISION[:12]},
                "revision_abbreviation_unresolved",
            ),
            "revision_mismatch": (
                {"observed_revision": "a" * 40},
                "revision_mismatch",
            ),
            "dirty": ({"observation_clean": False}, "worktree_not_clean_or_unknown"),
            "unstable": (
                {"observation_stable": False},
                "observation_stability_unconfirmed",
            ),
            "h2_permission": (
                {"permission_scope": H2_PERMISSION_SCOPE},
                "permission_scope_h2_only",
            ),
            "bindings": (
                {"bindings_match": False},
                "source_manifest_packet_binding_invalid",
            ),
            "identity": (
                {"identity_match": False},
                "report_packet_identity_mismatch",
            ),
            "provenance": (
                {"provenance_verified": False},
                "provenance_unverified",
            ),
            "not_actual": (
                {"observation_actual": False},
                "authorized_current_source_reobservation_absent",
            ),
            "reobservation_stale": (
                {"reobserved_at": "2026-07-17T20:00:00+09:00"},
                "timestamp_threshold_exceeded",
            ),
            "scope": (
                {"observer_only": False},
                "observer_scope_boundary_invalid",
            ),
            "execution": (
                {"non_executable": False},
                "observer_scope_boundary_invalid",
            ),
        }
        for name, (changes, reason) in cases.items():
            with self.subTest(name=name):
                conditions = self._positive_conditions()
                conditions.update(changes)
                evaluation = evaluate_authority_conditions(**conditions)
                self.assertFalse(evaluation["current_claim_eligibility"])
                self.assertFalse(evaluation["live_coverage"])
                self.assertIn(reason, evaluation["reason_codes"])

    def test_loader_rederives_every_serialized_authority_claim(self) -> None:
        mutations = {
            "eligibility": lambda item: item["authority"].__setitem__(
                "current_claim_eligibility", True
            ),
            "reason": lambda item: item["authority"].__setitem__(
                "reason_codes", sorted(item["authority"]["reason_codes"] + ["forged_reason"])
            ),
            "assessed_at": lambda item: item["assessment"].__setitem__(
                "assessed_at", "2026-07-19T22:11:54+09:00"
            ),
            "revision": lambda item: item["report"].__setitem__("source_revision", "a" * 40),
            "permission": lambda item: item["report"].__setitem__(
                "observer_permission_scope", H3_CURRENT_PERMISSION_SCOPE
            ),
            "hash": lambda item: item["bindings"]["packet"].__setitem__(
                "content_sha256", "a" * 64
            ),
            "identity": lambda item: item["identity"].__setitem__("task_id", "task-forged"),
            "observation": lambda item: item["observation"].__setitem__(
                "authorization_scope", H3_CURRENT_PERMISSION_SCOPE
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root, manifest, packet = self._copy_h2_package(Path(temporary))
                envelope = build_authority_envelope(
                    manifest_path=manifest,
                    packet_path=packet,
                    repo_root=root,
                    assessed_at=ASSESSED_AT,
                )
                mutate(envelope)
                envelope_path = root / "authority.json"
                envelope_path.write_text(
                    dumps_authority_envelope(envelope, pretty=True), encoding="utf-8"
                )

                with self.assertRaisesRegex(
                    AuthorityEnvelopeError,
                    r"source-bound authority envelope mismatch at \$",
                ):
                    load_authority_envelope(
                        envelope_path,
                        manifest_path=manifest,
                        packet_path=packet,
                        repo_root=root,
                        assessed_at=ASSESSED_AT,
                    )

    def test_loader_accepts_only_exact_source_reprojection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, manifest, packet = self._copy_h2_package(Path(temporary))
            envelope = build_authority_envelope(
                manifest_path=manifest,
                packet_path=packet,
                repo_root=root,
                assessed_at=ASSESSED_AT,
            )
            envelope_path = root / "authority.json"
            envelope_path.write_text(
                dumps_authority_envelope(envelope, pretty=True), encoding="utf-8"
            )

            self.assertEqual(
                envelope,
                load_authority_envelope(
                    envelope_path,
                    manifest_path=manifest,
                    packet_path=packet,
                    repo_root=root,
                    assessed_at=ASSESSED_AT,
                ),
            )

    def test_source_manifest_and_packet_drift_are_rejected(self) -> None:
        mutations = {
            "source": lambda root, manifest, packet: (root / H2_SOURCE_RELATIVE).write_bytes(
                (root / H2_SOURCE_RELATIVE).read_bytes() + b"\n"
            ),
            "manifest": self._drift_manifest,
            "packet": self._drift_packet,
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root, manifest, packet = self._copy_h2_package(Path(temporary))
                mutate(root, manifest, packet)
                with self.assertRaises(AuthorityEnvelopeError):
                    build_authority_envelope(
                        manifest_path=manifest,
                        packet_path=packet,
                        repo_root=root,
                        assessed_at=ASSESSED_AT,
                    )

    def test_exact_key_wrong_type_and_scope_tampering_fail_closed(self) -> None:
        base = self._build()
        cases = {
            "missing_root": lambda item: item.pop("authority"),
            "unknown_root": lambda item: item.__setitem__("unexpected", False),
            "missing_nested": lambda item: item["authority"].pop("live_coverage"),
            "unknown_nested": lambda item: item["report"].__setitem__("unexpected", "x"),
            "wrong_type": lambda item: item["authority"].__setitem__(
                "current_claim_eligibility", 0
            ),
            "live": lambda item: item["authority"].__setitem__("live_coverage", True),
            "executable": lambda item: item["scope_boundary"].__setitem__(
                "executable", True
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                changed = copy.deepcopy(base)
                mutate(changed)
                with self.assertRaises(AuthorityEnvelopeError):
                    validate_authority_envelope(changed)

    def test_duplicate_key_is_rejected_with_object_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, manifest, packet = self._copy_h2_package(Path(temporary))
            envelope = build_authority_envelope(
                manifest_path=manifest,
                packet_path=packet,
                repo_root=root,
                assessed_at=ASSESSED_AT,
            )
            text = dumps_authority_envelope(envelope, pretty=False).replace(
                '"live_coverage":false',
                '"live_coverage":false,"live_coverage":false',
            )
            envelope_path = root / "authority.json"
            envelope_path.write_text(text, encoding="utf-8")

            with self.assertRaisesRegex(
                AuthorityEnvelopeError,
                r"duplicate JSON key at \$\.authority\.live_coverage",
            ):
                load_authority_envelope(
                    envelope_path,
                    manifest_path=manifest,
                    packet_path=packet,
                    repo_root=root,
                    assessed_at=ASSESSED_AT,
                )

    def test_h2_source_permission_cannot_be_extended_by_observation_input(self) -> None:
        envelope = build_authority_envelope(
            manifest_path=H2_MANIFEST,
            packet_path=H2_PACKET,
            repo_root=ROOT,
            assessed_at=ASSESSED_AT,
            current_observation={
                "observed_revision": SOURCE_REVISION,
                "reobserved_at": "2026-07-19T21:30:00+09:00",
                "actual": True,
                "clean": True,
                "stable": True,
                "authorization_scope": H3_CURRENT_PERMISSION_SCOPE,
            },
        )

        self.assertEqual(H2_PERMISSION_SCOPE, envelope["report"]["observer_permission_scope"])
        self.assertEqual(
            "insufficient_h2_only", envelope["authority"]["permission_state"]
        )
        self.assertFalse(envelope["authority"]["current_claim_eligibility"])

    def _build(self) -> dict[str, object]:
        return build_authority_envelope(
            manifest_path=H2_MANIFEST,
            packet_path=H2_PACKET,
            repo_root=ROOT,
            assessed_at=ASSESSED_AT,
        )

    @staticmethod
    def _positive_conditions() -> dict[str, object]:
        return {
            "report_observed_at": "2026-07-19T21:00:00+09:00",
            "assessed_at": ASSESSED_AT,
            "threshold_seconds": 86400,
            "source_revision": SOURCE_REVISION,
            "observed_revision": SOURCE_REVISION,
            "reobserved_at": "2026-07-19T21:30:00+09:00",
            "permission_scope": H3_CURRENT_PERMISSION_SCOPE,
            "observation_actual": True,
            "observation_clean": True,
            "observation_stable": True,
            "bindings_match": True,
            "identity_match": True,
            "provenance_verified": True,
            "observer_only": True,
            "non_executable": True,
            "evidence_class": AUTHENTIC_EVIDENCE_CLASS,
            "authority_basis": AUTHENTIC_AUTHORITY_BASIS,
        }

    @staticmethod
    def _copy_h2_package(temporary: Path) -> tuple[Path, Path, Path]:
        root = temporary / "repo"
        package = root / H2_RELATIVE
        package.parent.mkdir(parents=True)
        shutil.copytree(H2_PACKAGE, package)
        return root, package / H2_MANIFEST.name, package / H2_PACKET.name

    @staticmethod
    def _drift_manifest(root: Path, manifest: Path, packet: Path) -> None:
        del root, packet
        value = json.loads(manifest.read_text(encoding="utf-8"))
        value["reports"][0]["content_sha256"] = "a" * 64
        manifest.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _drift_packet(root: Path, manifest: Path, packet: Path) -> None:
        del root, manifest
        value = json.loads(packet.read_text(encoding="utf-8"))
        value["global_attention_queue"][0]["current_state"] = "forged state"
        packet.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _package_hashes() -> dict[str, str]:
        return {
            path.relative_to(H3_PACKAGE).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in sorted(item for item in H3_PACKAGE.rglob("*") if item.is_file())
        }


if __name__ == "__main__":
    unittest.main()
