"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mocked wrapper cases: no real pidfd syscall, signal or child.
"""
import ctypes
import errno
import fcntl
import unittest
from unittest.mock import Mock,patch
import pidfd_compat as p


class PidfdCases(unittest.TestCase):
    def test_typed_x86_fallback_and_cloexec(self):
        call=Mock(return_value=37)
        with patch.object(p,'_native_open',return_value=None),patch.object(p,'_syscall',return_value=call),\
             patch.object(p.fcntl,'fcntl',side_effect=[fcntl.FD_CLOEXEC,0]):
            self.assertEqual(p.open_pidfd(123),37)
        args=call.call_args.args
        self.assertEqual([x.value for x in args],[434,123,0])
        self.assertIsInstance(args[0],ctypes.c_long)
        self.assertIsInstance(args[1],ctypes.c_int)
        self.assertIsInstance(args[2],ctypes.c_uint)

    def test_requested_nonblocking_is_verified(self):
        with patch.object(p,'_native_open',return_value=lambda pid,flags:40),\
             patch.object(p.fcntl,'fcntl',side_effect=[fcntl.FD_CLOEXEC,p.os.O_NONBLOCK]):
            self.assertEqual(p.open_pidfd(12,p.os.O_NONBLOCK),40)
        with patch.object(p,'_native_open',return_value=lambda pid,flags:41),\
             patch.object(p.fcntl,'fcntl',side_effect=[fcntl.FD_CLOEXEC,0]):
            with self.assertRaises(p.PidfdVerificationError) as got:p.open_pidfd(12,p.os.O_NONBLOCK)
        self.assertEqual(got.exception.fd,41)

    def test_fallback_libc_signature_is_explicit(self):
        function=Mock();lib=type('Library',(),{'syscall':function})()
        with patch.object(p,'fallback_supported',return_value=True),patch.object(p.ctypes,'CDLL',return_value=lib):
            self.assertIs(p._syscall(),function)
        self.assertEqual(function.argtypes,[ctypes.c_long])
        self.assertIs(function.restype,ctypes.c_long)

    def test_fallback_errno_propagates(self):
        def call(*args):ctypes.set_errno(errno.EACCES);return -1
        with patch.object(p,'_native_open',return_value=None),patch.object(p,'_syscall',return_value=call):
            with self.assertRaises(OSError) as got:p.open_pidfd(12)
        self.assertEqual(got.exception.errno,errno.EACCES)

    def test_new_fd_retained_on_cloexec_failure(self):
        with patch.object(p,'_native_open',return_value=lambda pid,flags:39),patch.object(p.fcntl,'fcntl',side_effect=[0,0]):
            with self.assertRaises(p.PidfdVerificationError) as got:p.open_pidfd(12)
        self.assertEqual(got.exception.fd,39)

    def test_signal_zero_uses_pidfd_and_typed_syscall(self):
        call=Mock(return_value=0)
        with patch.object(p,'_native_signal',return_value=None),patch.object(p,'_syscall',return_value=call):
            self.assertIsNone(p.send_signal(8,0))
        args=call.call_args.args
        self.assertEqual([x.value for x in args],[424,8,0,None,0])
        self.assertIsInstance(args[3],ctypes.c_void_p)

    def test_unsupported_fallback_never_opens_libc(self):
        with patch.object(p,'fallback_supported',return_value=False),patch.object(p.ctypes,'CDLL') as cdll:
            with self.assertRaises(p.UnsupportedRuntime):p._syscall()
            cdll.assert_not_called()

    def test_waitstatus_terminal_only(self):
        self.assertEqual(p.waitstatus_exitcode(42<<8),42)
        self.assertEqual(p.waitstatus_exitcode(15),-15)
        with self.assertRaises(ValueError):p.waitstatus_exitcode(0x7f)


if __name__=='__main__':unittest.main()
