# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Prepared source only. Running requires separate admission; no real child is launched.
import importlib.util
import json
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('perf_supervisor', Path(__file__).with_name('serial_supervised.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SupervisorDecisionTests(unittest.TestCase):
    def test_deadline_during_staging_or_popen(self):
        worker = [{'state': 'S', 'rss': 0}]
        self.assertIsNone(module.decision(179.9, 0, None, worker, None, []))
        self.assertEqual(module.decision(180, 0, None, worker, None, []), 'OUTER_DEADLINE')

    def test_signal_in_launch_window(self):
        self.assertEqual(module.decision(1, 0, 15, [{'state': 'S', 'rss': 0}], None, []), 'SUPERVISOR_SIGNAL_15')

    def test_exited_leader_and_live_owned_child_is_not_success(self):
        members = [{'state': 'Z', 'rss': 0}, {'state': 'S', 'rss': 1}]
        self.assertEqual(module.decision(2, 0, None, members, object(), []), 'WORKER_EXIT_WITH_LIVE_GROUP')

    def test_preexec_grace_and_unexpected_after_grace(self):
        live = [{'state': 'S', 'rss': 1}]
        self.assertIsNone(module.decision(1, 0, None, live, None, []))
        self.assertEqual(module.decision(3, 0, None, live, None, live), 'UNEXPECTED_EXECUTABLE_AFTER_GRACE')

    def test_process_and_memory_limits(self):
        self.assertEqual(module.decision(2, 0, None, [{'state': 'S', 'rss': 0}] * 8, None, []), 'PROCESS_COUNT')
        self.assertEqual(module.decision(2, 0, None, [{'state': 'S', 'rss': 2147483649}], None, []), 'CHILD_RSS_PLANNING_LIMIT')

    def test_unknown_child_ownership_never_claims_join(self):
        self.assertEqual(module.group_retirement_state(False, []), 'UNKNOWN_GROUP_RETIREMENT')
        self.assertEqual(module.group_retirement_state(True, [{'state': 'S'}]), 'UNKNOWN_GROUP_RETIREMENT')
        self.assertEqual(module.group_retirement_state(True, [{'state': 'Z'}]), 'UNKNOWN_GROUP_RETIREMENT')
        self.assertEqual(module.group_retirement_state(True, []), 'JOINABLE')

    def test_normal_completion_and_failure_are_separate_from_decision(self):
        self.assertIsNone(module.decision(2, 0, None, [{'state': 'Z', 'rss': 0}], object(), []))
        # Group census, waitpid status and worker evidence still decide acceptance.


class WorkerLaunchFailureTests(unittest.TestCase):
    # Mocks prevent all command execution; use fresh temporary output only.
    def run_fake_worker(self, popen):
        old_term = signal.getsignal(signal.SIGTERM)
        old_int = signal.getsignal(signal.SIGINT)
        try:
            with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ, clear=False), \
                 mock.patch.object(module, 'verified', side_effect=lambda path, wanted: wanted), \
                 mock.patch.object(module.subprocess, 'Popen', side_effect=popen):
                root = Path(temp)
                result = module.worker(root)
                record = json.loads((root / 'worker.json').read_text())
                stages = {name: json.loads((root / (name + '.json')).read_text())
                          for name in ('compile', 'fixture') if (root / (name + '.json')).exists()}
                return result, record, stages
        finally:
            signal.signal(signal.SIGTERM, old_term)
            signal.signal(signal.SIGINT, old_int)

    def test_compile_spawn_exception_keeps_launch_intent(self):
        result, record, stages = self.run_fake_worker(OSError('mock spawn failure'))
        self.assertEqual(result, 1)
        self.assertEqual(record['status'], 'STOPPED_ERROR')
        self.assertEqual(stages['compile']['status'], 'LAUNCH_INTENT')
        self.assertNotIn('fixture', stages)

    def test_fixture_spawn_exception_after_compiler_join(self):
        fake = mock.Mock(pid=123, wait=mock.Mock(return_value=0))
        result, record, stages = self.run_fake_worker([fake, OSError('mock fixture spawn failure')])
        self.assertEqual(result, 1)
        self.assertEqual(record['status'], 'STOPPED_ERROR')
        self.assertEqual(stages['compile']['status'], 'LEADER_JOINED')
        self.assertEqual(stages['fixture']['status'], 'LAUNCH_INTENT')


if __name__ == '__main__':
    unittest.main()
