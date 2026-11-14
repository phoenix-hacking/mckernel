"""Fail-closed source checks for the fresh scratch17 futex packet.

No build, Docker, privileged operation, or guest is performed here.
"""
import hashlib
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs/verification/stability-native-diagnostic-futex-scratch17-execution-packet-20261001-1.md"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Scratch17FutexPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PACKET.read_text(encoding="utf-8")

    def test_packet_is_unreleased_and_fail_closed(self):
        self.assertIn("Status: **NOT_RELEASED**", self.text)
        self.assertIn("module, image, and manifest bindings are currently `UNBOUND`", self.text)
        self.assertIn("separate exact", self.text)
        self.assertIn("privileged execution release", self.text)
        self.assertNotIn("PASS_EXECUTION", self.text)

    def test_target_and_source_hashes_are_exact(self):
        self.assertIn("50b084322610a9326b1b7b528edd4cd73b635632", self.text)
        self.assertIn("d28aaf4fa3df195e7ea36c4fa51b9392bfcb5620", self.text)
        expected = {
            "host-kernel/native-rust/mcctrl_process.rs": "148134730b5fed7f14770eb070529b5227bb6ab790b7199f8800968219dffc70",
            "scripts/tests/fixtures/native-application-return-adapter.rs": "d8b340c6305f1b4ce65f57b3b7e9e573f5b43f1a9e8b2760cb31176e0ce2158b",
            "scripts/application-tests/native_diagnostic.py": "2aa9b0257395624ced3ecb4d9e4d3e9373310a9266653b1d1f3cec9d2c8f9356",
            "scripts/application-tests/native_diagnostic_guest_collector.c": "82825cf128689ba8f8a74d9528c1acffb724a9356a2c6192c67c8abe4a74965e",
            "scripts/tests/test_native_diagnostic_guest_collector.py": "3128e4a4463877c94ed2a6d4ade8be113e507ce28762cd4d5bd42b2ca25b5d2f",
        }
        for relative, digest in expected.items():
            self.assertEqual(sha256(ROOT / relative), digest, relative)
            self.assertIn(digest, self.text)

    def test_fresh_paths_are_distinct_and_not_prior_attempts(self):
        paths = re.findall(r"^\w[^:]+:\s+(/home/holden/mckernel-work/scratch/[^\n]+)$", self.text, re.MULTILINE)
        self.assertEqual(len(paths), 6)
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all("scratch17" in path for path in paths))
        for old in ("1a9f699e18ae309d0cb9205564458ab0", "01d30ee0c82232c5efe4a3d810fe8af7",
                    "ndfutexc81-20261001-2", "native-diagnostic-futex-c81-20261001-4"):
            self.assertNotIn(old, self.text)

    def test_terminal_sampler_and_strict_runtime_contract_are_bound(self):
        self.assertIn("let traced = number == 231 || self.trace();", self.text)
        self.assertIn("exactly one\nterminal delivered syscall with `number=231`", self.text)
        self.assertIn("16 ordered CASE records followed by THREADS and CLONE", self.text)
        self.assertIn("stdout = NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\\n", self.text)
        self.assertIn("exit   = 37", self.text)
        self.assertIn("retirement", self.text)
        self.assertIn("`errno=0`", self.text)
        self.assertIn("process release", self.text)
        self.assertIn("`cleanup_errno=0`", self.text)

    def test_isolation_and_no_retry_contracts_are_present(self):
        for required in (
                "CPUs 2-5", "12 GiB memory", "512 pids", "no network",
                "dropped capabilities", "no-new-privileges", "private QMP",
                "four vCPUs", "8 GiB/two NUMA nodes", "one serialized heavy lease",
                "without retry"):
            self.assertIn(required, self.text)


if __name__ == "__main__":
    unittest.main()
