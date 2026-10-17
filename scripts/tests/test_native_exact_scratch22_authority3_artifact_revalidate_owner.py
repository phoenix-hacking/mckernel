import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_exact_scratch22_authority3_artifact_revalidate_owner as owner
from native_rust_exact_build_container_owner import LIMITS


def container_info(name, nonce, capture, state='created'):
    return {'Name': '/' + name, 'Image': owner.IMAGE,
            'State': {'Status': state, 'Running': state == 'running',
                      'Pid': 100 if state == 'running' else 0},
            'Config': {'Labels': {'mckernel.owner': nonce},
                       'User': '%d:%d' % (os.getuid(), os.getgid()),
                       'Entrypoint': ['/usr/bin/sleep'], 'Cmd': ['infinity']},
            'HostConfig': dict(LIMITS, Privileged=False, ReadonlyRootfs=True,
                               CapDrop=['ALL'], SecurityOpt=['no-new-privileges'],
                               Init=True, IpcMode='private',
                               Tmpfs={'/tmp': 'rw,nodev,nosuid,size=256m'},
                               RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0}),
            'Mounts': [{'Type': 'bind', 'Source': str(source), 'Destination': target,
                        'RW': writable, 'Propagation': 'rprivate'}
                       for source, target, writable in owner.mounts(capture)]}


class FakeDocker:
    def __init__(self, capture, mode='ok', locked=lambda: None):
        self.capture, self.mode, self.locked = capture, mode, locked
        self.calls = []
        self.client_retirement_unproven = False
        self.name = self.nonce = None
        self.state = 'created'
        self.removed = False

    def call(self, args, **kwargs):
        self.locked()
        self.calls.append(args)
        code, stdout, stderr = 0, '', ''
        if args[:2] == ['image', 'inspect']:
            stdout = json.dumps([{'Id': owner.IMAGE, 'Architecture': 'amd64', 'Os': 'linux'}])
        elif args[0] == 'create':
            self.name = args[args.index('--name') + 1]
            self.nonce = args[args.index('--label') + 1].split('=', 1)[1]
            if self.mode == 'lost-create':
                raise RuntimeError('create response lost')
        elif args[0] == 'inspect':
            if self.removed:
                code, stdout, stderr = 1, '[]\n', 'Error: No such object: %s\n' % args[1]
                if self.mode == 'absence-uncertain':
                    stderr = 'Cannot connect to Docker daemon\n'
            else:
                stdout = json.dumps([container_info(self.name, self.nonce, self.capture, self.state)])
        elif args[0] == 'start':
            self.state = 'running'
        elif args[0] == 'exec':
            if self.mode == 'client-uncertain':
                self.client_retirement_unproven = True
                raise RuntimeError('client reaping uncertain')
            code = 1 if self.mode == 'payload-fail' else 0
            owner._write_json(self.capture / 'payload/result.json', {
                'status': 'FAIL' if code else 'PASS_DIAGNOSTIC_FINAL_CHECKS',
                'strict_fresh_build_pass': False, 'runtime_or_acceptance_credit': False})
        elif args[0] in ('stop', 'kill'):
            self.state = 'exited'
        elif args[0] == 'rm':
            self.removed = True
        return subprocess.CompletedProcess(args, code, stdout, stderr)


class OwnerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.capture = self.root / 'capture'
        self.request_path = self.root / 'request.json'
        self.shared = self.root / 'shared'
        self.signals = owner.CliSignals()
        patch = mock.patch.object(owner, 'verify_retained_bindings')
        self.binding_mock = patch.start()
        self.addCleanup(patch.stop)

    def contract(self, locked=lambda: None):
        contract = mock.Mock()
        contract.SHARED_HEAVY_LOCK_PATH = str(self.shared)
        def acquire(request, kind):
            locked()
            self.shared.write_text('owned')
            return self.shared, {'owner': 'test'}
        def release(path, record, result):
            locked()
            self.assertEqual(result['status'], 'PASS')  # cleanup proof only
            self.assertFalse(owner.lease_path(self.capture).exists())
            self.shared.unlink()
            return True
        contract.acquire_heavy_operation.side_effect = acquire
        contract._release_exclusion.side_effect = release
        return contract

    def run_core(self, mode='ok', locked=lambda: None):
        docker = FakeDocker(self.capture, mode, locked)
        contract = self.contract(locked)
        with mock.patch.object(owner, 'check_capacity'), mock.patch.object(
                owner, '_SHARED_HEAVY_ENTRY_CONTRACT', contract):
            result = owner.execute({'capture': str(self.capture)}, 'a' * 64,
                                   self.request_path, self.signals, runner=docker)
        return result, docker, contract

    def test_success_uses_real_profile_and_retires_before_release(self):
        result, docker, _ = self.run_core()
        self.assertEqual(result['status'], 'PASS_DIAGNOSTIC_REVALIDATION')
        self.assertTrue(result['ownership_released'])
        self.assertFalse(result['strict_fresh_build_pass'])
        self.assertFalse(self.shared.exists())
        self.assertFalse(owner.lease_path(self.capture).exists())
        self.assertTrue(Path(str(self.request_path) + '.consumed.json').exists())
        self.assertIn(['exec', docker.name, *owner.COMMAND], docker.calls)
        self.assertTrue((self.capture / 'payload/result.json').is_file())
        self.assertFalse((self.capture / 'result.json').exists())
        self.assertEqual(owner.mounts(self.capture)[-1],
                         (self.capture / 'payload', '/capture', True))

    def test_payload_failure_can_return_only_after_positive_cleanup(self):
        result, docker, _ = self.run_core('payload-fail')
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['ownership_released'])
        self.assertTrue(docker.removed)

    def test_lost_create_keeps_lease_and_shared_and_never_removes(self):
        result, docker, contract = self.run_core('lost-create')
        self.assertFalse(result['ownership_released'])
        self.assertTrue(self.shared.exists())
        self.assertTrue(owner.lease_path(self.capture).exists())
        contract._release_exclusion.assert_not_called()
        self.assertFalse(any(args[0] == 'rm' for args in docker.calls))

    def test_unproven_client_never_releases_even_with_known_container(self):
        result, docker, contract = self.run_core('client-uncertain')
        self.assertTrue(result['client_retirement_unproven'])
        self.assertFalse(result['ownership_released'])
        self.assertTrue(owner.lease_path(self.capture).exists())
        contract._release_exclusion.assert_not_called()

    def test_remove_response_without_absence_never_releases(self):
        result, docker, contract = self.run_core('absence-uncertain')
        self.assertTrue(docker.removed)
        self.assertFalse(result['ownership_released'])
        self.assertTrue(owner.lease_path(self.capture).exists())
        contract._release_exclusion.assert_not_called()

    def test_all_four_signal_latches_prevent_diagnostic_success(self):
        for number in owner.DEFERRED_SIGNALS:
            with self.subTest(signal=number), tempfile.TemporaryDirectory() as directory:
                capture = Path(directory) / 'capture'
                request = Path(directory) / 'request.json'
                docker = FakeDocker(capture)
                signals = owner.CliSignals()
                signals.receive(number, None)
                shared = Path(directory) / 'shared'
                contract = mock.Mock()
                def acquire(*args):
                    shared.touch()
                    return shared, {}
                def release(*args):
                    shared.unlink()
                    return True
                contract.acquire_heavy_operation.side_effect = acquire
                contract._release_exclusion.side_effect = release
                with mock.patch.object(owner, '_SHARED_HEAVY_ENTRY_CONTRACT', contract):
                    result = owner.execute({'capture': str(capture)}, 'a' * 64,
                                           request, signals, runner=docker)
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['interrupted_signal'], number)
                self.assertTrue(result['ownership_released'])

    def test_any_input_writable_or_extra_mount_is_rejected(self):
        original = container_info('name', 'nonce', self.capture)
        for index in range(5):
            info = json.loads(json.dumps(original))
            info['Mounts'][index]['RW'] = True
            with self.subTest(index=index), self.assertRaises(RuntimeError):
                owner.validate_container(info, 'nonce', self.capture)
        original['Mounts'].append(dict(original['Mounts'][0]))
        with self.assertRaises(RuntimeError):
            owner.validate_container(original, 'nonce', self.capture)

    def test_resource_profile_drift_is_rejected(self):
        for key, value in [('MemorySwap', 24 * 2**30), ('CpusetCpus', '0-7'),
                           ('NetworkMode', 'bridge'), ('Privileged', True)]:
            info = container_info('name', 'nonce', self.capture)
            info['HostConfig'][key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                owner.validate_container(info, 'nonce', self.capture)

    def test_request_digest_cannot_be_omitted(self):
        with self.assertRaisesRegex(RuntimeError, 'external request SHA256'):
            owner.authenticate_request(self.request_path, None)

    def test_guard_holds_lock_through_all_docker_and_shared_release(self):
        lock = self.root / 'development.lock'
        lock.touch(mode=0o644)
        lock.chmod(0o644)
        identity = (lock.stat().st_dev, lock.stat().st_ino)
        def locked():
            fd = os.open(lock, os.O_RDONLY)
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(fd)
        real_execute = owner.execute
        docker = FakeDocker(self.capture, locked=locked)
        contract = self.contract(locked)
        def execute(*args):
            return real_execute(*args, runner=docker)
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        handlers = {number: signal.getsignal(number) for number in owner.DEFERRED_SIGNALS}
        with mock.patch.object(owner, 'authenticate_request', return_value=(
                {'capture': str(self.capture)}, 'a' * 64)), mock.patch.object(
                owner, 'execute', side_effect=execute), mock.patch.object(
                owner, 'check_capacity'), mock.patch.object(
                owner, '_SHARED_HEAVY_ENTRY_CONTRACT', contract):
            result = owner.guarded_execute(self.request_path, 'a' * 64,
                        lock_path=lock, lock_identity=identity,
                        lock_owner=(os.getuid(), os.getgid()))
        self.assertTrue(result['ownership_released'])
        fd = os.open(lock, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)
        self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, set()), mask)
        self.assertEqual({number: signal.getsignal(number) for number in owner.DEFERRED_SIGNALS}, handlers)

    def test_guard_enters_quarantine_with_lock_held_on_lost_create(self):
        lock = self.root / 'development.lock'
        lock.touch(mode=0o644)
        lock.chmod(0o644)
        class Quarantined(Exception):
            pass
        def quarantine(fd, request):
            other = os.open(lock, os.O_RDONLY)
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(other)
                # Test-only escape from production's non-returning quarantine.
                os.close(fd)
            raise Quarantined()
        real_execute = owner.execute
        docker = FakeDocker(self.capture, 'lost-create')
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        old_handlers = {number: signal.getsignal(number) for number in owner.DEFERRED_SIGNALS}
        try:
            with mock.patch.object(owner, 'authenticate_request', return_value=(
                    {'capture': str(self.capture)}, 'a' * 64)), mock.patch.object(
                    owner, 'execute', side_effect=lambda *args: real_execute(*args, runner=docker)), mock.patch.object(
                    owner, 'check_capacity'), mock.patch.object(
                    owner, '_SHARED_HEAVY_ENTRY_CONTRACT', self.contract()), mock.patch.object(
                    owner, 'quarantine_root_lock', side_effect=quarantine):
                with self.assertRaises(Quarantined):
                    owner.guarded_execute(self.request_path, 'a' * 64, lock_path=lock,
                        lock_identity=(lock.stat().st_dev, lock.stat().st_ino),
                        lock_owner=(os.getuid(), os.getgid()))
        finally:
            for number, handler in old_handlers.items():
                signal.signal(number, handler)
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
        self.assertTrue(self.shared.exists())
        self.assertTrue(owner.lease_path(self.capture).exists())


class RetainedBindingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'source'
        self.output = self.root / 'output'
        self.bindings = {}
        for base, paths in ((self.source, owner.FROZEN_FILES), (self.output, owner.ARTIFACTS)):
            for name in paths:
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                raw = name.encode() + b'\n'
                path.write_bytes(raw)
                self.bindings[str(path)] = {'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)}
        self.request = {'retained_file_bindings': self.bindings,
                        'retained_candidate': {'head': owner.CANDIDATE, 'tree': owner.TREE},
                        'scratch_binding': {'uuid': owner.SCRATCH_UUID, 'device': self.root.stat().st_dev}}
        for name, value in [('observe_candidate', self.request['retained_candidate']),
                            ('observe_scratch', self.request['scratch_binding'])]:
            patch = mock.patch.object(owner, name, return_value=value)
            patch.start()
            self.addCleanup(patch.stop)

    def test_changed_artifact_is_rejected_against_retained_receipt_row(self):
        owner.verify_retained_bindings(self.request)
        path = self.output / owner.ARTIFACTS[0]
        raw = path.read_bytes()
        path.write_bytes(b'X' + raw[1:])
        with self.assertRaisesRegex(RuntimeError, 'hash/identity differs'):
            owner.verify_retained_bindings(self.request)

    def test_changed_frozen_workflow_is_rejected(self):
        path = self.source / owner.FROZEN_FILES[0]
        raw = path.read_bytes()
        path.write_bytes(b'X' + raw[1:])
        with self.assertRaisesRegex(RuntimeError, 'hash/identity differs'):
            owner.verify_retained_bindings(self.request)

    def test_wrong_scratch_uuid_is_rejected_before_any_file_read(self):
        with mock.patch.object(owner, 'observe_scratch', return_value={
                'uuid': 'wrong', 'device': self.root.stat().st_dev}), mock.patch.object(
                owner, 'stable_hash_matches') as read:
            with self.assertRaisesRegex(RuntimeError, 'scratch UUID/device changed'):
                owner.verify_retained_bindings(self.request)
        read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
