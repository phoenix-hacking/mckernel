"""Functional-only mocked caller regression; UNRUN, no fork/pidfd/signal."""
import contextlib
import importlib.util
import select
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('test_wait_caller',HERE/'prepare_and_exec.py')
caller=importlib.util.module_from_spec(spec);spec.loader.exec_module(caller)


class WaitNonterminal(unittest.TestCase):
    def test_ready_then_wnohang_zero_keeps_actual_resource_record(self):
        fake_poll=mock.Mock();fake_poll.poll.side_effect=[[(7,select.POLLIN)],[(7,select.POLLIN)]]
        actual={'sudo_overhead_observed_bytes':7,'sudo_overhead_reserved_bytes':100}
        request={'deadline_boot_ns':999,'deadline_mono_ns':999,'utc_cap_ns':999}
        latch=mock.Mock();latch.failure=None
        captures=[({'device':8,'inode':9},b'full-data'),({'device':8,'inode':10},b'')]
        tree={321:({'pid':321,'rss_bytes':10},b'sudo')}
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(caller.select,'poll',return_value=fake_poll))
            stack.enter_context(mock.patch.object(caller,'caller_rss',return_value=11))
            stack.enter_context(mock.patch.object(caller.time,'clock_gettime_ns',return_value=1))
            stack.enter_context(mock.patch.object(caller.time,'monotonic_ns',return_value=1))
            stack.enter_context(mock.patch.object(caller.time,'time_ns',return_value=1))
            walk=stack.enter_context(mock.patch.object(caller,'owned_tree',return_value=tree))
            stack.enter_context(mock.patch.object(caller,'identify_roles',return_value={}))
            wait=stack.enter_context(mock.patch.object(caller.os,'waitpid',side_effect=[(0,0),(321,0)]))
            capture=stack.enter_context(mock.patch.object(caller,'capture_close_and_hash',side_effect=captures))
            parser=stack.enter_context(mock.patch.object(caller,'parse_captured_data',return_value={'verified':True}))
            journal=stack.enter_context(mock.patch.object(caller,'write_new'))
            stack.enter_context(mock.patch.object(caller.os,'fsync'))
            result=caller.supervise(3,latch,None,321,7,'123',object(),object(),'boot','wait',request,actual)
        self.assertEqual(wait.call_count,2);self.assertEqual(walk.call_count,2)
        self.assertEqual(capture.call_count,2);parser.assert_called_once();journal.assert_called_once()
        self.assertEqual(result['sudo_direct_wait_status'],0)
        self.assertEqual(result['host_control_observed_peak_bytes'],28)
        self.assertEqual(result['status'],'FULL_DATA_CAPTURED_AWAIT_ROOT_SESSION_JOIN')
        self.assertEqual(actual,{'sudo_overhead_observed_bytes':7,'sudo_overhead_reserved_bytes':100})
        latch.fail.assert_not_called()


if __name__=='__main__':unittest.main()
