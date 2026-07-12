from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dev_cockpit.evidence_freshness import (
    AUTHORITY_CLASSIFICATION,
    HASH_BASIS,
    OBSERVATIONS_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION,
    RECEIPT_SCHEMA_VERSION,
    REMOTE_PARITY_BASIS,
    TEMPORAL_BOUNDARY,
    EvidenceFreshnessError,
    build_receipt,
    canonical_sha256,
    dumps_receipt,
    evaluate_revision,
    evaluate_temporal,
    load_observations,
    load_policy,
    load_receipt,
    main,
    redact_path,
    render_markdown,
    validate_receipt,
    verify_receipt_hashes,
    write_receipt,
    _capture_id,
)


SAMPLE_DIR = ROOT / "samples" / "evidence_freshness"
POLICY_PATH = SAMPLE_DIR / "evidence_freshness_policy_v1.json"
OBSERVATIONS_PATH = SAMPLE_DIR / "evidence_freshness_example_observations_v1.json"
RECEIPT_PATH = SAMPLE_DIR / "evidence_freshness_receipt_v1.json"
MARKDOWN_PATH = SAMPLE_DIR / "evidence_freshness_receipt_v1.md"
ASSESSED_AT = "2026-07-12T00:00:00Z"
REVISION_A = "a" * 40
REVISION_B = "b" * 40
PRODUCTION_GENERATOR_BLOB = "8e047f50f9e9525533f5fbd6d784b27508b6d10f"

RECEIPT_KEYS = {
    "schema_version",
    "capture_id",
    "assessed_at",
    "producer",
    "policy",
    "authority",
    "observation_mode",
    "remote_parity_evidence",
    "projects",
    "sources",
    "summary",
    "scope_boundary",
}
SOURCE_KEYS = {
    "project_id",
    "source_id",
    "source_kind",
    "required",
    "availability",
    "schema_version",
    "source_path",
    "content_sha256",
    "hash_basis",
    "generated_at",
    "observed_at",
    "timestamp_field",
    "assessed_at",
    "age_seconds",
    "fresh_through",
    "temporal_state",
    "source_revision",
    "observed_revision",
    "revision_binding_state",
    "freshness_state",
    "reason_codes",
    "current_state_claim_eligible",
    "authority_classification",
}


class EvidenceFreshnessTests(unittest.TestCase):
    def test_tracked_receipt_has_strict_provenance_and_summary_contract(self) -> None:
        policy = load_policy(POLICY_PATH)
        observations = load_observations(OBSERVATIONS_PATH)
        receipt = build_receipt(
            policy,
            repo_root=ROOT,
            assessed_at=ASSESSED_AT,
            observations=observations,
            tracked_example=True,
        )
        self.assertEqual(receipt, validate_receipt(receipt))
        loaded = load_receipt(RECEIPT_PATH, repo_root=ROOT, verify_hashes=True)
        self.assertEqual(receipt, loaded)
        self.assertEqual(
            {"verified": 7, "skipped_missing": 1},
            verify_receipt_hashes(loaded, repo_root=ROOT),
        )

        self.assertEqual(RECEIPT_SCHEMA_VERSION, receipt["schema_version"])
        self.assertEqual(RECEIPT_KEYS, set(receipt))
        self.assertEqual(TEMPORAL_BOUNDARY, receipt["policy"]["temporal_boundary"])
        self.assertEqual(86400, receipt["policy"]["threshold_seconds"])
        self.assertEqual(AUTHORITY_CLASSIFICATION, receipt["authority"]["classification"])
        self.assertTrue(receipt["authority"]["point_in_time"])
        self.assertFalse(receipt["authority"]["live"])
        self.assertTrue(receipt["authority"]["tracked_example"])
        self.assertFalse(receipt["authority"]["authoritative_for_live_state"])
        self.assertFalse(receipt["authority"]["may_support_current_state_at_assessed_at"])
        self.assertEqual(REMOTE_PARITY_BASIS, receipt["remote_parity_evidence"]["basis"])
        self.assertFalse(receipt["remote_parity_evidence"]["fetch_performed"])
        self.assertFalse(receipt["remote_parity_evidence"]["live_remote_state_claimed"])

        projects = receipt["projects"]
        sources = receipt["sources"]
        self.assertEqual(
            [item["project_id"] for item in projects],
            sorted(item["project_id"] for item in projects),
        )
        self.assertEqual(
            [(item["project_id"], item["source_id"]) for item in sources],
            sorted((item["project_id"], item["source_id"]) for item in sources),
        )
        self.assertTrue(all(not item["current_state_claim_eligible"] for item in sources))

        for source in sources:
            with self.subTest(source_id=source["source_id"]):
                self.assertEqual(SOURCE_KEYS, set(source))
                self.assertEqual(HASH_BASIS, source["hash_basis"])
                self.assertEqual(AUTHORITY_CLASSIFICATION, source["authority_classification"])
                self.assertIn(source["temporal_state"], {"fresh", "stale", "unknown"})
                self.assertIn(source["revision_binding_state"], {"match", "mismatch", "unknown"})
                self.assertIn(source["freshness_state"], {"fresh", "stale", "unknown"})
                self.assertEqual(sorted(set(source["reason_codes"])), source["reason_codes"])
                if source["availability"] == "available":
                    self.assertRegex(source["content_sha256"], r"\A[0-9a-f]{64}\Z")
                else:
                    self.assertIsNone(source["content_sha256"])

        counts = receipt["summary"]["source_counts"]
        self.assertEqual(len(sources), counts["total"])
        self.assertEqual(
            len(sources),
            counts["fresh"] + counts["stale"] + counts["unknown"],
        )
        eligibility = receipt["summary"]["current_state_claim_eligible"]
        self.assertEqual(len(sources), eligibility["eligible"] + eligibility["ineligible"])

        tracked = [item for item in sources if item["source_kind"] == "tracked_point_in_time_artifact"]
        self.assertTrue(tracked)
        for source in tracked:
            path = ROOT / source["source_path"]
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(canonical_sha256(data), source["content_sha256"])

        markdown = render_markdown(receipt)
        for source in sources:
            self.assertIn(source["source_id"], markdown)
            if source["content_sha256"]:
                self.assertIn(source["content_sha256"], markdown)

    def test_production_loaders_reject_duplicate_policy_and_source_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            duplicate_policy = root / "duplicate-policy.json"
            policy_text = POLICY_PATH.read_text(encoding="utf-8")
            policy_text = policy_text.replace(
                '  "threshold_seconds": 86400,',
                '  "threshold_seconds": 86400,\n  "threshold_seconds": 1,',
                1,
            )
            duplicate_policy.write_text(policy_text, encoding="utf-8", newline="\n")

            with self.assertRaisesRegex(
                EvidenceFreshnessError,
                r"duplicate JSON key: threshold_seconds",
            ):
                load_policy(duplicate_policy)

            duplicate_receipt = root / "duplicate-receipt.json"
            receipt_text = RECEIPT_PATH.read_text(encoding="utf-8")
            receipt_text = receipt_text.replace(
                '  "capture_id":',
                '  "capture_id": "efr-00000000000000000000",\n  "capture_id":',
                1,
            )
            duplicate_receipt.write_text(receipt_text, encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(
                EvidenceFreshnessError,
                r"duplicate JSON key: capture_id",
            ):
                load_receipt(duplicate_receipt)

            (root / "duplicate-source.json").write_text(
                '{"schema_version":"unit.v1",'
                '"generated_at":"2026-07-12T00:00:00Z",'
                '"generated_at":"2026-07-11T00:00:00Z",'
                f'"revision":"{REVISION_A}"}}\n',
                encoding="utf-8",
                newline="\n",
            )
            receipt = build_receipt(
                _policy("duplicate-source.json"),
                repo_root=root,
                assessed_at=ASSESSED_AT,
                observations=_observations(),
                tracked_example=True,
            )
            validate_receipt(receipt)
            invalid_verification = verify_receipt_hashes(receipt, repo_root=root)

        source = _source(receipt, "fixture-source")
        self.assertEqual("invalid_contract", source["availability"])
        self.assertEqual("unknown", source["freshness_state"])
        self.assertEqual(["source_json_duplicate_key"], source["reason_codes"])
        self.assertRegex(source["content_sha256"], r"\A[0-9a-f]{64}\Z")
        self.assertEqual("raw_bytes_sha256_v1", source["hash_basis"])
        self.assertFalse(source["current_state_claim_eligible"])
        self.assertEqual(0, receipt["summary"]["required_missing"])
        self.assertEqual(1, receipt["summary"]["required_invalid"])
        self.assertEqual({"verified": 2, "skipped_missing": 0}, invalid_verification)

    def test_receipt_validation_recomputes_eligibility_and_hash_bound_projection(self) -> None:
        receipt = load_receipt(RECEIPT_PATH)
        eligibility_tamper = copy.deepcopy(receipt)
        stale = next(
            source
            for source in eligibility_tamper["sources"]
            if source["freshness_state"] == "stale"
        )
        stale["current_state_claim_eligible"] = True
        eligibility_tamper["summary"]["current_state_claim_eligible"] = {
            "eligible": 1,
            "ineligible": len(eligibility_tamper["sources"]) - 1,
        }
        _refresh_capture_id(eligibility_tamper)
        with self.assertRaisesRegex(
            EvidenceFreshnessError,
            r"semantic freshness projection is inconsistent",
        ):
            validate_receipt(eligibility_tamper)

        projection_tamper = copy.deepcopy(receipt)
        tracked = next(
            source
            for source in projection_tamper["sources"]
            if source["source_kind"] == "tracked_point_in_time_artifact"
        )
        tracked["schema_version"] = "forged.v1"
        _refresh_capture_id(projection_tamper)
        validate_receipt(projection_tamper)
        with self.assertRaisesRegex(
            EvidenceFreshnessError,
            r"source provenance projection mismatch",
        ):
            verify_receipt_hashes(projection_tamper, repo_root=ROOT)

    def test_policy_model_rejects_wrong_schema_bad_threshold_and_absolute_source(self) -> None:
        invalid_cases = (
            ("wrong-schema", {**_policy("source.json"), "schema_version": "other.v1"}),
            ("zero-threshold", {**_policy("source.json"), "threshold_seconds": 0}),
            (
                "absolute-source",
                {
                    **_policy("source.json"),
                    "tracked_sources": [
                        {
                            **_policy("source.json")["tracked_sources"][0],
                            "path": r"C:\Users\alice\source.json",
                        }
                    ],
                },
            ),
        )
        for label, policy in invalid_cases:
            with self.subTest(label=label), self.assertRaises(EvidenceFreshnessError):
                build_receipt(
                    policy,
                    repo_root=ROOT,
                    assessed_at=ASSESSED_AT,
                    observations=_observations(),
                )

    def test_temporal_policy_inclusive_boundary_and_unknown_reason_codes(self) -> None:
        cases = (
            ("one-second-inside", "2026-07-11T00:00:01Z", "fresh", 86399, "timestamp_within_threshold"),
            ("exact-boundary", "2026-07-11T00:00:00Z", "fresh", 86400, "timestamp_within_threshold"),
            ("one-second-stale", "2026-07-10T23:59:59Z", "stale", 86401, "timestamp_threshold_exceeded"),
            ("missing", None, "unknown", None, "timestamp_missing"),
            ("malformed", "not-a-time", "unknown", None, "timestamp_malformed"),
            ("timezone-naive", "2026-07-11T00:00:00", "unknown", None, "timestamp_timezone_missing"),
            ("future", "2026-07-12T00:00:01Z", "unknown", None, "timestamp_in_future"),
        )
        for label, timestamp, state, age, reason in cases:
            with self.subTest(label=label):
                result = evaluate_temporal(
                    timestamp,
                    assessed_at=ASSESSED_AT,
                    threshold_seconds=86400,
                )
                self.assertEqual(state, result["temporal_state"])
                self.assertEqual(age, result["age_seconds"])
                self.assertEqual([reason], result["reason_codes"])
                if state == "unknown":
                    self.assertIsNone(result["fresh_through"])

    def test_revision_binding_match_mismatch_missing_and_abbreviation(self) -> None:
        cases = (
            ("match", REVISION_A, REVISION_A, "match", "revision_match"),
            ("mismatch", REVISION_A, REVISION_B, "mismatch", "revision_mismatch"),
            ("source-missing", None, REVISION_A, "unknown", "source_revision_missing"),
            ("observed-missing", REVISION_A, None, "unknown", "observed_revision_missing"),
            ("unresolved-prefix", REVISION_A[:7], REVISION_A, "unknown", "revision_abbreviation_unresolved"),
            ("invalid-format", "not-a-revision", REVISION_A, "unknown", "revision_format_unsupported"),
        )
        for label, source_revision, observed_revision, state, reason in cases:
            with self.subTest(label=label):
                result = evaluate_revision(source_revision, observed_revision)
                self.assertEqual(state, result["revision_binding_state"])
                self.assertEqual([reason], result["reason_codes"])

    def test_tracked_example_regeneration_is_byte_deterministic_and_non_authoritative(self) -> None:
        policy_raw = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        observations_raw = json.loads(OBSERVATIONS_PATH.read_text(encoding="utf-8"))
        reversed_policy = copy.deepcopy(policy_raw)
        reversed_policy["tracked_sources"].reverse()
        reversed_observations = copy.deepcopy(observations_raw)
        reversed_observations["projects"].reverse()
        for project in reversed_observations["projects"]:
            project["reason_codes"] = list(reversed(project.get("reason_codes", [])))

        receipt = build_receipt(
            policy_raw,
            repo_root=ROOT,
            assessed_at=ASSESSED_AT,
            observations=observations_raw,
            tracked_example=True,
        )
        reordered = build_receipt(
            reversed_policy,
            repo_root=ROOT,
            assessed_at=ASSESSED_AT,
            observations=reversed_observations,
            tracked_example=True,
        )

        expected_json = RECEIPT_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
        expected_markdown = MARKDOWN_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
        self.assertEqual(dumps_receipt(receipt, pretty=True), dumps_receipt(reordered, pretty=True))
        self.assertEqual(expected_json, dumps_receipt(receipt, pretty=True))
        self.assertEqual(expected_markdown, render_markdown(receipt))
        self.assertFalse(receipt["authority"]["may_support_current_state_at_assessed_at"])
        self.assertTrue(all(not item["current_state_claim_eligible"] for item in receipt["sources"]))

        with tempfile.TemporaryDirectory() as temp:
            json_output = Path(temp) / "receipt.json"
            markdown_output = Path(temp) / "receipt.md"
            write_receipt(
                reordered,
                json_output,
                output_markdown=markdown_output,
                pretty=True,
            )
            self.assertEqual(expected_json, json_output.read_text(encoding="utf-8"))
            self.assertEqual(expected_markdown, markdown_output.read_text(encoding="utf-8"))

    def test_required_source_and_optional_project_missing_are_structured_cli_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_json(
                root / "source.json",
                {
                    "schema_version": "unit_evidence.v1",
                    "generated_at": ASSESSED_AT,
                    "revision": REVISION_A,
                },
            )
            policy_path = root / "policy.json"
            observations_path = root / "observations.json"
            output_json = root / "receipt.json"
            output_markdown = root / "receipt.md"
            _write_json(policy_path, _policy("source.json"))
            _write_json(
                observations_path,
                _observations(include_optional_missing=True),
            )

            result = main(
                [
                    "--policy",
                    str(policy_path),
                    "--repo-root",
                    str(root),
                    "--observations",
                    str(observations_path),
                    "--assessed-at",
                    ASSESSED_AT,
                    "--output-json",
                    str(output_json),
                    "--output-markdown",
                    str(output_markdown),
                    "--pretty",
                ]
            )
            self.assertEqual(0, result)
            receipt = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertTrue(receipt["authority"]["tracked_example"])
            self.assertFalse(receipt["authority"]["may_support_current_state_at_assessed_at"])
            self.assertEqual(
                "injected_deterministic_observations",
                receipt["observation_mode"],
            )
            markdown = output_markdown.read_text(encoding="utf-8")
            self.assertEqual(1, receipt["summary"]["project_counts"]["missing_optional"])
            self.assertEqual(0, receipt["summary"]["required_missing"])
            optional = _source(receipt, "optionalproject.live_status_observation")
            self.assertEqual("missing", optional["availability"])
            self.assertEqual(["optional_project_missing"], optional["reason_codes"])
            self.assertFalse(optional["current_state_claim_eligible"])
            self.assertIn("optional_project_missing", markdown)

            missing_policy = _policy("missing-required-source.json")
            _write_json(policy_path, missing_policy)
            missing_output = root / "missing-receipt.json"
            result = main(
                [
                    "--policy",
                    str(policy_path),
                    "--repo-root",
                    str(root),
                    "--observations",
                    str(observations_path),
                    "--assessed-at",
                    ASSESSED_AT,
                    "--tracked-example",
                    "--output-json",
                    str(missing_output),
                    "--pretty",
                ]
            )
            self.assertEqual(1, result)
            missing_receipt = json.loads(missing_output.read_text(encoding="utf-8"))

        missing = _source(missing_receipt, "fixture-source")
        self.assertEqual("missing", missing["availability"])
        self.assertEqual("unknown", missing["freshness_state"])
        self.assertEqual(["required_source_missing"], missing["reason_codes"])
        self.assertFalse(missing["current_state_claim_eligible"])
        self.assertEqual(1, missing_receipt["summary"]["required_missing"])

    def test_paths_are_repo_relative_or_user_redacted_in_json_and_markdown(self) -> None:
        windows_path = r"C:\Users\alice\Project\evidence.json"
        posix_path = "/home/alice/Project/evidence.json"
        self.assertEqual(
            "<redacted-absolute>/evidence.json",
            redact_path(windows_path),
        )
        self.assertEqual(
            "<redacted-absolute>/evidence.json",
            redact_path(posix_path),
        )
        self.assertEqual(
            "<redacted-absolute>/private.json",
            redact_path(r"D:\Secret\private.json"),
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "nested" / "evidence.json"
            self.assertEqual("nested/evidence.json", redact_path(str(nested), repo_root=root))
            _write_json(
                root / "source.json",
                {
                    "schema_version": "unit_evidence.v1",
                    "generated_at": ASSESSED_AT,
                    "revision": REVISION_A,
                },
            )
            observations = _observations(path=windows_path)
            receipt = build_receipt(
                _policy("source.json"),
                repo_root=root,
                assessed_at=ASSESSED_AT,
                observations=observations,
                tracked_example=True,
            )
        payload = dumps_receipt(receipt, pretty=True)
        markdown = render_markdown(receipt)
        self.assertNotIn("alice", payload)
        self.assertNotIn("alice", markdown)
        self.assertIn("<redacted-absolute>/evidence.json", payload)
        self.assertIn("<redacted-absolute>/evidence.json", markdown)

    def test_live_observer_preserves_git_state_and_eligibility_requires_clean_stable_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            policy = _create_live_fixture_repo(root)
            before_head = _git(root, "rev-parse", "HEAD")
            before_status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")

            receipt = build_receipt(
                policy,
                repo_root=root,
                assessed_at=ASSESSED_AT,
            )

            after_head = _git(root, "rev-parse", "HEAD")
            after_status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
            self.assertEqual(before_head, after_head)
            self.assertEqual(before_status, after_status)
            project = receipt["projects"][0]
            self.assertEqual(before_head, project["head_revision"])
            self.assertTrue(project["observation_unchanged"])
            self.assertFalse(project["target_repo_modified"])
            self.assertEqual(project["before_sha256"], project["after_sha256"])
            self.assertTrue(receipt["scope_boundary"]["target_repositories_observed_read_only"])
            self.assertTrue(receipt["scope_boundary"]["all_available_observations_unchanged"])
            self.assertFalse(receipt["scope_boundary"]["fetch_performed"])
            self.assertFalse(receipt["scope_boundary"]["default_validation_executed"])
            live = _source(receipt, "devcockpitcore.live_status_observation")
            self.assertEqual("fresh", live["temporal_state"])
            self.assertEqual("match", live["revision_binding_state"])
            self.assertEqual("fresh", live["freshness_state"])
            self.assertTrue(live["current_state_claim_eligible"])

            (root / "dirty.txt").write_text("dirty\n", encoding="utf-8", newline="\n")
            dirty_before = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
            dirty_receipt = build_receipt(
                policy,
                repo_root=root,
                assessed_at=ASSESSED_AT,
            )
            dirty_after = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
            self.assertEqual(dirty_before, dirty_after)
            dirty_live = _source(dirty_receipt, "devcockpitcore.live_status_observation")
            self.assertEqual("fresh", dirty_live["freshness_state"])
            self.assertFalse(dirty_live["current_state_claim_eligible"])
            self.assertIn("worktree_not_clean_or_unknown", dirty_live["reason_codes"])

    def test_cli_help_and_invalid_contract_exit_are_observable(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout), self.assertRaises(SystemExit) as raised:
            main(["--help"])
        self.assertEqual(0, raised.exception.code)
        self.assertIn("evidence_freshness_receipt.v1", stdout.getvalue())

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = main(["--policy", "missing-policy.json"])
        self.assertEqual(2, result)
        self.assertIn("evidence freshness error:", stderr.getvalue())

    def test_production_dashboard_generator_blob_remains_unchanged(self) -> None:
        completed = subprocess.run(
            ["git", "hash-object", "src/dev_cockpit/dashboard.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(PRODUCTION_GENERATOR_BLOB, completed.stdout.strip())


def _policy(source_path: str) -> dict[str, object]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "policy_id": "unit-policy-v1",
        "threshold_seconds": 86400,
        "temporal_boundary": TEMPORAL_BOUNDARY,
        "cross_project_smoke_path": "samples/cross_project_smokes/smoke.json",
        "tracked_sources": [
            {
                "project_id": "devcockpitcore",
                "source_id": "fixture-source",
                "source_kind": "tracked_point_in_time_artifact",
                "required": True,
                "path": source_path,
                "schema_path": ["schema_version"],
                "timestamp_kind": "generated_at",
                "timestamp_path": ["generated_at"],
                "revision_path": ["revision"],
            }
        ],
    }


def _observations(
    *,
    include_optional_missing: bool = False,
    path: str = ".",
) -> dict[str, object]:
    projects: list[dict[str, object]] = [
        {
            "project_id": "devcockpitcore",
            "required": True,
            "available": True,
            "path": path,
            "schema_version": "status_snapshot.v1",
            "observed_at": ASSESSED_AT,
            "branch": "main",
            "head_revision": REVISION_A,
            "worktree_state": "clean",
            "upstream": "origin/main",
            "remote_parity": {
                "status": "in_sync",
                "ahead": 0,
                "behind": 0,
                "tracking_ref": "origin/main",
            },
            "observation_unchanged": True,
            "target_repo_modified": False,
            "before_sha256": "1" * 64,
            "after_sha256": "1" * 64,
            "reason_codes": [],
        }
    ]
    if include_optional_missing:
        projects.append(
            {
                "project_id": "optionalproject",
                "required": False,
                "available": False,
                "path": "../OptionalProject",
                "schema_version": None,
                "observed_at": ASSESSED_AT,
                "branch": None,
                "head_revision": None,
                "worktree_state": "unknown",
                "upstream": None,
                "remote_parity": None,
                "observation_unchanged": None,
                "target_repo_modified": None,
                "before_sha256": None,
                "after_sha256": None,
                "reason_codes": ["optional_project_missing"],
            }
        )
    return {
        "schema_version": OBSERVATIONS_SCHEMA_VERSION,
        "observed_at": ASSESSED_AT,
        "projects": projects,
    }


def _source(receipt: dict[str, object], source_id: str) -> dict[str, object]:
    matches = [item for item in receipt["sources"] if item["source_id"] == source_id]
    if len(matches) != 1:
        raise AssertionError(f"expected one source {source_id!r}, found {len(matches)}")
    return matches[0]


def _refresh_capture_id(receipt: dict[str, object]) -> None:
    receipt["capture_id"] = _capture_id(
        policy_id=receipt["policy"]["policy_id"],
        policy_sha256=receipt["policy"]["policy_content_sha256"],
        assessed_at=receipt["assessed_at"],
        observation_mode=receipt["observation_mode"],
        tracked_example=receipt["authority"]["tracked_example"],
        projects=receipt["projects"],
        sources=receipt["sources"],
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _create_live_fixture_repo(root: Path) -> dict[str, object]:
    adapter = json.loads((ROOT / "adapters" / "devcockpitcore.json").read_text(encoding="utf-8"))
    _write_json(root / "adapters" / "devcockpitcore.json", adapter)
    _write_json(
        root / "samples" / "cross_project_smokes" / "smoke.json",
        {
            "schema_version": "cross_project_smoke.v1",
            "smoke_key": "evidence_freshness_unit",
            "project_key": "devcockpitcore",
            "description": "Read-only unit observation.",
            "adapters": [
                {
                    "adapter_path": "adapters/devcockpitcore.json",
                    "required": True,
                    "expected_default_branch": "main",
                    "notes": [],
                }
            ],
        },
    )
    _write_json(
        root / "source.json",
        {
            "schema_version": "unit_evidence.v1",
            "generated_at": ASSESSED_AT,
            "revision": REVISION_A,
        },
    )
    policy = _policy("source.json")
    _write_json(root / "policy.json", policy)
    _git(root, "init", "--initial-branch=main")
    _git(root, "config", "user.name", "DevCockpitCore Test")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "add", "--all")
    _git(root, "commit", "-m", "fixture")
    return policy


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    unittest.main()
