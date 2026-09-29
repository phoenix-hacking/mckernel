import copy
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_rust_exact_build_container_owner as owner

IMAGE = 'sha256:' + 'b' * 64
BASE = 'sha256:' + 'c' * 64

# A private Linux subreaper supervisor contains the abrupt-death regression.
# It reaps the owner and any orphaned emitter, without modifying the test runner.
SIGNAL_HARNESS = r'''
import ctypes, json, os, pathlib, subprocess, sys
from types import SimpleNamespace
root, mode = pathlib.Path(sys.argv[1]), sys.argv[2]
sys.path.insert(0, sys.argv[3])
import native_rust_exact_build_container_owner as owner
import native_rust_exact_build_image_prepare as prep
from scripts.tests.test_native_rust_exact_build_container_owner import FakeDocker
# Signal lifecycle coverage uses a minimal synthetic request; provenance is
# covered by the in-process admission tests.
owner.provenance.verify_inputs = lambda *args, **kwargs: None
if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
    raise RuntimeError('private subreaper setup failed')
pid = os.fork()
if pid:
    (root / 'owner.pid').write_text(str(pid))
    waited, status = os.waitpid(pid, 0)
    (root / 'owner.wait').write_text(str(status))
    while True:
        try: os.waitpid(-1, 0)
        except ChildProcessError: break
    sys.exit(0)
request = json.loads((root / 'signal-request.json').read_text())
RealDocker, RealPopen = owner.Docker, subprocess.Popen
emitter = "import os,time; from pathlib import Path; os.write(1,b'SIGNAL-STDOUT\\n'); os.write(2,b'SIGNAL-STDERR\\n'); Path(%r).write_text('ready'); time.sleep(1.5)" % str(root / 'emitter.ready')
def local_popen(argv, **kwargs):
    assert argv[0] == 'docker', argv
    return RealPopen([sys.executable, '-u', '-c', emitter], **kwargs)
owner.subprocess.Popen = local_popen
owner.measure = prep.measure = lambda *a, **kw: {'host_free': 64 * 2**30, 'scratch_free': 64 * 2**30, 'memory_available': 32 * 2**30}
class Hybrid(FakeDocker):
    def __init__(self, log, signals=None):
        super().__init__(request if mode.startswith('owner') else None)
        self.live = RealDocker(log, signals=signals)
        self.injected = False
        self.unretirable = mode.endswith('-hold')
        self.timeout = self.unretirable
    @property
    def client_retirement_unproven(self):
        return self.live.client_retirement_unproven
    def call(self, args, timeout=120, check=True):
        target = args[0] == ('wait' if mode.startswith('owner') else 'exec')
        if target and not self.injected:
            self.injected = True
            return self.live.call(args, timeout, check)
        with (root / 'cleanup.commands').open('a') as stream:
            stream.write(json.dumps(args) + '\n')
        return super().call(args, timeout, check)
owner.Docker = prep.Docker = Hybrid
if mode.startswith('owner'):
    sys.argv = ['owner', str(root / 'signal-request.json')]
    code = owner.main()
else:
    sys.argv = ['prepare']
    for key, value in request.items(): sys.argv.extend(['--' + key.replace('_', '-'), str(value)])
    code = prep.main()
os._exit(code)
'''


def signal_regression(test, root, mode, request, signum):
    """Real CLI, child wait, OS signal, evidence files and cleanup; fake daemon."""
    root = Path(root)
    (root / 'signal-request.json').write_text(json.dumps(request))
    script = root / 'signal-harness.py'
    script.write_text(SIGNAL_HARNESS)
    project = Path(__file__).resolve().parents[2]
    proc = subprocess.Popen([sys.executable, '-B', str(script), str(root), mode,
                             str(project / 'scripts')], cwd=project,
                            env=dict(os.environ, PYTHONPATH=str(project)),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 8
        while not (root / 'emitter.ready').exists():
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                test.fail('signal harness exited before emission: ' + stdout + stderr)
            if time.monotonic() >= deadline:
                test.fail('signal harness did not emit before deadline')
            time.sleep(0.01)
        evidence = Path(request['evidence_root'])
        outputs = list(evidence.glob('command-*/stdout'))
        errors = list(evidence.glob('command-*/stderr'))
        test.assertEqual(len(outputs), 1)
        test.assertEqual(outputs[0].read_bytes(), b'SIGNAL-STDOUT\n')
        test.assertEqual(errors[0].read_bytes(), b'SIGNAL-STDERR\n')
        os.kill(int((root / 'owner.pid').read_text()), signum)
        stdout, stderr = proc.communicate(timeout=10)
        test.assertEqual(proc.returncode, 0, stdout + stderr)
        test.assertEqual(outputs[0].read_bytes(), b'SIGNAL-STDOUT\n')
        test.assertEqual(errors[0].read_bytes(), b'SIGNAL-STDERR\n')
        receipt = evidence / ('receipt.json' if mode.startswith('owner') else 'image-receipt.json')
        if signum == signal.SIGKILL:
            test.assertFalse(receipt.exists())
            test.assertTrue(Path(request['lease_path']).exists())
            test.assertTrue(os.WIFSIGNALED(int((root / 'owner.wait').read_text())))
        else:
            result = json.loads(receipt.read_text())
            test.assertEqual(result['status'], 'FAIL')
            test.assertEqual(result['interrupted_signal'], signum)
            test.assertEqual(result['retired'], not mode.endswith('-hold'))
            test.assertEqual(Path(request['lease_path']).exists(), mode.endswith('-hold'))
            commands = [json.loads(line) for line in (root / 'cleanup.commands').read_text().splitlines()]
            test.assertTrue(any(c[0] == 'stop' for c in commands))
            command_status = json.loads((outputs[0].parent / 'status.json').read_text())
            test.assertEqual(command_status['state'], 'failed')
            # Cancellation first relays TERM to the client group.  A clean
            # relay is proved by its TERM exit; SIGKILL is reserved for the
            # separately covered forced path.
            test.assertEqual(command_status['exit_code'],
                             -signal.SIGKILL if signum == signal.SIGKILL else -signal.SIGTERM)
            test.assertTrue(os.WIFEXITED(int((root / 'owner.wait').read_text())))
    finally:
        if proc.poll() is None:
            # The private supervisor retains/reaps all descendants.
            if (root / 'owner.pid').exists():
                try: os.kill(int((root / 'owner.pid').read_text()), signal.SIGKILL)
                except ProcessLookupError: pass
            proc.communicate(timeout=10)


class FakeDocker:
    """Stateful Docker protocol fake: unknown commands fail the test."""
    def __init__(self, request=None):
        self.request = request
        self.commands = []
        self.info = None
        self.mutate = lambda info: None
        self.timeout = False
        self.unretirable = False
        self.omit_artifact = False
        self.exit_code = 0
        self.probe = None
        self.fail_command = None

    def call(self, args, timeout=120, check=True):
        self.commands.append(list(args))
        op = args[0]
        if op == self.fail_command:
            raise RuntimeError('injected ' + op + ' failure')
        text = ''
        if args[:2] == ['image', 'inspect']:
            value = args[2]
            text = json.dumps([{'Id': value if value.startswith('sha256:') else BASE,
                               'Architecture': 'amd64', 'Os': 'linux', 'RepoDigests': [value]}])
        elif op == 'create':
            def option(key):
                return args[args.index(key) + 1]
            entry = option('--entrypoint')
            image_index = args.index('--entrypoint') + 2
            host = dict(owner.LIMITS, Privileged=False, ReadonlyRootfs='--read-only' in args,
                        CapDrop=['ALL'], SecurityOpt=['no-new-privileges'], Init=True,
                        PidMode='', IpcMode='private', Binds=None,
                        CapAdd=sorted(a.split('=', 1)[1] for a in args if a.startswith('--cap-add=')))
            host['NetworkMode'] = 'bridge' if '--network=bridge' in args else 'none'
            if '--tmpfs' in args:
                target, options = option('--tmpfs').split(':', 1)
                host['Tmpfs'] = {target: options}
            mounts = []
            for i, arg in enumerate(args):
                if arg == '--mount':
                    parts = args[i + 1].split(',')
                    values = dict(p.split('=', 1) for p in parts if '=' in p)
                    mounts.append({'Type': 'bind', 'Source': values['src'],
                                   'Destination': values['dst'], 'RW': 'readonly' not in parts})
            self.info = {'Name': '/' + option('--name'), 'Image': args[image_index],
                         'HostConfig': host, 'Mounts': mounts,
                         'Config': {'Entrypoint': [entry], 'Cmd': args[image_index + 1:],
                                    'User': option('--user') if '--user' in args else '',
                                    'Labels': {'mckernel.owner': option('--label').split('=', 1)[1]}},
                         'State': {'Status': 'created', 'Running': False, 'Pid': 0}}
            text = 'container-id\n'
        elif op == 'inspect':
            if self.info is None:
                raise RuntimeError('no such container')
            info = copy.deepcopy(self.info)
            self.mutate(info)
            text = json.dumps([info])
        elif op == 'start':
            self.info['State'] = {'Status': 'running', 'Running': True, 'Pid': 1234}
        elif op == 'wait':
            if self.timeout and self.info['State']['Running']:
                raise RuntimeError('injected wait timeout')
            self.info['State'] = {'Status': 'exited', 'Running': False, 'Pid': 0}
            text = str(self.exit_code)
            if self.request and not self.timeout:
                self.build_outputs()
        elif op in ('stop', 'kill'):
            if not self.unretirable:
                self.info['State'] = {'Status': 'exited', 'Running': False, 'Pid': 0}
        elif op == 'logs':
            text = 'complete captured output\n'
        elif op == 'rm':
            if self.info['State']['Running']:
                raise AssertionError('removed a live container')
            self.info = None
        elif op == 'commit':
            if self.info['State']['Running']:
                raise AssertionError('committed live preparation')
            text = IMAGE
        elif op == 'exec':
            if '-c' in args and args[-2] == '-c':
                text = json.dumps(self.probe)
            elif 'dnf' not in args:
                raise AssertionError('unexpected exec ' + repr(args))
        elif op != 'pull':
            raise AssertionError('unexpected Docker operation ' + repr(args))
        return SimpleNamespace(returncode=0, stdout=text, stderr='')

    def build_outputs(self):
        evidence = Path(self.request['evidence_root']) / 'build'
        root = evidence / 'native-rust-build-evidence'
        root.mkdir(parents=True, exist_ok=True)
        for name in ('bzImage', 'ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko', 'SHA256SUMS'):
            if not (self.omit_artifact and name == 'bzImage'):
                (root / name).write_text('observed artifact ' + name)
        (evidence / 'receipt.json').write_text(json.dumps(
            {'status': 'PASS', 'candidate_sha': self.request['candidate_sha']}))


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        # Candidate source/output roots may live on different filesystems;
        # model that explicitly with the host's tmpfs for focused validation.
        self.measure_output = Path(tempfile.mkdtemp(prefix='mckernel-owner-', dir='/dev/shm'))
        for directory in ('src', 'assets', 'out', 'ev'):
            (self.root / directory).mkdir()
        source_info = (self.root / 'src').stat()
        self.source_device = '%d:%d' % (os.major(source_info.st_dev),
                                        os.minor(source_info.st_dev))
        # The owner admits only standalone repositories; keep the ordinary
        # fixture representative of the checked-in source layout.
        for git_root in (self.root / 'src' / '.git', self.root / 'src' / 'ihk' / '.git'):
            git_root.mkdir(parents=True)
            (git_root / 'config').write_text('[core]\n\trepositoryformatversion = 0\n')
        self.request = {'candidate_sha': 'a' * 40, 'image_id': IMAGE, 'timeout': 20,
                        'source_root': str(self.root / 'src'), 'assets_root': str(self.root / 'assets'),
                        'output_root': str(self.root / 'out'), 'evidence_root': str(self.root / 'ev'),
                        'host_measure_root': str(self.root),
                        'scratch_measure_root': str(self.measure_output),
                        'memory_allocation_roots': [str(self.root / 'src')],
                        'lease_path': str(self.root / 'lease')}
        files = {'driver_path': 'driver', 'image_receipt': json.dumps({'status': 'PASS', 'image_id': IMAGE}),
                 'input_manifest': json.dumps({'candidate_sha': 'a' * 40})}
        for key, contents in files.items():
            p = self.root / key
            p.write_text(contents)
            self.request[key] = str(p)
            self.request[key + '_sha256'] = owner.digest(p)
        self.disk = mock.patch.object(owner.shutil, 'disk_usage', return_value=SimpleNamespace(free=64 * 2**30))
        self.disk.start()
        # Real /proc is read; tests require only memory observation to be isolated.
        original = owner.Path.read_text
        self.mem = mock.patch.object(owner.Path, 'read_text', lambda p, *a, **kw:
            'MemAvailable: 33554432 kB\n' if str(p) == '/proc/meminfo' else original(p, *a, **kw))
        self.mem.start()
        # Lifecycle tests use intentionally minimal request fixtures; the
        # dedicated admission tests below exercise the real verifier.
        self.provenance = mock.patch.object(owner.provenance, 'verify_inputs',
                                            return_value=None)
        self.provenance.start()

    def tearDown(self):
        self.mem.stop()
        self.provenance.stop()
        self.disk.stop()
        shutil.rmtree(str(self.measure_output))
        self.temp.cleanup()

    def execute(self, fake=None):
        return owner.BuildOwner(self.request, fake or FakeDocker(self.request)).run()

    def test_positive_complete_receipt_and_lease_release(self):
        fake = FakeDocker(self.request)
        result = self.execute(fake)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertTrue(result['retired'])
        self.assertFalse(Path(self.request['lease_path']).exists())
        self.assertIn('container.log', result['evidence'])
        self.assertFalse(any(c[0] == 'rm' for c in fake.commands))
        self.assertTrue(result['terminal_container_retained'])
        self.assertEqual(result['terminal_container_retention_state'],
                         'verified_owned_terminal_retained')
        self.assertEqual(result['terminal_container_name'], result['container_name'])
        self.assertEqual(result['terminal_container_label'],
                         'mckernel.owner=' + result['owner']['nonce'])
        self.assertEqual(result['terminal_container_info']['Name'],
                         '/' + result['container_name'])
        self.assertTrue(result['cleanup_separately_required'])

    def test_candidate_mode_admission_precedes_lease_and_docker(self):
        manifest_path = Path(self.request['input_manifest'])
        manifest_path.write_text(json.dumps({'candidate_sha': self.request['candidate_sha'],
                                             'repository_files': {}}))
        self.request['input_manifest_sha256'] = owner.digest(manifest_path)
        fake = FakeDocker(self.request)
        with mock.patch.object(owner.provenance, 'verify_inputs',
                               side_effect=owner.provenance.BuildError(
                                   'indexed executable mode differs')):
            with self.assertRaisesRegex(ValueError, 'candidate input admission failed'):
                owner.BuildOwner(self.request, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_missing_or_malformed_inventory_cannot_reach_lease_or_docker(self):
        self.provenance.stop()
        try:
            for value in ('missing', None, []):
                with self.subTest(repository_files=value):
                    manifest = {'candidate_sha': self.request['candidate_sha']}
                    if value != 'missing':
                        manifest['repository_files'] = value
                    path = Path(self.request['input_manifest'])
                    path.write_text(json.dumps(manifest))
                    self.request['input_manifest_sha256'] = owner.digest(path)
                    fake = FakeDocker(self.request)
                    with self.assertRaisesRegex(ValueError, 'candidate input admission failed'):
                        owner.BuildOwner(self.request, fake).run()
                    self.assertEqual(fake.commands, [])
                    self.assertFalse(Path(self.request['lease_path']).exists())
        finally:
            self.provenance = mock.patch.object(owner.provenance, 'verify_inputs',
                                                return_value=None)
            self.provenance.start()

    def test_start_is_once_and_precedes_wait(self):
        fake = FakeDocker(self.request)
        result = self.execute(fake)
        self.assertEqual(result['status'], 'PASS', result)
        lifecycle = [command[0] for command in fake.commands]
        self.assertEqual(lifecycle.count('start'), 1)
        start_index = lifecycle.index('start')
        wait_indices = [index for index, operation in enumerate(lifecycle)
                        if operation == 'wait']
        self.assertEqual(len(wait_indices), 1)
        self.assertEqual(wait_indices[0], start_index + 1)

    def test_missing_artifact_cannot_pass_and_container_preserved(self):
        fake = FakeDocker(self.request)
        fake.omit_artifact = True
        self.assertEqual(self.execute(fake)['status'], 'FAIL')
        self.assertIsNotNone(fake.info)
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_timeout_retires_then_releases(self):
        fake = FakeDocker(self.request)
        fake.timeout = True
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['retired'])
        self.assertTrue(any(c[0] == 'stop' for c in fake.commands))
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_unretirable_timeout_holds_lease(self):
        fake = FakeDocker(self.request)
        fake.timeout = fake.unretirable = True
        result = self.execute(fake)
        self.assertFalse(result['retired'])
        lease = json.loads(Path(self.request['lease_path']).read_text())
        self.assertEqual(lease['pid'], os.getpid())
        self.assertTrue(lease['starttime'].isdigit())
        self.assertEqual(len(lease['nonce']), 32)
        self.assertTrue(any(c[0] == 'kill' for c in fake.commands))
        self.assertIsNone(result['terminal_container_retained'])
        self.assertEqual(result['terminal_container_retention_state'], 'unresolved')
        self.assertFalse(result['terminal_container_info_current'])

    def test_create_failure_after_object_exists_retains_verified_terminal(self):
        class CreateAfterObjectFailure(FakeDocker):
            def call(inner, args, **kwargs):
                result = super().call(args, **kwargs)
                if args[0] == 'create':
                    raise RuntimeError('injected post-create failure')
                return result

        fake = CreateAfterObjectFailure(self.request)
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['retired'])
        self.assertTrue(result['terminal_container_retained'])
        self.assertEqual(result['terminal_container_retention_state'],
                         'verified_owned_terminal_retained')
        self.assertTrue(result['terminal_container_info_current'])
        self.assertFalse(any(c[0] == 'rm' for c in fake.commands))
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_unproven_client_retirement_downgrades_historical_terminal(self):
        fake = FakeDocker(self.request)
        fake.client_retirement_unproven = True
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIsNone(result['terminal_container_retained'])
        self.assertEqual(result['terminal_container_retention_state'],
                         'unresolved_after_historical_terminal_observation')
        self.assertFalse(result['terminal_container_info_current'])
        self.assertTrue(Path(self.request['lease_path']).exists())

    def test_effective_limits_reject_before_start(self):
        for key in owner.LIMITS:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as unused:
                fake = FakeDocker(self.request)
                fake.mutate = lambda info, k=key: info['HostConfig'].__setitem__(k, 'wrong')
                # Fresh evidence roots for each attempted run.
                self.request['evidence_root'] = unused
                result = self.execute(fake)
                self.assertEqual(result['status'], 'FAIL')
                self.assertFalse(any(c[0] == 'start' for c in fake.commands))

    def test_actual_mount_and_driver_reject_before_start(self):
        fake = FakeDocker(self.request)
        fake.mutate = lambda info: info['Config'].__setitem__('Cmd', ['wrong'])
        self.assertEqual(self.execute(fake)['status'], 'FAIL')
        self.assertFalse(any(c[0] == 'start' for c in fake.commands))

    def test_mount_writability_and_added_capability_rejected(self):
        mutations = [lambda i: i['Mounts'][0].__setitem__('RW', True),
                     lambda i: i['HostConfig'].__setitem__('CapAdd', ['SYS_ADMIN']),
                     lambda i: i['HostConfig'].__setitem__('CgroupParent', '/unreviewed'),
                     lambda i: i['HostConfig'].__setitem__('Privileged', True),
                     lambda i: i['Config'].__setitem__('User', '0:0')]
        for mutation in mutations:
            with tempfile.TemporaryDirectory() as fresh:
                self.request['evidence_root'] = fresh
                fake = FakeDocker(self.request)
                fake.mutate = mutation
                self.assertEqual(self.execute(fake)['status'], 'FAIL')
                self.assertFalse(any(c[0] == 'start' for c in fake.commands))

    def test_driver_nonzero_is_failure_even_with_artifacts(self):
        fake = FakeDocker(self.request)
        fake.exit_code = 37
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['exit_code'], 37)
        self.assertIsNotNone(fake.info)

    def test_latched_signal_during_log_capture_fails_and_retains_terminal(self):
        signals = SimpleNamespace(requested=None, cleaning=False)
        fake = FakeDocker(self.request)
        original = fake.call

        def capture_signal(args, **kwargs):
            result = original(args, **kwargs)
            if args[0] == 'logs':
                signals.requested = signal.SIGTERM
            return result

        fake.call = capture_signal
        result = owner.BuildOwner(self.request, fake, signals=signals).run()
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['interrupted_signal'], signal.SIGTERM)
        self.assertTrue(result['terminal_container_retained'])
        self.assertEqual(result['terminal_container_retention_state'],
                         'verified_owned_terminal_retained')
        self.assertTrue(result['terminal_container_info'])
        self.assertFalse(any(c[0] == 'rm' for c in fake.commands))
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_final_allocation_revalidation_failure_fails_and_retains_terminal(self):
        fake = FakeDocker(self.request)
        original = owner._revalidate_allocation_binding
        calls = {'count': 0}

        def fail_final(binding):
            calls['count'] += 1
            # measure() performs three binding checks (capture, per-root,
            # aggregate); the fourth is the run() final reconciliation.
            if calls['count'] >= 4:
                raise RuntimeError('injected final allocation binding failure')
            return original(binding)

        with mock.patch.object(owner, '_revalidate_allocation_binding', side_effect=fail_final):
            result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('final allocation binding failure', result['allocation_revalidation_error'])
        self.assertTrue(result['terminal_container_retained'])
        self.assertEqual(result['terminal_container_retention_state'],
                         'verified_owned_terminal_retained')
        self.assertTrue(result['terminal_container_info'])
        self.assertFalse(any(c[0] == 'rm' for c in fake.commands))
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_actual_image_identity_mismatch_before_create(self):
        fake = FakeDocker(self.request)
        original = fake.call
        def changed(args, **kwargs):
            result = original(args, **kwargs)
            if args[:2] == ['image', 'inspect']:
                result.stdout = json.dumps([{'Id': BASE, 'Architecture': 'amd64'}])
            return result
        fake.call = changed
        result = self.execute(fake)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['retired'])
        self.assertFalse(any(c[0] == 'create' for c in fake.commands))

    def test_measured_floor_not_caller_claim(self):
        self.request['host_free_gib'] = 99999
        with mock.patch.object(owner.shutil, 'disk_usage', return_value=SimpleNamespace(free=1)):
            with self.assertRaisesRegex(RuntimeError, 'measured resource'):
                self.execute()

    def test_measurement_uses_declared_roots_and_records_devices_and_tmpfs(self):
        calls = []
        usage = SimpleNamespace(free=64 * 2**30)
        with mock.patch.object(owner.shutil, 'disk_usage', side_effect=lambda path: calls.append(path) or usage):
            result = owner.BuildOwner(self.request).validate()
        self.assertEqual(calls, [self.request['host_measure_root'],
                                 self.request['scratch_measure_root'],
                                 self.request['source_root'], self.request['output_root']])
        measurement = owner.BuildOwner(self.request)
        measurement.validate()
        self.assertEqual(measurement.measurement['source_free'], usage.free)
        self.assertEqual(measurement.measurement['output_free'], usage.free)
        self.assertEqual(measurement.measurement['host_device'],
                         Path(self.request['host_measure_root']).stat().st_dev)
        self.assertEqual(measurement.measurement['scratch_device'],
                         Path(self.request['scratch_measure_root']).stat().st_dev)
        self.assertEqual(measurement.measurement['source_device'],
                         Path(self.request['source_root']).stat().st_dev)
        self.assertEqual(measurement.measurement['output_device'],
                         Path(self.request['output_root']).stat().st_dev)
        self.assertEqual(measurement.measurement['container_tmpfs_bytes'], 256 * 2**20)
        self.assertEqual(measurement.measurement['candidate_memory_effect']['classification'],
                         'none')

    def test_measurement_roots_missing_symlink_or_same_device_rejected_before_lease(self):
        cases = {
            'missing': str(self.root / 'does-not-exist'),
            'symlink': str(self.root / 'measure-link'),
            'same-device': self.request['host_measure_root'],
        }
        Path(cases['symlink']).symlink_to(self.measure_output, target_is_directory=True)
        for label, value in cases.items():
            with self.subTest(label=label):
                changed = dict(self.request, scratch_measure_root=value)
                fake = FakeDocker(changed)
                with self.assertRaises(ValueError):
                    owner.BuildOwner(changed, fake).run()
                self.assertEqual(fake.commands, [])
                self.assertFalse(Path(changed['lease_path']).exists())

    def test_memory_allocation_roots_require_source_and_reject_aliases_overlap_and_symlinks(self):
        source = Path(self.request['source_root'])
        backup = self.root / 'metadata-backup'
        backup.mkdir()
        link = self.root / 'metadata-link'
        link.symlink_to(backup, target_is_directory=True)
        cases = {
            'missing-field': None,
            'missing-source': [str(backup)],
            'duplicate': [str(source), str(source)],
            'alias': [str(source), str(source / '..' / source.name)],
            'overlap': [str(source), str(source / 'ihk')],
            'symlink': [str(source), str(link)],
        }
        for label, roots in cases.items():
            with self.subTest(label=label):
                changed = dict(self.request)
                if roots is None:
                    changed.pop('memory_allocation_roots')
                else:
                    changed['memory_allocation_roots'] = roots
                fake = FakeDocker(changed)
                with self.assertRaises(ValueError):
                    owner.BuildOwner(changed, fake).run()
                self.assertEqual(fake.commands, [])
                self.assertFalse(Path(changed['lease_path']).exists())

    def test_memory_allocation_unknown_and_backup_walk_failure_precede_lease_or_docker(self):
        source = Path(self.request['source_root'])
        backup = self.root / 'metadata-backup'
        backup.mkdir()
        changed = dict(self.request,
                       memory_allocation_roots=[str(source), str(backup)])
        fake = FakeDocker(changed)
        with mock.patch.object(owner, '_filesystem_type',
                               side_effect=lambda path, **unused: 'unknown' if Path(path) == backup else 'ext4'):
            with self.assertRaisesRegex(RuntimeError, 'filesystem classification unknown'):
                owner.BuildOwner(changed, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(changed['lease_path']).exists())

        original_walk = owner.os.walk

        def denied_backup_walk(path, followlinks=False, onerror=None):
            if Path(path) == backup:
                onerror(PermissionError(13, 'permission denied', str(backup)))
                return iter(())
            return original_walk(path, followlinks=followlinks, onerror=onerror)

        fake = FakeDocker(changed)
        with mock.patch.object(owner.os, 'walk', side_effect=denied_backup_walk):
            with self.assertRaisesRegex(RuntimeError, 'allocation walk failed'):
                owner.BuildOwner(changed, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(changed['lease_path']).exists())

    def test_measurement_floor_failure_precedes_lease_and_docker(self):
        fake = FakeDocker(self.request)
        with mock.patch.object(owner.shutil, 'disk_usage',
                               side_effect=[SimpleNamespace(free=1),
                                            SimpleNamespace(free=64 * 2**30),
                                            SimpleNamespace(free=64 * 2**30),
                                            SimpleNamespace(free=64 * 2**30)]):
            with self.assertRaisesRegex(RuntimeError, 'measured resource'):
                owner.BuildOwner(self.request, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_tmpfs_source_allocation_is_candidate_memory_effect(self):
        source = Path(tempfile.mkdtemp(prefix='mckernel-source-', dir='/dev/shm'))
        try:
            for git_root in (source / '.git', source / 'ihk' / '.git'):
                git_root.mkdir(parents=True)
                (git_root / 'config').write_text('[core]\n\trepositoryformatversion = 0\n')
            (source / 'candidate.bin').write_bytes(b'x' * 4096)
            changed = dict(self.request, source_root=str(source),
                           memory_allocation_roots=[str(source)])
            checked = owner.BuildOwner(changed)
            checked.validate()
            measurement = checked.measurement
            self.assertEqual(measurement['source_filesystem'], 'tmpfs')
            self.assertGreater(measurement['candidate_allocated_bytes'], 0)
            self.assertEqual(measurement['candidate_memory_effect']['classification'], 'tmpfs')
            self.assertEqual(measurement['candidate_memory_effect']['bytes'],
                             measurement['candidate_allocated_bytes'])
        finally:
            shutil.rmtree(str(source))

    def test_tmpfs_candidate_plus_container_over_aggregate_rejected_before_lease(self):
        fake = FakeDocker(self.request)
        source = Path(self.request['source_root'])
        with mock.patch.object(owner, '_filesystem_type',
                               side_effect=lambda path, **unused: 'tmpfs' if Path(path) == source else 'ext4'), \
             mock.patch.object(owner, '_allocated_bytes', return_value=13 * 2**30):
            with self.assertRaisesRegex(RuntimeError, 'memory aggregate'):
                owner.BuildOwner(self.request, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_tmpfs_candidate_and_backup_over_aggregate_rejected_before_lease(self):
        fake = FakeDocker(self.request)
        source = Path(self.request['source_root'])
        backup = self.root / 'metadata-backup'
        backup.mkdir()
        changed = dict(self.request,
                       memory_allocation_roots=[str(source), str(backup)])

        def allocated(path, **unused):
            return 8 * 2**30 if Path(path) == source else 5 * 2**30

        with mock.patch.object(owner, '_filesystem_type',
                               side_effect=lambda path, **unused: 'tmpfs' if Path(path) in (source, backup) else 'ext4'), \
             mock.patch.object(owner, '_allocated_bytes', side_effect=allocated):
            with self.assertRaisesRegex(RuntimeError, 'memory aggregate'):
                owner.BuildOwner(changed, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(changed['lease_path']).exists())

    def test_tmpfs_candidate_at_aggregate_limit_is_admitted_with_16g_available(self):
        fake = FakeDocker(self.request)
        source = Path(self.request['source_root'])
        sixteen_gib = 16 * 2**30
        original_read_text = owner.Path.read_text

        def read_with_sixteen_gib(path, *args, **kwargs):
            if str(path) == '/proc/meminfo':
                return 'MemAvailable: %d kB\n' % (sixteen_gib // 1024)
            return original_read_text(path, *args, **kwargs)

        with mock.patch.object(owner, '_filesystem_type',
                               side_effect=lambda path, **unused: 'tmpfs' if Path(path) == source else 'ext4'), \
             mock.patch.object(owner, '_allocated_bytes', return_value=12 * 2**30), \
             mock.patch.object(owner.Path, 'read_text', new=read_with_sixteen_gib):
            result = self.execute(fake)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['measurement']['aggregate_memory_required'], 24 * 2**30)
        self.assertEqual(result['measurement']['memory_available'], sixteen_gib)

    def test_tmpfs_candidate_and_backup_at_aggregate_limit_record_receipt_rows(self):
        source = Path(self.request['source_root'])
        backup = self.root / 'metadata-backup'
        backup.mkdir()
        changed = dict(self.request,
                       memory_allocation_roots=[str(source), str(backup)])
        fake = FakeDocker(changed)
        sixteen_gib = 16 * 2**30
        original_read_text = owner.Path.read_text

        def read_with_sixteen_gib(path, *args, **kwargs):
            if str(path) == '/proc/meminfo':
                return 'MemAvailable: %d kB\n' % (sixteen_gib // 1024)
            return original_read_text(path, *args, **kwargs)

        def allocated(path, **unused):
            return 8 * 2**30 if Path(path) == source else 4 * 2**30

        with mock.patch.object(owner, '_filesystem_type',
                               side_effect=lambda path, **unused: 'tmpfs' if Path(path) in (source, backup) else 'ext4'), \
             mock.patch.object(owner, '_allocated_bytes', side_effect=allocated), \
             mock.patch.object(owner.Path, 'read_text', new=read_with_sixteen_gib):
            result = owner.BuildOwner(changed, fake).run()
        self.assertEqual(result['status'], 'PASS', result)
        measurement = result['measurement']
        self.assertEqual(measurement['aggregate_memory_required'], 24 * 2**30)
        self.assertEqual(measurement['memory_allocation_tmpfs_bytes'], 12 * 2**30)
        self.assertEqual(measurement['memory_allocation_total_bytes'], 12 * 2**30)
        self.assertEqual(measurement['memory_allocation_roots'], [
            {'path': str(source), 'device': source.stat().st_dev, 'filesystem': 'tmpfs',
             'free': 64 * 2**30, 'allocated_bytes': 8 * 2**30,
             'memory_effect_bytes': 8 * 2**30},
            {'path': str(backup), 'device': backup.stat().st_dev, 'filesystem': 'tmpfs',
             'free': 64 * 2**30, 'allocated_bytes': 4 * 2**30,
             'memory_effect_bytes': 4 * 2**30}])

    def test_non_tmpfs_candidate_allocation_does_not_consume_memory_aggregate(self):
        source = Path(self.request['source_root'])
        with mock.patch.object(owner, '_filesystem_type',
                               side_effect=lambda path, **unused: 'ext4' if Path(path) == source else 'xfs'), \
             mock.patch.object(owner, '_allocated_bytes', return_value=13 * 2**30):
            checked = owner.BuildOwner(self.request)
            checked.validate()
        self.assertEqual(checked.measurement['candidate_memory_effect'],
                         {'classification': 'none', 'bytes': 0})
        self.assertEqual(checked.measurement['aggregate_memory_required'], 12 * 2**30)

    def test_unknown_source_filesystem_rejected_before_allocation_lease_or_docker(self):
        fake = FakeDocker(self.request)
        allocated = mock.Mock(return_value=0)
        with mock.patch.object(owner, '_filesystem_type', return_value='unknown'), \
             mock.patch.object(owner, '_allocated_bytes', allocated):
            with self.assertRaisesRegex(RuntimeError, 'filesystem classification unknown'):
                owner.BuildOwner(self.request, fake).run()
        allocated.assert_not_called()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_unknown_candidate_allocation_rejected_before_lease_or_docker(self):
        fake = FakeDocker(self.request)
        with mock.patch.object(owner, '_filesystem_type', return_value='ext4'), \
             mock.patch.object(owner, '_allocated_bytes', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'memory allocation unknown'):
                owner.BuildOwner(self.request, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_allocated_bytes_scandir_and_lstat_fail_closed_before_lease_or_docker(self):
        source = Path(self.request['source_root'])
        raced = source / 'allocation-race'
        raced.write_text('race')
        original_walk = owner.os.walk

        def denied_walk(path, followlinks=False, onerror=None):
            if Path(path) == source:
                onerror(PermissionError(13, 'permission denied', str(source)))
                return iter(())
            return original_walk(path, followlinks=followlinks, onerror=onerror)

        fake = FakeDocker(self.request)
        with mock.patch.object(owner.os, 'walk', side_effect=denied_walk):
            with self.assertRaisesRegex(RuntimeError, 'allocation walk failed'):
                owner.BuildOwner(self.request, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

        original_lstat = owner.os.lstat

        def denied_lstat(path):
            if Path(path) == raced:
                raise PermissionError(13, 'permission denied', str(raced))
            return original_lstat(path)

        fake = FakeDocker(self.request)
        with mock.patch.object(owner.os, 'lstat', side_effect=denied_lstat):
            with self.assertRaisesRegex(RuntimeError, 'allocation lstat failed'):
                owner.BuildOwner(self.request, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_allocated_bytes_skips_symlinks_but_rejects_other_device_directory_and_file(self):
        root = self.root / 'allocation-root'
        root.mkdir()
        counted = root / 'counted'
        counted.write_bytes(b'x' * 4096)
        other_device = root / 'other-device'
        other_device.mkdir()
        other_file = root / 'other-file'
        other_file.write_bytes(b'y' * 4096)
        (root / 'link').symlink_to(other_device / 'not-counted')
        original_lstat = owner.os.lstat
        root_info = original_lstat(str(root))

        def cross_device_lstat(path):
            info = original_lstat(path)
            if Path(path) in (other_device, other_file):
                return SimpleNamespace(st_mode=info.st_mode, st_blocks=info.st_blocks,
                                       st_dev=root_info.st_dev + 1)
            return info

        with mock.patch.object(owner.os, 'lstat', side_effect=cross_device_lstat):
            with self.assertRaisesRegex(RuntimeError, 'crossed device'):
                owner._allocated_bytes(root)

        # A file crossing must be rejected as well; it used to be silently
        # omitted by the allocator's same-device filter.
        def file_only_cross_device_lstat(path):
            info = original_lstat(path)
            if Path(path) == other_file:
                return SimpleNamespace(st_mode=info.st_mode, st_blocks=info.st_blocks,
                                       st_dev=root_info.st_dev + 1)
            return info

        with mock.patch.object(owner.os, 'lstat', side_effect=file_only_cross_device_lstat):
            with self.assertRaisesRegex(RuntimeError, 'crossed device'):
                owner._allocated_bytes(root)

    def test_nested_mount_inventory_rejected_before_lease_or_docker(self):
        source = Path(self.request['source_root'])
        nested = source / 'same-device-bind-alias'
        nested.mkdir()
        self.assertEqual(source.stat().st_dev, nested.stat().st_dev)
        fake = FakeDocker(self.request)
        inventory = [
            {'mount_id': '10', 'parent_id': '1', 'mountpoint': str(source),
             'filesystem': 'ext4', 'device': self.source_device},
            {'mount_id': '11', 'parent_id': '10', 'mountpoint': str(nested),
             'filesystem': 'ext4', 'device': self.source_device},
        ]
        with mock.patch.object(owner, '_filesystem_type', return_value='ext4'), \
             mock.patch.object(owner, '_mount_inventory', return_value=inventory):
            with self.assertRaisesRegex(RuntimeError, 'nested mount'):
                owner.BuildOwner(self.request, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_raw_mountinfo_nonbreaking_space_tmpfs_is_memory_backed_before_lease(self):
        # U+00A0 is a pathname byte sequence, not a mountinfo field separator.
        # Unicode split() used to truncate this path and select the outer ext4.
        source = self.root / 'source-with-\u00a0space'
        for git_root in (source / '.git', source / 'ihk' / '.git'):
            git_root.mkdir(parents=True)
            (git_root / 'config').write_text('[core]\n\trepositoryformatversion = 0\n')
        device = '%d:%d' % (os.major(source.stat().st_dev), os.minor(source.stat().st_dev))
        raw = (b'1 0 ' + device.encode('ascii') + b' / / rw - ext4 /dev/mock rw\n' +
               b'30 1 ' + device.encode('ascii') + b' / ' + os.fsencode(str(source)) +
               b' rw - tmpfs tmpfs rw\n')
        changed = dict(self.request, source_root=str(source),
                       memory_allocation_roots=[str(source)])
        fake = FakeDocker(changed)
        with mock.patch.object(owner.Path, 'read_bytes', return_value=raw), \
             mock.patch.object(owner, '_allocated_bytes', return_value=13 * 2**30):
            with self.assertRaisesRegex(RuntimeError, 'memory aggregate'):
                owner.BuildOwner(changed, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(changed['lease_path']).exists())

    def test_raw_mountinfo_malformed_bytes_and_escapes_fail_closed(self):
        cases = {
            'malformed-escape': b'1 0 8:1 / /bad\\999 rw - ext4 /dev/mock rw\n',
            'nul-path': b'1 0 8:1 / /bad\0path rw - ext4 /dev/mock rw\n',
            'raw-tab-path': b'1 0 8:1 / /bad\tpath rw - ext4 /dev/mock rw\n',
            'raw-space-path': b'1 0 8:1 / /bad path rw - ext4 /dev/mock rw\n',
            'bad-device': b'1 0 device / / rw - ext4 /dev/mock rw\n',
        }
        for label, raw in cases.items():
            with self.subTest(label=label), \
                 mock.patch.object(owner.Path, 'read_bytes', return_value=raw):
                with self.assertRaises(RuntimeError):
                    owner._mount_inventory()

    def test_mount_device_mismatch_rejected_before_allocation_lease_or_docker(self):
        source = Path(self.request['source_root'])
        fake = FakeDocker(self.request)
        allocated = mock.Mock(return_value=0)
        inventory = [
            {'mount_id': '1', 'parent_id': '0', 'mountpoint': '/',
             'filesystem': 'ext4', 'device': '8:1'},
            {'mount_id': '30', 'parent_id': '1', 'mountpoint': str(source),
             'filesystem': 'ext4', 'device': '0:0'},
        ]
        with mock.patch.object(owner, '_mount_inventory', return_value=inventory), \
             mock.patch.object(owner, '_allocated_bytes', allocated):
            with self.assertRaisesRegex(RuntimeError, 'mount device mismatch'):
                owner.BuildOwner(self.request, fake).run()
        allocated.assert_not_called()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_first_root_replacement_during_second_root_scan_rejected_before_lease_or_docker(self):
        source = Path(self.request['source_root'])
        backup = self.root / 'metadata-backup'
        backup.mkdir()
        backup_device = '%d:%d' % (os.major(backup.stat().st_dev), os.minor(backup.stat().st_dev))
        changed = dict(self.request,
                       memory_allocation_roots=[str(source), str(backup)])
        fake = FakeDocker(changed)
        stable = [
            {'mount_id': '1', 'parent_id': '0', 'mountpoint': '/',
             'filesystem': 'ext4', 'device': '8:1'},
            {'mount_id': '30', 'parent_id': '1', 'mountpoint': str(source),
             'filesystem': 'ext4', 'device': self.source_device},
            {'mount_id': '31', 'parent_id': '1', 'mountpoint': str(backup),
             'filesystem': 'ext4', 'device': backup_device},
        ]
        replaced = [
            {'mount_id': '1', 'parent_id': '0', 'mountpoint': '/',
             'filesystem': 'ext4', 'device': '8:1'},
            {'mount_id': '32', 'parent_id': '1', 'mountpoint': str(source),
             'filesystem': 'tmpfs', 'device': '0:42'},
            {'mount_id': '31', 'parent_id': '1', 'mountpoint': str(backup),
             'filesystem': 'ext4', 'device': backup_device},
        ]
        # Four reads validate/scan source.  The replacement starts while the
        # second root is being bound/scanned; only the aggregate-wide final
        # revalidation of source can close this cross-root race.
        with mock.patch.object(owner, '_mount_inventory',
                               side_effect=[stable] * 6 + [replaced] * 3):
            with self.assertRaisesRegex(RuntimeError, 'mount identity changed'):
                owner.BuildOwner(changed, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(changed['lease_path']).exists())

    def test_stacked_exact_root_mount_is_rejected_before_lease_or_docker(self):
        source = Path(self.request['source_root'])
        fake = FakeDocker(self.request)
        allocated = mock.Mock(return_value=0)
        inventory = [
            {'mount_id': '1', 'parent_id': '0', 'mountpoint': '/',
             'filesystem': 'ext4', 'device': '8:1'},
            {'mount_id': '20', 'parent_id': '1', 'mountpoint': str(source),
             'filesystem': 'ext4', 'device': self.source_device},
            # An upper tmpfs mounted at the identical path must never be
            # selected according to procfs row order.
            {'mount_id': '21', 'parent_id': '20', 'mountpoint': str(source),
             'filesystem': 'tmpfs', 'device': '0:42'},
        ]
        with mock.patch.object(owner, '_mount_inventory', return_value=inventory), \
             mock.patch.object(owner, '_allocated_bytes', allocated):
            with self.assertRaisesRegex(RuntimeError, 'ambiguous stacked mount'):
                owner.BuildOwner(self.request, fake).run()
        allocated.assert_not_called()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_root_mount_replacement_during_allocation_rejected_before_lease_or_docker(self):
        source = Path(self.request['source_root'])
        fake = FakeDocker(self.request)
        stable = [
            {'mount_id': '1', 'parent_id': '0', 'mountpoint': '/',
             'filesystem': 'ext4', 'device': '8:1'},
            {'mount_id': '30', 'parent_id': '1', 'mountpoint': str(source),
             'filesystem': 'ext4', 'device': self.source_device},
        ]
        replacement = [
            {'mount_id': '1', 'parent_id': '0', 'mountpoint': '/',
             'filesystem': 'ext4', 'device': '8:1'},
            {'mount_id': '31', 'parent_id': '1', 'mountpoint': str(source),
             'filesystem': 'tmpfs', 'device': '0:42'},
        ]
        # The third read is the allocation post-walk binding check.  A root
        # remount can preserve the pathname, so both mount identity and fs
        # type are checked instead of relying on the earlier ext4 label.
        with mock.patch.object(owner, '_mount_inventory',
                               side_effect=[stable, stable, replacement]):
            with self.assertRaisesRegex(RuntimeError, 'mount identity changed'):
                owner.BuildOwner(self.request, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_unambiguous_exact_root_mount_binding_remains_admissible(self):
        source = Path(self.request['source_root'])
        fake = FakeDocker(self.request)
        inventory = [
            {'mount_id': '1', 'parent_id': '0', 'mountpoint': '/',
             'filesystem': 'ext4', 'device': '8:1'},
            {'mount_id': '30', 'parent_id': '1', 'mountpoint': str(source),
             'filesystem': 'ext4', 'device': self.source_device},
        ]
        with mock.patch.object(owner, '_mount_inventory', return_value=inventory):
            result = owner.BuildOwner(self.request, fake).run()
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['measurement']['memory_allocation_bindings'][0]['mount'],
                         {'mount_id': '30', 'parent_id': '1', 'device': self.source_device,
                          'mountpoint': str(source), 'filesystem': 'ext4'})

    def test_ramfs_allocation_counts_against_aggregate_before_lease_or_docker(self):
        source = Path(self.request['source_root'])
        fake = FakeDocker(self.request)
        with mock.patch.object(owner, '_filesystem_type',
                               side_effect=lambda path, **unused: 'ramfs' if Path(path) == source else 'ext4'), \
             mock.patch.object(owner, '_allocated_bytes', return_value=13 * 2**30):
            with self.assertRaisesRegex(RuntimeError, 'memory aggregate'):
                owner.BuildOwner(self.request, fake).run()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_unsupported_allocation_filesystem_precedes_allocation_lease_or_docker(self):
        fake = FakeDocker(self.request)
        allocated = mock.Mock(return_value=0)
        with mock.patch.object(owner, '_filesystem_type', return_value='fuse.memoryfs'), \
             mock.patch.object(owner, '_allocated_bytes', allocated):
            with self.assertRaisesRegex(RuntimeError, 'filesystem unsupported'):
                owner.BuildOwner(self.request, fake).run()
        allocated.assert_not_called()
        self.assertEqual(fake.commands, [])
        self.assertFalse(Path(self.request['lease_path']).exists())

    def test_ext4_and_xfs_allocation_roots_remain_zero_memory_effect(self):
        source = Path(self.request['source_root'])
        backup = self.root / 'metadata-backup'
        backup.mkdir()
        changed = dict(self.request,
                       memory_allocation_roots=[str(source), str(backup)])

        def filesystem(path, **unused):
            return 'ext4' if Path(path) == source else 'xfs'

        with mock.patch.object(owner, '_filesystem_type', side_effect=filesystem), \
             mock.patch.object(owner, '_allocated_bytes', return_value=13 * 2**30):
            checked = owner.BuildOwner(changed)
            checked.validate()
        self.assertEqual(checked.measurement['candidate_memory_effect'],
                         {'classification': 'none', 'bytes': 0})
        self.assertEqual(checked.measurement['memory_allocation_memory_backed_bytes'], 0)
        self.assertEqual(checked.measurement['aggregate_memory_required'], 12 * 2**30)

    def test_lease_exclusive_and_cannot_steal(self):
        lease = owner.Lease(self.request['lease_path'], 'test')
        lease.acquire()
        with self.assertRaises(FileExistsError):
            owner.Lease(self.request['lease_path'], 'other').acquire()
        changed = json.loads(lease.path.read_text())
        changed['nonce'] = 'other'
        lease.path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(RuntimeError, 'changed'):
            lease.release()

    def test_hash_image_timeout_and_overlap_rejections(self):
        for key, value in [('candidate_sha', 'wrong'), ('image_id', 'tag'), ('timeout', 19801),
                           ('driver_path_sha256', '0' * 64), ('evidence_root', self.request['source_root'])]:
            changed = dict(self.request, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                owner.BuildOwner(changed).validate()

    def test_standalone_git_directories_are_admitted(self):
        owner.BuildOwner(self.request).validate()

    def test_main_and_ihk_gitfiles_are_rejected_before_lease(self):
        for relative in ('.git', 'ihk/.git'):
            with self.subTest(relative=relative):
                git_dir = Path(self.request['source_root']) / relative
                config = git_dir / 'config'
                config.unlink()
                git_dir.rmdir()
                git_dir.write_text('gitdir: /outside/worktree/.git\n')
                with self.assertRaisesRegex(ValueError, 'self-contained'):
                    owner.BuildOwner(self.request).validate()
                git_dir.unlink()
                git_dir.mkdir()
                config = git_dir / 'config'
                config.write_text('[core]\n\trepositoryformatversion = 0\n')

    def test_git_external_metadata_indirections_are_rejected(self):
        git_dir = Path(self.request['source_root']) / '.git'
        cases = [
            ('commondir', 'gitdir: /outside/common\n'),
            ('objects/info/alternates', '/outside/objects\n'),
            ('config', '[include]\n\tpath = /outside/config\n'),
            ('config', '[core]\n\tworktree = /outside/worktree\n'),
            ('config', '[core]\n\thooksPath = /outside/hooks\n'),
            ('config', '[core]\n\tfsmonitor = /outside/fsmonitor\n'),
        ]
        for relative, contents in cases:
            with self.subTest(relative=relative, contents=contents):
                target = git_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents)
                with self.assertRaises(ValueError):
                    owner.BuildOwner(self.request).validate()
                target.unlink()

    def test_git_metadata_symlink_is_rejected(self):
        git_dir = Path(self.request['source_root']) / '.git'
        target = self.root / 'outside-metadata'
        target.write_text('not metadata')
        link = git_dir / 'objects' / 'info' / 'link'
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'metadata symlink'):
            owner.BuildOwner(self.request).validate()

    def test_git_admission_does_not_add_metadata_mount(self):
        fake = FakeDocker(self.request)
        result = self.execute(fake)
        self.assertEqual(result['status'], 'PASS', result)
        create = next(command for command in fake.commands if command[0] == 'create')
        mounts = [create[index + 1] for index, value in enumerate(create) if value == '--mount']
        self.assertEqual(len(mounts), 6)
        self.assertEqual(sum(',dst=/src' in mount for mount in mounts), 1)
        self.assertFalse(any('/.git' in mount or 'git' in mount.lower() and '/src' not in mount
                             for mount in mounts))

    def test_real_and_effective_root_are_rejected(self):
        for real, effective in ((0, 1000), (1000, 0)):
            with self.subTest(real=real, effective=effective):
                with mock.patch.object(owner.os, 'getuid', return_value=real), \
                     mock.patch.object(owner.os, 'geteuid', return_value=effective):
                    with self.assertRaisesRegex(ValueError, 'unprivileged'):
                        owner.BuildOwner(self.request).validate()

    def test_create_uncertainty_preserves_lease(self):
        fake = FakeDocker(self.request)
        fake.fail_command = 'create'
        result = self.execute(fake)
        self.assertFalse(result['retired'])
        self.assertIsNone(result['terminal_container_retained'])
        self.assertEqual(result['terminal_container_retention_state'], 'unresolved')
        self.assertTrue(result['cleanup_separately_required'])
        self.assertTrue(Path(self.request['lease_path']).exists())

    def test_real_cli_sigterm_captures_partial_bytes_and_retires(self):
        signal_regression(self, self.root, 'owner', self.request, signal.SIGTERM)

    def test_real_cli_sigint_captures_partial_bytes_and_retires(self):
        signal_regression(self, self.root, 'owner', self.request, signal.SIGINT)

    def test_real_cli_sigterm_retains_unproven_lease(self):
        signal_regression(self, self.root, 'owner-hold', self.request, signal.SIGTERM)

    def test_real_sigkill_preserves_first_bytes_without_owner_finally(self):
        signal_regression(self, self.root, 'owner', self.request, signal.SIGKILL)

    def test_cli_signal_scope_restores_handlers(self):
        before = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
        with owner.CliSignals() as signals:
            signals.receive(signal.SIGTERM, None)
            with self.assertRaises(owner.OwnerInterrupted):
                signals.check()
            signals.cleaning = True
            signals.receive(signal.SIGINT, None)
            signals.check()
            self.assertEqual(signals.requested, signal.SIGTERM)
        self.assertEqual(before, {sig: signal.getsignal(sig) for sig in before})

    def test_real_command_keeps_parseable_stdout_separate_from_stderr(self):
        real_popen = subprocess.Popen
        def local(argv, **kwargs):
            self.assertEqual(argv[0], 'docker')
            self.assertNotEqual(kwargs['stdout'], subprocess.PIPE)
            self.assertNotEqual(kwargs['stderr'], subprocess.PIPE)
            return real_popen([sys.executable, '-u', '-c',
                               'import os; os.write(1,b\'{"Id":"bound-image"}\\n\'); os.write(2,b"diagnostic\\n")'], **kwargs)
        with mock.patch.object(owner.subprocess, 'Popen', local):
            result = owner.Docker(self.root / 'live.log').call(['inspect', 'local-fixture'])
        self.assertEqual(json.loads(result.stdout), {'Id': 'bound-image'})
        self.assertEqual(result.stderr, 'diagnostic\n')
        capture = next(self.root.glob('command-*'))
        self.assertEqual((capture / 'stdout').read_text(), result.stdout)
        self.assertEqual((capture / 'stderr').read_text(), result.stderr)
        self.assertEqual(json.loads((capture / 'status.json').read_text())['exit_code'], 0)

    def test_real_timeout_keeps_partial_output_and_reaps_client(self):
        real_popen = subprocess.Popen
        def local(argv, **kwargs):
            return real_popen([sys.executable, '-u', '-c',
                               'import os,time; os.write(1,b"timeout-out\\n"); os.write(2,b"timeout-err\\n"); time.sleep(10)'], **kwargs)
        docker = owner.Docker(self.root / 'live.log')
        with mock.patch.object(owner.subprocess, 'Popen', local):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                docker.call(['exec', 'local-fixture'], timeout=0.2)
        capture = next(self.root.glob('command-*'))
        self.assertEqual((capture / 'stdout').read_bytes(), b'timeout-out\n')
        self.assertEqual((capture / 'stderr').read_bytes(), b'timeout-err\n')
        status = json.loads((capture / 'status.json').read_text())
        self.assertEqual(status['exit_code'], -signal.SIGTERM)
        with self.assertRaises(ProcessLookupError):
            os.kill(status['pid'], 0)
        self.assertFalse(docker.client_retirement_unproven)

    def test_real_owner_prefix_is_immutable_and_askpass_is_not_evidence(self):
        seen = {}
        real_popen = subprocess.Popen
        def local(argv, **kwargs):
            seen['argv'] = list(argv)
            seen['env'] = dict(kwargs['env'])
            return real_popen([sys.executable, '-u', '-c', 'print("ok")'], **kwargs)
        with mock.patch.dict(os.environ, {'SUDO_ASKPASS': 'secret-do-not-log'}, clear=False), \
             mock.patch.object(owner.subprocess, 'Popen', local):
            result = owner.Docker(self.root / 'sudo.log', sudo=True).call(['inspect', 'local-fixture'])
        self.assertEqual(seen['argv'][:4], list(owner.SUDO_DOCKER_PREFIX))
        self.assertEqual(seen['argv'][4:], ['inspect', 'local-fixture'])
        self.assertEqual(seen['env']['SUDO_ASKPASS'], 'secret-do-not-log')
        log = (self.root / 'sudo.log').read_text()
        self.assertNotIn('secret-do-not-log', log)

    def test_term_is_sent_before_forced_kill_and_forced_path_is_unproven(self):
        process = mock.Mock(pid=12345, returncode=0)
        process.poll.side_effect = [None, None, 0]
        process.wait.side_effect = [subprocess.TimeoutExpired('docker', 5), 0]
        docker = owner.Docker(self.root / 'term.log')
        with mock.patch.object(owner.os, 'killpg') as killpg:
            status = {}
            docker._retire_client(process, status)
        self.assertEqual(killpg.call_args_list[0].args, (12345, signal.SIGTERM))
        self.assertEqual(killpg.call_args_list[1].args, (12345, signal.SIGKILL))
        self.assertTrue(docker.client_retirement_unproven)

    def test_already_exited_sudo_signal_is_unproven_even_without_group_members(self):
        for code in (-signal.SIGTERM, -signal.SIGKILL, 1, 0):
            with self.subTest(code=code):
                process = mock.Mock(pid=12345, returncode=code)
                process.poll.return_value = code
                docker = owner.Docker(self.root / 'already-exited.log', sudo=True)
                status = {}
                with mock.patch.object(docker, '_surviving_group_members', return_value=[]), \
                     mock.patch.object(owner.os, 'killpg') as killpg:
                    docker._retire_client(process, status)
                self.assertEqual(status['exit_code'], code)
                self.assertEqual(docker.client_retirement_unproven, code < 0)
                killpg.assert_not_called()
                process.wait.assert_not_called()

    def test_sudo_term_retirement_is_unproven_even_after_wrapper_reap(self):
        process = mock.Mock(pid=12345, returncode=-signal.SIGTERM)
        process.poll.side_effect = [None, -signal.SIGTERM]
        process.wait.return_value = -signal.SIGTERM
        docker = owner.Docker(self.root / 'term-sudo.log', sudo=True)
        status = {}
        with mock.patch.object(docker, '_surviving_group_members', return_value=[]), \
             mock.patch.object(owner.os, 'killpg') as killpg:
            docker._retire_client(process, status)
        killpg.assert_called_once_with(process.pid, signal.SIGTERM)
        self.assertEqual(status['exit_code'], -signal.SIGTERM)
        self.assertTrue(docker.client_retirement_unproven)
        self.assertTrue(status['client_retirement_unproven'])

    def test_normal_wait_classifies_sudo_signal_with_both_check_modes(self):
        real_popen = subprocess.Popen
        for sudo, code in ((True, -signal.SIGTERM), (True, -signal.SIGKILL),
                           (True, 1), (False, -signal.SIGTERM)):
            for check in (True, False):
                with self.subTest(sudo=sudo, code=code, check=check):
                    def local(argv, **kwargs):
                        program = ('import os,signal; os.kill(os.getpid(), %d)' % -code
                                   if code < 0 else 'raise SystemExit(%d)' % code)
                        return real_popen([sys.executable, '-u', '-c', program], **kwargs)
                    docker = owner.Docker(self.root / 'normal-wait.log', sudo=sudo)
                    with mock.patch.object(owner.subprocess, 'Popen', local):
                        if check:
                            with self.assertRaisesRegex(RuntimeError, 'docker command failed'):
                                docker.call(['start', 'local-fixture'], check=check)
                        else:
                            self.assertEqual(docker.call(['start', 'local-fixture'],
                                                         check=check).returncode, code)
                    self.assertEqual(docker.client_retirement_unproven, sudo and code < 0)

    def test_sudo_wrapper_death_and_delayed_start_keep_lease_after_terminal_observation(self):
        live = owner.Docker(self.root / 'ev' / 'sudo.log', sudo=True)
        process = mock.Mock(pid=12345, returncode=-signal.SIGKILL)
        process.wait.return_value = process.poll.return_value = -signal.SIGKILL

        class DelayedClient(FakeDocker):
            @property
            def client_retirement_unproven(self):
                return live.client_retirement_unproven

            def call(self, args, timeout=120, check=True):
                if args[0] == 'start':
                    self.commands.append(list(args))
                    # sudo dies before its escaped client sends the mutation.
                    return live.call(args, timeout, check)
                if args[0] == 'logs':
                    # Retirement has observed 'created'. The surviving client
                    # sends its delayed start after that final observation.
                    self.info['State'] = {'Status': 'running', 'Running': True, 'Pid': 1234}
                return super().call(args, timeout, check)

        fake = DelayedClient(self.request)
        with mock.patch.object(owner.subprocess, 'Popen', return_value=process), \
             mock.patch.object(live, '_surviving_group_members', return_value=[]):
            result = self.execute(fake)
        terminal = json.loads((self.root / 'ev' / 'inspect-terminal.json').read_text())
        self.assertEqual(terminal['State']['Status'], 'created')
        self.assertTrue(fake.info['State']['Running'])
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['retired'])
        self.assertTrue(result['client_retirement_unproven'])
        self.assertTrue(Path(self.request['lease_path']).exists())
        status = json.loads(next((self.root / 'ev').glob('command-*/status.json')).read_text())
        self.assertEqual(status['exit_code'], -signal.SIGKILL)
        self.assertTrue(status['client_retirement_unproven'])
        self.assertEqual([c[0] for c in fake.commands].count('start'), 1)
        self.assertFalse(any(c[0] in ('wait', 'rm') for c in fake.commands))


if __name__ == '__main__':
    unittest.main()
