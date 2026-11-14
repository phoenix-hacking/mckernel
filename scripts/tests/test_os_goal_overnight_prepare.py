"""Preparation orchestration with fake external probes; no power changes."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_guardian as guardian
import os_goal_overnight_prepare as subject
import os_goal_power as power
import os_goal_service as service


REPO = Path(__file__).resolve().parents[2]


class OvernightPreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='overnight-prepare-test-')
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name) / 'runtime'
        self.binary_check = subject._binaries
        self.binaries = self.fake(subject, '_binaries', return_value={'required_executables_available': True})
        self.manager = self.fake(subject, '_manager', return_value={'user_manager_reachable': True})
        self.resources = self.fake(subject, '_resources', return_value={'available_memory_gib': 30})
        self.owners = self.fake(subject, '_owners', return_value={'model_and_submission_leases_free': True})
        self.public = self.fake(subject, '_public_status', return_value={'existing_status_file_verified': True})
        self.readiness = self.fake(subject, 'evaluate_readiness', return_value={
            'monitoring_ready': False, 'missing_stages': ['guardian', 'mailbox', 'publication']})
        self.linger = self.fake(power, 'check_linger', return_value={'enabled': True})
        self.inhibit = self.fake(power, 'probe_inhibition', return_value={'inhibition_verified': True})
        self.enable = self.fake(power, 'ensure_linger', side_effect=AssertionError('Preparation cannot enable lingering'))
        self.mailbox = self.fake(service, 'mailbox_preflight', return_value={'status': 'READ_ACCESS_VERIFIED'})
        self.authorize = self.fake(guardian, 'authorize_start', side_effect=AssertionError('Preparation cannot authorize'))
        self.install = self.fake(service, 'install_units', side_effect=AssertionError('Preparation cannot install'))
        self.external = self.fake(subject.subprocess, 'run', side_effect=AssertionError('External probes must be fake'))

    def fake(self, target, name, **kwargs):
        handle = patch.object(target, name, **kwargs)
        result = handle.start()
        self.addCleanup(handle.stop)
        return result

    def prepare(self, repo=REPO):
        result = subject.prepare_overnight(repo, self.directory)
        self.enable.assert_not_called()
        self.authorize.assert_not_called()
        self.install.assert_not_called()
        self.external.assert_not_called()
        self.assertFalse(self.directory.exists())
        self.assertEqual(result['model_calls'], 0)
        self.assertFalse(result['services_started'])
        return result

    def test_reviewed_defaults_are_checked_without_claiming_runtime_started(self):
        result = self.prepare()
        self.assertEqual(result['status'], 'PREPARED')
        config = result['checks']['configuration']['details']
        self.assertEqual((config['hours'], config['max_restarts']), (0, -1))
        self.assertTrue(config['repair_agent_failures'] and config['stop_after_m14_m15'])
        self.assertEqual((config['max_agents'], config['build_jobs'], config['memory_gib_total']), (2, 3, 4))
        self.assertEqual((config['mailbox_poll_seconds'], config['status_refresh_seconds']), (600, 600))
        self.assertFalse(result['monitoring']['monitoring_ready'])

    def test_missing_executable_is_blocked_without_start_or_install(self):
        self.binaries.side_effect = self.binary_check
        with patch.object(subject.shutil, 'which', side_effect=lambda name: None if name == 'gh' else '/fake/' + name):
            result = self.prepare()
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('executables', result['blocked_checks'])
        self.assertIn('gh', result['checks']['executables']['reason'])

    def test_resource_rejection_is_reported_without_creating_authority(self):
        self.resources.side_effect = RuntimeError('Insufficient resources: retain the 26 GiB requirement')
        result = self.prepare()
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('resources', result['blocked_checks'])

    def test_missing_instruction_input_blocks_configuration_and_dependent_checks(self):
        repo = self.directory.parent / 'missing-input-repo'
        repo.mkdir()
        result = self.prepare(repo)
        self.assertIn('configuration', result['blocked_checks'])
        self.binaries.assert_not_called()
        self.resources.assert_not_called()

    def test_disabled_linger_needs_setup_without_enabling_it(self):
        self.linger.return_value = {'enabled': False}
        result = self.prepare()
        self.assertEqual(result['status'], 'SETUP_NEEDED')
        self.assertEqual(result['setup_checks'], ['logout_persistence'])
        self.assertIn('explicit start command', result['checks']['logout_persistence']['next_action'])

    def test_unreachable_user_manager_is_an_explicit_blocker(self):
        self.manager.side_effect = RuntimeError('User service manager unavailable')
        result = self.prepare()
        self.assertIn('user_service_manager', result['blocked_checks'])
        self.assertEqual(result['status'], 'BLOCKED')

    def test_github_identity_failure_skips_status_probe_and_retains_no_start(self):
        self.mailbox.side_effect = RuntimeError('GitHub identity or network unavailable')
        result = self.prepare()
        self.assertIn('github_identity_and_mailbox', result['blocked_checks'])
        self.public.assert_not_called()

    def test_missing_public_status_is_not_confused_with_github_mailbox_access(self):
        self.public.side_effect = RuntimeError('The fixed public status file is unavailable')
        result = self.prepare()
        self.assertEqual(result['checks']['github_identity_and_mailbox']['status'], 'PASS')
        self.assertIn('github_status_file', result['blocked_checks'])

    def test_inhibitor_failure_is_reported_without_power_fallback(self):
        self.inhibit.side_effect = RuntimeError('Inhibitor permission unavailable')
        result = self.prepare()
        self.assertIn('sleep_and_lid_inhibitor_permission', result['blocked_checks'])


if __name__ == '__main__':
    unittest.main()
