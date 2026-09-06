"""Execute the x86_64 probe against own-child syscall simulation only.

This tests the freestanding probe's decisions and guards.  No device node or
kernel module is opened, created, or loaded, and these tests provide no native
module runtime evidence or tracker credit.  Linux memory protection is real:
process_vm_writev copies into the traced child's actual mapped address space.
"""

import ctypes
import errno
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


class _Registers(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "r15", "r14", "r13", "r12", "rbp", "rbx", "r11", "r10", "r9", "r8",
        "rax", "rcx", "rdx", "rsi", "rdi", "orig_rax", "rip", "cs", "eflags",
        "rsp", "ss", "fs_base", "gs_base", "ds", "es", "fs", "gs",
    )]


class _Iovec(ctypes.Structure):
    _fields_ = [("base", ctypes.c_void_p), ("length", ctypes.c_size_t)]


class NativeRustProbeSyscallSimulationTests(unittest.TestCase):
    """Only the fresh static x86_64 assembly executable runs under this tracer."""

    @classmethod
    def setUpClass(cls):
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise unittest.SkipTest("own-child syscall simulation requires Linux x86_64")
        assembler, linker = shutil.which("as"), shutil.which("ld")
        if assembler is None or linker is None:
            raise unittest.SkipTest("GNU assembler/linker unavailable for fresh probe build")
        cls.libc = ctypes.CDLL(None, use_errno=True)
        for name in ("ptrace", "process_vm_readv", "process_vm_writev"):
            if not hasattr(cls.libc, name):
                raise unittest.SkipTest("own-child simulation API unavailable: " + name)
        cls.libc.ptrace.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
        cls.libc.ptrace.restype = ctypes.c_long
        for name in ("process_vm_readv", "process_vm_writev"):
            function = getattr(cls.libc, name)
            function.argtypes = [ctypes.c_int, ctypes.POINTER(_Iovec), ctypes.c_ulong,
                                ctypes.POINTER(_Iovec), ctypes.c_ulong, ctypes.c_ulong]
            function.restype = ctypes.c_ssize_t
        cls.temporary = tempfile.TemporaryDirectory(prefix="native-probe-syscall-simulation-")
        cls.addClassCleanup(cls.temporary.cleanup)
        root = Path(__file__).resolve().parents[2]
        source = root / "scripts/native-rust-runtime-mcd0-ioctl-x86_64.S"
        obj = Path(cls.temporary.name) / "mcd0-probe.o"
        cls.executable = str(Path(cls.temporary.name) / "mcd0-probe")
        commands = (
            [assembler, "--64", "-mx86-used-note=no", str(source), "-o", str(obj)],
            [linker, "-m", "elf_x86_64", "-nostdlib", "-static", "-s", "-z",
             "noexecstack", "-z", "separate-code", "-o", cls.executable, str(obj)],
        )
        for command in commands:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=15, check=False)
            if result.returncode:
                raise AssertionError("fresh probe build failed: " + result.stderr.decode("utf-8", "replace"))

    def _ptrace(self, request, child, data=None):
        ctypes.set_errno(0)
        result = self.libc.ptrace(request, child, None, data)
        if result == -1:
            code = ctypes.get_errno()
            if code in (errno.EPERM, errno.ENOSYS):
                raise unittest.SkipTest("own-child ptrace unavailable: " + os.strerror(code))
            raise OSError(code, os.strerror(code))
        return result

    def _read_path(self, child, address):
        buffer = ctypes.create_string_buffer(10)
        local = _Iovec(ctypes.addressof(buffer), 10)
        remote = _Iovec(address, 10)
        count = self.libc.process_vm_readv(child, ctypes.byref(local), 1,
                                         ctypes.byref(remote), 1, 0)
        if count < 0 and ctypes.get_errno() in (errno.EPERM, errno.ENOSYS):
            raise unittest.SkipTest("own-child process_vm_readv unavailable")
        self.assertEqual(10, count, "cannot read traced probe's fixed device path")
        return buffer.raw

    def _copy_payload(self, child, address, payload):
        buffer = ctypes.create_string_buffer(payload, len(payload))
        local = _Iovec(ctypes.addressof(buffer), len(payload))
        remote = _Iovec(address, len(payload))
        ctypes.set_errno(0)
        copied = self.libc.process_vm_writev(child, ctypes.byref(local), 1,
                                           ctypes.byref(remote), 1, 0)
        code = ctypes.get_errno() if copied < 0 else 0
        if code in (errno.EPERM, errno.ENOSYS):
            raise unittest.SkipTest("own-child process_vm_writev unavailable")
        if copied < 0:
            self.assertEqual(errno.EFAULT, code)
        return copied, code

    def _simulate(self, identity, mutation=None):
        child = os.fork()
        if child == 0:
            # The harness never attaches to another process: the new child
            # explicitly opts in, then execs only the freshly built probe.
            if self.libc.ptrace(0, 0, None, None) == -1:  # PTRACE_TRACEME
                os._exit(125)
            try:
                os.execv(self.executable, [self.executable, identity])
            except BaseException:
                os._exit(126)
        reaped = False
        deadline = time.monotonic() + 5
        events = []

        def wait_status():
            while time.monotonic() < deadline:
                waited, status = os.waitpid(child, os.WNOHANG)
                if waited == child:
                    return status
                time.sleep(0.001)
            raise AssertionError("own-child probe simulation exceeded five seconds")

        try:
            status = wait_status()
            if os.WIFEXITED(status):
                reaped = True
                if os.WEXITSTATUS(status) == 125:
                    raise unittest.SkipTest("own-child PTRACE_TRACEME unavailable")
                self.fail("fresh probe failed before its exec trap")
            self.assertTrue(os.WIFSTOPPED(status))
            self.assertEqual(signal.SIGTRAP, os.WSTOPSIG(status))
            # TRACESYSGOOD distinguishes syscall stops; EXITKILL contains the
            # child if the test process itself unexpectedly terminates.
            self._ptrace(0x4200, child, ctypes.c_void_p(1 | (1 << 20)))
            entering = True
            override = None
            synthetic_fd = 900
            get_count = 0
            for unused in range(128):
                self._ptrace(24, child)  # PTRACE_SYSCALL
                status = wait_status()
                if os.WIFEXITED(status):
                    reaped = True
                    return os.WEXITSTATUS(status), events
                if os.WIFSIGNALED(status):
                    reaped = True
                    self.fail("probe terminated by signal {0}".format(os.WTERMSIG(status)))
                self.assertTrue(os.WIFSTOPPED(status))
                self.assertEqual(signal.SIGTRAP | 0x80, os.WSTOPSIG(status))
                registers = _Registers()
                self._ptrace(12, child, ctypes.byref(registers))  # PTRACE_GETREGS
                if entering:
                    override = None
                    number = registers.orig_rax
                    if number == 2:  # open: never dispatch to a real device
                        self.assertEqual(b"/dev/mcd0\0", self._read_path(child, registers.rdi))
                        self.assertEqual(2, registers.rsi)
                        override = -errno.EACCES if mutation == "open_errno" else synthetic_fd
                        events.append(("open", override))
                    elif number == 16:  # ioctl on the synthetic descriptor
                        self.assertEqual(synthetic_fd, registers.rdi)
                        if registers.rsi == 0x11290b:
                            get_count += 1
                            payload = identity.encode("ascii") + b"\0"
                            if get_count == 1:
                                if mutation == "missing_nul":
                                    payload = payload[:-1]
                                elif mutation == "wrong_bytes":
                                    payload = bytes([payload[0] ^ 0x20]) + payload[1:]
                                elif mutation == "overrun":
                                    payload += b"\0"
                            copied, code = self._copy_payload(child, registers.rdx, payload)
                            override = 0 if copied == len(payload) else -errno.EFAULT
                            if copied != len(payload) and mutation == "fault_errno":
                                override = -errno.EINVAL
                            if get_count == 1 and mutation == "success_return":
                                override = 1
                            events.append(("get_buildid", copied, code, override))
                        else:
                            self.assertEqual(0xdeadbeef, registers.rsi)
                            override = -errno.ENOTTY if mutation == "unknown_errno" else -errno.EINVAL
                            events.append(("unknown", override))
                    elif number == 3:  # close synthetic fd, never a real fd
                        self.assertEqual(synthetic_fd, registers.rdi)
                        override = -errno.EBADF if mutation == "close_errno" else 0
                        events.append(("close", override))
                    else:
                        self.assertIn(number, (9, 10, 11, 60), "unexpected probe syscall")
                        events.append(("real", number))
                    if override is not None:
                        registers.orig_rax = (1 << 64) - 1
                        self._ptrace(13, child, ctypes.byref(registers))  # PTRACE_SETREGS
                elif override is not None:
                    registers.rax = override & ((1 << 64) - 1)
                    self._ptrace(13, child, ctypes.byref(registers))
                entering = not entering
            self.fail("probe exceeded bounded syscall stop budget")
        finally:
            if not reaped:
                try:
                    os.kill(child, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                os.waitpid(child, 0)

    def test_simulated_success_checks_bytes_and_real_user_memory_protections(self):
        for identity in ("abcd", "v1.2-rc_3+test", "a" * 40):
            with self.subTest(identity=identity):
                code, events = self._simulate(identity)
                self.assertEqual(0, code)
                gets = [event for event in events if event[0] == "get_buildid"]
                self.assertEqual(5, len(gets))
                self.assertEqual(("get_buildid", len(identity) + 1, 0, 0), gets[0])
                self.assertEqual([("get_buildid", -1, errno.EFAULT, -errno.EFAULT)] * 3, gets[1:4])
                self.assertIn(gets[4][1], (-1, 1))
                self.assertEqual(-errno.EFAULT, gets[4][3])
                self.assertEqual(2, len([event for event in events if event[0] == "unknown"]))
                self.assertEqual(1, len([event for event in events if event[0] == "close"]))
                self.assertEqual([9, 10, 10, 11, 60], [event[1] for event in events if event[0] == "real"])

    def test_simulated_bad_copy_or_return_values_fail_the_executed_probe(self):
        for mutation in ("missing_nul", "wrong_bytes", "overrun", "success_return",
                         "fault_errno", "unknown_errno"):
            with self.subTest(mutation=mutation):
                code, events = self._simulate("a1b2c3d", mutation)
                self.assertEqual(11, code)
                self.assertEqual(1, len([event for event in events if event[0] == "close"]))

    def test_simulated_open_and_close_failures_remain_distinct(self):
        for mutation, expected in (("open_errno", 10), ("close_errno", 12)):
            with self.subTest(mutation=mutation):
                code, events = self._simulate("a1b2c3d", mutation)
                self.assertEqual(expected, code)
                if mutation == "open_errno":
                    self.assertFalse(any(event[0] in ("get_buildid", "close") for event in events))


if __name__ == "__main__":
    unittest.main()
