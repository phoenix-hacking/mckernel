"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure controller fixtures: temporary campaign only, no live queue/process/workload.
"""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('steer_every_ten_minutes.py')
spec = importlib.util.spec_from_file_location('private_steering', SOURCE)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
NOW = 1792792600.0


def state():
    return dict(thread_id=app.THREAD, phase='running', goal=dict(status='active', threadId=app.THREAD),
                heartbeat_at=datetime.fromtimestamp(NOW, timezone.utc).isoformat(),
                worker_pid=111, server_pid=222, stop_reason=None)


class Decisions(unittest.TestCase):
    def test_active_due(self):
        self.assertEqual(app.decision(state(), {}, NOW, False), 'queue')

    def test_paused_stopped_goal_complete(self):
        cases = [('phase', 'stopped'), ('phase', 'paused'), ('goal', {'status': 'paused'}),
                 ('goal', {'status': 'complete'}), ('paused', True), ('checkpoint_requested', True)]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                sample = state(); sample[key] = value
                self.assertTrue(app.decision(sample, {}, NOW, False).startswith('stop:'))

    def test_holds_and_policy_error(self):
        for key, value in [('stop_reason', 'turn_failed'), ('service_hold', True),
                           ('policy_hold', True), ('last_error', {'codexErrorInfo': 'cyberPolicy'})]:
            sample = state(); sample[key] = value
            self.assertTrue(app.decision(sample, {}, NOW, False).startswith('stop:'))

    def test_historical_capacity_error_does_not_masquerade_as_hold(self):
        sample = state(); sample['last_error'] = {'codexErrorInfo': 'serverOverloaded'}
        sample['retryable'] = False
        self.assertEqual(app.decision(sample, {}, NOW, False), 'queue')

    def test_real_heartbeat_required_not_updated_at(self):
        for heartbeat in [None, 'bad', '2026-10-01T00:00:00Z']:
            sample = state(); sample['heartbeat_at'] = heartbeat
            sample['updated_at'] = datetime.fromtimestamp(NOW, timezone.utc).isoformat()
            self.assertTrue(app.decision(sample, {}, NOW, False).startswith('stop:'))

    def test_future_heartbeat_stops(self):
        sample = state(); sample['heartbeat_at'] = datetime.fromtimestamp(NOW+60, timezone.utc).isoformat()
        self.assertEqual(app.decision(sample, {}, NOW, False), 'stop:heartbeat_stale')

    def test_thread_change_stops_even_with_active_goal(self):
        sample = state(); sample['thread_id'] = 'different'
        self.assertEqual(app.decision(sample, {}, NOW, False), 'stop:thread_changed')
        sample = state(); sample['goal']['threadId'] = 'different'
        self.assertEqual(app.decision(sample, {}, NOW, False), 'stop:goal_not_active')

    def test_cadence_no_duplicate_and_rollback(self):
        journal = dict(status='queued', queued_at=NOW, thread_id=app.THREAD)
        self.assertEqual(app.decision(state(), journal, NOW+1, False), 'wait:interval')
        sample = state(); sample['heartbeat_at'] = datetime.fromtimestamp(NOW+600, timezone.utc).isoformat()
        self.assertEqual(app.decision(sample, journal, NOW+600, False), 'queue')
        self.assertTrue(app.decision(state(), journal, NOW-1, False).startswith('stop:'))

    def test_uncertain_submission_is_not_replayed(self):
        for status in ['intent', 'uncertain', 'stopped']:
            self.assertTrue(app.decision(state(), {'status': status}, NOW, False).startswith('stop:'))


class QueueFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.campaign = Path(self.temp.name)/'campaign'; self.campaign.mkdir()
        self.output = Path(self.temp.name)/'private'; self.output.mkdir()
        self.log = self.campaign/'runs'/'active'; self.log.mkdir(parents=True)
        for name in ['dispatcher.txt', 'console.log']:
            (self.log/name).write_text('x'*20000+'\nactual bounded tail\n')
        self.sample = state(); self.sample['log_dir'] = str(self.log)
        app.atomic(self.campaign/'state.json', self.sample)
        self.guard = patch.object(app, 'CAMPAIGN', self.campaign); self.guard.start()
        self.addCleanup(self.guard.stop)
        self.clock = patch.object(app.time, 'time', return_value=NOW); self.clock.start()
        self.addCleanup(self.clock.stop)
        self.queue, self.sha = app.load_queue()

    def test_actual_existing_queue_once_and_durable_interval(self):
        before = (self.campaign/'state.json').read_bytes()
        verdict, journal = app.step(self.campaign, self.output, self.queue, {}, NOW)
        self.assertEqual(verdict, 'queued')
        pending = list((self.campaign/'instructions'/'pending').glob('*.json'))
        self.assertEqual(len(pending), 1)
        item = json.loads(pending[0].read_text())
        self.assertIn(app.MARKER, item['text']); self.assertIn(app.THREAD, item['text'])
        self.assertIn('M14', item['text']); self.assertIn('P12', item['text'])
        self.assertEqual(before, (self.campaign/'state.json').read_bytes())
        again, saved = app.step(self.campaign, self.output, self.queue, journal, NOW+1)
        self.assertEqual(again, 'wait:interval')
        self.assertEqual(len(list((self.campaign/'instructions'/'pending').glob('*.json'))), 1)
        self.assertEqual(app.read_json(self.output/'journal.json')['instruction_id'], item['id'])
        snap = app.read_json(self.output/'snapshot.json')
        self.assertTrue(all(len(t['tail'].encode()) <= app.TAIL_CAP for t in snap['tails']))

    def test_pending_and_uncertain_sending_backlog(self):
        for name in ['pending', 'sending']:
            folder = self.campaign/'instructions'/name; folder.mkdir(parents=True, exist_ok=True)
            item = folder/'other.json'; item.write_text('{}')
            verdict, _ = app.step(self.campaign, self.output, self.queue, {}, NOW)
            self.assertEqual(verdict, 'wait:queue_backlog')
            self.assertFalse((self.output/'journal.json').exists())
            item.unlink()

    def test_crash_after_queue_leaves_intent_and_cannot_duplicate(self):
        def uncertain(campaign, text):
            self.queue(campaign, text)
            raise RuntimeError('simulated crash after persisted queue')
        with self.assertRaises(RuntimeError):
            app.step(self.campaign, self.output, uncertain, {}, NOW)
        saved = app.read_json(self.output/'journal.json')
        self.assertEqual(saved['status'], 'uncertain')
        verdict, _ = app.step(self.campaign, self.output, self.queue, saved, NOW)
        self.assertTrue(verdict.startswith('stop:'))
        self.assertEqual(len(list((self.campaign/'instructions'/'pending').glob('*.json'))), 1)

    def test_thread_change_during_snapshot_never_submits(self):
        original = app.snapshot
        def changed(sample):
            result = original(sample)
            newer = deepcopy(self.sample); newer['thread_id'] = 'other'
            app.atomic(self.campaign/'state.json', newer)
            return result
        with patch.object(app, 'snapshot', changed):
            verdict, _ = app.step(self.campaign, self.output, self.queue, {}, NOW)
        self.assertEqual(verdict, 'stop:thread_changed')
        self.assertFalse((self.campaign/'instructions').exists())

    def test_pause_during_snapshot_never_submits(self):
        original = app.snapshot
        def changed(sample):
            result = original(sample)
            newer = deepcopy(self.sample); newer['goal']['status'] = 'paused'
            app.atomic(self.campaign/'state.json', newer)
            return result
        with patch.object(app, 'snapshot', changed):
            verdict, _ = app.step(self.campaign, self.output, self.queue, {}, NOW)
        self.assertEqual(verdict, 'stop:goal_not_active')
        self.assertFalse((self.campaign/'instructions').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
