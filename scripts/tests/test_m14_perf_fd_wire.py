"""Check the real C perf-FD request payload and provider/error ordering.

The selected executor ignores the six argument slots. Its real request
declaration and the actual helper bodies are used; the observing provider and
addressed map object are HOST fixtures, not a guest lifetime or native witness.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.tests.test_m14_util_wire import extract_definition

ROOT = Path(__file__).resolve().parents[2]


def fixture_source(source):
    header = (ROOT / "kernel/include/syscall.h").read_text()
    declaration = extract_definition(header, "struct syscall_request {", True)
    provider = re.findall(r"typedef long \(\*perf_open_syscall_fn_t\)[^;]+;", source)
    if len(provider) != 1:
        raise ValueError("Expected one real perf syscall provider declaration")
    number = re.search(r"^\s*__NR_perf_event_open = (\d+),$", header, re.M)
    if number is None:
        raise ValueError("Missing real perf syscall number")
    bit = extract_definition(source, "static unsigned long\nperf_event_bit_result(int index)")
    body = extract_definition(source, "SYSCALL_POLICY_HELPER_SCOPE long\nperf_event_open_linux_fd_body_result(")
    fixture = (Path(__file__).parent / "fixtures/m14_perf_fd_wire.c.in").read_text()
    return (fixture.replace("@REAL_DECLARATION@", declaration)
            .replace("@REAL_PROVIDER_TYPE@", provider[0])
            .replace("@REAL_NUMBER@", number.group(1))
            .replace("@ACTUAL_BIT_HELPER@", bit)
            .replace("@ACTUAL_FD_HELPER@", body))


class PerfFdWireTest(unittest.TestCase):
    def test_payload_identity_errors_and_counter_publication(self):
        compiler = shutil.which("cc")
        self.assertIsNotNone(compiler, "HOST C compiler is required")
        source = fixture_source((ROOT / "kernel/syscall.c").read_text())
        with tempfile.TemporaryDirectory(prefix="m14-perf-fd-wire-") as temp:
            path = Path(temp)
            (path / "perf.c").write_text(source)
            subprocess.run([compiler, "-std=gnu11", "-O2", "-g0", "-Wall", "-Wextra", "-Werror",
                            str(path / "perf.c"), "-o", str(path / "perf")],
                           check=True, capture_output=True, text=True, timeout=30)
            result = subprocess.run([str(path / "perf")], check=True,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(json.loads(result.stdout),
                             {"cases": 12, "wire_errors": 0, "other_errors": 0})


if __name__ == "__main__":
    unittest.main()
