"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fake backend only; no procfs, syscalls, signals, processes, FD ownership or clocks.
"""
import unittest
from recover_growth_custody import Recovery

class Fake:
    def __init__(self,fail=None):self.fail=fail;self.events=[];self.has_join=True;self.review=True;self.copy_consumed=False;self.now=99;self.cutoff=100;self.delay_close=False;self.delay_retire=False
    def event(self,name,result=None):
        self.events.append(name)
        if self.fail==name:raise RuntimeError(name)
        return result
    def before_copy(self):self.event('before_copy')
    def consume_copy(self):
        self.event('consume_COPY')
        if self.copy_consumed:raise ValueError('COPY replay')
        self.copy_consumed=True
    def open_pidfd(self):return self.event('open_pidfd',11)
    def check_old(self,p):self.event('check_old')
    def copy_fd(self,p):return self.event('copy_fd',12)
    def verify_copy(self,*_):return self.event('verify_copy',{'fd':12})
    def publish(self,n,p):return self.event('publish_'+n,{'event':n,'data':p})
    def authorize(self,n,*_):
        self.event('authorize_'+n)
        if not self.review:raise ValueError('missing review')
        if n=='CLOSE' and not self.has_join:raise ValueError('missing actual join')
    def consume(self,n,c):
        self.event('consume_'+n)
        if n=='CLOSE' and self.delay_close:self.now=101
        if n=='RETIRE' and self.delay_retire:self.now=101
        return {'consumed':n}
    def final_retire_check(self,*_):
        self.event('final_retire_check')
        if self.now>=self.cutoff:raise ValueError('retire expiry after consume')
    def final_close_check(self,*_):
        self.event('final_close_check')
        if self.now>=self.cutoff:raise ValueError('fixed cutoff after consume')
    def kill_exact(self,p):self.event('kill_exact')
    def positive_exit(self,p):self.event('positive_exit')
    def verify_after_exit(self,*_):self.event('verify_after_exit')
    def close_copy(self,f):self.event('close_copy')

class Tests(unittest.TestCase):
    def test_three_phases_separate_and_consumed_before_effect(self):
        b=Fake();s=Recovery(b);s.copy();self.assertNotIn('kill_exact',b.events);self.assertNotIn('close_copy',b.events)
        s.retire({});self.assertLess(b.events.index('consume_RETIRE'),b.events.index('kill_exact'));self.assertEqual(s.fd,12)
        self.assertEqual(s.close({}),0);self.assertLess(b.events.index('consume_CLOSE'),b.events.index('close_copy'));self.assertTrue(s.closed);self.assertIsNone(s.fd)
    def test_copy_packet_replay_refuses_before_pidfd_or_getfd(self):
        b=Fake();first=Recovery(b);first.copy()
        replay=Recovery(b)
        with self.assertRaisesRegex(ValueError,'COPY replay'):replay.copy()
        self.assertEqual(b.events.count('open_pidfd'),1);self.assertEqual(b.events.count('copy_fd'),1)
        self.assertFalse(replay.copy_possible)
    def test_delayed_retire_consumption_crossing_expiry_keeps_fd_without_signal(self):
        b=Fake();s=Recovery(b);s.copy();b.delay_retire=True
        with self.assertRaisesRegex(ValueError,'retire expiry after consume'):s.retire({})
        self.assertEqual(s.fd,12);self.assertFalse(s.closed);self.assertNotIn('kill_exact',b.events)
        self.assertIn('RETIRE',s.consumed)
    def test_delayed_consumption_crossing_cutoff_keeps_fd(self):
        b=Fake();s=Recovery(b);s.copy();s.retire({});b.delay_close=True
        with self.assertRaisesRegex(ValueError,'cutoff after consume'):s.close({})
        self.assertEqual(s.fd,12);self.assertFalse(s.closed);self.assertNotIn('close_copy',b.events)
        self.assertIn('CLOSE',s.consumed)
    def test_copy_fail_and_uncertain_acquisition_never_signal_or_close(self):
        for fail in ('copy_fd','verify_copy','publish_RAWREADY'):
            b=Fake(fail);s=Recovery(b)
            with self.subTest(fail=fail),self.assertRaises(RuntimeError):s.copy()
            self.assertTrue(s.copy_possible);self.assertNotIn('kill_exact',b.events);self.assertNotIn('close_copy',b.events)
            if fail!='copy_fd':self.assertEqual(s.fd,12)
    def test_old_birth_or_source_review_failure_before_copy(self):
        for fail in ('before_copy','check_old'):
            b=Fake(fail);s=Recovery(b)
            with self.subTest(fail=fail),self.assertRaises(RuntimeError):s.copy()
            self.assertFalse(s.copy_possible);self.assertNotIn('copy_fd',b.events)
    def test_missing_phase_review_keeps_copy(self):
        b=Fake();s=Recovery(b);s.copy();b.review=False
        with self.assertRaises(ValueError):s.retire({})
        self.assertEqual(s.fd,12);self.assertNotIn('kill_exact',b.events)
    def test_duplicate_command_and_failed_kill_cannot_retry(self):
        b=Fake('kill_exact');s=Recovery(b);s.copy()
        with self.assertRaises(RuntimeError):s.retire({})
        with self.assertRaises(ValueError):s.retire({})
        self.assertEqual(b.events.count('kill_exact'),1);self.assertEqual(s.fd,12)
    def test_close_before_retire_or_without_genuine_join_keeps_copy(self):
        b=Fake();s=Recovery(b);s.copy()
        with self.assertRaises(ValueError):s.close({})
        s.retire({});b.has_join=False
        with self.assertRaises(ValueError):s.close({})
        self.assertEqual(s.fd,12);self.assertNotIn('close_copy',b.events)
    def test_pidfd_exit_or_custody_uncertainty_cannot_close(self):
        for fail in ('positive_exit','verify_after_exit','publish_PIDFD-EXIT'):
            b=Fake();s=Recovery(b);s.copy();b.fail=fail
            with self.subTest(fail=fail),self.assertRaises(RuntimeError):s.retire({})
            self.assertEqual(s.fd,12);self.assertNotIn('close_copy',b.events)
    def test_postclose_publication_failure_records_closed_truth(self):
        b=Fake();s=Recovery(b);s.copy();s.retire({});b.fail='publish_NORMAL-CLOSE'
        with self.assertRaises(RuntimeError):s.close({})
        self.assertTrue(s.closed);self.assertIsNone(s.fd);self.assertEqual(s.phase,'CLOSED')
    def test_copy_once_and_close_once(self):
        b=Fake();s=Recovery(b);s.copy()
        with self.assertRaises(ValueError):s.copy()
        s.retire({});s.close({})
        with self.assertRaises(ValueError):s.close({})
        self.assertEqual(b.events.count('copy_fd'),1);self.assertEqual(b.events.count('close_copy'),1)

if __name__=='__main__':unittest.main(verbosity=2)
