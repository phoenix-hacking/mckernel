import importlib.util
import json
import os
import stat
import tempfile
import unittest
import contextlib
import io
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "native_rust_exact_candidate_inventory.py"
SPEC = importlib.util.spec_from_file_location("candidate_inventory", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CandidateInventoryTests(unittest.TestCase):
    def test_inventory_hashes_files_links_and_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            (root / "file").write_bytes(b"abc\0")
            os.chmod(root / "file", 0o600)
            (root / "link").symlink_to("file")
            result = MODULE.inventory([str(root)])
            rows = {Path(row["path"]).name: row for row in result["worktree_inventory"]}
            self.assertIsNone(rows["root"]["sha256"])
            self.assertEqual(rows["file"]["type"], "file")
            self.assertEqual(set(rows["file"]), {"path", "type", "mode", "sha256"})
            self.assertEqual(rows["file"]["mode"], "0600")
            self.assertEqual(rows["link"]["type"], "symlink")
            self.assertEqual(rows["link"]["sha256"], MODULE._digest(b"file"))

    def test_rejects_duplicate_and_nested_roots_and_special_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            nested = root / "nested"
            nested.mkdir()
            with self.assertRaises(MODULE.InventoryError):
                MODULE.inventory([str(root), str(root)])
            with self.assertRaises(MODULE.InventoryError):
                MODULE.inventory([str(root), str(nested)])
            fifo = root / "fifo"
            os.mkfifo(fifo)
            with self.assertRaises(MODULE.InventoryError):
                MODULE.inventory([str(root)])

    def test_verify_detects_content_and_mode_churn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            target = root / "file"
            target.write_bytes(b"before")
            os.chmod(target, 0o644)
            result = MODULE.inventory([str(root)])
            target.write_bytes(b"after")
            with self.assertRaises(MODULE.InventoryError):
                # verify accepts an inventory path, so use a temporary JSON file.
                path = Path(tmp) / "inventory.json"
                path.write_text(json.dumps(result), encoding="utf-8")
                MODULE.verify(path, [str(root)])
            target.write_bytes(b"before")
            result = MODULE.inventory([str(root)])
            os.chmod(target, 0o600)
            path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaises(MODULE.InventoryError):
                MODULE.verify(path, [str(root)])

    def test_cli_requires_explicit_output_and_verify_roots(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                MODULE.main(["generate", "--root", "/missing"])
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                MODULE.main(["verify", "--inventory", "/missing"])


if __name__ == "__main__":
    unittest.main()
