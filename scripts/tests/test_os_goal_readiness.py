"""Pure readiness evidence tests: fake identities/leases and temporary receipts."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_guard_protocol as protocol
import os_goal_readiness as subject


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='readiness-test-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.now = 2000
        self.body = b'Complete public status snapshot\n'
        self.digest = hashlib.sha256(self.body).hexdigest()
        self.data = {
            'guardian.json': {'pid': 101, 'start': '11', 'run_id': 'a' * 32,
                              'started_at': 1900, 'heartbeat_at': 1995, 'phase': 'HELD',
                              'reason': 'missing eligible source'},
            'mailbox-state.json': {'last_successful_poll_at': 1950,
                                   'next_poll_at': 2550, 'last_error': None, 'failures': 0},
            'status-text-state.json': {'status': 'PUBLISHED', 'generated_at': 1960,
                                      'next_refresh_at': 2560, 'publication': {
                                          'status': 'PUBLISHED', 'desired_sha256': self.digest,
                                          'published_sha256': self.digest, 'desired_current': True}},
            'status-publish.json': {'status': 'PUBLISHED', 'published_verified_at': 1961,
                                   'published_sha256': self.digest, 'next_publish_at': 2561,
                                   'intent': None, 'last_error': None,
                                   'repository': 'phoenix-hacking/mckernel',
                                   'branch': 'codex/mckernel-control-mailbox', 'path': 'status.txt'},
            'state.json': {'guardian_run_id': 'a' * 32, 'worker_pid': 102,
                           'worker_start': '12', 'heartbeat_at': 1999,
                           'phase': 'waiting_for_input', 'goal': {'status': 'blocked'},
                           'active_turns': {}, 'stop_reason': None},
            'watcher.json': {'guardian_run_id': 'a' * 32, 'watcher_pid': 103,
                             'watcher_start': '13', 'worker_pid': 102},
        }
        self.births = {101: '11', 102: '12', 103: '13'}
        self.lease = patch.object(subject, 'lease_free', return_value=False)
        self.free = self.lease.start()
        self.addCleanup(self.lease.stop)
        self.save()

    def save(self):
        for name, data in self.data.items():
            protocol.atomic_json(self.directory / name, data)
        (self.directory / 'status.txt').write_bytes(self.body)

    def evaluate(self):
        return subject.evaluate_readiness(self.directory, now=self.now,
                                          identity_checker=lambda pid, birth: self.births.get(pid) == birth)

    def test_current_receipts_make_monitoring_ready_while_model_is_blocked(self):
        result = self.evaluate()
        self.assertTrue(result['monitoring_ready'])
        self.assertEqual(result['missing_stages'], [])
        self.assertEqual(result['work_state']['state'], 'BLOCKED')
        self.assertTrue(result['work_state']['engine_live'])
        self.assertEqual(result['next_due']['mailbox_poll_epoch'], 2550)
        self.assertIn('no email delivery', result['limits'])

    def test_monitoring_can_be_ready_without_a_live_engine(self):
        self.births.pop(102)
        result = self.evaluate()
        self.assertTrue(result['monitoring_ready'])
        self.assertFalse(result['work_state']['engine_live'])
        self.assertEqual(result['work_state']['state'], 'UNVERIFIED')
        self.assertIsNone(result['work_state']['active_turn_count'])

    def test_old_receipts_cannot_prove_new_guardian_start(self):
        self.data['guardian.json']['started_at'] = 1980
        self.save()
        result = self.evaluate()
        self.assertFalse(result['monitoring_ready'])
        self.assertEqual(set(result['missing_stages']), {'mailbox', 'publication'})
        self.assertTrue(any('this guardian instance' in message
                            for message in result['stages']['mailbox']['missing']))

    def test_missing_guardian_start_timestamp_never_reuses_historical_success(self):
        self.data['guardian.json'].pop('started_at')
        self.save()
        self.assertEqual(set(self.evaluate()['missing_stages']), {'guardian', 'mailbox', 'publication'})

    def test_exact_guardian_identity_lease_and_fresh_heartbeat_are_required(self):
        self.births[101] = 'reused'
        self.assertIn('guardian', self.evaluate()['missing_stages'])
        self.births[101] = '11'
        self.free.return_value = True
        self.assertIn('guardian', self.evaluate()['missing_stages'])
        self.free.return_value = False
        self.data['guardian.json']['heartbeat_at'] = 1900
        self.save()
        self.assertIn('guardian', self.evaluate()['missing_stages'])

    def test_mailbox_error_and_overdue_next_poll_are_visible(self):
        self.data['mailbox-state.json'].update(last_error='Network unavailable', failures=1)
        self.save()
        result = self.evaluate()
        self.assertIn('mailbox', result['missing_stages'])
        self.data['mailbox-state.json'].update(last_error=None, failures=0, next_poll_at=1960)
        self.save()
        result = self.evaluate()
        self.assertTrue(any('overdue' in message for message in result['stages']['mailbox']['missing']))

    def test_due_poll_has_small_guardian_tick_grace(self):
        self.data['mailbox-state.json']['next_poll_at'] = self.now - 10
        self.save()
        self.assertTrue(self.evaluate()['stages']['mailbox']['ready'])

    def test_generated_local_report_does_not_prove_publication(self):
        self.data['status-text-state.json']['status'] = 'GENERATED'
        self.save()
        result = self.evaluate()
        self.assertIn('publication', result['missing_stages'])
        self.assertTrue(any('GENERATED alone' in message for message in result['stages']['publication']['missing']))

    def test_backoff_retains_ready_only_for_actual_matching_published_bytes(self):
        self.data['status-text-state.json'].update(status='BACKOFF', publication={
            'status': 'BACKOFF', 'desired_current': False})
        self.save()
        self.assertTrue(self.evaluate()['monitoring_ready'])
        (self.directory / 'status.txt').write_bytes(b'New unpublished rendering\n')
        result = self.evaluate()
        self.assertIn('publication', result['missing_stages'])

    def test_declared_current_flag_cannot_override_wrong_actual_or_desired_hash(self):
        self.data['status-text-state.json']['publication']['desired_sha256'] = 'b' * 64
        self.save()
        self.assertIn('publication', self.evaluate()['missing_stages'])
        self.data['status-text-state.json']['publication']['desired_sha256'] = self.digest
        self.save()
        (self.directory / 'status.txt').write_bytes(b'Different complete report\n')
        self.assertIn('publication', self.evaluate()['missing_stages'])

    def test_uncertain_publication_or_other_destination_never_ready(self):
        for changes in ({'intent': {'status': 'sending'}}, {'status': 'UNKNOWN'},
                        {'last_error': 'Lost response'}, {'branch': 'another-branch'}):
            with self.subTest(changes=changes):
                original = copy.deepcopy(self.data['status-publish.json'])
                self.data['status-publish.json'].update(changes)
                self.save()
                self.assertIn('publication', self.evaluate()['missing_stages'])
                self.data['status-publish.json'] = original

    def test_receipts_over_nine_hundred_seconds_old_are_unverified(self):
        self.data['guardian.json'].update(started_at=1000, heartbeat_at=1999)
        self.data['mailbox-state.json'].update(last_successful_poll_at=1099, next_poll_at=2550)
        self.data['status-text-state.json']['generated_at'] = 1099
        self.data['status-publish.json']['published_verified_at'] = 1099
        self.save()
        self.assertEqual(set(self.evaluate()['missing_stages']), {'mailbox', 'publication'})

    def test_missing_and_malformed_snapshots_are_explicitly_unverified(self):
        (self.directory / 'guardian.json').unlink()
        (self.directory / 'mailbox-state.json').write_text('{broken')
        (self.directory / 'status-text-state.json').write_text('[]')
        result = self.evaluate()
        self.assertFalse(result['monitoring_ready'])
        self.assertEqual(result['data_issues']['guardian.json'], 'missing')
        self.assertEqual(result['data_issues']['mailbox-state.json'], 'unreadable or malformed')

    def test_malformed_field_types_are_unverified_without_raising(self):
        self.data['guardian.json'].update(started_at=float('nan'), heartbeat_at=[])
        self.data['mailbox-state.json'].update(last_successful_poll_at={}, next_poll_at='not a time')
        self.data['status-publish.json']['status'] = []
        self.data['status-text-state.json']['status'] = {}
        self.data['state.json'].update(goal={'status': []}, phase={}, stop_reason={'command': 'private'})
        self.save()
        result = self.evaluate()
        self.assertFalse(result['monitoring_ready'])
        self.assertIsNone(result['work_state']['reason'])

    def test_unrelated_runtime_private_fields_are_not_copied(self):
        self.data['state.json'].update(command='private command sentinel', password='private password sentinel')
        self.data['mailbox-state.json']['messages'] = {'secret': {'body': 'private message sentinel'}}
        self.save()
        encoded = json.dumps(self.evaluate())
        for value in ('private command sentinel', 'private password sentinel', 'private message sentinel'):
            self.assertNotIn(value, encoded)

    def test_evaluation_does_not_write_any_receipt(self):
        before = {path.name: path.read_bytes() for path in self.directory.iterdir()}
        self.evaluate()
        after = {path.name: path.read_bytes() for path in self.directory.iterdir()}
        self.assertEqual(after, before)

    def test_iso_timestamps_are_accepted_but_naive_and_future_receipts_are_not(self):
        self.data['guardian.json']['started_at'] = '1970-01-01T00:31:40Z'
        self.data['status-publish.json']['published_verified_at'] = '1970-01-01T00:32:41+00:00'
        self.save()
        self.assertTrue(self.evaluate()['monitoring_ready'])
        self.data['status-publish.json']['published_verified_at'] = '1970-01-01T00:32:41'
        self.save()
        self.assertIn('publication', self.evaluate()['missing_stages'])
        self.data['status-publish.json']['published_verified_at'] = self.now + 60
        self.save()
        self.assertIn('publication', self.evaluate()['missing_stages'])


if __name__ == '__main__':
    unittest.main()
