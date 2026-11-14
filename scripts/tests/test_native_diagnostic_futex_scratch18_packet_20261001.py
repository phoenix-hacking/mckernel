"""Source-only fail-closed checks for the future scratch18 futex packet.

No build, Docker, privilege, network, or guest operation is performed.
"""
import hashlib
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs/verification/stability-native-diagnostic-futex-scratch18-execution-packet-20261001-1.md"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Scratch18FutexPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PACKET.read_text(encoding="utf-8")

    def test_unreleased_unbound_and_privileged_release_required(self):
        for value in ("Status: **NOT_RELEASED**", "**UNBOUND**", "independent privileged reviewer",
                      "one-shot release", "No launch is permitted", "without retry"):
            self.assertIn(value, self.text)
        self.assertNotIn("PASS_EXECUTION", self.text)
        self.assertNotIn("RELEASED", self.text.replace("NOT_RELEASED", ""))

    def test_exact_source_oracle_bindings(self):
        self.assertIn("50b084322610a9326b1b7b528edd4cd73b635632", self.text)
        self.assertIn("d28aaf4fa3df195e7ea36c4fa51b9392bfcb5620", self.text)
        expected = {
            "host-kernel/native-rust/mcctrl_process.rs": "148134730b5fed7f14770eb070529b5227bb6ab790b7199f8800968219dffc70",
            "scripts/tests/fixtures/native-application-return-adapter.rs": "d8b340c6305f1b4ce65f57b3b7e9e573f5b43f1a9e8b2760cb31176e0ce2158b",
            "scripts/application-tests/native_diagnostic.py": "2aa9b0257395624ced3ecb4d9e4d3e9373310a9266653b1d1f3cec9d2c8f9356",
            "scripts/application-tests/native_diagnostic_guest_collector.c": "82825cf128689ba8f8a74d9528c1acffb724a9356a2c6192c67c8abe4a74965e",
            "scripts/tests/test_native_diagnostic_guest_collector.py": "3128e4a4463877c94ed2a6d4ade8be113e507ce28762cd4d5bd42b2ca25b5d2f",
        }
        for relative, expected_hash in expected.items():
            self.assertEqual(digest(ROOT / relative), expected_hash, relative)
            self.assertIn(expected_hash, self.text)

    def test_all_runtime_identities_are_fresh_scratch18(self):
        paths = re.findall(r"^\w[^:]+:\s+(/home/holden/mckernel-work/scratch/[^\n]+)$", self.text, re.MULTILINE)
        self.assertGreaterEqual(len(paths), 10)
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all("scratch18" in path for path in paths))
        self.assertEqual(self.text.count("7e3c1f9a6b4d2e80f5a1c7d9b3e6f042"), 1)
        for forbidden in ("scratch17", "scratch16", "c81", "ndfutex", "1a9f699e18ae309d0cb9205564458ab0",
                          "01d30ee0c82232c5efe4a3d810fe8af7", "native-diagnostic-futex-c81"):
            self.assertNotIn(forbidden, self.text.lower())

    def test_strict_16_case_output_and_terminal_trace(self):
        cases = ["wait_mismatch", "wait_relative_zero", "wait_relative_10ms",
                 "wait_bitset_expired", "wait_bitset_future", "wait_null_word",
                 "wait_unaligned_word", "timeout_protected", "timeout_cross_page",
                 "timeout_negative_seconds", "timeout_negative_nanoseconds",
                 "timeout_large_nanoseconds", "wait_bitset_zero", "wake_empty",
                 "wake_unmapped_private", "wait_relative_runnable"]
        positions = [self.text.index("`" + case + "`") for case in cases]
        self.assertEqual(positions, sorted(positions))
        for case in cases:
            self.assertIn("`" + case + "`", self.text)
        for required in (
                "let traced = number == 231 || self.trace();",
                "16 ordered CASE records, then THREADS, then CLONE",
                "wait_mismatch`, `wait_relative_zero`, `wait_relative_10ms`",
                "wake_unmapped_private`,", "wait_relative_runnable`.",
                "exactly one terminal delivered syscall", "with `number=231`",
                "matching return and any required route record", "terminal delivery must have no RET",
                "stdout = NATIVE_ULTRA_FUTEX PASS cases=16 threads=2 raw_clone=1\\n",
                "exit   = 37", "retirement `errno=0`", "process release `cleanup_errno=0`"):
            self.assertIn(required, self.text)
        self.assertNotIn("case-01", self.text)
        self.assertNotIn("case-16", self.text)
        self.assertNotIn("Delivered count is exactly 231", self.text)
        self.assertNotIn("at least 16 cases", self.text)
        self.assertNotIn("up to 16 cases", self.text)
        self.assertNotIn("approximately", self.text.lower())

    def test_isolation_bounds_and_diagnostic_only(self):
        for required in ("CPUs 2-5", "12 GiB memory", "512 pids", "no network",
                         "dropped capabilities", "no-new-privileges", "q35 TCG",
                         "four vCPUs", "8 GiB/two NUMA nodes", "private QMP",
                         "at least 16 GiB and 12 GiB", "formal application acceptance",
                         "general futex coverage"):
            self.assertIn(required, self.text)


if __name__ == "__main__":
    unittest.main()
