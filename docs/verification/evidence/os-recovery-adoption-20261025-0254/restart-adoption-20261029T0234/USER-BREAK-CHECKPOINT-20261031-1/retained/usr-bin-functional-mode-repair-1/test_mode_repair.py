"""Functional-only synthetic mode repair checks; UNRUN, no real chmod or signals."""
import errno
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('test_usr_bin_repair',HERE/'mode_repair.py')
repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)


class ModeRepair(unittest.TestCase):
    def test_exact_observed_inode_and_mode_required(self):
        row={'path':'/usr/bin','device':66306,'inode':1048578,'uid':0,'gid':0,'mode':0o777,
             'mtime_ns':1793383731386311743,'ctime_ns':1793383731386311743}
        repair.expected_row(2,row)
        for key,value in (('inode',1048579),('device',2),('mode',0o755)):
            with self.assertRaises(ValueError):repair.expected_row(2,dict(row,**{key:value}))
    def test_both_acl_names_must_be_absent(self):
        with mock.patch.object(repair.os,'getxattr',side_effect=OSError(errno.ENODATA,'absent')) as call:
            repair.no_acl(7);self.assertEqual(call.call_count,2)
        with mock.patch.object(repair.os,'getxattr',return_value=b'present'):
            with self.assertRaises(ValueError):repair.no_acl(7)
        with mock.patch.object(repair.os,'getxattr',side_effect=OSError(errno.EPERM,'unknown')):
            with self.assertRaises(OSError):repair.no_acl(7)
    def test_ambiguous_close_is_never_retried(self):
        rec={'state':'OWNED','fd':7,'historical_fd':None}
        with mock.patch.object(repair.signal,'pthread_sigmask',return_value=set()), \
             mock.patch.object(repair.os,'close',side_effect=InterruptedError('ambiguous')) as close:
            with self.assertRaises(InterruptedError):repair.close_owned(rec)
            self.assertEqual(rec['state'],'CLOSURE_UNKNOWN');self.assertIsNone(rec['fd'])
            with self.assertRaises(ValueError):repair.close_owned(rec)
            close.assert_called_once_with(7)


if __name__=='__main__':unittest.main()
