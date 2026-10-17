"""Offline launch admission and initial-instruction ordering; no inference."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
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

    def stopped_state_with_retired_turn(self):
        # These values are outside Linux's PID range, so no live process can
        # accidentally satisfy a fixture's recorded identity.
        return {'thread_id': 'saved', 'goal': {'status': 'paused'},
                'phase': 'stopped', 'active_turns': {'saved': 'old-turn'},
                'worker_pid': 2147483646, 'server_pid': 2147483647}

    def test_stopped_dead_launcher_can_resume_with_retained_turn_metadata(self):
        state = self.stopped_state_with_retired_turn()
        path = self.root / 'state.json'
        raw = json.dumps(state).encode()
        path.write_bytes(raw)
        self.assertEqual(parallel.stopped_blockers(self.root, state), [])
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(state['active_turns'], {'saved': 'old-turn'})

    def test_retained_turn_does_not_hide_a_live_worker_server_or_watcher(self):
        for key in ('worker_pid', 'server_pid', 'watcher_pid'):
            with self.subTest(key=key):
                state = self.stopped_state_with_retired_turn()
                watch = self.root / 'watcher.json'
                if key == 'watcher_pid':
                    watch.write_text(json.dumps({'watcher_pid': os.getpid()}))
                else:
                    state[key] = os.getpid()
                self.assertTrue(parallel.stopped_blockers(self.root, state))
                if watch.exists():
                    watch.unlink()

    def test_retained_turn_requires_positive_recorded_process_ids(self):
        for key in ('worker_pid', 'server_pid'):
            for value in (None, False, True, 0, -1, '2147483647'):
                with self.subTest(key=key, value=value):
                    state = self.stopped_state_with_retired_turn()
                    state[key] = value
                    self.assertTrue(parallel.stopped_blockers(self.root, state))

    def test_policy_blocked_goal_explains_service_error_without_allowing_retry(self):
        state = self.stopped_state_with_retired_turn()
        state.update(goal={'status': 'blocked'}, stop_reason='turn_failed',
                     last_error={'codexErrorInfo': 'cyberPolicy'},
                     last_turn={'id': 'failed-compact-turn'})
        failures = parallel.stopped_blockers(self.root, state)
        self.assertEqual(len(failures), 1)
        self.assertIn('service-side', failures[0])
        self.assertIn('/feedback', failures[0])
        self.assertIn('failed-compact-turn', failures[0])
        self.assertNotIn('run the same command', failures[0])

    def test_retained_turn_still_blocks_for_wrong_phase_goal_or_uncertain_delivery(self):
        for phase in ('running', 'starting', 'ready'):
            state = self.stopped_state_with_retired_turn()
            state['phase'] = phase
            self.assertTrue(parallel.stopped_blockers(self.root, state))
        for status in ('active', 'complete', 'blocked', 'usageLimited'):
            state = self.stopped_state_with_retired_turn()
            state['goal']['status'] = status
            self.assertTrue(parallel.stopped_blockers(self.root, state))
        for status in ('sending', 'delivery_uncertain'):
            state = self.stopped_state_with_retired_turn()
            state['resume_instruction'] = {'status': status}
            self.assertTrue(parallel.stopped_blockers(self.root, state))

    def test_retained_turn_still_blocks_each_held_launcher_lease(self):
        for name in ('run.lock', 'watch.lock'):
            with self.subTest(name=name):
                path = self.root / name
                path.touch()
                inode = path.stat().st_ino
                with path.open('rb') as stream:
                    parallel.fcntl.flock(stream, parallel.fcntl.LOCK_EX)
                    failures = parallel.stopped_blockers(
                        self.root, self.stopped_state_with_retired_turn())
                self.assertTrue(any(name in item for item in failures))
                self.assertEqual(path.stat().st_ino, inode)

    def test_uncertain_startup_receipt_blocks_before_preflight_or_launch(self):
        for status in ('sending', 'delivery_uncertain'):
            with self.subTest(status=status):
                failures = parallel.stopped_blockers(self.root, {
                    'thread_id': 'existing', 'goal': {'status': 'paused'},
                    'phase': 'stopped', 'active_turns': {},
                    'resume_instruction': {'sha256': '1' * 64, 'status': status}})
                self.assertTrue(any('delivery is uncertain' in value for value in failures))
                result, _, run, execute, popen, report = self.fake_main(
                    ['--run', '--background'], failures)
                self.assertEqual(result, 1)
                self.assertEqual(report['launch_blockers'], failures)
                run.assert_not_called()
                execute.assert_not_called()
                popen.assert_not_called()

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

    def test_supersession_requires_a_hash_pinned_startup_instruction(self):
        note = self.root / 'note'
        note.write_text('Reconcile an exact historical hold before resuming.')
        binding = parallel.HOLD_ID + ':' + parallel.HOLD_SHA
        for options in (["--supersede-instruction", binding],
                        ["--startup-instruction-file", str(note), "--supersede-instruction", binding]):
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit):
                launcher.arguments(options)

    def fake_main(self, argv, failures=(), preflight_error=None):
        note = self.root / 'note'
        note.write_text('Reconcile ' + parallel.HOLD_ID)
        state_path = self.root / 'state.json'
        state_path.write_text(json.dumps({'thread_id': 'existing', 'phase': 'stopped',
            'active_turns': {}, 'goal': {'status': 'paused', 'objective': launcher.OBJECTIVE,
                                       'tokenBudget': 432100, 'tokensUsed': 1234}}))
        saved_state = state_path.read_bytes()
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
                mock.patch.object(parallel.subprocess, 'Popen') as popen, \
                mock.patch.object(parallel.os, 'execv') as execute, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            popen.return_value.pid = 43210
            run.side_effect = preflight_error
            if preflight_error is not None:
                with self.assertRaises(type(preflight_error)):
                    parallel.main(argv)
                result = 1
            else:
                result = parallel.main(argv)
        self.assertEqual(state_path.read_bytes(), saved_state)
        report, end = json.JSONDecoder().raw_decode(output.getvalue())
        background_launch = output.getvalue()[end:].strip()
        if background_launch:
            report['background_launch'] = json.loads(background_launch)
        return result, resolve, run, execute, popen, report

    def assert_gpt_61_command(self, command):
        self.assertEqual(command[command.index('--model') + 1], 'gpt-6.1-sol')
        self.assertEqual(command[command.index('--effort') + 1], 'medium')
        self.assertNotIn('--token-budget', command)
        self.assertNotIn('--objective', command)
        self.assertNotIn('--new', command)
        self.assertEqual(command[command.index('--supersede-instruction') + 1],
                         parallel.HOLD_ID + ':' + parallel.HOLD_SHA)
        note = Path(command[command.index('--startup-instruction-file') + 1])
        self.assertEqual(command[command.index('--startup-instruction-sha256') + 1],
                         hashlib.sha256(note.read_bytes()).hexdigest())

    def test_default_is_preview_with_maximum_measured_pool(self):
        result, resolve, run, execute, popen, report = self.fake_main([])
        self.assertEqual(result, 0)
        self.assertEqual(resolve.call_args.kwargs['max_agents'], 12)
        run.assert_not_called()
        execute.assert_not_called()
        popen.assert_not_called()
        self.assertFalse(report['background'])
        self.assertFalse(report['inference_started'])
        self.assertEqual(report['thread_id'], 'existing')
        self.assertEqual(report['model_routing'], {
            'dispatcher': {'model': 'gpt-6.1-sol', 'effort': 'medium'},
            'default_worker': {'model': 'gpt-6.1-sol', 'effort': 'medium'},
            'complex_worker': {'model': 'gpt-6.1-sol', 'effort': 'high'},
            'auditor': {'model': 'gpt-6.1-sol', 'effort': 'low'},
            'reviewer': {'model': 'gpt-6.1-sol', 'effort': 'high'},
        })
        self.assertTrue(all(selection['model'] == 'gpt-6.1-sol'
                            for selection in report['model_routing'].values()))
        self.assert_gpt_61_command(shlex.split(report['command']))

    def test_check_has_only_settings_preflight(self):
        result, _, run, execute, popen, _ = self.fake_main(['--check'])
        self.assertEqual(result, 0)
        self.assertEqual(run.call_args.args[0][-1], '--check')
        self.assert_gpt_61_command(run.call_args.args[0])
        self.assertTrue(run.call_args.kwargs['check'])
        execute.assert_not_called()
        popen.assert_not_called()

    def test_run_uses_existing_launcher_after_successful_preflight(self):
        result, _, run, execute, popen, _ = self.fake_main(['--run', '--agents', '8'])
        self.assertEqual(result, 0)
        run.assert_called_once()
        command = execute.call_args.args[1]
        self.assertIn(str(SCRIPTS / 'run_os_goal.py'), command)
        self.assertIn('--startup-instruction-file', command)
        self.assert_gpt_61_command(command)
        self.assertEqual(run.call_args.args[0], command + ['--check'])
        popen.assert_not_called()

    def test_blocker_prevents_preflight_and_execution(self):
        result, _, run, execute, popen, _ = self.fake_main(['--run'], ['live owner'])
        self.assertEqual(result, 1)
        run.assert_not_called()
        execute.assert_not_called()
        popen.assert_not_called()

    def test_background_requires_explicit_run(self):
        for options in (['--background'], ['--check', '--background']):
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit):
                parallel.main(options)

    def test_background_detaches_existing_launcher_after_preflight_with_private_log(self):
        result, _, run, execute, popen, report = self.fake_main(['--run', '--background'])
        self.assertEqual(result, 0)
        run.assert_called_once()
        popen.assert_called_once()
        execute.assert_not_called()
        command = popen.call_args.args[0]
        self.assert_gpt_61_command(command)
        self.assertEqual(run.call_args.args[0], command + ['--check'])
        options = popen.call_args.kwargs
        self.assertEqual(options['cwd'], parallel.REPO)
        self.assertEqual(options['stdin'], subprocess.DEVNULL)
        self.assertEqual(options['stderr'], subprocess.STDOUT)
        self.assertTrue(options['start_new_session'])
        self.assertTrue(options['close_fds'])
        path = Path(options['stdout'].name)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertEqual(report['background_launch']['console_log'], str(path))
        self.assertEqual(report['background_launch']['launcher_pid'], 43210)
        self.assertTrue(report['background'])
        popen.return_value.wait.assert_not_called()

    def test_failed_preflight_prevents_background_launch(self):
        error = subprocess.CalledProcessError(1, ['fake-preflight'])
        result, _, run, execute, popen, report = self.fake_main(
            ['--run', '--background'], preflight_error=error)
        self.assertEqual(result, 1)
        run.assert_called_once()
        execute.assert_not_called()
        popen.assert_not_called()
        self.assertNotIn('background_launch', report)

    def test_invalid_hours_refused(self):
        for value in ('nan', 'inf', '-1'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parallel.main(['--hours', value])

    def test_other_model_overrides_refused_before_preflight_or_execution(self):
        for model in ('gpt-5.6-sol', 'gpt-5.6-luna', 'gpt-6-astra', 'unknown'):
            with self.subTest(model=model), \
                    mock.patch.object(parallel.subprocess, 'run') as run, \
                    mock.patch.object(parallel.os, 'execv') as execute, \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    parallel.main(['--run', '--model', model])
                run.assert_not_called()
                execute.assert_not_called()

    def test_efforts_above_high_are_refused_before_execution(self):
        for effort in ('xhigh', 'max', 'ultra'):
            with self.subTest(effort=effort), \
                    mock.patch.object(parallel.subprocess, 'run') as run, \
                    mock.patch.object(parallel.subprocess, 'Popen') as popen, \
                    mock.patch.object(parallel.os, 'execv') as execute, \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    parallel.main(['--run', '--effort', effort])
                run.assert_not_called()
                popen.assert_not_called()
                execute.assert_not_called()

    def test_explicit_low_effort_keeps_worker_defaults_and_gpt_61(self):
        result, _, run, execute, popen, report = self.fake_main(['--check', '--effort', 'low'])
        self.assertEqual(result, 0)
        command = run.call_args.args[0]
        self.assertEqual(command[command.index('--effort') + 1], 'low')
        self.assertEqual(command[command.index('--model') + 1], 'gpt-6.1-sol')
        self.assertEqual(report['model_routing']['dispatcher'], {'model': 'gpt-6.1-sol', 'effort': 'low'})
        self.assertEqual(report['model_routing']['default_worker'],
                         {'model': 'gpt-6.1-sol', 'effort': 'medium'})
        execute.assert_not_called()
        popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
