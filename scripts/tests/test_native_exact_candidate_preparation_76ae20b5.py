"""Contract checks for the 76ae20b5 candidate preparation packet.

These checks are source-only: they never execute preparation, Docker, a build,
or a guest, and they never consume the dirty nested IHK checkout.
"""

import hashlib
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
PACKET = ROOT / "docs/verification/evidence/native-exact-candidate-preparation-76ae20b5-1.sh"
OVERLAY = ROOT / "host-kernel/exact-build/ihk-clear-host-pte-overlay.patch"
SOURCE_SHA = "76ae20b523f57dee8e0fb1fb834caf5443f9f671"
IHK_SHA = "3114d9e7101ad52030eb3effa849a5c108972a1f"
OVERLAY_SHA = "cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7"


class PreparationPacketContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = PACKET.read_text(encoding="utf-8")
        cls.overlay = OVERLAY.read_bytes()

    def test_exact_fresh_bindings(self):
        self.assertEqual(hashlib.sha256(self.overlay).hexdigest(), OVERLAY_SHA)
        self.assertIn(f"readonly SHA={SOURCE_SHA}", self.packet)
        self.assertIn(f"readonly IHK_SHA={IHK_SHA}", self.packet)
        self.assertIn(f"readonly OVERLAY_SHA={OVERLAY_SHA}", self.packet)
        self.assertIn("readonly OVERLAY_BASE_SHA=" + IHK_SHA, self.packet)
        self.assertIn("readonly OVERLAY_RESULT_SHA=21a0d1eb1705c3ee597aed41358ba4c0a92d5f8c", self.packet)
        self.assertNotIn("f5d8d914", self.packet)
        self.assertRegex(self.packet, r"mckernel-exact-candidate-76ae20b5-1")
        self.assertIn("readonly MANIFEST_SHA=9723cec5c36ad77e90d7619f1ad9fae3e193f1b92a9b152193f2c223b3453b38", self.packet)
        self.assertIn("readonly OFFLINE_SHA=9a51ad43e5fc86700eed9e6cd60522f18f50520eb9455a46d185d0982efbc1cd", self.packet)

    def test_overlay_is_explicitly_checked_and_carried(self):
        for token in ("IHK_OVERLAY_APPLY_CHECK PASS", "git\", \"-C\", root, \"apply\", \"--check\"",
                      "ihk_overlay_path", "ihk_overlay_sha256", "ihk_overlay_base_sha",
                      "ihk_overlay_result_sha"):
            self.assertIn(token, self.packet)
        self.assertIn('OVERLAY_BASE_SHA', self.packet)
        self.assertIn('OVERLAY_RESULT_SHA', self.packet)
        self.assertIn("test ! -e \"$LEASE\"", self.packet)

    def test_preparation_only_and_no_dirty_checkout_consumption(self):
        for token in ("preparation-only", "PASS_PREPARATION_VALIDATE_ONLY", "validate()",
                      "--self-test", "EXTERNAL_PREFLIGHT_REQUIRED"):
            self.assertIn(token, self.packet)
        for forbidden in ("docker run", "docker build", "sudo", "qemu-system", "git -C ihk checkout"):
            self.assertNotIn(forbidden, self.packet)
        self.assertIn("21a0d1eb1705c3ee597aed41358ba4c0a92d5f8c", self.packet)

    def test_shell_syntax_and_digest(self):
        self.assertRegex(hashlib.sha256(PACKET.read_bytes()).hexdigest(), r"^[0-9a-f]{64}$")
        result = subprocess.run(["/usr/bin/bash", "-n", str(PACKET)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
