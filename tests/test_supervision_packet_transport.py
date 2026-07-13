from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKET_ROOT = ROOT / "samples" / "supervision_packets"
MANIFEST_PATH = PACKET_ROOT / "task_report_manifest_v1.json"
CANONICAL_ARTIFACT_HASHES = {
    "samples/supervision_packets/cross_project_supervision_packet_v1.json": (
        "07965839fdef3d591776804e23d94d26996b5a13a6bf380fbe4e263231f59aec"
    ),
    "samples/supervision_packets/cross_project_supervision_packet_v1.md": (
        "d28dbfbde4d162e84843889141408972ea2946d09ba6b581e56c7c2378362fb7"
    ),
}


class SupervisionPacketTransportTests(unittest.TestCase):
    def test_repository_declares_lf_checkout_for_byte_bound_text(self) -> None:
        self.assertEqual(
            b"* text=auto eol=lf\n",
            (ROOT / ".gitattributes").read_bytes(),
        )
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        protected_paths = [
            "samples/supervision_packets/task_report_manifest_v1.json",
            *[entry["report_path"] for entry in manifest["reports"]],
            *CANONICAL_ARTIFACT_HASHES,
        ]

        for relative_path in protected_paths:
            with self.subTest(path=relative_path):
                result = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(ROOT),
                        "check-attr",
                        "text",
                        "eol",
                        "--",
                        relative_path,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                self.assertIn(f"{relative_path}: text: auto", result.stdout)
                self.assertIn(f"{relative_path}: eol: lf", result.stdout)

    def test_manifest_report_hashes_bind_raw_lf_bytes(self) -> None:
        manifest_bytes = MANIFEST_PATH.read_bytes()
        self.assertNotIn(b"\r", manifest_bytes)
        manifest = json.loads(manifest_bytes.decode("utf-8"))

        for entry in manifest["reports"]:
            with self.subTest(path=entry["report_path"]):
                raw = (ROOT / entry["report_path"]).read_bytes()
                self.assertNotIn(b"\r", raw)
                self.assertEqual(entry["content_sha256"], sha256(raw).hexdigest())

    def test_canonical_packet_artifact_hashes_are_unchanged(self) -> None:
        for relative_path, expected_hash in CANONICAL_ARTIFACT_HASHES.items():
            with self.subTest(path=relative_path):
                raw = (ROOT / relative_path).read_bytes()
                self.assertNotIn(b"\r", raw)
                self.assertEqual(expected_hash, sha256(raw).hexdigest())


if __name__ == "__main__":
    unittest.main()
