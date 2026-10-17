"""Offline launch admission and initial-instruction ordering; no inference."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import run_os_goal as launcher
import run_os_parallel as parallel


class ParallelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_known_hold_is_retained_and_unknown_hold_blocks(self):
        pending = self.root / 'instructions/pending'
        pending.mkdir(parents=True)
        path = pending / (parallel.HOLD_ID + '.json')
        raw = b'{"text":"old hold"}'
        path.write_bytes(raw)
        with mock.patch.object(parallel, 'HOLD_SHA', hashlib.sha256(raw).hexdigest()):
            self.assertEqual(parallel.queue_blockers(self.root), [])
            self.assertEqual(path.read_bytes(), raw)
            path.write_bytes(b'{"text":"new stop"}')
            self.assertTrue(parallel.queue_blockers(self.root))

    def test_uncertain_delivery_blocks(self):
        sending = self.root / 'instructions/sending'
        sending.mkdir(parents=True)
        (sending / 'uncertain.json').write_text('{}')
        self.assertTrue(parallel.queue_blockers(self.root))

    def test_active_campaign_and_missing_goal_block(self):
        self.assertTrue(parallel.stopped_blockers(self.root, {}))
        self.assertTrue(parallel.stopped_blockers(self.root, {
            'thread_id': 'saved', 'goal': {'status': 'active'},
            'phase': 'running', 'active_turns': {'saved': 'turn'}}))

    def test_held_existing_lease_blocks_without_replacing_it(self):
        path = self.root / 'watch.lock'
        path.touch()
        inode = path.stat().st_ino
        with path.open('rb') as stream:
            parallel.fcntl.flock(stream, parallel.fcntl.LOCK_EX)
            errors = parallel.stopped_blockers(self.root, {
                'thread_id': 'saved', 'goal': {'status': 'paused'}, 'phase': 'stopped'})
        self.assertTrue(any('watch.lock' in item for item in errors))
        self.assertEqual(inode, path.stat().st_ino)

    def test_new_invocation_note_is_present_at_initial_resume(self):
        note = self.root / 'note'
        note.write_text('Reconcile old preparation hold before any dispatch.')
        args = launcher.arguments(['--startup-instruction-file', str(note)])
        campaign = launcher.Campaign(args, self.root, self.root)
        try:
            instructions = campaign.instructions()
            self.assertTrue(instructions.startswith('Current user instruction for this invocation'))
            self.assertIn(note.read_text(), instructions)
            # begin passes these instructions in thread/resume, before goal activation.
            source = (SCRIPTS / 'run_os_goal.py').read_text()
            self.assertLess(source.index('"developerInstructions": self.instructions()'),
                            source.index('self.rpc.call("thread/resume", params)'))
        finally:
            campaign.output.close()

    def test_note_refuses_symlink_empty_oversize_and_fifo(self):
        path = self.root / 'note'
        for raw in (b'', b'a' * 8193, b'bad\x00text', b'\xff'):
            path.write_bytes(raw)
            with self.assertRaises((ValueError, UnicodeError)):
                launcher.read_startup_instruction(path)
        link = self.root / 'link'
        link.symlink_to(path)
        with self.assertRaises(OSError):
            launcher.read_startup_instruction(link)
        fifo = self.root / 'fifo'
        os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            launcher.read_startup_instruction(fifo)

    def test_note_digest_refuses_drift_before_any_resume(self):
        note = self.root / 'note'
        note.write_text('Original invocation instruction')
        digest = hashlib.sha256(note.read_bytes()).hexdigest()
        options = ['--startup-instruction-file', str(note), '--startup-instruction-sha256', digest]
        self.assertEqual(launcher.arguments(options).startup_instruction, note.read_text())
        note.write_text('Changed instruction')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            launcher.arguments(options)

    def fake_main(self, argv, failures=()):
        note = self.root / 'note'
        note.write_text('Reconcile ' + parallel.HOLD_ID)
        (self.root / 'state.json').write_text(json.dumps({'thread_id': 'existing'}))
        resources = {'cpu_count': 7, 'memory_gib': 24, 'agent_memory_gib': 2,
                     'max_agents': 12, 'build_jobs': 7}
        with mock.patch.object(parallel, 'NOTE', note), \
                mock.patch.object(parallel, 'state_directory', return_value=self.root), \
                mock.patch.object(parallel, 'resolve_resources', return_value=resources) as resolve, \
                mock.patch.object(parallel, 'check_resources'), \
                mock.patch.object(parallel, 'stopped_blockers', return_value=list(failures)), \
                mock.patch.object(parallel, 'queue_blockers', return_value=[]), \
                mock.patch.object(parallel, 'host_blockers', return_value=({}, [])), \
                mock.patch.object(parallel.subprocess, 'run') as run, \
                mock.patch.object(parallel.os, 'execv') as execute, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            result = parallel.main(argv)
        return result, resolve, run, execute, json.loads(output.getvalue())

    def test_default_is_preview_with_maximum_measured_pool(self):
        result, resolve, run, execute, report = self.fake_main([])
        self.assertEqual(result, 0)
        self.assertEqual(resolve.call_args.kwargs['max_agents'], 12)
        run.assert_not_called()
        execute.assert_not_called()
        self.assertFalse(report['inference_started'])

    def test_check_has_only_settings_preflight(self):
        result, _, run, execute, _ = self.fake_main(['--check'])
        self.assertEqual(result, 0)
        self.assertEqual(run.call_args.args[0][-1], '--check')
        execute.assert_not_called()

    def test_run_uses_existing_launcher_after_successful_preflight(self):
        result, _, run, execute, _ = self.fake_main(['--run', '--agents', '8'])
        self.assertEqual(result, 0)
        run.assert_called_once()
        command = execute.call_args.args[1]
        self.assertIn(str(SCRIPTS / 'run_os_goal.py'), command)
        self.assertIn('--startup-instruction-file', command)
        self.assertNotIn('--token-budget', command)

    def test_blocker_prevents_preflight_and_execution(self):
        result, _, run, execute, _ = self.fake_main(['--run'], ['live owner'])
        self.assertEqual(result, 1)
        run.assert_not_called()
        execute.assert_not_called()

    def test_invalid_hours_refused(self):
        for value in ('nan', 'inf', '-1'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parallel.main(['--hours', value])


if __name__ == '__main__':
    unittest.main()
