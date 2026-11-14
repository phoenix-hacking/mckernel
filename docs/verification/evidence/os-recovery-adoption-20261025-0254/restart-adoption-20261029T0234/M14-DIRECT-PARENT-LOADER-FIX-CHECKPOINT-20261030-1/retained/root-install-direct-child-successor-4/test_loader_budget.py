"""Ordinary read-only loader budget regressions; no root or process creation."""
import importlib.util
import os
import pathlib
import resource
import stat
import sys
import unittest
from unittest import mock

HERE=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('direct_loader_budget_fixture',str(HERE/'direct_entry.py'))
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)


def descriptor_count():
    return len(os.listdir('/proc/self/fd'))


class LoaderBudget(unittest.TestCase):
    def test_a_one_shot_loader_and_inherited_reuse_fit_128(self):
        self.assertEqual(sys.version_info[:2],(3,8))
        self.assertEqual(resource.getrlimit(resource.RLIMIT_NOFILE)[0],128)
        before=descriptor_count()
        completion=entry.load_for_parent()
        after=descriptor_count()
        self.assertLessEqual(after-before,16)
        self.assertLess(after,128)
        held=[fd for fd in entry.HELD if fd is not None]
        self.assertEqual(len(held),14)
        self.assertTrue(all(stat.S_ISREG(os.fstat(fd).st_mode) for fd in held))
        self.assertTrue(all(row['state']=='CLOSED' for row in entry.CLOSE_HISTORY))
        self.assertIs(entry.load_for_parent(),completion)
        self.assertEqual(descriptor_count(),after)
        self.assertEqual(entry.LOAD_STATE,'READY')
        installer=entry.LOADED['install']
        self.assertIn(installer._BOOTSTRAP_SOURCE_FD,held)

    def test_b_ambiguous_close_is_sticky_and_never_retried(self):
        with mock.patch.object(entry,'HELD',[87]), mock.patch.object(entry,'CLOSE_HISTORY',[]), mock.patch.object(entry,'LOAD_STATE','NEW'), mock.patch.object(entry.signal,'pthread_sigmask',return_value=set()), mock.patch.object(entry.os,'close',side_effect=OSError('uncertain close')) as close:
            with self.assertRaisesRegex(OSError,'uncertain close'):
                entry.held_close(87)
            self.assertEqual(entry.CLOSE_HISTORY[-1],{'fd':87,'state':'CLOSE_UNKNOWN'})
            self.assertEqual(entry.LOAD_STATE,'FAILED')
            with self.assertRaisesRegex(ValueError,'custody UNKNOWN'):
                entry.load_for_parent()
            close.assert_called_once_with(87)

    def test_c_source_compiles_under_actual_python_38(self):
        self.assertEqual(sys.version_info[:2],(3,8))
        for name in ('direct_entry.py','phase0.py','install_issuer.py','install_completion.py',
                     'install_source_closure.py','WAIT-INSTALL-CODE.py','test_direct_model.py',
                     'test_direct_ack.py','test_loader_budget.py'):
            path=HERE/name
            compile(path.read_bytes(),str(path),'exec',dont_inherit=True,optimize=0)

if __name__=='__main__':unittest.main()
