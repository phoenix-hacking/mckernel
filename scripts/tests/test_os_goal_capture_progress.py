"""No subprocesses: AST-extracted queue/registration/read methods and fake RPC."""
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import tempfile
import time
from types import SimpleNamespace
import unittest
from uuid import uuid4

SOURCE = Path(__file__).resolve().parents[1] / 'run_os_goal.py'


def extracted():
    tree = ast.parse(SOURCE.read_text())
    names = {'utc', 'atomic_json', 'validate_capture_progress_directory', 'queue_instruction'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    campaign = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Campaign')
    methods = [node for node in campaign.body if isinstance(node, ast.FunctionDef)
               and node.name in {'register_instruction_capture_progress', 'deliver_instruction', 'poll_capture_progress'}]
    version = next(node for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'CAPTURE_PROGRESS_CAPABILITY'
                           for target in node.targets))
    capability = ast.literal_eval(version.value)
    scope = dict(CAPTURE_PROGRESS_CAPABILITY=capability, datetime=datetime, timezone=timezone, json=json, os=os, Path=Path,
                 stat=stat, tempfile=tempfile, uuid4=uuid4)
    exec(compile(ast.Module(body=nodes + methods, type_ignores=[]), '<private-queue-methods>', 'exec'), scope)
    fixture = type('FixtureCampaign', (), {node.name: scope[node.name] for node in methods})
    return scope, fixture


class QueueRegistrationTests(unittest.TestCase):
    def fixture(self, directory):
        scope, cls = extracted()
        campaign = cls()
        campaign.directory = Path(directory)
        campaign.log_dir = Path(directory) / 'runs' / 'instance-a'
        campaign.state = dict(schema_version=1, capture_progress_capability=scope['CAPTURE_PROGRESS_CAPABILITY'],
                              phase='running', thread_id='thread-a',
                              worker_pid=os.getpid(), log_dir=str(campaign.log_dir))
        campaign.controlled = True
        campaign.checkpoint_requested = False
        campaign.stop_reason = None
        campaign.goal = {'status': 'active'}
        campaign.active = {'thread-a': 'turn-a'}
        campaign.capture_progress_directory = None
        campaign.capture_progress_accepted = {}
        campaign.capture_progress_notices = set()
        campaign.calls, campaign.notices = [], []
        def save(**fields):
            campaign.state.update(fields)
            scope['atomic_json'](Path(directory) / 'state.json', campaign.state)
        campaign.save = save
        campaign.output = type('Output', (), {'notice': staticmethod(campaign.notices.append)})()
        def rpc_call(method, params):
            # Observe the saved acknowledgment at precisely the steering boundary.
            saved = json.loads((Path(directory) / 'state.json').read_text())
            campaign.calls.append((method, params, saved))
            return {}
        campaign.rpc = type('RPC', (), {'call': staticmethod(rpc_call)})()
        campaign.save()
        return scope, campaign

    def test_new_instance_archives_old_hints_and_clears_live_view_with_or_without_new_path(self):
        for explicit in (False, True):
            with self.subTest(explicit=explicit), tempfile.TemporaryDirectory(prefix='capture-resume-test-') as directory:
                scope, fixture_class = extracted()
                tree = ast.parse(SOURCE.read_text())
                cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Campaign')
                init = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
                root = Path(directory)
                repo = root / 'repo'
                old_capture = root / 'old-capture'
                old_capture.mkdir()
                old_artifact = old_capture / 'progress-quarantine_marker_observed.json'
                old_artifact.write_text('{"preserved":"old original evidence"}')
                old_receipt = root / 'old-instruction.receipt.json'
                old_receipt.write_text('{"status":"accepted_by_server","preserved":true}')
                original_files = {p: p.read_bytes() for p in (old_artifact, old_receipt)}
                old_registration = dict(directory=str(old_capture), registered_at='2026-10-21T19:00:00+00:00')
                old_rows = [dict(observation='QUARANTINE_MARKER_OBSERVED', pid=99,
                                 proc_start_ticks='123', terminal=False)]
                saved = dict(schema_version=1, repo=str(repo), thread_id='existing-thread',
                    worker_pid=999, log_dir='/previous-instance', goal={'status':'active'},
                    agent_event_count=41, capture_progress_registration=old_registration,
                    capture_progress=old_rows)
                (root / 'state.json').write_text(json.dumps(saved))
                class FakeOutput:
                    def __init__(self, log_dir, quiet, agent_windows):
                        self.primary = None
                scope.update(RPC=object(), LiveOutput=FakeOutput, time=time)
                exec(compile(ast.Module(body=[init], type_ignores=[]), '<private-real-init>', 'exec'), scope)
                instance = fixture_class()
                fresh = root / 'future-capture' if explicit else None
                args = SimpleNamespace(quiet=True, agent_windows='off', capture_progress_directory=fresh)
                scope['__init__'](instance, args, repo, root)
                self.assertEqual(instance.state['capture_progress'], [])
                self.assertEqual(instance.state['goal'], {'status':'active'})
                self.assertEqual(instance.state['agent_event_count'], 41)
                self.assertEqual(instance.state['thread_id'], 'existing-thread')
                history = json.loads((instance.log_dir / 'prior-capture-progress.json').read_text())
                self.assertEqual(history['classification'], 'historical_inactive_instance_hints')
                self.assertEqual(history['previous_worker_pid'], 999)
                self.assertEqual(history['previous_log_dir'], '/previous-instance')
                self.assertEqual(history['hints']['capture_progress_registration'], old_registration)
                self.assertEqual(history['hints']['capture_progress'], old_rows)
                for path, data in original_files.items():
                    self.assertEqual(path.read_bytes(), data)
                if explicit:
                    self.assertEqual(instance.capture_progress_directory, fresh)
                    self.assertEqual(instance.state['capture_progress_registration']['directory'], str(fresh))
                    notices = []
                    instance.output.notice = notices.append
                    instance.poll_capture_progress()
                    self.assertEqual([r['observation'] for r in instance.state['capture_progress']],
                                     ['awaiting_file', 'awaiting_file'])
                    self.assertTrue(all(str(fresh) in r['path'] for r in instance.state['capture_progress']))
                else:
                    self.assertIsNone(instance.capture_progress_directory)
                    self.assertNotIn('capture_progress_registration', instance.state)
                    # No output or old-file polling is possible without a registration.
                    instance.poll_capture_progress()
                    self.assertEqual(instance.state['capture_progress'], [])

    def test_old_or_incompatible_launcher_rejected_but_plain_instruction_works(self):
        for value in (None, True, 0, 2):
            with self.subTest(capability=value), tempfile.TemporaryDirectory(prefix='capture-capability-test-') as directory:
                scope, campaign = self.fixture(directory)
                if value is None:
                    campaign.state.pop('capture_progress_capability')
                else:
                    campaign.state['capture_progress_capability'] = value
                campaign.save()
                with self.assertRaisesRegex(ValueError, 'resident launcher'):
                    scope['queue_instruction'](Path(directory), 'Next capture', Path(directory) / 'future')
                self.assertFalse((Path(directory) / 'instructions' / 'pending').exists())
                # Plain instructions still queue without any advertised capability.
                ident = scope['queue_instruction'](Path(directory), 'Report current status')
                campaign.deliver_instruction()
                self.assertEqual(len(campaign.calls), 1)
                self.assertEqual(campaign.calls[0][1]['input'][0]['text'],
                                 'Live user instruction ' + ident + ':\nReport current status')

    def test_matching_capability_enqueues_and_mismatch_at_drain_refuses(self):
        for mismatch in ('state', 'metadata'):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory(prefix='capture-capability-test-') as directory:
                scope, campaign = self.fixture(directory)
                ident = scope['queue_instruction'](Path(directory), 'Next capture', Path(directory) / 'future')
                pending = Path(directory) / 'instructions' / 'pending' / (ident + '.json')
                item = json.loads(pending.read_text())
                self.assertEqual(item['capture_progress']['capability_version'], scope['CAPTURE_PROGRESS_CAPABILITY'])
                if mismatch == 'state':
                    campaign.state['capture_progress_capability'] = 2
                else:
                    item['capture_progress']['capability_version'] = 2
                    pending.write_text(json.dumps(item))
                original = pending.read_bytes()
                campaign.deliver_instruction()
                self.assertEqual(campaign.calls, [])
                self.assertEqual(campaign.state['last_instruction']['status'], 'registration_refused_before_steer')
                self.assertEqual((Path(directory) / 'instructions' / 'refused' / (ident + '.json')).read_bytes(), original)

    def test_real_save_advertises_capability_without_starting_campaign(self):
        tree = ast.parse(SOURCE.read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Campaign')
        node = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'save')
        scope, fixture = extracted()
        writes = []
        scope['atomic_json'] = lambda path, state: writes.append(dict(state))
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<private-real-save>', 'exec'), scope)
        output = type('Output', (), dict(snapshot=lambda self: {}, agent_event_count=0))()
        fake = type('SavedCampaign', (), {})()
        fake.state = {}
        fake.log_dir = Path('/private-fixture-run')
        fake.state_path = Path('/private-fixture-state.json')
        fake.active = {}
        fake.output = output
        scope['save'](fake, phase='running')
        self.assertEqual(writes[0]['capture_progress_capability'], scope['CAPTURE_PROGRESS_CAPABILITY'])

    def test_two_successive_registrations_persist_before_steer_and_monitor_new_path(self):
        with tempfile.TemporaryDirectory(prefix='capture-queue-test-') as directory:
            scope, campaign = self.fixture(directory)
            old_bytes = {}
            previous_path = None
            for index in (1, 2):
                path = Path(directory) / ('capture-' + str(index))
                ident = scope['queue_instruction'](Path(directory), 'Prepare next authorized capture', path)
                campaign.deliver_instruction()
                self.assertEqual(len(campaign.calls), index)
                method, params, saved = campaign.calls[-1]
                registration = saved['capture_progress_registration']
                self.assertEqual(method, 'turn/steer')
                self.assertEqual(params['threadId'], 'thread-a')
                self.assertEqual(params['expectedTurnId'], 'turn-a')
                self.assertEqual(registration['directory'], str(path))
                self.assertEqual(registration['instruction_id'], ident)
                self.assertIsNotNone(datetime.fromisoformat(registration['registered_at']).tzinfo)
                self.assertIn('Launcher visibility acknowledgment:', params['input'][0]['text'])
                self.assertFalse(registration['terminal'])
                self.assertFalse(registration['direct_child_joined'])
                self.assertFalse(registration['release_authorized'])
                receipt = json.loads((Path(directory) / 'instructions' / 'delivered' / (ident + '.json')).read_text())
                self.assertEqual(receipt['status'], 'accepted_by_server')
                if previous_path is not None:
                    self.assertEqual(receipt['previous_capture_progress_registration']['directory'], str(previous_path))
                    self.assertEqual(len(receipt['previous_capture_progress']), 2)
                path.mkdir()
                for event in ('CHILD_JOIN_PENDING', 'QUARANTINE_MARKER_OBSERVED'):
                    value = dict(schema='capture-progress.v1', event=event, terminal=False,
                        direct_child_joined=False, release_authorized=False, pid=100 + index,
                        proc_start_ticks=str(200 + index), capture_directory=str(path))
                    (path / ('progress-' + event.lower() + '.json')).write_text(json.dumps(value))
                campaign.poll_capture_progress()
                self.assertEqual([row['pid'] for row in campaign.state['capture_progress']], [100 + index] * 2)
                self.assertEqual(campaign.active, {'thread-a': 'turn-a'})
                self.assertEqual(campaign.goal, {'status': 'active'})
                for name, value in old_bytes.items():
                    self.assertEqual(Path(name).read_bytes(), value)
                old_bytes.update({str(p): p.read_bytes() for p in path.iterdir()})
                campaign.save()
                previous_path = path

    def test_plain_instruction_keeps_original_queue_shape_and_routing(self):
        with tempfile.TemporaryDirectory(prefix='capture-queue-test-') as directory:
            scope, campaign = self.fixture(directory)
            ident = scope['queue_instruction'](Path(directory), 'Continue ordinary authorized work')
            pending = Path(directory) / 'instructions' / 'pending' / (ident + '.json')
            self.assertEqual(set(json.loads(pending.read_text())), {'id', 'submitted_at', 'text'})
            campaign.deliver_instruction()
            self.assertEqual(len(campaign.calls), 1)
            self.assertEqual(campaign.calls[0][1]['input'][0]['text'],
                             'Live user instruction ' + ident + ':\nContinue ordinary authorized work')
            self.assertNotIn('capture_progress_registration', campaign.state)
            self.assertIsNone(campaign.capture_progress_directory)

    def test_wrong_thread_or_instance_refuses_without_steering(self):
        for change in ('thread', 'worker', 'instance'):
            with self.subTest(change=change), tempfile.TemporaryDirectory(prefix='capture-queue-test-') as directory:
                scope, campaign = self.fixture(directory)
                ident = scope['queue_instruction'](Path(directory), 'Next capture', Path(directory) / 'fresh')
                if change == 'thread':
                    campaign.state['thread_id'] = 'thread-b'
                    campaign.active = {'thread-b': 'turn-b'}
                elif change == 'worker':
                    campaign.state['worker_pid'] += 1
                else:
                    campaign.log_dir = Path(directory) / 'runs' / 'instance-b'
                campaign.deliver_instruction()
                self.assertEqual(campaign.calls, [])
                self.assertEqual(campaign.state['last_instruction']['status'], 'registration_refused_before_steer')
                self.assertFalse((Path(directory) / 'instructions' / 'sending' / (ident + '.json')).exists())
                self.assertTrue((Path(directory) / 'instructions' / 'refused' / (ident + '.json')).exists())
                self.assertNotIn('capture_progress_registration', campaign.state)
                self.assertIsNone(campaign.capture_progress_directory)

    def test_directory_becoming_nonfresh_before_drain_refuses(self):
        with tempfile.TemporaryDirectory(prefix='capture-queue-test-') as directory:
            scope, campaign = self.fixture(directory)
            path = Path(directory) / 'fresh'
            scope['queue_instruction'](Path(directory), 'Next capture', path)
            path.mkdir()
            campaign.deliver_instruction()
            self.assertEqual(campaign.calls, [])
            self.assertEqual(campaign.state['last_instruction']['status'], 'registration_refused_before_steer')

    def test_definite_refusal_retains_original_and_allows_later_get_unstuck_instruction(self):
        for reason in ('identity', 'path'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory(prefix='capture-queue-test-') as directory:
                scope, campaign = self.fixture(directory)
                path = Path(directory) / 'fresh'
                ident = scope['queue_instruction'](Path(directory), 'Rejected capture request', path)
                pending = Path(directory) / 'instructions' / 'pending' / (ident + '.json')
                if reason == 'identity':
                    value = json.loads(pending.read_text())
                    value['capture_progress']['expected_thread_id'] = 'old-thread'
                    pending.write_text(json.dumps(value))
                else:
                    path.mkdir()
                original = pending.read_bytes()
                campaign.deliver_instruction()
                self.assertEqual(campaign.calls, [])
                refused = Path(directory) / 'instructions' / 'refused'
                self.assertEqual((refused / (ident + '.json')).read_bytes(), original)
                receipt = json.loads((refused / (ident + '.receipt.json')).read_text())
                self.assertEqual(receipt['status'], 'registration_refused_before_steer')
                self.assertEqual(list((Path(directory) / 'instructions' / 'sending').glob('*.json')), [])
                later = scope['queue_instruction'](Path(directory), 'Get unstuck: report status')
                campaign.deliver_instruction()
                campaign.deliver_instruction()
                self.assertEqual(len(campaign.calls), 1)
                self.assertEqual(campaign.calls[0][1]['input'][0]['text'],
                                 'Live user instruction ' + later + ':\nGet unstuck: report status')
                self.assertEqual((refused / (ident + '.json')).read_bytes(), original)

    def test_save_failure_never_steers_or_changes_active_monitor(self):
        with tempfile.TemporaryDirectory(prefix='capture-queue-test-') as directory:
            scope, campaign = self.fixture(directory)
            scope['queue_instruction'](Path(directory), 'Next capture', Path(directory) / 'fresh')
            save = campaign.save
            def controlled_failure(**fields):
                if 'capture_progress_registration' in fields:
                    campaign.state.update(fields)  # Match real save's pre-write mutation.
                    raise OSError('controlled acknowledgement persistence failure')
                save(**fields)
            campaign.save = controlled_failure
            campaign.deliver_instruction()
            self.assertEqual(campaign.calls, [])
            self.assertIsNone(campaign.capture_progress_directory)
            self.assertNotIn('capture_progress_registration', campaign.state)
            self.assertEqual(campaign.state['last_instruction']['status'], 'registration_persistence_failed_before_steer')

    def test_registration_never_bypasses_existing_stop_gate(self):
        with tempfile.TemporaryDirectory(prefix='capture-queue-test-') as directory:
            scope, campaign = self.fixture(directory)
            ident = scope['queue_instruction'](Path(directory), 'Next capture', Path(directory) / 'fresh')
            campaign.stop_reason = 'service_policy_hold'
            campaign.deliver_instruction()
            self.assertEqual(campaign.calls, [])
            self.assertTrue((Path(directory) / 'instructions' / 'pending' / (ident + '.json')).exists())
            self.assertNotIn('capture_progress_registration', campaign.state)

    def test_nonsymlink_fresh_path_required_at_enqueue(self):
        with tempfile.TemporaryDirectory(prefix='capture-queue-test-') as directory:
            scope, campaign = self.fixture(directory)
            actual = Path(directory) / 'actual'
            actual.mkdir()
            link = Path(directory) / 'linked'
            link.symlink_to(actual, target_is_directory=True)
            with self.assertRaises(ValueError):
                scope['queue_instruction'](Path(directory), 'Next capture', link / 'future')
            with self.assertRaises(ValueError):
                scope['queue_instruction'](Path(directory), 'Next capture', 'relative')
            with self.assertRaises(ValueError):
                scope['queue_instruction'](Path(directory), 'Next capture', actual)


if __name__ == '__main__':
    unittest.main()
