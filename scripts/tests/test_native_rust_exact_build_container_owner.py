import copy
import json
import os
from pathlib import Path
import signal
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
            test.assertEqual(command_status['exit_code'], -signal.SIGKILL)
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
        for directory in ('src', 'assets', 'out', 'ev'):
            (self.root / directory).mkdir()
        self.request = {'candidate_sha': 'a' * 40, 'image_id': IMAGE, 'timeout': 20,
                        'source_root': str(self.root / 'src'), 'assets_root': str(self.root / 'assets'),
                        'output_root': str(self.root / 'out'), 'evidence_root': str(self.root / 'ev'),
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

    def tearDown(self):
        self.mem.stop()
        self.disk.stop()
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
        self.assertTrue(any(c[0] == 'rm' for c in fake.commands))

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

    def test_create_uncertainty_preserves_lease(self):
        fake = FakeDocker(self.request)
        fake.fail_command = 'create'
        result = self.execute(fake)
        self.assertFalse(result['retired'])
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
        with mock.patch.object(owner.subprocess, 'Popen', local):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                owner.Docker(self.root / 'live.log').call(['exec', 'local-fixture'], timeout=0.2)
        capture = next(self.root.glob('command-*'))
        self.assertEqual((capture / 'stdout').read_bytes(), b'timeout-out\n')
        self.assertEqual((capture / 'stderr').read_bytes(), b'timeout-err\n')
        status = json.loads((capture / 'status.json').read_text())
        self.assertEqual(status['exit_code'], -signal.SIGKILL)
        with self.assertRaises(ProcessLookupError):
            os.kill(status['pid'], 0)


if __name__ == '__main__':
    unittest.main()
