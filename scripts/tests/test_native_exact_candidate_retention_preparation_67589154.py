"""Pure contract tests for the non-executed live retention packet."""
import hashlib, os, subprocess, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
PACKET = ROOT / "docs/verification/evidence/native-exact-candidate-retention-preparation-67589154-1.py"

class PacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.text = PACKET.read_text(encoding="utf-8")

    def test_defaults_to_draft_and_does_not_create_state(self):
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(["/usr/bin/python3", "-E", "-s", "-B", str(PACKET)], cwd=td,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 3); self.assertIn("DRAFT_NOT_RELEASED", r.stderr)
            self.assertEqual(os.listdir(td), [])

    def test_exact_bindings_and_fresh_outputs(self):
        for value in ("6f8a499ec33359ac49a1191a2a8139790e2044ce", "ac3bb0354d1353928fd5f63ddf6743b636642fab79a4f5a3ec9195d5721d0b26", "6a28184e13e4ddec3a5e2fe6229c618929df29f235901083d55918c8291ac06e", "675891545c881b8d625256ade56fe66ac69fe794", "3114d9e7101ad52030eb3effa849a5c108972a1f", "25166", "35798"): self.assertIn(value, self.text)
        self.assertIn("RELEASE_HASH_REQUIRED", self.text)
        self.assertIn("DRAFT_NOT_RELEASED", self.text)
        self.assertIn("--main-revision", self.text); self.assertIn("--ihk-revision", self.text)
        self.assertIn("os.O_EXCL", self.text); self.assertIn("os.fsync", self.text)

    def test_no_privileged_or_runtime_operations(self):
        for forbidden in ("docker", "sudo", "qemu", "chmod", "rename", "unlink(candidate)", "unlink(backup)"):
            self.assertNotIn(forbidden, self.text.lower())
        self.assertIn("subprocess.Popen", self.text); self.assertIn("timeout=1800", self.text)

    def test_source_is_python_compilable_and_digestable(self):
        with tempfile.TemporaryDirectory() as td:
            env = dict(os.environ, PYTHONPYCACHEPREFIX=td)
            result = subprocess.run(["/usr/bin/python3", "-E", "-s", "-B", "-m", "py_compile", str(PACKET)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(hashlib.sha256(PACKET.read_bytes()).hexdigest()), 64)

if __name__ == "__main__": unittest.main()
