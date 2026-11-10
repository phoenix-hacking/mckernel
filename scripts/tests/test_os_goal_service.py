"""Service boundaries with fake systemd, GitHub and exec; no workloads started."""
from contextlib import nullcontext, redirect_stdout
import fcntl
import hashlib
import io
import json
import shlex
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_guard_protocol as protocol
import os_goal_guardian as guardian
import os_goal_service as subject
import run_os_goal as launcher
import start_os_overnight as overnight


class ServiceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='os-service-test-')
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name) / 'repo'
        self.directory = self.repo / 'runtime'
        self.directory.mkdir(parents=True)
        (self.repo / 'scripts').mkdir()
        (self.repo / 'scripts/m14-m15-overnight-instruction.txt').write_text('Continue eligible work.')
        self.arguments = ['--hours', '0', '--max-agents', '2', '--agent-windows', 'off']
        self.names = subject.unit_names(self.directory)
        self.systemctl = self.patch(subject, '_systemctl', return_value='inactive')
        self.install_implementation = subject.install_units
        self.install = self.patch(subject, 'install_units', return_value=self.names)
        self.preflight = self.patch(subject, 'mailbox_preflight', return_value={'status': 'READ_ACCESS_VERIFIED'})
        self.patch(subject.shutil, 'which', side_effect=lambda name: '/fake/' + name)
        self.exec = self.patch(subject.os, 'execv')
        self.patch(subject.subprocess, 'run', side_effect=AssertionError('No external process in service tests'))
        self.patch(subject.subprocess, 'check_output', side_effect=AssertionError('No external process in service tests'))

    def patch(self, target, name, **kwargs):
        handle = patch.object(target, name, **kwargs)
        result = handle.start()
        self.addCleanup(handle.stop)
        return result

    def write(self, name, data):
        protocol.atomic_json(self.directory / name, data)

    def live_guard(self):
        value = {'run_id': 'a' * 32, 'pid': 20000007, 'start': '321',
                 'phase': 'HELD', 'heartbeat_at': 123, 'reason': 'needs_input'}
        self.write('guardian.json', value)
        return value

    def engine_fixture(self):
        guard = self.live_guard()
        self.write(subject.CONFIG, {'repo': str(self.repo), 'arguments': self.arguments})
        launch = {'run_id': guard['run_id'], 'guardian_pid': guard['pid'],
                  'guardian_start': guard['start'], 'proof_path': str(self.directory / 'guardian-recovery-test.json')}
        self.write(subject.NEXT, launch)
        return guard, launch

    def test_units_isolate_monitor_watchdog_from_engine_work(self):
        units = subject.render_units(self.repo, self.directory, python='/fake/python', path_environment='/fake/bin')
        self.assertEqual(set(units), set(self.names.values()))
        monitor, engine = units[self.names['guardian']], units[self.names['engine']]
        for setting in ('Type=notify', 'NotifyAccess=all', 'WatchdogSec=90',
                        'Restart=always', 'KillMode=control-group'):
            self.assertIn(setting + '\n', monitor)
        self.assertIn(' guardian\n', monitor)
        self.assertNotIn('run_os_goal.py', monitor)
        self.assertIn('Restart=no\n', engine)
        self.assertIn('KillMode=process\n', engine)
        self.assertIn(' engine\n', engine)
        self.assertNotIn('WatchdogSec=', engine)
        self.assertNotIn('PartOf=', engine)
        self.assertNotIn('BindsTo=', engine)

    def test_unit_path_environment_and_exec_arguments_use_their_correct_escaping(self):
        repo = self.repo / 'space and 100%$cash'
        units = subject.render_units(repo, self.directory, python='/fake/100%$python',
                                     path_environment='/fake/$cash/100%bin')
        for unit in units.values():
            self.assertIn('WorkingDirectory=' + str(repo).replace('%', '%%') + '\n', unit)
            self.assertNotIn('WorkingDirectory="', unit)
            self.assertIn('Environment="PATH=/fake/$cash/100%%bin"\n', unit)
            self.assertIn('"/fake/100%%$$python" "-B"', unit)

    def test_guardian_inhibits_sleep_independently_and_routes_child_notifications(self):
        units = subject.render_units(self.repo, self.directory, python='/fake/python')
        monitor = units[self.names['guardian']]
        engine = units[self.names['engine']]
        fields = dict(line.split('=', 1) for line in monitor.splitlines() if '=' in line)
        command = shlex.split(fields['ExecStart'])
        self.assertEqual(command[0], '/fake/systemd-inhibit')
        self.assertEqual(command[1:3], ['--what=idle:sleep:handle-lid-switch', '--mode=block'])
        self.assertNotIn('--no-ask-password', command)
        self.assertEqual(command[command.index('--') + 1:],
                         ['/fake/python', '-B', str(self.repo / 'scripts/os_goal_service.py'), 'guardian'])
        self.assertEqual(fields['Type'], 'notify')
        self.assertEqual(fields['NotifyAccess'], 'all', 'The notifying guardian is a child of the inhibitor')
        self.assertEqual(fields['WatchdogSec'], '90')
        self.assertEqual(fields['KillMode'], 'control-group')
        self.assertNotIn('shutdown', command[1])
        self.assertNotIn('handle-power-key', command[1])
        self.assertNotIn('BindsTo=', monitor)
        self.assertNotIn('PartOf=', monitor)
        self.assertIn('ExecStart="/fake/python"', engine)
        self.assertNotIn('systemd-inhibit', engine, 'Engine execution stays in its existing independent adapter')

    def test_guardian_units_have_no_uninhibited_fallback_if_binary_missing_or_relative(self):
        for resolved in (None, 'relative/systemd-inhibit'):
            with self.subTest(resolved=resolved), patch.object(subject.shutil, 'which', return_value=resolved):
                with self.assertRaisesRegex(RuntimeError, 'no uninhibited fallback'):
                    subject.render_units(self.repo, self.directory, python='/fake/python')
        self.exec.assert_not_called()
        self.systemctl.assert_not_called()

    def test_busy_engine_prevents_config_overwrite_and_new_authorization(self):
        self.write(subject.CONFIG, {'preserved': 'prior invocation'})
        original = (self.directory / subject.CONFIG).read_bytes()
        for state in ('active', 'activating', 'deactivating', 'reloading'):
            with self.subTest(state=state), patch.object(guardian, 'authorize_start') as authorize:
                self.systemctl.reset_mock()
                self.systemctl.return_value = state
                result = subject.start(self.repo, self.directory, self.arguments)
                self.assertEqual(result['status'], 'EXISTING_OWNER')
                self.assertEqual((self.directory / subject.CONFIG).read_bytes(), original)
                authorize.assert_not_called()
                self.preflight.assert_not_called()
                self.assertFalse(any(call.args[0] in {'enable', 'start'} for call in self.systemctl.call_args_list))

    def test_start_publication_lock_prevents_parallel_authorization(self):
        with subject._service_lock(self.directory), patch.object(guardian, 'authorize_start') as authorize:
            result = subject.start(self.repo, self.directory, self.arguments)
        self.assertEqual(result['status'], 'EXISTING_OWNER')
        authorize.assert_not_called()
        self.install.assert_not_called()
        self.systemctl.assert_not_called()

    def test_model_lease_prevents_new_service_start(self):
        stream = (self.directory / 'run.lock').open('w')
        self.addCleanup(stream.close)
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with patch.object(guardian, 'authorize_start') as authorize:
            result = subject.start(self.repo, self.directory, self.arguments)
        self.assertEqual(result['status'], 'EXISTING_OWNER')
        authorize.assert_not_called()
        self.install.assert_not_called()

    def test_unresolved_legacy_launch_receipt_is_preserved(self):
        self.write(overnight.LATEST, {'status': 'STARTING', 'launch_pid': None})
        self.write('state.json', {'thread_id': 'saved-root', 'goal': {'status': 'blocked'}})
        handoff = self.directory / 'RECOVERY.md'
        handoff.write_text('Retained handoff and held ownership.')
        before = {path: path.read_bytes() for path in (
            self.directory / overnight.LATEST, self.directory / 'state.json', handoff)}
        with patch.object(guardian, 'authorize_start') as authorize:
            result = subject.start(self.repo, self.directory, self.arguments)
        self.assertEqual(result['status'], 'EXISTING_OWNER')
        self.assertEqual({path: path.read_bytes() for path in before}, before)
        authorize.assert_not_called()
        self.install.assert_not_called()

    def test_legacy_pre_receipt_lock_prevents_migration_race(self):
        stream = (self.directory / 'overnight-start.lock').open('w')
        self.addCleanup(stream.close)
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subject.start(self.repo, self.directory, self.arguments)
        self.assertEqual(result['status'], 'EXISTING_OWNER')
        self.install.assert_not_called()

    def test_pending_explicit_intent_keeps_its_original_settings(self):
        original = {'repo': str(self.repo), 'arguments': ['--hours', '1']}
        self.write(subject.CONFIG, original)
        intent = guardian.authorize_start(self.directory, request_id='already-authorized')
        with patch.object(guardian, 'authorize_start') as authorize:
            result = subject.start(self.repo, self.directory, self.arguments)
        self.assertEqual(result['start_request_id'], intent['request_id'])
        self.assertEqual(protocol.read_json(self.directory / subject.CONFIG), original)
        authorize.assert_not_called()
        self.preflight.assert_not_called()
        self.systemctl.assert_any_call('enable', '--now', self.names['guardian'])
        self.assertEqual(len(list((self.directory / 'guardian-intents').glob('*.json'))), 1)

    def test_mailbox_preflight_failure_creates_no_authorization_or_config(self):
        self.preflight.side_effect = RuntimeError('Identity is not the mailbox owner')
        with patch.object(guardian, 'authorize_start') as authorize, self.assertRaises(RuntimeError):
            subject.start(self.repo, self.directory, self.arguments)
        authorize.assert_not_called()
        self.assertFalse((self.directory / subject.CONFIG).exists())
        self.assertFalse((self.directory / 'guardian-intents').exists())
        self.assertFalse(any(call.args[0] in {'enable', 'start'} for call in self.systemctl.call_args_list))

    def test_successful_start_publishes_settings_and_intent_before_enabling_monitor(self):
        enabled = []
        def systemctl(*arguments, **kwargs):
            if arguments[0] == 'show':
                return 'inactive'
            self.assertEqual(arguments, ('enable', '--now', self.names['guardian']))
            config = protocol.read_json(self.directory / subject.CONFIG)
            self.assertEqual(config['repo'], str(self.repo))
            self.assertIn('--max-agents', config['arguments'])
            self.assertEqual(config['mailbox_preflight']['status'], 'READ_ACCESS_VERIFIED')
            intents = list((self.directory / 'guardian-intents').glob('*.json'))
            self.assertEqual(len(intents), 1)
            self.assertEqual(protocol.read_json(intents[0])['status'], 'pending')
            enabled.append(arguments)
            return ''
        self.systemctl.side_effect = systemctl
        result = subject.start(self.repo, self.directory, self.arguments)
        self.assertTrue(result['start_request_id'])
        self.assertEqual(len(enabled), 1)
        self.preflight.assert_called_once_with(self.repo)

    def test_credit_identity_is_durable_before_start_and_reused_by_guardian_recovery(self):
        from os_goal_credits import CreditBudget

        def systemctl(*values, **kwargs):
            if values[0] == 'show':
                return 'inactive'
            config = protocol.read_json(self.directory / subject.CONFIG)
            parsed = launcher.arguments(config['arguments'])
            self.assertIsNotNone(parsed.credit_run_id,
                                 'The identity must be durable before guardian enablement')
            return ''

        self.systemctl.side_effect = systemctl
        subject.start(self.repo, self.directory, self.arguments + ['--credit-budget', '25'])
        config = protocol.read_json(self.directory / subject.CONFIG)
        parsed = launcher.arguments(config['arguments'])
        identifier = parsed.credit_run_id
        budget = CreditBudget(self.directory, identifier, parsed.credit_budget, protocol.atomic_json)
        limits = {'credits': {'hasCredits': True, 'unlimited': False, 'balance': '50'}}
        budget.observe(limits)
        guard = self.live_guard()
        for proof in (None, str(self.directory / 'guardian-recovery-test.json')):
            self.write(subject.NEXT, {'run_id': guard['run_id'], 'guardian_pid': guard['pid'],
                       'guardian_start': guard['start'], 'proof_path': proof})
            with patch.object(subject, 'process_start', return_value=guard['start']), \
                    patch.object(subject, 'lease_free', side_effect=lambda directory, name: name != 'guardian.lock'):
                subject.engine(self.repo, self.directory)
            command = self.exec.call_args.args[1]
            index = command.index(str(self.repo / 'scripts/run_os_goal.py'))
            engine_args = launcher.arguments(command[index + 1:])
            self.assertEqual(engine_args.credit_run_id, identifier)
            self.assertEqual(engine_args.credit_budget, '25')
        recovered = CreditBudget(self.directory, identifier, '25', protocol.atomic_json, recovered=True)
        limits['credits']['balance'] = '47'
        saved, exhausted = recovered.observe(limits)
        self.assertEqual(saved['spent'], '3')
        self.assertEqual(saved['remaining'], '22')
        self.assertFalse(exhausted)
        self.assertEqual(protocol.read_json(self.directory / subject.CONFIG), config)

    def test_service_restart_guardian_entry_never_creates_manual_intent(self):
        with patch.object(subject, 'runtime_directory', return_value=self.directory), \
                patch.object(subject, 'guardian', return_value=0) as run_guardian, \
                patch.object(guardian, 'authorize_start') as authorize:
            self.assertEqual(subject.main(['guardian']), 0)
        run_guardian.assert_called_once_with(subject.REPO, self.directory)
        authorize.assert_not_called()
        self.install.assert_not_called()
        self.preflight.assert_not_called()
        self.systemctl.assert_not_called()

    def explicit_engine_arguments(self):
        instruction = self.repo / 'scripts' / 'explicit-engine-instruction.txt'
        instruction.write_text(
            'Continue eligible work only. HOST CPUs0,6,7: max3 jobs and4 GiB TOTAL '
            'including overhead. Planner12 GiB is a ceiling, not extra HOST RAM. '
            'Preserve source, native and service holds.')
        digest = hashlib.sha256(instruction.read_bytes()).hexdigest()
        return ['--hours', '0', '--watchdog-seconds', '180', '--stall-seconds', '1200',
                '--max-restarts', '3', '--max-agents', '6', '--build-jobs', '3',
                '--memory-gib', '12', '--profile', 'aggressive', '--agent-windows', 'off',
                '--startup-instruction-file', str(instruction),
                '--startup-instruction-sha256', digest]

    def assert_explicit_engine_arguments(self, values, expected_pair):
        parsed = launcher.arguments(values)
        self.assertEqual((parsed.repair_agent_failures, parsed.stop_after_m14_m15), expected_pair)
        self.assertEqual(parsed.hours, 0)
        self.assertEqual(parsed.watchdog_seconds, 180)
        self.assertEqual(parsed.stall_seconds, 1200)
        self.assertEqual(parsed.max_restarts, 3)
        self.assertEqual(parsed.max_agents, 6)
        self.assertEqual(parsed.build_jobs, 3)
        self.assertEqual(parsed.memory_gib, 12)
        self.assertEqual(parsed.profile, 'aggressive')
        self.assertEqual(parsed.agent_windows, 'off')
        instruction = self.repo / 'scripts' / 'explicit-engine-instruction.txt'
        self.assertEqual(parsed.startup_instruction_file, instruction)
        self.assertEqual(parsed.startup_instruction, instruction.read_text())
        self.assertEqual(parsed.startup_instruction_sha256,
                         hashlib.sha256(instruction.read_bytes()).hexdigest())
        # Parsing a planner ceiling does not grant more than the source-bound HOST budget.
        self.assertIn('4 GiB TOTAL', parsed.startup_instruction)
        self.assertIn('not extra HOST RAM', parsed.startup_instruction)

    def test_validator_preserves_each_explicit_optional_flag_combination(self):
        cases = [((), (False, False)),
                 (('--repair-agent-failures',), (True, False)),
                 (('--stop-after-m14-m15',), (False, True)),
                 (('--repair-agent-failures', '--stop-after-m14-m15'), (True, True))]
        for optional, expected in cases:
            with self.subTest(optional=optional):
                flags = self.explicit_engine_arguments() + list(optional)
                original = flags.copy()
                values = subject._validated_arguments(self.repo, flags)
                self.assert_explicit_engine_arguments(values, expected)
                self.assertEqual(values, original)
                self.assertEqual(flags, original)

    def test_validator_none_keeps_intentional_both_true_defaults(self):
        values = subject._validated_arguments(self.repo, None)
        parsed = launcher.arguments(values)
        self.assertEqual(values, subject.default_arguments(self.repo))
        self.assertTrue(parsed.repair_agent_failures)
        self.assertTrue(parsed.stop_after_m14_m15)
        self.assertEqual(parsed.memory_gib, 4)

    def test_legacy_forwarding_reaches_real_validator_without_adding_optional_flags(self):
        cases = [((), (False, False)),
                 (('--repair-agent-failures',), (True, False)),
                 (('--stop-after-m14-m15',), (False, True)),
                 (('--repair-agent-failures', '--stop-after-m14-m15'), (True, True))]
        for optional, expected in cases:
            with self.subTest(optional=optional):
                flags = self.explicit_engine_arguments() + list(optional)
                original = flags.copy()
                output = io.StringIO()
                # Keep launch_legacy, service.main/start, validator and parser real.
                # Mock only service ownership, publication and external launch effects.
                with patch.object(subject, 'REPO', self.repo), \
                        patch.object(subject, 'runtime_directory', return_value=self.directory), \
                        patch.object(subject.os, 'umask'), \
                        patch.object(subject, '_service_lock', return_value=nullcontext()), \
                        patch.object(subject, 'lease_free', return_value=True), \
                        patch.object(subject, '_legacy_owner', return_value=None), \
                        patch.object(guardian, 'authorize_start', return_value={'request_id': 'fake-intent'}) as authorize, \
                        patch.object(subject, 'atomic_json') as publish, \
                        patch.object(subject, 'status', return_value={'status': 'NOT_STARTED'}), \
                        patch.object(subject.subprocess, 'Popen', side_effect=AssertionError('No process launch')), \
                        patch.object(subject, '_validated_arguments', wraps=subject._validated_arguments) as validate, \
                        redirect_stdout(output):
                    self.assertEqual(overnight.launch_legacy(flags), 0)
                validate.assert_called_once_with(self.repo.resolve(), original)
                publish.assert_called_once()
                destination, config = publish.call_args.args
                self.assertEqual(destination, self.directory / subject.CONFIG)
                self.assert_explicit_engine_arguments(config['arguments'], expected)
                self.assertEqual(config['arguments'], original)
                self.assertEqual(flags, original)
                authorize.assert_called_once_with(self.directory)
                self.assertEqual(json.loads(output.getvalue())['start_request_id'], 'fake-intent')
                self.assertFalse((self.directory / subject.CONFIG).exists())
                self.assertFalse((self.directory / 'guardian-intents').exists())
                self.exec.assert_not_called()

    def test_legacy_entry_points_forward_existing_cli_flags_exactly(self):
        flags = ['--hours', '24', '--max-restarts', '-1', '--token-budget', '5000', '--agent-windows', 'off']
        with patch.object(subject, 'main', return_value=7) as entry:
            self.assertEqual(overnight.launch_legacy(flags), 7)
            entry.assert_called_once_with(['start'], engine_arguments=flags)
            self.assertEqual(flags[1], '24')
            entry.reset_mock()
            self.assertEqual(overnight.main(['status']), 7)
            entry.assert_called_once_with(['status'])

    def test_engine_exec_preserves_flags_and_authenticated_recovery_lineage(self):
        guard, launch = self.engine_fixture()
        self.write(subject.CONFIG, {'repo': str(self.repo),
                   'arguments': self.arguments + ['--fresh-session', '--fresh-on-recovery']})
        with patch.object(subject, 'process_start', return_value=guard['start']), \
                patch.object(subject, 'lease_free', side_effect=lambda directory, name: name != 'guardian.lock'):
            subject.engine(self.repo, self.directory)
        executable, command = self.exec.call_args.args
        self.assertEqual(executable, '/fake/systemd-inhibit')
        self.assertEqual(command[command.index('-c') + 1], '0,6,7')
        index = command.index(str(self.repo / 'scripts/run_os_goal.py'))
        parsed = launcher.arguments(command[index + 1:])
        self.assertTrue(parsed.supervisor)
        self.assertFalse(parsed.worker)
        self.assertFalse(parsed.recovered)
        self.assertFalse(parsed.fresh_session)
        self.assertFalse(parsed.fresh_on_recovery)
        self.assertEqual(parsed.guardian_run_id, guard['run_id'])
        self.assertEqual(parsed.guardian_recovery_proof, Path(launch['proof_path']))
        self.assertEqual(parsed.max_agents, 2)
        self.assertFalse(parsed.repair_agent_failures)
        self.assertFalse(parsed.stop_after_m14_m15)

    def test_engine_rejects_stale_guardian_or_mismatched_launch_without_exec(self):
        guard, launch = self.engine_fixture()
        for changes in ({'run_id': 'b' * 32}, {'guardian_pid': 42}, {'guardian_start': '999'}):
            with self.subTest(changes=changes):
                self.write(subject.NEXT, dict(launch, **changes))
                with patch.object(subject, 'process_start', return_value=guard['start']), \
                        patch.object(subject, 'lease_free', return_value=False), self.assertRaises(RuntimeError):
                    subject.engine(self.repo, self.directory)
                self.exec.assert_not_called()
        self.write(subject.NEXT, launch)
        for actual_birth, free in (('999', False), (guard['start'], True)):
            with patch.object(subject, 'process_start', return_value=actual_birth), \
                    patch.object(subject, 'lease_free', return_value=free), self.assertRaises(RuntimeError):
                subject.engine(self.repo, self.directory)
            self.exec.assert_not_called()

    def test_busy_engine_callback_never_overwrites_receipt_or_submits_start(self):
        guard = self.live_guard()
        self.write(subject.NEXT, {'preserved': 'pending prior launch'})
        original = (self.directory / subject.NEXT).read_bytes()
        self.systemctl.return_value = 'deactivating'
        with patch.object(subject, 'process_start', return_value=guard['start']), \
                self.assertRaises(subject.EngineLaunchDeferred):
            subject._launch_engine(self.repo, self.directory, self.directory / 'proof.json')
        self.assertEqual((self.directory / subject.NEXT).read_bytes(), original)
        self.assertFalse(any(call.args[0] == 'start' for call in self.systemctl.call_args_list))

    def test_idle_engine_submission_persists_guardian_identity_and_proof_before_start(self):
        guard = self.live_guard()
        proof = self.directory / 'guardian-recovery-exact.json'
        def systemctl(*arguments, **kwargs):
            if arguments[0] == 'show':
                return 'inactive'
            self.assertEqual(arguments, ('start', self.names['engine']))
            row = protocol.read_json(self.directory / subject.NEXT)
            self.assertEqual(row['run_id'], guard['run_id'])
            self.assertEqual(row['guardian_pid'], guard['pid'])
            self.assertEqual(row['guardian_start'], guard['start'])
            self.assertEqual(row['proof_path'], str(proof))
            return ''
        self.systemctl.side_effect = systemctl
        with patch.object(subject, 'process_start', return_value=guard['start']):
            result = subject._launch_engine(self.repo, self.directory, proof)
        self.assertTrue(result['started'])
        self.assertEqual(sum(call.args[0] == 'start' for call in self.systemctl.call_args_list), 1)

    def test_status_reports_real_mailbox_schema_without_claiming_email(self):
        guard = self.live_guard()
        self.write('mailbox-state.json', {
            'last_poll_at': 100, 'last_successful_poll_at': 99, 'next_poll_at': 160,
            'last_error': None, 'pending_resumes': [{'request_id': 'reply'}],
            'active_notice_event_id': 'event',
            'notices': {'event': {'requested': True, 'observed_comment_id': 1234}},
        })
        with patch.object(subject, 'process_start', return_value=guard['start']), \
                patch.object(subject, 'lease_free', return_value=False):
            result = subject.status(self.repo, self.directory)
        self.assertTrue(result['guardian_live'])
        mailbox = result['mailbox']
        self.assertEqual(mailbox['pending_resumes'], [{'request_id': 'reply'}])
        self.assertEqual(mailbox['last_successful_poll_at'], 99)
        self.assertTrue(mailbox['notice_requested'] and mailbox['observed_notice'])
        self.assertEqual(mailbox['observed_comment_id'], 1234)
        self.assertNotIn('email_delivered', mailbox)

    def test_dry_run_renders_without_authorization_network_or_service_actions(self):
        output = io.StringIO()
        with patch.object(subject, 'REPO', self.repo), \
                patch.object(subject, 'runtime_directory', return_value=self.directory), \
                patch.object(guardian, 'authorize_start') as authorize, redirect_stdout(output):
            self.assertEqual(subject.main(['dry-run']), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['status'], 'DRY_RUN')
        self.assertEqual(result['model_calls'], 0)
        self.assertEqual(set(result['units']), set(self.names.values()))
        authorize.assert_not_called()
        self.systemctl.assert_not_called()
        self.install.assert_not_called()
        self.preflight.assert_not_called()
        self.exec.assert_not_called()

    def test_stop_requests_checkpoint_without_stopping_monitor_or_engine_unit(self):
        output = io.StringIO()
        with patch.object(subject, 'runtime_directory', return_value=self.directory), \
                patch.object(subject, 'lease_free', return_value=False), redirect_stdout(output):
            self.assertEqual(subject.main(['stop']), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['status'], 'STOP_REQUESTED')
        self.assertEqual(protocol.read_json(self.directory / 'guardian-stop.json')['status'], 'pending')
        self.systemctl.assert_not_called()
        self.exec.assert_not_called()


    def test_guardian_retains_resume_reply_when_status_feed_fails_after_watchdog_ping(self):
        import os_goal_mailbox as mailbox_module
        import os_goal_status_feed as feed_module
        events, replies = [], []
        reply = {'status': 'POLLED', 'resume_request_id': 'github-comment-123',
                 'resume_created_at': 900}
        mailbox, feed, monitor = Mock(), Mock(), Mock()
        mailbox.poll.side_effect = lambda context: events.append('mailbox') or reply
        def broken_feed(context):
            events.append('feed')
            raise TypeError('Synthetic malformed status telemetry')
        feed.tick.side_effect = broken_feed
        monitor.run.return_value = 0
        with patch.object(mailbox_module, 'Mailbox', return_value=mailbox), \
                patch.object(feed_module, 'StatusFeed', return_value=feed), \
                patch.object(guardian, 'sd_notify', side_effect=lambda message: events.append('notify')), \
                patch.object(guardian, 'Guardian', return_value=monitor) as constructor, \
                patch.object(subject.time, 'time', return_value=1000):
            def run_one_cycle():
                callback = constructor.call_args.kwargs['mailbox_poll']
                replies.append(callback(self.directory, {
                    'phase': 'HELD', 'engine_state': {'goal': {'status': 'blocked'}}}))
                return 0
            monitor.run.side_effect = run_one_cycle
            self.assertEqual(subject.guardian(self.repo, self.directory), 0)
        self.assertEqual(events, ['mailbox', 'notify', 'feed'])
        self.assertIs(replies[0], reply)
        failure = protocol.read_json(self.directory / 'status-text-state.json')
        self.assertEqual(failure['status'], 'ERROR')
        self.assertIn('Synthetic malformed status telemetry', failure['reason'])
        self.assertEqual(failure['next_refresh_at'], 1600)
        self.assertIs(constructor.call_args.kwargs['mailbox_ack'], mailbox.ack_resume)
        monitor.close.assert_called_once()
        self.systemctl.assert_not_called()
        self.exec.assert_not_called()


    def test_status_text_command_renders_locally_without_publication_or_start(self):
        import os_goal_status_feed as feed_module
        output = io.StringIO()
        feed = Mock()
        def preview(*args, **kwargs):
            self.assertEqual(args, ())
            self.assertEqual(kwargs, {'publish': False})
            (self.directory / 'status.txt').write_text('Complete local status preview\n')
            return {'status': 'GENERATED'}
        feed.tick.side_effect = preview
        with patch.object(subject, 'REPO', self.repo), \
                patch.object(subject, 'runtime_directory', return_value=self.directory), \
                patch.object(feed_module, 'StatusFeed', return_value=feed) as constructor, \
                patch.object(guardian, 'authorize_start') as authorize, redirect_stdout(output):
            self.assertEqual(subject.main(['status-text']), 0)
        self.assertEqual(output.getvalue(), 'Complete local status preview\n')
        constructor.assert_called_once_with(self.repo, self.directory)
        feed.tick.assert_called_once_with(publish=False)
        authorize.assert_not_called()
        self.systemctl.assert_not_called()
        self.install.assert_not_called()
        self.preflight.assert_not_called()
        self.exec.assert_not_called()

    def test_prepare_cli_is_read_only_and_does_not_authorize_or_install(self):
        import os_goal_overnight_prepare as preparation
        output = io.StringIO()
        prepared = {'status': 'PREPARED', 'model_calls': 0, 'services_started': False,
                    'monitoring': {'monitoring_ready': False}}
        with patch.object(subject, 'REPO', self.repo), \
                patch.object(subject, 'runtime_directory', return_value=self.directory), \
                patch.object(preparation, 'prepare_overnight', return_value=prepared) as prepare, \
                patch.object(guardian, 'authorize_start') as authorize, redirect_stdout(output):
            self.assertEqual(subject.main(['prepare']), 0)
        self.assertEqual(json.loads(output.getvalue()), prepared)
        prepare.assert_called_once_with(self.repo, self.directory)
        authorize.assert_not_called()
        self.install.assert_not_called()
        self.systemctl.assert_not_called()
        self.exec.assert_not_called()

    def test_status_live_guardian_does_not_imply_successful_first_mailbox_poll(self):
        import os_goal_readiness as readiness
        guard = self.live_guard()
        guard.update(started_at=1900, heartbeat_at=1999)
        self.write('guardian.json', guard)
        self.write('mailbox-state.json', {'last_poll_at': 1999, 'next_poll_at': 2599,
                                           'notices': {}, 'last_error': None})
        with patch.object(subject, 'process_start', return_value=guard['start']), \
                patch.object(subject, 'lease_free', return_value=False), \
                patch.object(readiness, 'process_start', return_value=guard['start']), \
                patch.object(readiness, 'lease_free', return_value=False), \
                patch.object(readiness.time, 'time', return_value=2000):
            result = subject.status(self.repo, self.directory)
        self.assertTrue(result['guardian_live'])
        self.assertTrue(result['readiness']['stages']['guardian']['ready'])
        self.assertFalse(result['readiness']['monitoring_ready'])
        self.assertIn('mailbox', result['readiness']['missing_stages'])

    def test_unit_install_verifies_linger_before_files_and_daemon_reload(self):
        import os_goal_power as power
        config_home = self.repo / 'isolated-user-config'
        units = config_home / 'systemd/user'
        events = []
        def verified_linger():
            self.assertFalse(units.exists())
            events.append('linger_verified')
            return {'enabled': True}
        def daemon_reload(*arguments, **kwargs):
            self.assertEqual(arguments, ('daemon-reload',))
            self.assertEqual(events, ['linger_verified'])
            self.assertEqual({path.name for path in units.iterdir()}, set(self.names.values()))
            events.append('daemon_reloaded')
            return ''
        self.systemctl.side_effect = daemon_reload
        with patch.dict(subject.os.environ, {'XDG_CONFIG_HOME': str(config_home)}), \
                patch.object(power, 'ensure_linger', side_effect=verified_linger):
            result = self.install_implementation(self.repo, self.directory)
        self.assertEqual(result, self.names)
        self.assertEqual(events, ['linger_verified', 'daemon_reloaded'])
        self.systemctl.assert_called_once_with('daemon-reload')

    def test_failed_linger_verification_refuses_unit_files_and_daemon_reload(self):
        import os_goal_power as power
        config_home = self.repo / 'isolated-user-config'
        with patch.dict(subject.os.environ, {'XDG_CONFIG_HOME': str(config_home)}), \
                patch.object(power, 'ensure_linger', side_effect=RuntimeError('Linger could not be verified')), \
                self.assertRaises(RuntimeError):
            self.install_implementation(self.repo, self.directory)
        self.assertFalse((config_home / 'systemd/user').exists())
        self.systemctl.assert_not_called()



if __name__ == '__main__':
    unittest.main()
