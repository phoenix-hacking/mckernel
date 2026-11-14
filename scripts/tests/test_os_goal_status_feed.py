"""Status orchestration with fake renderer/publisher; no GitHub or workloads."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_guard_protocol as protocol
import os_goal_status_feed as subject


REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / 'docs/verification/m14-m15-closure-progress.json'


class StatusFeedTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='status-feed-test-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.publisher = Mock()
        self.publisher.publish.return_value = {'status': 'PUBLISHED', 'published_verified_at': 'receipt'}
        self.feed = subject.StatusFeed(REPO, self.directory, publisher=self.publisher)
        self.clock = [1000.0]
        self.revision = patch.object(self.feed, '_revision', return_value='a' * 40)
        self.revision.start()
        self.addCleanup(self.revision.stop)
        self.time = patch.object(subject.time, 'time', side_effect=lambda: self.clock[0])
        self.time.start()
        self.addCleanup(self.time.stop)
        self.writer = patch.object(subject, 'write_status_text', side_effect=self.write_fake)
        self.render = self.writer.start()
        self.addCleanup(self.writer.stop)

    def write_fake(self, path, ledger, **kwargs):
        Path(path).write_text('Synthetic derived status\n')
        return {'path': str(path), 'row_counts': {
            'requirements': len(ledger['requirements']), 'tasks': len(ledger['tasks'])}}

    def save(self, name, data):
        protocol.atomic_json(self.directory / name, data)

    def test_entire_actual_canonical_ledger_reaches_renderer_without_filtering(self):
        expected = json.loads(LEDGER.read_text())
        result = self.feed.tick()
        self.assertEqual(result['status'], 'PUBLISHED')
        passed = self.render.call_args.args[1]
        self.assertEqual(passed, expected)
        self.assertEqual(len(passed['requirements']), 31)
        self.assertEqual(len(passed['tasks']), 391)
        self.assertEqual(self.render.call_args.kwargs['source_commit'], 'a' * 40)
        self.assertEqual(self.render.call_args.kwargs['generated_at'], 1000)
        self.publisher.publish.assert_called_once_with(self.directory / 'status.txt')

    def test_absent_runtime_is_unavailable_not_an_invented_empty_live_roster(self):
        self.feed.tick()
        self.assertIsNone(self.render.call_args.kwargs['runtime'])

    def test_explicit_empty_engine_context_does_not_import_old_disk_state(self):
        self.save('state.json', {'worker_pid': 987, 'agents': {'old-agent': {'status': 'inProgress'}}})
        context = {'pid': 123, 'start': '45', 'phase': 'HELD', 'engine_state': {}}
        self.feed.tick(context)
        runtime = self.render.call_args.kwargs['runtime']
        self.assertEqual(runtime['state'], {})
        self.assertEqual(runtime['guardian'], {'pid': 123, 'start': '45', 'phase': 'HELD'})

    def test_missing_engine_in_explicit_context_does_not_mix_stale_disk_state(self):
        self.save('state.json', {'worker_pid': 987, 'agents': {'old-agent': {'status': 'inProgress'}}})
        context = {'pid': 123, 'start': '45', 'phase': 'HELD'}
        self.feed.tick(context)
        runtime = self.render.call_args.kwargs['runtime']
        self.assertEqual(runtime['state'], {})
        self.assertEqual(runtime['guardian'], context)

    def test_disk_runtime_snapshots_are_supplied_when_no_context_was_given(self):
        values = {'state.json': {'worker_pid': 1}, 'guardian.json': {'pid': 2},
                  'watcher.json': {'watcher_pid': 3}, 'mailbox-state.json': {'next_poll_at': 1600},
                  'latest-stop.json': {'reason': 'retained'}}
        for name, data in values.items():
            self.save(name, data)
        self.feed.tick()
        self.assertEqual(self.render.call_args.kwargs['runtime'], {
            key: values[name] for key, name in (
                ('state', 'state.json'), ('guardian', 'guardian.json'), ('watcher', 'watcher.json'),
                ('mailbox', 'mailbox-state.json'), ('latest_stop', 'latest-stop.json'))})

    def test_six_hundred_second_cadence_skips_both_render_and_publication(self):
        first = self.feed.tick()
        self.assertEqual(first['next_refresh_at'], 1600)
        self.clock[0] = 1599.9
        self.assertEqual(self.feed.tick()['status'], 'BACKOFF')
        self.assertEqual(self.render.call_count, 1)
        self.assertEqual(self.publisher.publish.call_count, 1)
        self.clock[0] = 1600
        self.feed.tick()
        self.assertEqual(self.render.call_count, 2)
        self.assertEqual(self.publisher.publish.call_count, 2)

    def test_renderer_failure_records_error_and_preserves_previous_file(self):
        path = self.directory / 'status.txt'
        path.write_bytes(b'Previous complete report\n')
        self.render.side_effect = ValueError('Full report exceeds bounded size')
        result = self.feed.tick()
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['error_type'], 'ValueError')
        self.assertIn('exceeds bounded size', result['reason'])
        self.assertEqual(path.read_bytes(), b'Previous complete report\n')
        self.publisher.publish.assert_not_called()
        self.assertEqual(protocol.read_json(self.directory / subject.STATE_FILE)['status'], 'ERROR')

    def test_malformed_renderer_metadata_type_keeps_previous_report_and_does_not_publish(self):
        path = self.directory / 'status.txt'
        path.write_bytes(b'Previous complete report\n')
        self.render.side_effect = TypeError('Synthetic malformed telemetry')
        result = self.feed.tick({'phase': 'HELD', 'engine_state': {}})
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['error_type'], 'TypeError')
        self.assertEqual(path.read_bytes(), b'Previous complete report\n')
        self.publisher.publish.assert_not_called()

    def test_publication_error_is_reported_without_stopping_caller(self):
        self.publisher.publish.return_value = {'status': 'ERROR', 'last_error': 'Network unavailable'}
        result = self.feed.tick({'phase': 'HELD', 'engine_state': {}})
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['publication']['last_error'], 'Network unavailable')
        self.assertTrue((self.directory / 'status.txt').exists())
        self.clock[0] = 1001
        self.assertEqual(self.feed.tick()['status'], 'BACKOFF')

    def test_publisher_exception_is_bounded_and_recorded(self):
        self.publisher.publish.side_effect = RuntimeError('Synthetic publisher failure')
        result = self.feed.tick()
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['error_type'], 'RuntimeError')
        self.assertTrue((self.directory / 'status.txt').exists())

    def test_local_preview_never_calls_github_or_defers_first_publication(self):
        self.feed.tick(publish=False)
        self.publisher.publish.assert_not_called()
        self.clock[0] = 1001
        result = self.feed.tick()
        self.assertNotEqual(result['status'], 'BACKOFF')
        self.publisher.publish.assert_called_once()

    def test_local_preview_does_not_extend_existing_remote_schedule(self):
        self.feed.tick()
        self.clock[0] = 1200
        local = self.feed.tick(publish=False)
        self.assertEqual(local['status'], 'GENERATED')
        self.assertEqual(self.publisher.publish.call_count, 1)
        self.clock[0] = 1600
        result = self.feed.tick()
        self.assertNotEqual(result['status'], 'BACKOFF')
        self.assertEqual(self.publisher.publish.call_count, 2)


if __name__ == '__main__':
    unittest.main()
