"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic custody tests: temporary journal, mocked root metadata and pidfd calls.
"""
import json
import os
import socket
import struct
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

base=Path(__file__).parent.parent
sys.path.append(str(base/'pidfd-compat-expert-1'))
sys.path.append(str(base/'adapter-readiness-expert-1'))
import adapter
import compositor
import pidfd_compat
import pidfd_custody
import test_pidfd_self as selfcheck


class FakeSocket:
    family=socket.AF_UNIX
    def getsockopt(self,level,option,*args):
        if option==socket.SO_TYPE:return socket.SOCK_STREAM
        return struct.pack('3i',os.getppid(),0,1000)
    def close(self):pass


def fake_root_stat(st):
    return types.SimpleNamespace(st_mode=st.st_mode,st_uid=0,st_nlink=st.st_nlink,
                                 st_dev=st.st_dev,st_ino=st.st_ino)


class CustodyCases(unittest.TestCase):
    def test_postopen_error_is_journaled_and_owned_before_exception(self):
        with tempfile.TemporaryDirectory() as path:
            name=os.path.join(path,'journal');journal=os.open(name,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL,0o600)
            try:
                st=os.fstat(journal);real_fstat=os.fstat
                def bound(fd):return fake_root_stat(st) if fd==journal else real_fstat(fd)
                with patch.object(pidfd_custody.os,'fstat',side_effect=bound):
                    record=pidfd_custody.PidfdCustodyRecord(journal,'a'*64)
                    error=pidfd_compat.PidfdVerificationError(91,'synthetic verification')
                    with patch.object(adapter.os,'dup',return_value=17),\
                         patch.object(adapter.socket,'socket',return_value=FakeSocket()),\
                         patch.object(adapter,'load_wire',return_value=object()),\
                         patch.object(adapter,'proc_identity',return_value=(1,'123')) ,\
                         patch.object(pidfd_compat,'open_pidfd',side_effect=error):
                        with self.assertRaises(pidfd_compat.PidfdVerificationError) as raised:
                            adapter.CustodySession(7,record)
                    self.assertIs(raised.exception.custody_record,record)
                    self.assertEqual((record.state,record.fd),('UNKNOWN_RETAINED',91))
                with open(name) as stream:event=json.loads(stream.readline())
                self.assertEqual((event['status'],event['pidfd']),('UNKNOWN_RETAINED',91))
            finally:os.close(journal)

    def test_failed_publication_preserves_fd_and_unknown_record(self):
        with tempfile.TemporaryDirectory() as path:
            name=os.path.join(path,'journal');journal=os.open(name,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL,0o600)
            try:
                st=os.fstat(journal);real_fstat=os.fstat
                with patch.object(pidfd_custody.os,'fstat',side_effect=lambda fd:fake_root_stat(st) if fd==journal else real_fstat(fd)):
                    record=pidfd_custody.PidfdCustodyRecord(journal,'a'*64)
                with patch.object(pidfd_custody.os,'fsync',side_effect=OSError('synthetic fsync')):
                    with self.assertRaises(pidfd_custody.PublicationUnknown) as raised:record.retain_unknown(93,11,'123')
                self.assertIs(raised.exception.record,record)
                self.assertEqual((record.state,record.fd),('UNKNOWN_RETAINED',93))
                with self.assertRaises(RuntimeError):record.retire()
            finally:os.close(journal)

    def test_caller_operation_retains_record_when_exception_is_discarded(self):
        with tempfile.TemporaryDirectory() as path:
            name=os.path.join(path,'journal');journal=os.open(name,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL,0o600)
            try:
                st=os.fstat(journal);real_fstat=os.fstat
                with patch.object(pidfd_custody.os,'fstat',side_effect=lambda fd:fake_root_stat(st) if fd==journal else real_fstat(fd)):
                    operation=compositor.OperationCustody(journal,'a'*64)
                    record=operation.reserve(types.SimpleNamespace(PidfdCustodyRecord=pidfd_custody.PidfdCustodyRecord))
                    record.retain_unknown(94,11,'123');operation.retain_unknown()
                self.assertEqual(operation.state,'UNKNOWN_RETAINED')
                self.assertIs(operation.record,record)
                self.assertIn(operation,compositor._UNKNOWN_OWNERS)
            finally:os.close(journal)

    def test_self_check_closes_only_its_own_error_fd_then_fails(self):
        error=pidfd_compat.PidfdVerificationError(95,'self-check')
        with patch.object(pidfd_compat,'open_pidfd',side_effect=error),patch.object(selfcheck.os,'close') as close:
            with self.assertRaises(pidfd_compat.PidfdVerificationError):selfcheck.main()
        close.assert_called_once_with(95)


if __name__=='__main__':unittest.main()
