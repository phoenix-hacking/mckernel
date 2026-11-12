"""Offline startup/resume and policy-stop regressions; no inference or OS payloads."""
import json
import unittest

import test_os_goal_launcher as fixtures


class WorkScopeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.CampaignTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def test_new_campaign_sends_engineering_scope_before_work_starts(self):
        def finish(rpc):
            rpc.completed()
            rpc.status('blocked')

        rpc = fixtures.FakeRPC(self.fixture.args, steps=[finish])
        state = self.fixture.run_campaign(rpc, 20)
        start = next(params for method, params in rpc.calls if method == 'thread/start')
        instructions = start['developerInstructions']
        self.assertIn('no security testing', instructions)
        self.assertIn('original M14/M15', instructions)
        self.assertIn('every delegated task', instructions)
        self.assertIn('Do not retry, rephrase or reassign the rejected task', instructions)
        self.assertEqual(start['model'], 'gpt-6.1-sol')
        self.assertEqual(state['goal']['objective'], fixtures.launcher.OBJECTIVE)

    def test_manual_resume_retains_failed_task_identity_after_startup_state_changes(self):
        goal = fixtures.goal('paused')
        self.fixture.saved(goal)
        path = self.fixture.directory / 'state.json'
        state = json.loads(path.read_text())
        error = {'codexErrorInfo': 'cyberPolicy', 'message': 'recorded service rejection'}
        state.update(log_dir='previous-run', stop_reason='turn_failed', last_error=error,
                     last_failure={'thread_id': 'rejected-worker', 'id': 'rejected-turn',
                                   'log_dir': 'previous-run', 'error': error})
        fixtures.launcher.atomic_json(path, state)
        self.fixture.startup_arguments()

        def finish(rpc):
            rpc.completed()
            rpc.status('blocked')

        # The fake server accepts this explicit resume; no real service hold is cleared.
        rpc = fixtures.FakeRPC(self.fixture.args, goal, steps=[finish])
        state = self.fixture.run_campaign(rpc, 20)
        resume = next(params for method, params in rpc.calls if method == 'thread/resume')
        self.assertEqual(resume['threadId'], 'test-thread')
        self.assertIn('no security testing', resume['developerInstructions'])
        prompts = '\n'.join(item['text'] for method, params in rpc.calls
                            if method in ('turn/start', 'turn/steer')
                            for item in params['input'] if item['type'] == 'text')
        self.assertIn('thread=rejected-worker; turn=rejected-turn', prompts)
        self.assertIn('task remains excluded from replay or reassignment', prompts)
        self.assertIn('not service/account clearance', prompts)
        self.assertEqual(state['last_failure']['id'], 'rejected-turn')
        self.assertEqual(state['goal']['tokensUsed'], goal['tokensUsed'])
        self.assertFalse(any(method == 'thread/start' for method, _ in rpc.calls))

    def test_stale_policy_error_does_not_quarantine_a_later_user_pause(self):
        self.fixture.saved(fixtures.goal('paused'))
        path = self.fixture.directory / 'state.json'
        state = json.loads(path.read_text())
        state.update(stop_reason='signal_15', last_error={'codexErrorInfo': 'cyberPolicy'})
        fixtures.launcher.atomic_json(path, state)
        campaign = fixtures.launcher.Campaign(self.fixture.args, self.fixture.directory,
                                             self.fixture.directory)
        try:
            self.assertNotIn('Preserved policy rejection:', campaign.manual_resume_instruction(''))
        finally:
            campaign.output.close()


if __name__ == '__main__':
    unittest.main()
