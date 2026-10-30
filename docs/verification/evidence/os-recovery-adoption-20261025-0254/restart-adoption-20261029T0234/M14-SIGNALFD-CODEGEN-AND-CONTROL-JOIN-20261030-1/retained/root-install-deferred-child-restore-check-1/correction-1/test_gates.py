"""Mock-only checks for the real probe's gating and close decisions."""
import importlib.util
import pathlib
import stat
import types
import unittest
from unittest import mock

path=pathlib.Path(__file__).with_name('restore_probe.py')
spec=importlib.util.spec_from_file_location('restore_probe_fixture',str(path))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


class Gates(unittest.TestCase):
    def setUp(self):
        self.event={'stage':'CALLBACK_AFTER_RESTORE','pid':22,'ppid':11,'mask':[14],'handlers_restored':True}

    def invoke(self,pinned=True,error=None,published=True,event=None):
        return p.release_gate(pinned,error,self.event if event is None else event,published,91,22,11,{14})

    def test_no_go_without_verified_pin_and_successful_publication(self):
        with mock.patch.object(p.os,'write') as write:
            self.assertFalse(self.invoke(pinned=False))
            self.assertFalse(self.invoke(published=False))
            self.assertFalse(self.invoke(error={'class':'RuntimeError'}))
            write.assert_not_called()

    def test_go_only_for_exact_restored_child(self):
        with mock.patch.object(p.os,'write',return_value=1) as write:
            self.assertTrue(self.invoke())
            write.assert_called_once_with(91,b'G')
        wrong=dict(self.event,pid=22.0)
        with mock.patch.object(p.os,'write') as write:
            self.assertFalse(self.invoke(event=wrong));write.assert_not_called()

    def test_no_pidfd_close_before_terminal_and_direct_wait(self):
        outcomes=[]
        with mock.patch.object(p.os,'close') as close:
            self.assertFalse(p.close_terminal_pidfd(88,False,True,0,outcomes))
            self.assertFalse(p.close_terminal_pidfd(88,True,False,0,outcomes))
            self.assertFalse(p.close_terminal_pidfd(88,True,True,None,outcomes))
            close.assert_not_called();self.assertEqual(outcomes,[])

    def test_verified_terminal_and_direct_wait_closes_once(self):
        outcomes=[]
        with mock.patch.object(p.os,'close') as close:
            self.assertTrue(p.close_terminal_pidfd(88,True,True,0,outcomes))
            close.assert_called_once_with(88)
        self.assertEqual(outcomes,[{'label':'verified-terminal-child-pidfd','historical_fd':88,'state':'CLOSED'}])

    def test_short_early_record_is_never_retried_or_fsynced(self):
        st=types.SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_nlink=1)
        with mock.patch.object(p.os,'fstat',return_value=st), mock.patch.object(p.fcntl,'fcntl',return_value=p.os.O_WRONLY), mock.patch.object(p.os,'write',side_effect=lambda fd,raw:len(raw)-1) as write, mock.patch.object(p.os,'fsync') as fsync:
            with self.assertRaisesRegex(OSError,'early custody short write'):
                p.publish_early({'stage':'PRE_GO'})
            write.assert_called_once();fsync.assert_not_called()

if __name__=='__main__':unittest.main()
