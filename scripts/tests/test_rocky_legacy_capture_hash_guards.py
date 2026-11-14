#!/usr/bin/env python3
"""Execute the legacy capture hash guards with inert files and real hashing."""

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/rocky-rust-validation.sh"
OVERLAY_SHA256 = (
    "f677c7dde6de2160fd9062fa998cb2c4aa14ba9eafdac8b86b592b78776bcd2e"
)


class RockyLegacyCaptureHashGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="legacy capture hashes-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.preflight = self.root / "preflight.json"
        self.producer = self.root / "inert-producer"
        self.overlay = self.root / "ihk/linux/core/host_driver.c"
        self.overlay.parent.mkdir(parents=True)
        self.preflight.write_bytes(b'{"fixture":"preflight authority"}\n')
        self.producer.write_bytes(b"inert producer fixture, never executed\n")
        self.overlay.write_bytes(b"inert compatibility overlay fixture\n")

        script = SCRIPT.read_text(encoding="utf-8")
        start = "capture_fp0006_legacy_negative_dispatch() {\n"
        stop = '\tstage="$FP0006_PREFLIGHT_DIR/capture-stage"\n'
        self.assertEqual(1, script.count(start))
        self.guard = start + script.split(start, 1)[1].split(stop, 1)[0]
        self.assertEqual(1, script.count(stop))
        self.assertEqual(1, self.guard.count(OVERLAY_SHA256))
        self.assertEqual(1, self.guard.count("[ ! -c /dev/mcd0 ]"))
        # Only fixture identity and the inert character-device check change.
        # The production comparisons, hashing pipelines, and returns execute
        # unchanged, stopping before any producer, ioctl, or capture side effect.
        self.guard = self.guard.replace(
            OVERLAY_SHA256, hashlib.sha256(self.overlay.read_bytes()).hexdigest()
        ).replace("[ ! -c /dev/mcd0 ]", "[ ! -c /dev/null ]")
        self.environment = {
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "ROOT_DIR": str(self.root),
            "FP0006_NEGATIVE_CAPTURE": "1",
            "FP0006_PREFLIGHT_MANIFEST": str(self.preflight),
            "FP0006_PREFLIGHT_MANIFEST_SHA256": hashlib.sha256(
                self.preflight.read_bytes()
            ).hexdigest(),
            "FP0006_PRODUCER_BINARY": str(self.producer),
            "FP0006_PRODUCER_BINARY_SHA256": hashlib.sha256(
                self.producer.read_bytes()
            ).hexdigest(),
        }

    def replay(self):
        return subprocess.run(
            [
                "/bin/bash", "--noprofile", "--norc", "-c",
                "set -euo pipefail\n" + self.guard
                + "printf 'capture-ready\\n'\n}\n"
                + "capture_fp0006_legacy_negative_dispatch\n",
            ],
            env=self.environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10,
        )

    def assert_rejected(self, message):
        result = self.replay()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertEqual("", result.stdout)
        self.assertIn(message, result.stderr)
        self.assertNotIn("missing `]'", result.stderr)
        self.assertNotIn("command not found", result.stderr)

    def test_matching_hashes_reach_capture_without_shell_errors(self):
        result = self.replay()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("capture-ready\n", result.stdout)
        self.assertEqual("", result.stderr)

    def test_changed_preflight_authority_is_rejected(self):
        self.preflight.write_bytes(b'{"fixture":"changed authority"}\n')
        self.assert_rejected("preflight authority or producer changed")

    def test_changed_producer_is_rejected(self):
        self.producer.write_bytes(b"changed inert producer\n")
        self.assert_rejected("preflight authority or producer changed")

    def test_changed_overlay_is_rejected(self):
        self.overlay.write_bytes(b"changed inert compatibility overlay\n")
        self.assert_rejected("compatibility-overlay observation digest differs")

    def test_missing_hash_input_is_rejected_before_capture(self):
        for path, message in (
            (self.preflight, "preflight authority or producer changed"),
            (self.producer, "preflight authority or producer changed"),
            (self.overlay, None),
        ):
            with self.subTest(missing=path.name):
                contents = path.read_bytes()
                path.unlink()
                try:
                    if message is None:
                        # The overlay assignment is outside an if condition:
                        # pipefail must stop execution when hashing fails.
                        result = self.replay()
                        self.assertNotEqual(0, result.returncode)
                        self.assertEqual("", result.stdout)
                        self.assertIn("No such file or directory", result.stderr)
                    else:
                        self.assert_rejected(message)
                finally:
                    path.write_bytes(contents)


if __name__ == "__main__":
    unittest.main()
