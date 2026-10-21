"""Private harmless-child regression; never imports or executes capture admission."""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import stat
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / 'capture_os_critical_operation.py'


def load_wait(writer):
    tree = ast.parse(SOURCE.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == 'wait_with_progress')
    scope = dict(os=os, json=json, time=time, subprocess=subprocess, sys=sys, write=writer)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), scope)
    return scope['wait_with_progress']


class CaptureProgressTests(unittest.TestCase):
    def test_quarantine_is_visible_before_direct_join(self):
        with tempfile.TemporaryDirectory(prefix='capture-progress-test-') as directory:
            run = Path(directory)
            def write(name, value):
                with (run / name).open('x') as stream:
                    json.dump(value, stream)
            wait = load_wait(write)
            payload = (b'{"status":"QUARANTINED_ROOT_LOCK_HELD",'
                       b'"requires":"independent-exact-state-reconciliation"}\n')
            program = ('import os,sys;os.write(1,' + repr(payload) + ');'
                       'sys.stdin.buffer.read(1);sys.exit(7)')
            results, errors = [], []
            console = io.StringIO()
            terminal_stdout = io.StringIO()
            with (run / 'stdout').open('xb') as stdout, (run / 'stderr').open('xb') as stderr:
                child = subprocess.Popen([sys.executable, '-I', '-B', '-c', program],
                                         stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                         start_new_session=True)
                birth = Path('/proc/' + str(child.pid) + '/stat').read_text().rsplit(')', 1)[1].split()[19]
                def worker():
                    try:
                        results.append(wait(child, run, child.pid, birth, time.monotonic()))
                    except BaseException as error:
                        errors.append(error)
                thread = threading.Thread(target=worker)
                with contextlib.redirect_stderr(console), contextlib.redirect_stdout(terminal_stdout):
                    thread.start()
                    try:
                        quarantine = run / 'progress-quarantine_marker_observed.json'
                        deadline = time.monotonic() + 5
                        while (not quarantine.exists() or 'QUARANTINE_MARKER_OBSERVED' not in console.getvalue()) and not errors and time.monotonic() < deadline:
                            time.sleep(0.02)
                        self.assertTrue(quarantine.exists(), str(errors))
                        # The file may be observed between exclusive open and close.
                        thread_deadline = time.monotonic() + 1
                        while True:
                            try:
                                event = json.loads(quarantine.read_text())
                                break
                            except json.JSONDecodeError:
                                if time.monotonic() >= thread_deadline:
                                    raise
                                time.sleep(0.01)
                        self.assertTrue(thread.is_alive())
                        self.assertIsNone(child.poll())
                        self.assertEqual(event['pid'], child.pid)
                        self.assertEqual(event['proc_start_ticks'], birth)
                        self.assertEqual(event['capture_directory'], str(run))
                        self.assertFalse(event['terminal'])
                        self.assertFalse(event['direct_child_joined'])
                        self.assertFalse(event['release_authorized'])
                        self.assertFalse((run / 'status.json').exists())
                        self.assertFalse((run / 'direct-join.json').exists())
                        self.assertIn('QUARANTINE_MARKER_OBSERVED', console.getvalue())
                    finally:
                        # Voluntary gate release only: never signal or kill the child.
                        child.stdin.write(b'x')
                        child.stdin.flush()
                        child.stdin.close()
                        thread.join(timeout=5)
                        child.wait()
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(results, [7])
                try:
                    os.killpg(child.pid, 0)
                except ProcessLookupError:
                    group_absent = True
                else:
                    group_absent = False
                self.assertTrue(group_absent)
                print('CONTROLLED_CHILD ' + json.dumps(dict(pid=child.pid,
                      proc_start_ticks=birth, direct_child_joined=True,
                      returncode=child.returncode, process_group_absent=group_absent)), file=sys.stderr)
            self.assertEqual((run / 'stdout').read_bytes(), payload)
            self.assertEqual((run / 'stderr').read_bytes(), b'')
            self.assertEqual(terminal_stdout.getvalue(), '')
            events = [json.loads(line.removeprefix('CAPTURE_PROGRESS ')) for line in console.getvalue().splitlines()]
            self.assertEqual([e['event'] for e in events],
                             ['CHILD_JOIN_PENDING', 'QUARANTINE_MARKER_OBSERVED'])
            self.assertEqual(len(list(run.glob('progress-*.json'))), 2)

    def test_progress_io_error_does_not_abandon_direct_join(self):
        def broken_writer(name, value):
            raise OSError('controlled visibility write failure')
        wait = load_wait(broken_writer)
        with tempfile.TemporaryDirectory(prefix='capture-progress-test-') as directory:
            run = Path(directory)
            with (run / 'stdout').open('xb') as stdout:
                child = subprocess.Popen([sys.executable, '-I', '-B', '-c', 'pass'], stdout=stdout, start_new_session=True)
                birth = Path('/proc/' + str(child.pid) + '/stat').read_text().rsplit(')', 1)[1].split()[19]
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(wait(child, run, child.pid, 'test-birth', time.monotonic()), 0)
                self.assertIsNotNone(child.returncode)
                try:
                    os.killpg(child.pid, 0)
                except ProcessLookupError:
                    group_absent = True
                else:
                    group_absent = False
                self.assertTrue(group_absent)
                print('CONTROLLED_CHILD ' + json.dumps(dict(pid=child.pid,
                      proc_start_ticks=birth, direct_child_joined=True,
                      returncode=child.returncode, process_group_absent=group_absent)), file=sys.stderr)

    def test_malformed_prefix_is_not_quarantine(self):
        class FakeChild:
            attempts = 0
            def wait(self, timeout):
                self.attempts += 1
                if self.attempts == 1:
                    raise subprocess.TimeoutExpired('controlled', timeout)
                return 0
        with tempfile.TemporaryDirectory(prefix='capture-progress-test-') as directory:
            run = Path(directory)
            (run / 'stdout').write_bytes(b'QUARANTINED_ROOT_LOCK_HELD\n')
            events = []
            wait = load_wait(lambda name, value: events.append(value))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(wait(FakeChild(), run, 123, '456', time.monotonic()), 0)
            self.assertEqual([e['event'] for e in events], ['CHILD_JOIN_PENDING'])



class LauncherProgressTests(unittest.TestCase):
    def test_registered_files_surface_during_tool_wait_without_completion(self):
        tree = ast.parse(SOURCE.with_name('run_os_goal.py').read_text())
        campaign = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Campaign')
        node = next(n for n in campaign.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'poll_capture_progress')
        scope = dict(os=os, json=json, stat=stat)
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<private-launcher-poll>', 'exec'), scope)
        poll = scope['poll_capture_progress']
        with tempfile.TemporaryDirectory(prefix='capture-progress-launcher-') as directory:
            run = Path(directory)
            notices = []
            state = dict(active_turns={'coordinator': 'toolwaitactive'}, goal={'status': 'active'})
            fake = SimpleNamespace(capture_progress_directory=run,
                capture_progress_accepted={}, capture_progress_notices=set(), state=state,
                output=SimpleNamespace(notice=notices.append))
            poll(fake)
            self.assertEqual([r['observation'] for r in state['capture_progress']],
                             ['awaiting_file', 'awaiting_file'])
            quarantine = run / 'progress-quarantine_marker_observed.json'
            quarantine.write_text('{')
            poll(fake)
            self.assertEqual(state['capture_progress'][1]['observation'], 'invalid_file')
            for event in ('CHILD_JOIN_PENDING', 'QUARANTINE_MARKER_OBSERVED'):
                data = dict(schema='capture-progress.v1', event=event, terminal=False,
                            direct_child_joined=False, release_authorized=False,
                            pid=123, proc_start_ticks='456', capture_directory=str(run))
                (run / ('progress-' + event.lower() + '.json')).write_text(json.dumps(data))
            poll(fake)
            count = len(notices)
            poll(fake)
            self.assertEqual(len(notices), count)
            self.assertEqual(state['capture_progress'][1]['observation'], 'QUARANTINE_MARKER_OBSERVED')
            self.assertEqual(state['active_turns'], {'coordinator': 'toolwaitactive'})
            self.assertEqual(state['goal'], {'status': 'active'})
            self.assertTrue(all(r['terminal'] is False and r['direct_child_joined'] is False
                                and r['release_authorized'] is False for r in state['capture_progress']))
            self.assertTrue(any('QUARANTINE_MARKER_OBSERVED' in text for text in notices))
            self.assertTrue(any('invalid_file' in text for text in notices))

    def test_terminal_shaped_progress_is_rejected(self):
        tree = ast.parse(SOURCE.with_name('run_os_goal.py').read_text())
        campaign = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Campaign')
        node = next(n for n in campaign.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'poll_capture_progress')
        scope = dict(os=os, json=json, stat=stat)
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<private-launcher-poll>', 'exec'), scope)
        with tempfile.TemporaryDirectory(prefix='capture-progress-launcher-') as directory:
            run = Path(directory)
            data = dict(schema='capture-progress.v1', event='CHILD_JOIN_PENDING', terminal=True,
                        direct_child_joined=True, release_authorized=True,
                        pid=123, proc_start_ticks='456', capture_directory=str(run))
            (run / 'progress-child_join_pending.json').write_text(json.dumps(data))
            fake = SimpleNamespace(capture_progress_directory=run,
                capture_progress_accepted={}, capture_progress_notices=set(), state={},
                output=SimpleNamespace(notice=lambda text: None))
            scope['poll_capture_progress'](fake)
            self.assertEqual(fake.state['capture_progress'][0]['observation'], 'invalid_file')

if __name__ == '__main__':
    unittest.main()
