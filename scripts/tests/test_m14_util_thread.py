"""Execute the complete actual Rust UTI body with real ABI types in hosted CI.

These focused HOST fixtures observe allocation, argument domains, synchronous
borrows, refill-before-free and every terminal/error branch. Test providers are
explicit doubles. They prove neither a real host ACK/drain contract nor final
production linkage/native behavior. Do not invoke this module without admission.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.tests.test_m14_f03_wait_results import function

ROOT = Path(__file__).resolve().parents[2]
BODY = ROOT / "kernel/rust/f03_util_thread.rs"
PROVIDERS = ROOT / "kernel/rust/uti_data_providers.rs"
FIXTURE = ROOT / "scripts/tests/fixtures/f03_util_thread_lifecycle.rs"
PROFILE = (
    "native_linux_irq_work_v6_12", "enable_profile", "enable_perf", "enable_rusage",
    "f03_do_syscall_outer_candidate", "f03_do_exit_supported_candidate",
    "f03_terminate_candidate", "f03_util_thread_candidate",
)


class UtilThreadTests(unittest.TestCase):
    def test_complete_body_abi_and_lifetime_with_both_debug_profiles(self):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        self.assertIsNotNone(compiler, "hosted UTI qualification requires the pinned Rust compiler")
        policy = (ROOT / "kernel/rust/syscall_policy.rs").read_text()
        debug = (ROOT / "kernel/rust/debug.rs").read_text()
        declaration = re.search(r"#\[repr\(C\)\]\npub struct Ddebug \{[^}]+\}", debug)
        self.assertIsNotNone(declaration, "the actual Ddebug ABI declaration must be present")
        text = FIXTURE.read_text()
        for token, value in {
            "@ABI@": str(ROOT / "kernel/rust/abi.rs"),
            "@PROVIDERS@": str(PROVIDERS), "@BODY@": str(BODY),
            "@DDEBUG@": declaration.group(0),
            "@PROXY_RESULT@": "const ERESTARTSYS: CLong = 512;\n" +
                function(policy, "syscall_proxy_dead_result"),
            "@BRIDGE@": function(policy, "syscall_util_thread_bridge"),
        }.items():
            text = text.replace(token, value)
        environment = dict(os.environ, MCKERNEL_DO_SYSCALL_C_FILE="/src/kernel/syscall.c")
        with tempfile.TemporaryDirectory(prefix="m14-util-thread-") as temporary:
            directory = Path(temporary)
            source = directory / "fixture.rs"
            source.write_text(text)
            for flags in ("0", "1"):
                with self.subTest(debug_flags=flags):
                    environment["MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS"] = flags
                    executable = directory / ("fixture-" + flags)
                    command = [compiler, "--edition=2021", "--test", str(source),
                               "-C", "opt-level=1", "-o", str(executable)]
                    for condition in PROFILE:
                        command.extend(["--cfg", condition])
                    result = subprocess.run(command, env=environment, capture_output=True,
                                            text=True, timeout=90)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    result = subprocess.run([str(executable), "--test-threads=1", "--nocapture"],
                                            capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("5 passed; 0 failed", result.stdout)
