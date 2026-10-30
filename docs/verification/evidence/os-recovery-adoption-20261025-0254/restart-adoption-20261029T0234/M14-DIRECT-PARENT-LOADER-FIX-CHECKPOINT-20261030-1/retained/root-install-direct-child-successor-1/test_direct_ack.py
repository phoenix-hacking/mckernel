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

    def test_parent_death_after_ack_does_not_authorize(self):
        with mock.patch.object(issuer.parent_control,'receive',return_value=(dict(self.expected),[])), mock.patch.object(issuer,'_parent_alive',side_effect=EOFError('parent lost')):
            with self.assertRaises(EOFError):self.call()

if __name__=='__main__':unittest.main()
