"""Source-only fault injections. Not run; review/admission required first.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
These inject failures into actual owner_candidate functions; they do not launch
real processes or establish timeout/OS process-group behavior.
"""
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location('owner_candidate', Path(__file__).with_name('owner_candidate.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class Handshake(unittest.TestCase):
    def test_wrong_group_parent_and_reused_worker_are_rejected(self):
        anchor = {'pid': 10, 'pgid': 10, 'sid': 10}
        worker = {'pid': 11, 'ppid': 10, 'pgid': 10, 'sid': 10, 'state': 'S', 'start': 42}
        runner.check_handshake(anchor, worker, 11, 42)
        for change in ({'ppid': 12}, {'pgid': 12}, {'sid': 12}, {'start': 43}, {'state': 'Z'}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                runner.check_handshake(anchor, dict(worker, **change), 11, 42)

    def test_eof_gate_cannot_begin_staging(self):
        stat = {'pid': 11}
        with mock.patch.object(runner, 'stat_pid', return_value=stat), \
                mock.patch.object(runner.os, 'getpid', return_value=11), \
                mock.patch.object(runner.os, 'write'), mock.patch.object(runner.os, 'close'), \
                mock.patch.object(runner, 'read_message', side_effect=RuntimeError('EOF')), \
                mock.patch.object(runner, 'verify') as verify:
            with self.assertRaisesRegex(RuntimeError, 'EOF'):
                runner.gated_worker(Path('/inert'), 1, 2)
            verify.assert_not_called()

    def test_read_message_eof_is_failure(self):
        with mock.patch.object(runner.select, 'select', return_value=([3], [], [])), \
                mock.patch.object(runner.os, 'read', return_value=b''):
            with self.assertRaisesRegex(RuntimeError, 'EOF'):
                runner.read_message(3, runner.time.monotonic() + 10)


class FamilyRetirement(unittest.TestCase):
    def setUp(self):
        self.process = mock.Mock(pid=12)
        self.process.wait.return_value = 0
        self.base = [{'pid': 10, 'state': 'S'}, {'pid': 11, 'state': 'S'},
                     {'pid': 12, 'state': 'Z'}]

    def test_live_or_zombie_compiler_descendant_blocks_fixture_barrier(self):
        for state in ('S', 'Z'):
            samples = [self.base + [{'pid': 13, 'state': state}], self.base]
            with self.subTest(state=state), \
                    mock.patch.object(runner.os, 'waitid', return_value=object()), \
                    mock.patch.object(runner, 'census', side_effect=samples), \
                    mock.patch.object(runner.time, 'sleep') as sleep:
                self.assertEqual(runner.retire_stage(self.process, 10, {10, 11}), (0, self.base))
                sleep.assert_called_once()
                self.process.wait.assert_called_once()
                self.process.wait.reset_mock()

    def test_census_failure_never_reaps_or_authorizes(self):
        with mock.patch.object(runner.os, 'waitid', return_value=object()), \
                mock.patch.object(runner, 'census', side_effect=PermissionError('procfs')):
            with self.assertRaises(PermissionError):
                runner.retire_stage(self.process, 10, {10, 11})
        self.process.wait.assert_not_called()

    def test_missing_anchor_is_unknown(self):
        with mock.patch.object(runner.os, 'waitid', return_value=object()), \
                mock.patch.object(runner, 'census', return_value=self.base[1:]):
            with self.assertRaisesRegex(RuntimeError, 'UNKNOWN'):
                runner.retire_stage(self.process, 10, {10, 11})
        self.process.wait.assert_not_called()

    def test_retirement_fault_prevents_fixture_launch(self):
        with mock.patch.object(runner, 'write_json'), \
                mock.patch.object(Path, 'open', mock.mock_open()), \
                mock.patch.object(runner.subprocess, 'Popen', return_value=self.process) as launch, \
                mock.patch.object(runner, 'guarded_stage', side_effect=RuntimeError('UNKNOWN')):
            with self.assertRaisesRegex(RuntimeError, 'UNKNOWN'):
                runner.run_stages(Path('/inert'), {}, 10, {10, 11})
        self.assertEqual(launch.call_count, 1)
        self.assertEqual(launch.call_args.args[0][0], runner.RUSTC)

    def test_failed_compile_never_starts_fixture(self):
        with mock.patch.object(runner, 'write_json'), \
                mock.patch.object(Path, 'open', mock.mock_open()), \
                mock.patch.object(runner.subprocess, 'Popen', return_value=self.process) as launch, \
                mock.patch.object(runner, 'guarded_stage', return_value=(1, [])):
            self.assertEqual(runner.run_stages(Path('/inert'), {}, 10, {10, 11}), 'compile')
        self.assertEqual(launch.call_count, 1)


class OwnedTermination(unittest.TestCase):
    def test_unverified_anchor_is_never_signaled(self):
        with mock.patch.object(runner, 'check_anchor', side_effect=RuntimeError('identity')), \
                mock.patch.object(runner.os, 'killpg') as signal_group:
            with self.assertRaisesRegex(RuntimeError, 'identity'):
                runner.terminate_owned(10, 42, {})
        signal_group.assert_not_called()

    def test_changed_anchor_prevents_escalation(self):
        times = iter([0.0, 5.0])
        with mock.patch.object(runner, 'check_anchor', side_effect=[{}, RuntimeError('changed')]), \
                mock.patch.object(runner.os, 'killpg') as signal_group, \
                mock.patch.object(runner.time, 'monotonic', side_effect=lambda: next(times)):
            with self.assertRaisesRegex(RuntimeError, 'changed'):
                runner.terminate_owned(10, 42, {})
        signal_group.assert_called_once_with(10, runner.signal.SIGTERM)


if __name__ == '__main__':
    unittest.main()
