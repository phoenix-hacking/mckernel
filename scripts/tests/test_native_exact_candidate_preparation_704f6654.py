"""Pure source-contract checks for the fresh exact-candidate preparation packet.

This test reads bytes only; it never imports or executes packet code and never
creates candidate, scratch, build, lease, or guest state.
"""

import hashlib
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "docs/verification/evidence"
PACKET = EVIDENCE / "native-exact-candidate-preparation-704f6654-1.sh"
OLD_PACKET = EVIDENCE / "native-exact-candidate-preparation-67589154-1.sh"
SOURCE_SHA = "704f6654fe95819f7dfd0e4d3665dc44fab63561"
IHK_SHA = "3114d9e7101ad52030eb3effa849a5c108972a1f"
OWNER_SHA = "a8c4c9fc61fab312e3a6e48e93b417453ec12e6543d6adbb7038933f92e79155"
FRESH = "704f6654-1"
OLD = "67589154-1"


class PreparationPacketContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = PACKET.read_text(encoding="utf-8")
        cls.old = OLD_PACKET.read_text(encoding="utf-8")

    def test_normalizes_exactly_to_reviewed_packet(self):
        normalized = self.packet.replace(SOURCE_SHA, "675891545c881b8d625256ade56fe66ac69fe794")
        normalized = normalized.replace(FRESH, OLD)
        self.assertEqual(normalized, self.old)

    def test_fresh_identity_and_exact_bindings(self):
        self.assertEqual(PACKET.name, "native-exact-candidate-preparation-704f6654-1.sh")
        self.assertNotIn(OLD, self.packet)
        self.assertEqual(len(re.findall(re.escape(FRESH), self.packet)), 9)
        self.assertIn(f"readonly SHA={SOURCE_SHA}", self.packet)
        self.assertIn(f"readonly IHK_SHA={IHK_SHA}", self.packet)
        self.assertIn(f"readonly OWNER_SHA={OWNER_SHA}", self.packet)
        for digest in (
            "b68a8b5d18a6642ef0043b791984e7a4ea2503a61b8d9153a781827a2277a10a",
            "28112e13a9932796080d8183e66e493b1bf0655631413b42775af865798c1d3f",
            "1e522a60a265cbd54f50f8856f2c1a8b2f140bd11e655d875f6db431f08a962b",
            "4fe5b7717a7ddc8694edaecc63d07f97a56460f8e692d3ebe2d682024dadbe8a",
            "079482060e5d0b461d15a5d1ffeb7f5d96719d70b877125665df8df7c4bcd7f1",
            "18225919a44e2c07e87a66711c8d1c9483d10e15da91fa5d7fcb7339ff888172",
        ):
            self.assertIn(digest, self.packet)

    def test_preparation_only_contract_and_paths(self):
        for token in ("preparation-only", "PASS_PREPARATION_VALIDATE_ONLY",
                      "validate()", "--self-test", "umask 0022"):
            self.assertIn(token, self.packet)
        self.assertNotIn("docker run", self.packet)
        self.assertNotIn("docker build", self.packet)
        self.assertNotIn("sudo", self.packet)
        self.assertNotIn("qemu-system", self.packet)
        self.assertNotIn("/work/", self.packet)
        self.assertRegex(self.packet, r"readonly -a TARGETS=\(\"\$C\" \"\$B\" \"\$ME\" \"\$LOG\" \"\$M\" \"\$R\" \"\$O\" \"\$E\" \"\$LEASE\"\)")
        self.assertIn("readonly LEASE=", self.packet)

    def test_packet_digest_and_bash_syntax_without_running_it(self):
        self.assertRegex(hashlib.sha256(PACKET.read_bytes()).hexdigest(), r"^[0-9a-f]{64}$")
        result = subprocess.run(["/usr/bin/bash", "-n", str(PACKET)],
                                check=False, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_py_compile_uses_temporary_output_only(self):
        with tempfile.TemporaryDirectory() as raw:
            result = subprocess.run(
                ["/usr/bin/python3", "-B", "-m", "py_compile", str(Path(__file__))],
                check=False, capture_output=True, text=True,
                env={"PYTHONPYCACHEPREFIX": raw},
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
