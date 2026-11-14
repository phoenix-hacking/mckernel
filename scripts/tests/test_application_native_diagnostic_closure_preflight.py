"""Synthetic, unprivileged closure tests; never execute retained application bytes."""
import importlib.util
import errno
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "application-tests/native_diagnostic_closure_preflight.py"
spec = importlib.util.spec_from_file_location("closure_preflight", MODULE)
preflight = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = preflight
spec.loader.exec_module(preflight)

CHILD = '''#!/usr/bin/python3
import os, sys, time, subprocess
a = sys.argv[1:]
assert a[:2] == ['--inhibit-cache', '--library-path']
assert a[2].startswith('/proc/self/fd/') and a[3:5] == ['--argv0', 'app']
assert a[5].startswith('/proc/self/fd/') and a[6:] == ['A', '', 'B'], repr(a)
assert open(a[5], 'rb').read() == b'synthetic payload'
assert open(a[2] + '/libc.so.6', 'rb').read() == b'synthetic libc'
assert {k:v for k,v in os.environ.items() if k != 'LC_CTYPE'} == {'PATH': '/usr/bin:/bin', 'COKERNEL_PATH': '/apps'}
assert os.getcwd().endswith('/case/work')
assert sys.stdin.read() == ''
if MODE == 'timeout':
    p = subprocess.Popen(['/usr/bin/python3', '-c', 'import time; time.sleep(30)'])
    open(MARKER, 'w').write(str(p.pid))
    time.sleep(30)
if MODE == 'survivor':
    p = subprocess.Popen(['/usr/bin/python3', '-c', 'import time; time.sleep(30)'])
    open(MARKER, 'w').write(str(p.pid))
if MODE == 'flood':
    sys.stdout.buffer.write(b'X' * 200000)
else:
    sys.stdout.buffer.write(bytes.fromhex(OUTPUT))
    if MODE == 'extra-output':
        sys.stdout.buffer.write(b'UNEXPECTED TRAILING BYTES')
sys.stdout.flush()
sys.exit(7 if MODE == 'wrong-exit' else 0)
'''


class ClosurePreflightTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.parent = self.base / "out"
        self.parent.mkdir(mode=0o700)
        self.payload = self.base / "payload"
        self.payload.write_bytes(b"synthetic payload")
        self.loader = self.base / "loader"
        self.libc = self.base / "libc.so.6"
        self.libc.write_bytes(b"synthetic libc")
        self.source = self.base / "source.c"
        self.source.write_bytes(b"synthetic source")
        self.oracle = self.base / "oracle.json"
        self.oracle.write_text(json.dumps({"stdout": {"kind": "exact-bytes", "hex": preflight.EXPECTED_STDOUT.hex()},
                                          "stderr": {"kind": "exact-bytes", "hex": ""},
                                          "wait_status": {"kind": "exited", "code": 0}}))
        self._child("pass")

    def _child(self, mode):
        script = CHILD.replace("MODE", repr(mode)).replace("OUTPUT", repr(preflight.EXPECTED_STDOUT.hex()))
        script = script.replace("MARKER", repr(str(self.base / "descendant.pid")))
        self.loader.write_text(script)
        self.loader.chmod(0o755)

    def _spec(self):
        paths = {"payload": self.payload, "loader": self.loader, "libc": self.libc,
                 "source": self.source, "oracle": self.oracle}
        expected = {name: {"size": path.stat().st_size, "sha256": preflight._sha(path.read_bytes()),
                           "mode": path.stat().st_mode & 0o7777} for name, path in paths.items()}
        return preflight.Spec(self.payload, self.loader, self.libc, self.source,
                              self.oracle, expected, inspect=False)

    def _run(self, name, **kwargs):
        return preflight.run(self.parent, name, self._spec(), **kwargs)

    def _assert_dead(self):
        pid = int((self.base / "descendant.pid").read_text())
        state = Path(f"/proc/{pid}/stat")
        if state.exists():
            self.assertEqual(state.read_text().split()[2], "Z")

    def test_exact_empty_argv_and_success_record(self):
        result = self._run("pass")
        self.assertEqual(result["status"], "PASS", (self.parent / "pass/stderr.bin").read_text())
        self.assertEqual(result["command"][-3:], ["A", "", "B"])
        self.assertEqual(result["environment"], preflight.ENV)
        self.assertEqual(result["stdout"]["sha256"], "e3ef69c5f8e85e2cdca6bac568664d3b146038ac5523185517595a70364a2884")
        self.assertEqual(json.loads((self.parent / "pass/result.json").read_text()), result)
        self.assertEqual(json.loads((self.parent / "pass/launch-intent.json").read_text())["command"], result["command"])

    def test_wrong_exit(self):
        self._child("wrong-exit")
        result = self._run("wrong-exit")
        self.assertEqual((result["status"], result["returncode"]), ("FAIL", 7))

    def test_timeout_descendant_cleanup(self):
        self._child("timeout")
        result = self._run("timeout", timeout=0.3)
        self.assertTrue(result["timed_out"])
        self.assertTrue(result["process_group_quiescent"])
        self._assert_dead()

    def test_leader_exit_surviving_descendant_cleanup(self):
        self._child("survivor")
        result = self._run("survivor")
        self.assertTrue(result["process_group_quiescent"])
        self._assert_dead()

    def test_stream_flood_bounded(self):
        self._child("flood")
        result = self._run("flood")
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["stream_overflow"])
        self.assertLessEqual((self.parent / "flood/stdout.bin").stat().st_size, preflight.STREAM_LIMIT)

    def test_input_drift_and_fifo_prevent_execution(self):
        frozen = self._spec()
        self.payload.write_bytes(b"changed")
        result = preflight.run(self.parent, "drift", frozen)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("drift", result["first_failure"])
        self.assertFalse((self.parent / "drift/launch-intent.json").exists())
        self.payload.unlink(); os.mkfifo(self.payload)
        result = preflight.run(self.parent, "fifo", frozen)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("not regular", result["first_failure"])

    def test_path_swap_detected(self):
        frozen = self._spec()
        original_stat = os.stat
        def swapped(path, *args, **kwargs):
            if path == "payload" and "dir_fd" in kwargs:
                self.payload.rename(self.base / "old-payload")
                self.payload.write_bytes(b"new payload")
            return original_stat(path, *args, **kwargs)
        with patch.object(preflight.os, "stat", side_effect=swapped):
            result = preflight.run(self.parent, "swap", frozen)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("swapped", result["first_failure"])

    def test_attempt_reuse_symlink_parent_alias_and_replacement(self):
        frozen = self._spec()
        (self.parent / "used").mkdir()
        with self.assertRaises(FileExistsError):
            preflight.run(self.parent, "used", frozen)
        (self.parent / "linked").symlink_to(self.base)
        with self.assertRaises(FileExistsError):
            preflight.run(self.parent, "linked", frozen)
        alias = self.base / "alias"
        alias.symlink_to(self.parent)
        with self.assertRaises(OSError):
            preflight.run(alias, "alias-run", frozen)
        moved = self.base / "out-moved"
        def replace():
            self.parent.rename(moved)
            self.parent.mkdir(mode=0o700)
        result = preflight.run(self.parent, "replaced", frozen, before_spawn=replace)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("replaced", result["first_failure"])
        self.assertTrue((moved / "replaced/launch-intent.json").exists())
        self.assertTrue((moved / "replaced/result.json").exists())

    def test_coordinator_failure_after_intent(self):
        def fail():
            raise RuntimeError("coordinator fault")
        result = self._run("after-intent", before_spawn=fail)
        self.assertEqual(result["status"], "ERROR")
        self.assertIn("coordinator fault", result["first_failure"])
        self.assertTrue((self.parent / "after-intent/launch-intent.json").exists())
        self.assertTrue((self.parent / "after-intent/result.json").exists())

    def test_short_capture_writes_preserve_all_bytes(self):
        original = os.write
        def short(fd, data):
            if os.readlink(f"/proc/self/fd/{fd}").endswith("stdout.bin"):
                return original(fd, data[:7])
            return original(fd, data)
        with patch.object(preflight.os, "write", side_effect=short):
            result = self._run("short")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["captured_bytes"], {"stdout": 91, "stderr": 0})
        self.assertEqual((self.parent / "short/stdout.bin").read_bytes(), preflight.EXPECTED_STDOUT)

    def test_capture_short_write_cannot_hide_trailing_output(self):
        self._child("extra-output")
        original = os.write
        def short(fd, data):
            if os.readlink(f"/proc/self/fd/{fd}").endswith("stdout.bin"):
                return original(fd, data[:91])
            return original(fd, data)
        with patch.object(preflight.os, "write", side_effect=short):
            result = self._run("short-extra")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual((self.parent / "short-extra/stdout.bin").read_bytes(),
                         preflight.EXPECTED_STDOUT + b"UNEXPECTED TRAILING BYTES")
        self.assertEqual(result["captured_bytes"]["stdout"], 116)

    def test_zero_and_enospc_after_oracle_prefix_cannot_pass(self):
        self._child("extra-output")
        original = os.write
        for fault in ("zero", "enospc"):
            with self.subTest(fault=fault):
                def fail(fd, data):
                    if os.readlink(f"/proc/self/fd/{fd}").endswith("stdout.bin"):
                        if os.fstat(fd).st_size >= 91:
                            if fault == "zero":
                                return 0
                            raise OSError(errno.ENOSPC, "injected no space")
                        return original(fd, data[:91])
                    return original(fd, data)
                with patch.object(preflight.os, "write", side_effect=fail):
                    result = self._run(fault)
                self.assertEqual(result["status"], "ERROR")
                self.assertIn("OSError", result["first_failure"])
                self.assertEqual(result["captured_bytes"]["stdout"], 91)
                self.assertEqual((self.parent / fault / "stdout.bin").read_bytes(), preflight.EXPECTED_STDOUT)
                self.assertTrue(result["process_group_quiescent"])
                self.assertEqual(json.loads((self.parent / fault / "result.json").read_text())["status"], "ERROR")

    def test_result_partial_zero_and_enospc_keep_staging_without_final(self):
        original = os.write
        for fault in ("zero", "enospc"):
            with self.subTest(fault=fault):
                def fail(fd, data):
                    if os.readlink(f"/proc/self/fd/{fd}").endswith("result.json.staging"):
                        if os.fstat(fd).st_size:
                            if fault == "zero":
                                return 0
                            raise OSError(errno.ENOSPC, "injected no space")
                        return original(fd, data[:10])
                    return original(fd, data)
                attempt = "publication-" + fault
                with patch.object(preflight.os, "write", side_effect=fail):
                    with self.assertRaises(OSError):
                        self._run(attempt)
                self.assertFalse((self.parent / attempt / "result.json").exists())
                self.assertEqual((self.parent / attempt / "result.json.staging").stat().st_size, 10)

    def test_result_file_and_directory_sync_failures_remove_final(self):
        original = os.fsync
        for fault in ("file", "directory"):
            with self.subTest(fault=fault):
                attempt = "sync-" + fault
                root = self.parent / attempt
                def fail(fd):
                    target = os.readlink(f"/proc/self/fd/{fd}")
                    if ((fault == "file" and target == str(root / "result.json.staging")) or
                            (fault == "directory" and target == str(root) and (root / "result.json").exists())):
                        raise OSError(errno.EIO, "injected sync failure")
                    return original(fd)
                with patch.object(preflight.os, "fsync", side_effect=fail):
                    with self.assertRaisesRegex(OSError, "injected sync failure"):
                        self._run(attempt)
                self.assertFalse((root / "result.json").exists())
                self.assertTrue((root / "result.json.staging").exists())

    def test_result_link_failure_keeps_staging_and_no_final(self):
        original = os.link
        def fail(src, dst, **kwargs):
            if dst == "result.json":
                raise OSError(errno.EIO, "injected link failure")
            return original(src, dst, **kwargs)
        with patch.object(preflight.os, "link", side_effect=fail):
            with self.assertRaisesRegex(OSError, "injected link failure"):
                self._run("link-fail")
        self.assertFalse((self.parent / "link-fail/result.json").exists())
        self.assertTrue((self.parent / "link-fail/result.json.staging").exists())

    def test_existing_result_is_never_replaced(self):
        root = self.parent / "collision"
        def existing():
            (root / "result.json").write_bytes(b"existing evidence")
        with self.assertRaises(FileExistsError):
            self._run("collision", before_spawn=existing)
        self.assertEqual((root / "result.json").read_bytes(), b"existing evidence")
        self.assertTrue((root / "result.json.staging").exists())

    def test_nonfinite_bool_and_out_of_range_timeout_rejected_before_output(self):
        for timeout in (float("nan"), float("inf"), float("-inf"), True, False, 0, -1, 61, "10", None):
            with self.subTest(timeout=timeout):
                with self.assertRaisesRegex(ValueError, "finite"):
                    self._run("bad-timeout", timeout=timeout)
                self.assertFalse((self.parent / "bad-timeout").exists())

    def _elf_outputs(self, payload_provider="libc.so.6", payload_version="GLIBC_2.34",
                     libc_versions="GLIBC_2.34", loader_versions="GLIBC_PRIVATE"):
        return {
            ("/proc/self/fd/10", "-lW"): "[Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]",
            ("/proc/self/fd/10", "-dW"): "(NEEDED) Shared library: [libc.so.6]",
            ("/proc/self/fd/10", "-VW"): f"Version needs section\nFile: {payload_provider} Cnt: 1\nName: {payload_version}",
            ("/proc/self/fd/11", "-dW"): "(NEEDED) Shared library: [ld-linux-x86-64.so.2]",
            ("/proc/self/fd/11", "-VW"): (f"Version definition section\nName: {libc_versions}\n"
                                          "Version needs section\nFile: ld-linux-x86-64.so.2 Cnt: 1\nName: GLIBC_PRIVATE"),
            ("/proc/self/fd/12", "-dW"): "",
            ("/proc/self/fd/12", "-VW"): f"Version definition section\nName: {loader_versions}",
        }

    def test_version_provider_exact_positive_and_mismatches(self):
        for name, params, error in (
                ("valid", {}, None),
                ("missing", {"payload_version": "GLIBC_9.99"}, "unprovided GLIBC versions"),
                ("wrong-provider", {"loader_versions": "GLIBC_2.34", "libc_versions": "GLIBC_2.2.5"},
                 "unprovided GLIBC versions"),
                ("wrong-needed", {"payload_provider": "ld-linux-x86-64.so.2"}, "unexpected version provider"),
                ("missing-loader-private", {"loader_versions": "GLIBC_2.34"}, "unprovided GLIBC versions")):
            with self.subTest(name=name):
                outputs = self._elf_outputs(**params)
                with patch.object(preflight, "_readelf", side_effect=lambda path, option, fds: outputs[path, option]):
                    if error:
                        with self.assertRaisesRegex(ValueError, error):
                            preflight.inspect_elf(10, 11, 12)
                    else:
                        result = preflight.inspect_elf(10, 11, 12)
                        self.assertEqual(result["version_needs"]["payload"], {"libc.so.6": ["GLIBC_2.34"]})


if __name__ == "__main__":
    unittest.main()
