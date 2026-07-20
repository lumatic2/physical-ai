import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB_ROOT))

from gen_arm_lab_manifest import build_bundle, json_bytes, verify_bundle  # noqa: E402


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class ArmLabManifestTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "bundle"
        build_bundle(self.output)

    def tearDown(self):
        self.temp.cleanup()

    def load_registry(self):
        return json.loads((self.output / "registry.json").read_text(encoding="utf-8"))

    def write_registry(self, registry):
        (self.output / "registry.json").write_bytes(json_bytes(registry))

    def test_build_is_byte_identical(self):
        first = tree_hash(self.output)
        build_bundle(self.output)
        self.assertEqual(first, tree_hash(self.output))

    def test_valid_bundle(self):
        result = verify_bundle(self.output)
        self.assertTrue(result["valid"])
        self.assertLess(result["bytes"], 5 * 1024 * 1024)

    def test_missing_media_fails(self):
        (self.output / "media" / "pass-main.mp4").unlink()
        with self.assertRaisesRegex(ValueError, "missing artifact"):
            verify_bundle(self.output)

    def test_hash_mismatch_fails(self):
        with (self.output / "traces" / "pass.json").open("ab") as handle:
            handle.write(b" ")
        with self.assertRaisesRegex(ValueError, "size mismatch|hash mismatch"):
            verify_bundle(self.output)

    def test_absolute_path_and_token_fail(self):
        registry = self.load_registry()
        registry["debug_path"] = r"C:\\Users\\someone\\episode.json"
        self.write_registry(registry)
        with self.assertRaisesRegex(ValueError, "absolute local path"):
            verify_bundle(self.output)
        registry.pop("debug_path")
        registry["debug_token"] = "hf_1234567890abcdef"
        self.write_registry(registry)
        with self.assertRaisesRegex(ValueError, "token-like value"):
            verify_bundle(self.output)

    def test_unknown_event_source_fails(self):
        registry = self.load_registry()
        record = registry["episodes"]["pass"]["event_lanes"]["vlm_skill"]
        event_path = self.output / record["path"]
        document = json.loads(event_path.read_text(encoding="utf-8"))
        document["events"][0]["source"] = "oracle"
        event_path.write_bytes(json_bytes(document))
        record["bytes"] = event_path.stat().st_size
        record["sha256"] = hashlib.sha256(event_path.read_bytes()).hexdigest()
        self.write_registry(registry)
        with self.assertRaisesRegex(ValueError, "unsupported event source"):
            verify_bundle(self.output)


if __name__ == "__main__":
    unittest.main()
