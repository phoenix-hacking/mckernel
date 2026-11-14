"""Functional-only synthetic pidfd identity and close-state regressions; UNRUN."""
import fcntl
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('stop_source_fixture',HERE/'control_stop.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)


class Control(unittest.TestCase):
    def test_reject_pidfd_with_wrong_target(self):
        with mock.patch.object(control,'proc_read',return_value=b'Pid:\t55\n'), \
             mock.patch.object(control.os,'readlink',return_value='anon_inode:[pidfd]'), \
             mock.patch.object(control.fcntl,'fcntl',return_value=fcntl.FD_CLOEXEC):
            with self.assertRaises(ValueError):control.own_pidfd_identity(7)
    def test_ambiguous_close_is_consumed_without_retry(self):
        record={'state':'VERIFIED_HELD','fd':7,'historical_fd':None}
        with mock.patch.object(control.signal,'pthread_sigmask',return_value=set()), \
             mock.patch.object(control.os,'close',side_effect=InterruptedError('ambiguous')) as close:
            with self.assertRaises(InterruptedError):control.close_owned(record)
            self.assertEqual(record['state'],'CLOSURE_UNKNOWN');self.assertIsNone(record['fd'])
            with self.assertRaises(ValueError):control.close_owned(record)
            close.assert_called_once_with(7)


if __name__=='__main__':unittest.main()
