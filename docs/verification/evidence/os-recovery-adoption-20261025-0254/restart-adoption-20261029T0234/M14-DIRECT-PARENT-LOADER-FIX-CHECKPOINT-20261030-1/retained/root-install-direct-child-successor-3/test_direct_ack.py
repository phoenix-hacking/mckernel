"""Mocked acknowledgement regressions; no process, socket, root or native work."""
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest import mock

spec=importlib.util.spec_from_file_location('direct_entry_fixture',str(pathlib.Path(__file__).with_name('direct_entry.py')))
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
entry.load_for_parent()
issuer=sys.modules['install_issuer']

class Ack(unittest.TestCase):
    def setUp(self):
        self.latch=types.SimpleNamespace(retained=[])
        self.channel=object();self.caps={'boot_ns':1,'mono_ns':1,'utc_ns':1}
        self.expected={'type':'GO_AUTH','nonce':'a'*64,'seq':3,'keeper_pid':42,'keeper_birth':'7',
                       'installer_pid':43,'installer_birth':'8','release_sha256':'b'*64}

    def call(self):issuer._expect_ack(self.channel,self.caps,self.latch,object(),21,'6',self.expected)

    def test_exact_ack_requires_parent_recheck(self):
        with mock.patch.object(issuer.parent_control,'receive',return_value=(dict(self.expected),[])), mock.patch.object(issuer,'_parent_alive') as alive:
            self.call();alive.assert_called_once()

    def test_wrong_nonce_does_not_authorize(self):
        wrong=dict(self.expected,nonce='c'*64)
        with mock.patch.object(issuer.parent_control,'receive',return_value=(wrong,[])), mock.patch.object(issuer,'_parent_alive') as alive:
            with self.assertRaises(ValueError):self.call()
            alive.assert_not_called()

    def test_extra_received_descriptor_does_not_authorize(self):
        with mock.patch.object(issuer.parent_control,'receive',return_value=(dict(self.expected),[11])), mock.patch.object(issuer,'_parent_alive') as alive:
            with self.assertRaises(ValueError):self.call()
            alive.assert_not_called()

    def test_float_sequence_does_not_alias_integer(self):
        wrong=dict(self.expected,seq=3.0)
        with mock.patch.object(issuer.parent_control,'receive',return_value=(wrong,[])), mock.patch.object(issuer,'_parent_alive') as alive:
            with self.assertRaises(ValueError):self.call()
            alive.assert_not_called()

    def test_ready_observes_installer_terminal(self):
        class Poll:
            def register(self,*args):pass
            def poll(self,*args):return [(22,issuer.select.POLLIN)]
        channel=types.SimpleNamespace(fileno=lambda:33)
        with mock.patch.object(issuer.fcntl,'fcntl',return_value=0), mock.patch.object(issuer.select,'poll',return_value=Poll()), mock.patch.object(issuer.parent_control,'remaining',return_value=1000000000):
            with self.assertRaisesRegex(EOFError,'installer terminal before READY'):
                issuer._read_ready(21,22,channel,self.caps)

    def test_unpinned_child_remains_unknown_without_signal(self):
        record=types.SimpleNamespace(pid=43,pidfd=None)
        with mock.patch.object(issuer.pidfd_compat,'send_signal') as send:
            self.assertIs(issuer._stop_unhanded(record,self.caps,1000),False)
            send.assert_not_called()

    def test_actual_pidfd_verification_error_retains_raw_without_signal(self):
        fork=sys.modules['deferred_fork'];ownership=sys.modules['ownership_latch']
        latch=ownership.CustodyLatch('HELD');record=latch.reserve_child('installer')
        guard=fork.DeferredFork();guard.entered=True
        failure=issuer.pidfd_compat.PidfdVerificationError(88,'fixture verification failure')
        with mock.patch.object(fork.signal,'sigpending',return_value=set()), mock.patch.object(fork.os,'fork',return_value=4321), mock.patch.object(fork.pidfd_compat,'open_pidfd',side_effect=failure):
            with self.assertRaises(issuer.pidfd_compat.PidfdVerificationError):
                guard.fork_and_pin(record,lambda:None)
        self.assertEqual(record.pid,4321);self.assertEqual(record.pidfd,88)
        self.assertIsNone(record.birth);self.assertEqual(record.status,'UNKNOWN_RETAINED')
        self.assertIn(record,latch.retained)
        with mock.patch.object(issuer.pidfd_compat,'send_signal') as send, mock.patch.object(issuer.os,'waitpid') as wait:
            self.assertIs(issuer._stop_unhanded(record,self.caps,1000),False)
            send.assert_not_called();wait.assert_not_called()

    def test_verified_record_can_be_stopped_and_directly_joined(self):
        ownership=sys.modules['ownership_latch'];latch=ownership.CustodyLatch('HELD')
        record=latch.reserve_child('installer');record.assigned(4321);record.pin_pidfd(88);record.identified('7',88)
        with mock.patch.object(issuer.pidfd_compat,'send_signal') as send, mock.patch.object(issuer.os,'waitpid',return_value=(4321,0)) as wait, mock.patch.object(issuer.time,'clock_gettime_ns',return_value=1), mock.patch.object(issuer.parent_control,'remaining',return_value=100):
            self.assertIs(issuer._stop_unhanded(record,{'boot_ns':100,'mono_ns':100,'utc_ns':100},50),True)
            send.assert_called_once_with(88,issuer.signal.SIGTERM);wait.assert_called_once_with(4321,issuer.os.WNOHANG)

    def test_parent_death_after_ack_does_not_authorize(self):
        with mock.patch.object(issuer.parent_control,'receive',return_value=(dict(self.expected),[])), mock.patch.object(issuer,'_parent_alive',side_effect=EOFError('parent lost')):
            with self.assertRaises(EOFError):self.call()

if __name__=='__main__':unittest.main()
