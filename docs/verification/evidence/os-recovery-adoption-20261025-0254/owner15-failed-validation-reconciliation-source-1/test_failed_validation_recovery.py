#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

PURE MOCKS ONLY. Never construct LocalOps, open a pidfd, query procfs, modify an
actual record, send a signal, use the network or run the historical helper.
"""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('owner15_recovery', ROOT / 'failed_validation_recovery.py')
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


class MockOps:
    def __init__(self, packet):
        self.packet = packet
        self.events, self.published, self.closed = [], {}, []
        self.fail = None
        self.snapshot_count = 0
        self.snapshot_changes = {}
        self.record_change = None
        self.verify_archive_count = 0
        self.shared_exists = True
        self.failure = None

    def event(self, name):
        self.events.append(name)
        if self.fail == name:
            raise recovery.Refusal('mock ' + name + ' uncertainty')

    def authorize(self, packet):
        self.event('authorize')

    def verify_static_failure(self, packet):
        self.event('static-failure-and-joined-owner')

    def pidfd_open(self):
        self.event('pidfd-open')
        return 50

    def bind_pidfd(self, fd):
        assert fd == 50
        self.event('pidfd-bind')

    def snapshot(self, shared_present):
        self.event('snapshot')
        value = dict(boot_id=recovery.BOOT, caller=copy.deepcopy(self.packet['caller_binding']),
                     flocks=[['FLOCK', 'ADVISORY', 'WRITE', str(recovery.PID), '00:1b:4', '0', 'EOF']],
                     owner_absent=True, absent_paths=copy.deepcopy(self.packet['absent_paths']),
                     namespaces=copy.deepcopy(self.packet['prepared_namespaces']),
                     permanent=copy.deepcopy(self.packet['permanent_identity']),
                     shared_present=self.shared_exists,
                     protected={str(pid): dict(pid=pid, parent=1, starttime=str(pid + 10), state='S')
                                for pid in recovery.PROTECTED})
        value['protected'][str(recovery.PARENT)]['starttime'] = self.packet['protected_model_starttime']
        change = self.snapshot_changes.get(self.snapshot_count)
        self.snapshot_count += 1
        if change:
            change(value)
        return value

    def check_clock(self):
        self.event('clock')

    def claim_evidence(self):
        self.event('claim-fresh-evidence')

    def publish(self, name, value):
        self.event('publish:' + name)
        assert name not in self.published
        self.published[name] = copy.deepcopy(value)

    def open_shared(self):
        self.event('shared-open-readonly')
        value = copy.deepcopy(self.packet['shared_record'])
        raw = json.dumps(value, sort_keys=True).encode()
        record = dict(value=value, raw_hex=raw.hex(), raw_sha256=recovery.digest(raw),
                      metadata=copy.deepcopy(self.packet['shared_original_identity']))
        if self.record_change:
            self.record_change(record)
        return 51, record

    def archive_record(self, record):
        self.event('archive-durable')
        return dict(bytes_path='mock/archive-bytes', metadata_path='mock/archive-metadata',
                    raw_sha256=record['raw_sha256'])

    def verify_archive(self, archive):
        self.verify_archive_count += 1
        self.event('verify-archive')
        if self.fail == 'archive-check-%d' % self.verify_archive_count:
            raise recovery.Refusal('mock archive invalidation')

    def recheck_shared(self, fd, linked):
        assert fd == 51 and linked == self.shared_exists
        self.event('recheck-shared-linked' if linked else 'recheck-shared-unlinked')

    def unlink_shared(self, fd):
        assert fd == 51
        assert 'SHARED-UNLINK-BUDGET-CONSUMED.json' in self.published
        self.shared_exists = False
        self.event('unlink')

    def sole_sigkill(self, fd):
        assert fd == 50 and not self.shared_exists
        assert 'SIGNAL-BUDGET-CONSUMED.json' in self.published
        self.event('signal')
        return dict(syscall=424, signal=9, returncode=0)

    def exit_ready(self, fd):
        assert fd == 50
        self.event('pidfd-positive-exit')
        return dict(pidfd_exit_ready=True, events=[[50, 1]])

    def postflight(self, protected, archive):
        self.event('postflight-free-two-protected-archive')
        return dict(permanent_unchanged_free_observations=[True, True], shared_absent=True,
                    protected_alive=True, archive_valid=True,
                    Root_tool10088_join_and_group_absence='EXTERNAL_PENDING')

    def preserve_failure(self, value):
        self.failure = value
        self.events.append('hold-no-retry')

    def close(self, fd):
        self.closed.append(fd)

    def finish(self):
        self.events.append('finish-close-local-fds')


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads((ROOT / 'FAILED-VALIDATION-RECOVERY.PACKET.NOT-GRANTED.json').read_text())

    def run_failure(self, ops):
        with self.assertRaises(recovery.Refusal):
            recovery.recover(self.packet, ops)
        self.assertLessEqual(ops.events.count('signal'), 1)
        self.assertLessEqual(ops.events.count('unlink'), 1)
        return ops

    def test_exact_success_order_and_no_formal_retirement_credit(self):
        ops = MockOps(self.packet)
        result = recovery.recover(self.packet, ops)
        before = ops.events.index
        self.assertLess(before('archive-durable'), before('unlink'))
        self.assertLess(before('publish:SHARED-UNLINK-BUDGET-CONSUMED.json'), before('unlink'))
        self.assertLess(before('unlink'), before('publish:SIGNAL-BUDGET-CONSUMED.json'))
        self.assertLess(before('publish:SIGNAL-BUDGET-CONSUMED.json'), before('signal'))
        self.assertLess(before('signal'), before('pidfd-positive-exit'))
        self.assertEqual(ops.events.count('unlink'), 1)
        self.assertEqual(ops.events.count('signal'), 1)
        self.assertEqual(ops.closed, [51, 50])
        self.assertEqual(result['status'], 'FAILED_VALIDATION_RECOVERY')
        self.assertTrue(result['Root_creator_join_and_group_postflight_pending'])
        self.assertFalse(result['normal_cleanup_credit'])
        self.assertFalse(result['new_heavy_admission'])

    def test_wrong_pid_birth_or_protected_target_is_rejected_before_pidfd(self):
        for field, value in [('pid', 997662), ('starttime', '79134159'),
                             ('pid', recovery.PARENT), ('parent', 1)]:
            with self.subTest(field=field, value=value):
                packet = copy.deepcopy(self.packet)
                packet['target'][field] = value
                ops = MockOps(packet)
                with self.assertRaises(recovery.Refusal):
                    recovery.recover(packet, ops)
                self.assertEqual(ops.events, [])

    def test_identity_children_fd_record_owner_and_namespace_negatives(self):
        changes = [
            lambda x: x['caller'].update(starttime='reused'),
            lambda x: x['caller'].update(parent=1),
            lambda x: x['caller'].update(uid=0),
            lambda x: x['caller'].update(threads=2),
            lambda x: x['caller'].update(children=[123]),
            lambda x: x['caller'].update(pgid=1),
            lambda x: x['caller'].update(session=1),
            lambda x: x['caller'].update(fd3_node=[27, 5]),
            lambda x: x['caller'].update(permanent_fds=[3, 4]),
            lambda x: x['caller']['guard'].update(argv=['wrong']),
            lambda x: x['caller']['guard'].update(exe_inode=1),
            lambda x: x.update(flocks=[]),
            lambda x: x.update(owner_absent=False),
            lambda x: x.update(absent_paths=[]),
            lambda x: x['namespaces'][0].update(inode=1),
            lambda x: x['permanent'].update(inode=5),
            lambda x: x.update(shared_present=False),
            lambda x: x['protected'][str(recovery.PARENT)].update(state='Z'),
            lambda x: x['protected'][str(recovery.PARENT)].update(starttime='reused'),
        ]
        for index, change in enumerate(changes):
            with self.subTest(index=index):
                ops = MockOps(self.packet)
                ops.snapshot_changes[0] = change
                self.run_failure(ops)
                self.assertNotIn('claim-fresh-evidence', ops.events)
                self.assertNotIn('unlink', ops.events)
                self.assertNotIn('signal', ops.events)

    def test_shared_bytes_tuple_and_inode_negatives(self):
        changes = [lambda x: x.update(raw_sha256='0' * 64),
                   lambda x: x.update(raw_hex='00'),
                   lambda x: x['value'].update(pid=1),
                   lambda x: x['metadata'].update(st_ino=116862),
                   lambda x: x['metadata'].update(st_nlink=2)]
        for change in changes:
            ops = MockOps(self.packet)
            ops.record_change = change
            self.run_failure(ops)
            self.assertNotIn('archive-durable', ops.events)
            self.assertNotIn('unlink', ops.events)

    def test_pidfd_and_archive_failures_preserve_lock_no_signal(self):
        for failure in ('pidfd-bind', 'archive-durable', 'archive-check-1',
                        'recheck-shared-linked'):
            ops = MockOps(self.packet)
            ops.fail = failure
            self.run_failure(ops)
            self.assertNotIn('unlink', ops.events)
            self.assertNotIn('signal', ops.events)

    def test_live_fd_change_after_archive_stops_before_unlink(self):
        ops = MockOps(self.packet)
        ops.snapshot_changes[4] = lambda x: x['caller'].update(fd3_node=[27, 5])
        self.run_failure(ops)
        self.assertIn('archive-durable', ops.events)
        self.assertNotIn('unlink', ops.events)
        self.assertNotIn('signal', ops.events)

    def test_uncertain_unlink_never_signals_or_retries(self):
        ops = MockOps(self.packet)
        ops.fail = 'unlink'
        self.run_failure(ops)
        self.assertEqual(ops.events.count('unlink'), 1)
        self.assertNotIn('signal', ops.events)
        self.assertEqual(ops.failure['shared_unlinked'], 'UNCERTAIN_CALL_ATTEMPTED')
        self.assertFalse(ops.failure['retry_authority'])

    def test_uncertain_budget_publication_conservatively_consumes_signal(self):
        ops = MockOps(self.packet)
        ops.fail = 'publish:SIGNAL-BUDGET-CONSUMED.json'
        self.run_failure(ops)
        self.assertTrue(ops.failure['signal_budget_consumed'])
        self.assertNotIn('signal', ops.events)

    def test_last_archive_check_failure_keeps_consumed_budget_without_signal(self):
        ops = MockOps(self.packet)
        ops.fail = 'archive-check-3'
        self.run_failure(ops)
        self.assertTrue(ops.failure['signal_budget_consumed'])
        self.assertNotIn('signal', ops.events)

    def test_uncertain_signal_consumes_exactly_one_call_no_retry(self):
        ops = MockOps(self.packet)
        ops.fail = 'signal'
        self.run_failure(ops)
        self.assertEqual(ops.events.count('signal'), 1)
        self.assertTrue(ops.failure['signal_budget_consumed'])
        self.assertTrue(ops.failure['signal_attempted'])
        self.assertFalse(ops.failure['retry_authority'])

    def test_exit_or_postflight_uncertainty_never_publishes_success(self):
        for failure in ('pidfd-positive-exit', 'postflight-free-two-protected-archive'):
            ops = MockOps(self.packet)
            ops.fail = failure
            self.run_failure(ops)
            self.assertEqual(ops.events.count('signal'), 1)
            self.assertNotIn('FAILED-VALIDATION-RECOVERY.json', ops.published)

    def test_protected_running_sleeping_transition_is_not_identity_change(self):
        ops = MockOps(self.packet)
        ops.snapshot_changes[1] = lambda x: x['protected'][str(recovery.PARENT)].update(state='R')
        recovery.recover(self.packet, ops)
        self.assertEqual(ops.events.count('signal'), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
