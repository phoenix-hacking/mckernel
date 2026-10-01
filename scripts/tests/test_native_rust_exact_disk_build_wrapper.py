import copy
import json
import os
import shutil
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock
import sys
import hashlib
import io
import subprocess

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import native_rust_exact_disk_build_wrapper as wrapper


class FakeOwner:
    LIMITS = dict(wrapper.EXPECTED_LIMITS)

    class provenance:
        ENV = {}

    class CliSignals:
        entered = 0
        exited = 0

        def __enter__(self):
            FakeOwner.CliSignals.entered += 1
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            FakeOwner.CliSignals.exited += 1
            return False

    calls = 0
    validations = 0
    measurement = None

    def __init__(self, request, signals=None):
        self.request = request
        self.signals = signals
        self.measurement = copy.deepcopy(FakeOwner.measurement)

    def validate(self):
        FakeOwner.validations += 1

    def run(self):
        self.validate()
        FakeOwner.calls += 1
        return {"status": "PASS", "retired": True,
                "cleanup_separately_required": False,
                "terminal_container_info": None,
                "terminal_container_info_current": True}


def request(source):
    return {
        "source_root": str(source),
        "memory_allocation_roots": [str(source)],
        "operational_exclusion_path": wrapper.OPERATIONAL_EXCLUSION_PATH,
    }


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.lock_dir = Path(tempfile.mkdtemp(prefix="mckernel-wrapper-lock-"))
        self.contract = mock.patch.object(wrapper, 'HEAVY_ENTRY_CONTRACT_RELEASED', True)
        self.contract.start()
        self.shared = mock.patch.object(wrapper, 'SHARED_HEAVY_LOCK_PATH', str(self.lock_dir / 'shared.lock'))
        self.shared.start()
        wrapper.OPERATIONAL_EXCLUSION_PATH = str(
            self.lock_dir / "native-exact-candidate-operational-exclusion-scratch18.json")
        wrapper.RETIRED_SCRATCH16_OPERATIONAL_EXCLUSION_PATH = str(
            self.lock_dir / "native-exact-candidate-operational-exclusion-scratch16.json")
        wrapper.RETIRED_SCRATCH17_OPERATIONAL_EXCLUSION_PATH = str(
            self.lock_dir / "native-exact-candidate-operational-exclusion-scratch17.json")
        FakeOwner.calls = FakeOwner.validations = 0
        FakeOwner.CliSignals.entered = FakeOwner.CliSignals.exited = 0
        FakeOwner.measurement = {
            "memory_allocation_memory_backed_bytes": 0,
            "memory_allocation_roots": [{"filesystem": "ext4", "memory_effect_bytes": 0, "allocated_bytes": 1}],
            "memory_allocation_total_bytes": 1,
            "memory_allocation_tmpfs_bytes": 0,
            "candidate_memory_effect": {"classification": "none", "bytes": 0},
            "aggregate_memory_required": wrapper.EXPECTED_LIMITS["Memory"],
        }
        self.reconcile = mock.patch.object(wrapper, "_dispatcher_reconcile", return_value={
            "processes": [], "containers": [], "leases": [],
            "resources": {"host_free": 64 * 2**30, "scratch_free": 64 * 2**30,
                          "memory_available": 32 * 2**30, "cpus": [2, 3, 4, 5]}})
        self.reconcile_mock = self.reconcile.start()

    def tearDown(self):
        shared = Path(wrapper.SHARED_HEAVY_LOCK_PATH)
        if shared.exists(): shared.unlink()
        self.shared.stop()
        self.contract.stop()
        lock = Path(wrapper.OPERATIONAL_EXCLUSION_PATH)
        if lock.exists():
            lock.unlink()
        self.reconcile.stop()
        self.lock_dir.rmdir()

    def test_retry2_release_classifier_and_exact_caller_contract(self):
        release = '/home/holden/mckernel/docs/verification/evidence/native-exact-scratch18-retry2-execution-20261001.py'
        self.assertTrue(wrapper._heavy_identity('/usr/bin/python3', ['python3', release]))
        self.assertTrue(wrapper._heavy_identity('/usr/bin/python3', ['python3', '/tmp/native-exact-scratch18-retry2-execution-20261001.py']))
        self.assertIn('script == RETRY2_RELEASE_PATH', wrapper.PRIVILEGED_PROCESS_OBSERVER_SOURCE)
        self.assertIn("Path(script).name == \"native_rust_exact_disk_build_wrapper.py\"", wrapper.PRIVILEGED_PROCESS_OBSERVER_SOURCE)
        self.assertNotIn("Path(script).name == \"native-exact-scratch18-retry2-execution-20261001.py\"", wrapper.PRIVILEGED_PROCESS_OBSERVER_SOURCE)

    def invoke(self, req, aggregate=wrapper.LAUNCHER_AGGREGATE_GIB):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)
            (source / "scripts").mkdir()
            owner_path = source / "scripts" / "native_rust_exact_build_container_owner.py"
            owner_path.write_text("# test placeholder\n")
            req = dict(req(source))
            with mock.patch.object(wrapper, "_load_owner", return_value=types.SimpleNamespace(
                    LIMITS=FakeOwner.LIMITS, provenance=FakeOwner.provenance,
                    CliSignals=FakeOwner.CliSignals,
                    BuildOwner=FakeOwner)):
                return wrapper.run_request(req, aggregate)

    def test_exact_boundary_runs_once(self):
        result = self.invoke(request)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(FakeOwner.calls, 1)
        self.assertEqual(FakeOwner.validations, 2)
        self.assertEqual(FakeOwner.CliSignals.entered, 1)
        self.assertEqual(FakeOwner.CliSignals.exited, 1)

    def test_shared_entry_contract_is_required_and_serializes_all_kinds(self):
        with mock.patch.object(wrapper, 'HEAVY_ENTRY_CONTRACT_RELEASED', False):
            with self.assertRaisesRegex(wrapper.AdmissionError, 'not released'):
                self.invoke(request)
        lock, record = wrapper.acquire_heavy_operation({}, 'image')
        for kind in ('build', 'guest', 'image'):
            with self.subTest(kind=kind), self.assertRaisesRegex(wrapper.AdmissionError, 'already exists'):
                wrapper.acquire_heavy_operation({}, kind)
        self.assertTrue(lock.exists())
        self.assertFalse(wrapper._release_exclusion(lock, record, {'status': 'FAIL'}))
        self.assertTrue(lock.exists())

    def test_validation_only_never_acquires_or_runs(self):
        owner = types.SimpleNamespace(LIMITS=FakeOwner.LIMITS, provenance=FakeOwner.provenance,
                                      BuildOwner=FakeOwner)
        with mock.patch.object(wrapper, '_load_owner', return_value=owner), \
             mock.patch.object(wrapper, '_acquire_exclusion') as acquire, \
             mock.patch.object(wrapper, '_dispatcher_reconcile') as census:
            result = wrapper.validate_request(request(self.lock_dir))
        self.assertEqual(result['status'], 'PASS_COMPATIBILITY_ONLY')
        self.assertEqual(FakeOwner.validations, 1)
        self.assertEqual(FakeOwner.calls, 0)
        acquire.assert_not_called(); census.assert_not_called()

    def test_nonempty_process_result_hard_blocks_before_owner_construction(self):
        self.reconcile.stop()
        try:
            for rows in ([{'pid': 55}], None, {'unknown': True}):
                with mock.patch.object(wrapper, '_dispatcher_processes', return_value=rows), \
                     mock.patch.object(wrapper, '_load_owner') as owner:
                    with self.assertRaisesRegex(wrapper.AdmissionError, 'heavy process'):
                        wrapper._dispatcher_reconcile(request(self.lock_dir))
                    owner.assert_not_called()
        finally:
            self.reconcile.start()

    def test_exact_executable_census_avoids_observer_self_match(self):
        for exe, argv in (('/usr/bin/qemu-system-x86_64', ['qemu-system-x86_64']),
                          ('/usr/bin/rustc', ['rustc', '--version']),
                          ('/usr/bin/python3.9', ['python3', '-B', '/x/native_rust_exact_build_container_owner.py'])):
            self.assertTrue(wrapper._heavy_identity(exe, argv))
        for exe, argv in (('/usr/bin/rg', ['rg', 'qemu|rustc']),
                          ('/usr/bin/python3.9', ['python3', '-c', 'rustc native_rust_exact_build_container_owner.py']),
                          ('/usr/bin/python3.9', ['python3', '-c', 'pass', 'native_rust_exact_build_container_owner.py']),
                          ('/usr/bin/python3.9evil', ['python3.9evil', 'native_rust_exact_build_container_owner.py']),
                          ('/usr/bin/bash', ['bash', '-c', 'echo qemu']),
                          ('/usr/bin/python3.9', ['python3', '/x/test_native_rust_exact_disk_build_wrapper.py'])):
            self.assertFalse(wrapper._heavy_identity(exe, argv))
        for exe in ('/usr/bin/python3.8', '/usr/bin/python3.9'):
            self.assertTrue(wrapper._heavy_identity(exe, ['python3', '-X', 'dev', '/x/native_rust_exact_build_container_owner.py']))
        self.assertTrue(wrapper._heavy_identity('/usr/bin/python3.9', ['python3', '-W', 'ignore', '/x/native_rust_exact_build_container_owner.py']))

    def test_embedded_and_wrapper_classifiers_have_python_option_parity(self):
        namespace = {'__name__': 'observer_test'}
        exec(wrapper.PRIVILEGED_PROCESS_OBSERVER_SOURCE, namespace)
        script = '/x/native_rust_exact_build_container_owner.py'
        for options in ([], ['-IW', 'ignore'], ['-IX', 'dev'], ['-IBWignore'],
                        ['-IBXdev'], ['-W', 'ignore'], ['-X', 'dev'],
                        ['-IBB', '-qSuv'], ['--check-hash-based-pycs', 'always'],
                        ['--check-hash-based-pycs=always'], ['--'],
                        ['-IX', '-W'], ['-IW', '-X']):
            argv = ['python3'] + options + [script]
            with self.subTest(argv=argv):
                self.assertEqual(wrapper._python_script_operand(argv), script)
                self.assertEqual(namespace['python_script'](argv), script)
                for exe in ('/usr/bin/python3.8', '/usr/bin/python3.9'):
                    self.assertTrue(wrapper._heavy_identity(exe, argv))
                    self.assertTrue(namespace['heavy'](exe, argv))
        for options in (['-c', 'pass'], ['-cpass'], ['-Icpass'], ['-m', 'pkg'],
                        ['-mpkg'], ['-Impkg'], ['-'], ['-V'], ['--help']):
            argv = ['python3'] + options + [script]
            with self.subTest(argv=argv):
                self.assertIsNone(wrapper._python_script_operand(argv))
                self.assertIsNone(namespace['python_script'](argv))
                self.assertFalse(namespace['heavy']('/usr/bin/python3.8', argv))
                self.assertFalse(wrapper._heavy_identity('/usr/bin/python3.8', argv))
        for options in (['-J'], ['-IJ'], ['--unknown'], ['--check-hash-based-pycsbad'],
                        ['--check-hash-based-pycs='], ['-I='], ['-IW'], ['-IX'],
                        ['--check-hash-based-pycs']):
            argv = ['python3'] + options
            with self.subTest(argv=argv):
                with self.assertRaises(wrapper.AdmissionError): wrapper._python_script_operand(argv)
                with self.assertRaises(ValueError): namespace['python_script'](argv)

    def test_attached_code_or_module_cannot_impersonate_calling_wrapper(self):
        namespace = {'__name__': 'observer_test'}
        exec(wrapper.PRIVILEGED_PROCESS_OBSERVER_SOURCE, namespace)
        for option in ('-cpass', '-mpkg', '-Icpass', '-Impkg'):
            with self.subTest(option=option), \
                 mock.patch.object(wrapper.os, 'getppid', return_value=91), \
                 mock.patch.object(wrapper.os, 'readlink', return_value='/usr/bin/python3.8'), \
                 mock.patch.dict(namespace, {'st': lambda pid: '1234',
                     'cmdline': lambda pid: ['python3', option, 'native_rust_exact_disk_build_wrapper.py']}), \
                 mock.patch.object(Path, 'read_text', return_value='Name:\ttest\nPPid:\t1\n'):
                with self.assertRaisesRegex(RuntimeError, 'calling wrapper identity unavailable'):
                    namespace['caller']()

    def test_process_census_requires_retirement_after_missing_or_empty_identity(self):
        entry = Path('/proc/900001')
        stat = '900001 (test) ' + ' '.join(['S', '1', '1', '1', '0', '0', '0'] + ['0'] * 12 + ['1234'])
        for raw in (b'python3\0worker.py\0', b''):
            with self.subTest(raw=raw), mock.patch.object(Path, 'iterdir', return_value=[entry]), \
                 mock.patch.object(wrapper, '_proc_starttime', return_value='1234'), \
                 mock.patch.object(Path, 'open', side_effect=lambda *a, **k: io.BytesIO(raw)), \
                 mock.patch.object(Path, 'read_text', return_value=stat), \
                 mock.patch.object(wrapper.os, 'readlink', side_effect=FileNotFoundError()):
                with self.assertRaises(wrapper.AdmissionError): wrapper._dispatcher_processes()
        for starts in (['1234', FileNotFoundError()], ['1234', '5678']):
            with self.subTest(starts=starts), mock.patch.object(Path, 'iterdir', return_value=[entry]), \
                 mock.patch.object(wrapper, '_proc_starttime', side_effect=starts), \
                 mock.patch.object(Path, 'open', return_value=io.BytesIO(b'python3\0worker.py\0')), \
                 mock.patch.object(wrapper.os, 'readlink', side_effect=FileNotFoundError()):
                self.assertEqual(wrapper._dispatcher_processes(), [])

    def test_empty_process_identity_parity_and_initial_stat_race(self):
        namespace = {'__name__': 'observer_test'}
        exec(wrapper.PRIVILEGED_PROCESS_OBSERVER_SOURCE, namespace)
        entry = Path('/proc/900001')
        for state, flags, accepted in (('S', '0', False), ('S', str(0x200000), True),
                                       ('Z', '0', True), ('X', '0', True)):
            stat = '900001 (test) ' + ' '.join([state, '1', '1', '1', '0', '0', flags] + ['0'] * 12 + ['1234'])
            with self.subTest(state=state, flags=flags), \
                 mock.patch.object(Path, 'iterdir', return_value=[entry]), \
                 mock.patch.object(Path, 'open', side_effect=lambda *a, **k: io.BytesIO(b'')), \
                 mock.patch.object(Path, 'read_text', return_value=stat), \
                 mock.patch.object(wrapper, '_proc_starttime', return_value='1234'), \
                 mock.patch.object(wrapper.os, 'geteuid', return_value=0), \
                 mock.patch.dict(namespace, {'caller': lambda: (91, '2345'), 'st': lambda pid: '1234'}), \
                 mock.patch('builtins.print'):
                if accepted:
                    self.assertEqual(wrapper._dispatcher_processes(), [])
                    namespace['observe']()
                else:
                    with self.assertRaises(wrapper.AdmissionError): wrapper._dispatcher_processes()
                    with self.assertRaisesRegex(RuntimeError, 'live process command line unavailable'):
                        namespace['observe']()
        for raw in (b'python3\0worker.py\0',):
            with mock.patch.object(Path, 'iterdir', return_value=[entry]), \
                 mock.patch.object(Path, 'open', side_effect=lambda *a, **k: io.BytesIO(raw)), \
                 mock.patch.object(Path, 'read_text', return_value='boot'), \
                 mock.patch.object(wrapper.os, 'geteuid', return_value=0), \
                 mock.patch.object(wrapper.os, 'readlink', side_effect=FileNotFoundError()), \
                 mock.patch.dict(namespace, {'caller': lambda: (91, '2345'), 'st': lambda pid: '1234'}):
                with self.assertRaisesRegex(RuntimeError, 'process executable disappeared'):
                    namespace['observe']()
        with mock.patch.object(Path, 'iterdir', return_value=[entry]), \
             mock.patch.object(wrapper, '_proc_starttime', side_effect=[FileNotFoundError(), '1234']):
            with self.assertRaises(wrapper.AdmissionError): wrapper._dispatcher_processes()

    def test_python_cluster_options_match_real_interpreter(self):
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / 'native_rust_exact_build_container_owner.py'
            script.write_text('print("parser-script-reached")\n')
            for options in (['-IW', 'ignore'], ['-IX', 'dev'], ['-IBWignore'], ['-IBXdev'],
                            ['-W', ''], ['-X', ''], ['-IW', ''], ['-IX', '']):
                with self.subTest(options=options):
                    result = subprocess.run([sys.executable] + options + [str(script)],
                                            capture_output=True, timeout=5)
                    self.assertEqual((result.returncode, result.stdout), (0, b'parser-script-reached\n'))
                    self.assertEqual(wrapper._python_script_operand([sys.executable] + options + [str(script)]), str(script))

    def test_embedded_cmdline_read_is_bounded_for_caller_and_census(self):
        namespace = {'__name__': 'observer_test'}
        exec(wrapper.PRIVILEGED_PROCESS_OBSERVER_SOURCE, namespace)
        stream = mock.MagicMock()
        stream.__enter__.return_value = stream
        stream.read.return_value = b'x' * (wrapper.MAX_CMDLINE_BYTES + 1)
        with mock.patch.object(Path, 'open', return_value=stream):
            with self.assertRaisesRegex(RuntimeError, 'command line exceeds bound'):
                namespace['cmdline'](91)
        stream.read.assert_called_once_with(wrapper.MAX_CMDLINE_BYTES + 1)

    def test_empty_option_operands_survive_both_complete_census_paths(self):
        namespace = {'__name__': 'observer_test'}
        exec(wrapper.PRIVILEGED_PROCESS_OBSERVER_SOURCE, namespace)
        entry = Path('/proc/900001')
        script = '/x/native_rust_exact_build_container_owner.py'
        expected = [{'pid': 900001, 'starttime': '1234', 'executable': '/usr/bin/python3.8'}]
        for option in ('-W', '-X', '-IW', '-IX'):
            raw = b'python3\0' + option.encode() + b'\0\0' + script.encode() + b'\0'
            with self.subTest(option=option), \
                 mock.patch.object(Path, 'iterdir', return_value=[entry]), \
                 mock.patch.object(Path, 'open', side_effect=lambda *a, **k: io.BytesIO(raw)), \
                 mock.patch.object(Path, 'read_text', return_value='boot'), \
                 mock.patch.object(wrapper, '_proc_starttime', return_value='1234'), \
                 mock.patch.object(wrapper.os, 'geteuid', return_value=0), \
                 mock.patch.object(wrapper.os, 'readlink', return_value='/usr/bin/python3.8'), \
                 mock.patch.dict(namespace, {'caller': lambda: (91, '2345'), 'st': lambda pid: '1234'}), \
                 mock.patch('builtins.print') as output:
                self.assertEqual(wrapper._dispatcher_processes(), expected)
                self.assertEqual(namespace['cmdline'](900001), ['python3', option, '', script])
                namespace['observe']()
                self.assertEqual(json.loads(output.call_args.args[0])['processes'], expected)
        raw = b'python3\0' + b'\0' * wrapper.MAX_ARG_COUNT
        with mock.patch.object(Path, 'iterdir', return_value=[entry]), \
             mock.patch.object(Path, 'open', side_effect=lambda *a, **k: io.BytesIO(raw)), \
             mock.patch.object(wrapper, '_proc_starttime', return_value='1234'):
            with self.assertRaisesRegex(wrapper.AdmissionError, 'argument exceeds bound'):
                wrapper._dispatcher_processes()
            with self.assertRaisesRegex(RuntimeError, 'argument exceeds bound'):
                namespace['cmdline'](900001)

    def test_bounded_observer_capture_caps_both_streams_and_reaps(self):
        for payload in ("import os; os.write(1, b'x' * 2000000)",
                        "import os; os.write(2, b'x' * 2000000)"):
            children = []
            real_popen = subprocess.Popen
            def launch(*args, **kwargs):
                child = real_popen(*args, **kwargs)
                children.append(child)
                return child
            with self.subTest(payload=payload), mock.patch.object(wrapper.subprocess, 'Popen', side_effect=launch):
                with self.assertRaisesRegex(wrapper.AdmissionError, 'report exceeds bound'):
                    wrapper._run_bounded_observer([sys.executable, '-I', '-B', '-'], payload.encode(), {})
            self.assertIsNotNone(children[0].poll())
            self.assertTrue(all(stream.closed for stream in (children[0].stdin, children[0].stdout, children[0].stderr)))
        result = wrapper._run_bounded_observer([sys.executable, '-I', '-B', '-'], b'print("{}")', {})
        self.assertEqual((result.returncode, result.stdout), (0, b'{}\n'))
        with self.assertRaisesRegex(wrapper.AdmissionError, 'timed out'):
            wrapper._run_bounded_observer([sys.executable, '-I', '-B', '-'], b'import time; time.sleep(3)', {}, timeout=0.05)

    def test_permission_limited_process_census_uses_authenticated_observer(self):
        report = {'schema': 'mckernel.heavy-process-observation.v1',
                  'status': 'PASS_READ_ONLY',
                  'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'processes': [{'pid': 91, 'starttime': '1234',
                                 'executable': '/usr/bin/rustc'}]}
        completed = types.SimpleNamespace(returncode=0,
                                          stdout=json.dumps(report).encode(), stderr=b'')
        with mock.patch.object(wrapper, '_proc_starttime', side_effect=PermissionError()), \
             mock.patch.object(wrapper, '_run_bounded_observer', return_value=completed) as run, \
             mock.patch.dict(os.environ, {'SUDO_ASKPASS': '/secret-askpass', 'EVIL': 'nope'}):
            self.assertEqual(wrapper._dispatcher_processes(), report['processes'])
        self.assertEqual(run.call_args.args[0],
                         ['/usr/bin/sudo', '-A', '/usr/bin/python3', '-I', '-B', '-'])
        self.assertNotIn(b'/secret-askpass', run.call_args.args[1])
        self.assertEqual(run.call_args.args[2], {
            'PATH': '/usr/bin:/bin', 'LANG': 'C',
            'LC_ALL': 'C', 'SUDO_ASKPASS': '/secret-askpass'})

    def test_privileged_process_report_is_strict_and_fail_closed(self):
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        base = {'schema': 'mckernel.heavy-process-observation.v1',
                'status': 'PASS_READ_ONLY', 'boot_id': boot,
                'processes': [{'pid': 91, 'starttime': '1234',
                               'executable': '/usr/bin/rustc'}]}
        for mutate in (lambda r: r.update(schema='wrong'),
                       lambda r: r.update(processes=[dict(r['processes'][0]), dict(r['processes'][0])]),
                       lambda r: r['processes'][0].update(pid=True),
                       lambda r: r['processes'][0].update(executable='rustc')):
            report = copy.deepcopy(base); mutate(report)
            completed = types.SimpleNamespace(returncode=0,
                                              stdout=json.dumps(report).encode(), stderr=b'')
            with self.subTest(report=report), mock.patch.object(wrapper, '_run_bounded_observer', return_value=completed):
                with self.assertRaises(wrapper.AdmissionError):
                    wrapper._privileged_process_observation()
        with mock.patch.object(wrapper, '_run_bounded_observer', side_effect=PermissionError('sudo denied')):
            with self.assertRaisesRegex(wrapper.AdmissionError, 'observer unavailable'):
                wrapper._privileged_process_observation()
        oversized = copy.deepcopy(base)
        oversized['processes'][0]['executable'] = '/' + ('x' * wrapper.MAX_REPORT_BYTES)
        completed = types.SimpleNamespace(returncode=0, stdout=json.dumps(oversized).encode(), stderr=b'')
        with mock.patch.object(wrapper, '_run_bounded_observer', return_value=completed):
            with self.assertRaisesRegex(wrapper.AdmissionError, 'report exceeds bound'):
                wrapper._privileged_process_observation()

    def test_observer_keeps_ordinary_unprivileged_census_path(self):
        with mock.patch.object(Path, 'iterdir', return_value=[Path('/proc/900001')]), \
             mock.patch.object(Path, 'open', return_value=io.BytesIO(b'rg\0pattern\0')), \
             mock.patch.object(wrapper, '_proc_starttime', return_value='1234'), \
             mock.patch.object(wrapper.os, 'readlink', return_value='/usr/bin/rg'):
            self.assertIsInstance(wrapper._dispatcher_processes(), list)

    def test_container_census_rejects_unknown_json_and_all_live_names(self):
        good = {'ID': 'a' * 64, 'Image': 'unrelated', 'Names': 'innocent',
                'State': 'running', 'Status': 'Up 10 seconds'}
        for data in (b'null', b'[]', b'1', b'{}', b'{"ID":"a","ID":"b"}',
                     json.dumps(dict(good, State='unknown')).encode(),
                     json.dumps(dict(good, ID=True)).encode(), json.dumps(good).encode()):
            result = types.SimpleNamespace(returncode=0, stdout=data, stderr=b'')
            with mock.patch.object(wrapper, '_run_bounded_observer', return_value=result):
                with self.assertRaises(wrapper.AdmissionError): wrapper._dispatcher_containers()
        with mock.patch.object(wrapper, '_run_bounded_observer', return_value=types.SimpleNamespace(returncode=0, stdout=b'')) as run, \
             mock.patch.dict(os.environ, {'SUDO_ASKPASS': '/synthetic-helper', 'EVIL': 'discard'}):
            self.assertEqual(wrapper._dispatcher_containers(), [])
            self.assertEqual(run.call_args.args[2].get('SUDO_ASKPASS'), '/synthetic-helper')
            self.assertNotIn('HOME', run.call_args.args[2])
            self.assertNotIn('EVIL', run.call_args.args[2])

    def test_sudo_environment_omits_home_and_unrelated_variables(self):
        base = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
        for helper in (None, '/synthetic-helper'):
            inherited = {'HOME': '/synthetic-home', 'PATH': '/untrusted-bin',
                         'LANG': 'other', 'LC_ALL': 'other', 'UNRELATED': 'discard'}
            expected = dict(base)
            if helper is not None:
                inherited['SUDO_ASKPASS'] = helper
                expected['SUDO_ASKPASS'] = helper
            with self.subTest(helper=helper), mock.patch.dict(os.environ, inherited, clear=True):
                self.assertEqual(wrapper._sudo_environment(), expected)
                self.assertNotIn('HOME', wrapper._sudo_environment())
                self.assertNotIn('UNRELATED', wrapper._sudo_environment())

    def test_recovery_census_cli_is_read_only_and_strict(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'request.json'
            raw = json.dumps(request(self.lock_dir)).encode()
            path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            before = path.stat()
            with mock.patch.object(wrapper, 'acquire_heavy_operation') as shared, \
                 mock.patch.object(wrapper, '_acquire_exclusion') as attempt, \
                 mock.patch.object(wrapper, '_load_owner') as owner, \
                 mock.patch.object(wrapper, 'run_request') as run, \
                 mock.patch('builtins.print') as output:
                self.assertEqual(wrapper.main([str(path), '--census-only', '--request-sha256', digest]), 0)
            shared.assert_not_called(); attempt.assert_not_called(); owner.assert_not_called(); run.assert_not_called()
            report = json.loads(output.call_args.args[0])
            self.assertEqual(set(report), {'schema', 'status', 'execution_released', 'boot_id', 'request',
                                          'processes', 'containers', 'leases', 'resources'})
            self.assertEqual(report['status'], 'PASS_READ_ONLY')
            self.assertFalse(report['execution_released'])
            self.assertEqual(report['request']['sha256'], digest)
            self.assertEqual(report['request']['inode'], before.st_ino)
            self.assertEqual(report['request']['normalized_sha256'], wrapper._request_hash(json.loads(raw)))
            self.assertEqual(path.stat(), before)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(list(Path(td).iterdir()), [path])
            for args in ([str(path), '--census-only'],
                         [str(path), '--census-only', '--validate-only', '--request-sha256', digest],
                         [str(path), '--request-sha256', digest],
                         [str(path), '--census', '--request-sha256', digest]):
                with self.subTest(args=args), mock.patch('sys.stderr', new_callable=io.StringIO):
                    with self.assertRaises(SystemExit): wrapper.main(args)

    def test_recovery_census_binds_open_descriptor_and_rejects_malformed_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'request.json'
            valid_raw = json.dumps(request(self.lock_dir)).encode()
            for raw in (b'[]', b'{"host_floor":NaN}', b'{"host_floor":1,"host_floor":2}',
                        b'{"host_floor":true}', b'x' * (wrapper.MAX_REPORT_BYTES + 1)):
                path.write_bytes(raw)
                with self.subTest(raw=raw[:60]), self.assertRaises(wrapper.AdmissionError):
                    wrapper.census_request(path, hashlib.sha256(raw).hexdigest())
            path.write_bytes(valid_raw)
            digest = hashlib.sha256(valid_raw).hexdigest()
            with self.assertRaises(wrapper.AdmissionError): wrapper.census_request(path, '0' * 64)
            with self.assertRaises(wrapper.AdmissionError): wrapper.census_request(path, None)
            link = Path(td) / 'link'; link.symlink_to(path)
            with self.assertRaises(wrapper.AdmissionError): wrapper.census_request(link, digest)
            good = copy.deepcopy(self.reconcile_mock.return_value)
            def change_bytes(req):
                path.write_bytes(valid_raw + b' ')
                return good
            def replace_inode(req):
                path.unlink(); path.write_bytes(valid_raw)
                return good
            for mutate in (change_bytes, replace_inode):
                path.write_bytes(valid_raw)
                with self.subTest(mutate=mutate.__name__), \
                     mock.patch.object(wrapper, '_dispatcher_reconcile', side_effect=mutate), \
                     self.assertRaisesRegex(wrapper.AdmissionError, 'changed during observations'):
                    wrapper.census_request(path, digest)
            path.write_bytes(valid_raw)
            for field, value in (('processes', [{'pid': 42}]), ('containers', [{'ID': 'live'}]),
                                 ('leases', [{}]), ('resources', {'host_free': float('nan')})):
                bad = copy.deepcopy(good); bad[field] = value
                with self.subTest(field=field), mock.patch.object(wrapper, '_dispatcher_reconcile', return_value=bad), \
                     self.assertRaises(wrapper.AdmissionError):
                    wrapper.census_request(path, digest)
            with mock.patch.object(wrapper, '_dispatcher_reconcile', side_effect=wrapper.AdmissionError('observer timed out')), \
                 mock.patch('builtins.print') as output:
                self.assertEqual(wrapper.main([str(path), '--census-only', '--request-sha256', digest]), 1)
                self.assertEqual(json.loads(output.call_args.args[0]),
                                 {'schema': 'mckernel.heavy-recovery-census.v1', 'status': 'REFUSED'})
            with self.assertRaisesRegex(wrapper.AdmissionError, 'report exceeds bound'):
                wrapper._encode_census_report({'x': 'y' * wrapper.MAX_REPORT_BYTES})
            with self.assertRaisesRegex(wrapper.AdmissionError, 'report malformed'):
                wrapper._encode_census_report({'x': float('nan')})

    def test_recovery_census_rejects_actual_ancestor_replacement(self):
        for replacement in ('different-bytes', 'same-bytes', 'symlink', 'mode-change'):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                ancestor = root / 'ancestor'
                parent = ancestor / 'requests'
                parent.mkdir(parents=True)
                path = parent / 'request.json'
                raw = json.dumps(request(self.lock_dir)).encode()
                path.write_bytes(raw)
                original_inode = path.stat().st_ino
                good = copy.deepcopy(self.reconcile_mock.return_value)
                def change_ancestor(req):
                    if replacement == 'mode-change':
                        ancestor.chmod(0o700)
                    else:
                        ancestor.rename(root / 'detached')
                        if replacement == 'symlink':
                            ancestor.symlink_to(root / 'detached', target_is_directory=True)
                        else:
                            parent.mkdir(parents=True)
                            path.write_bytes(raw if replacement == 'same-bytes' else b'replacement')
                            self.assertNotEqual(path.stat().st_ino, original_inode)
                    return good
                ancestor.chmod(0o755)
                with mock.patch.object(wrapper, '_dispatcher_reconcile', side_effect=change_ancestor):
                    with self.assertRaises(wrapper.AdmissionError):
                        wrapper.census_request(path, hashlib.sha256(raw).hexdigest())
                if replacement != 'mode-change':
                    self.assertEqual((root / 'detached/requests/request.json').read_bytes(), raw)

    def test_recovery_subprocess_keeps_real_wrapper_caller_identity(self):
        # Test-only copy instruments observation boundaries; production offers
        # no environment hook or caller spoof. The embedded caller() reads the
        # actual /proc identity of the wrapper subprocess launched by recovery.
        fixture = r'''
def _test_permission(pid): raise PermissionError()
_proc_starttime = _test_permission
def _test_observe(command, source, env, timeout=15):
    assert command == ['/usr/bin/sudo', '-A', '/usr/bin/python3', '-I', '-B', '-']
    assert source == PRIVILEGED_PROCESS_OBSERVER_SOURCE.encode()
    import sys
    probe = source.decode().replace('if __name__ == "__main__": observe()', '')
    probe += '\nassert caller()[0] == os.getppid()\n'
    probe += 'print(json.dumps({"schema":"mckernel.heavy-process-observation.v1", "status":"PASS_READ_ONLY", "boot_id":Path("/proc/sys/kernel/random/boot_id").read_text().strip(), "processes":[]}))\n'
    return subprocess.run([sys.executable, '-I', '-B', '-'], input=probe.encode(), capture_output=True, timeout=5)
_run_bounded_observer = _test_observe
_dispatcher_containers = lambda: []
_dispatcher_leases = lambda request: []
_dispatcher_resources = lambda request: {'host_free': 64 * 2**30, 'scratch_free': 64 * 2**30, 'memory_available': 32 * 2**30, 'cpus': [2,3,4,5]}
def _test_mutation(*args, **kwargs): raise AssertionError('mutation entered')
acquire_heavy_operation = _acquire_exclusion = _load_owner = run_request = _test_mutation
'''
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            script = root / 'native_rust_exact_disk_build_wrapper.py'
            source = Path(wrapper.__file__).read_text()
            marker = 'if __name__ == "__main__":\n    raise SystemExit(main())'
            self.assertEqual(source.count(marker), 1)
            script.write_text(source.replace(marker, fixture + '\n' + marker))
            caller = root / 'recovery_caller.py'
            caller.write_text('import subprocess,sys\np=subprocess.run([sys.executable,"-I","-B"]+sys.argv[1:],capture_output=True,timeout=10)\nsys.stdout.buffer.write(p.stdout)\nsys.stderr.buffer.write(p.stderr)\nsys.exit(p.returncode)\n')
            path = root / 'request.json'
            # Read the production constant from the unmodified source namespace.
            production = {'__name__': 'synthetic_import', '__file__': str(script)}
            exec(source, production)
            raw = json.dumps({'operational_exclusion_path': production['OPERATIONAL_EXCLUSION_PATH']}).encode()
            path.write_bytes(raw)
            before = path.stat()
            result = subprocess.run([sys.executable, '-I', '-B', str(caller), str(script), str(path),
                                     '--census-only', '--request-sha256', hashlib.sha256(raw).hexdigest()],
                                    capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            report = json.loads(result.stdout)
            self.assertEqual(report['status'], 'PASS_READ_ONLY')
            self.assertEqual(report['processes'], [])
            self.assertEqual(path.stat(), before)
            self.assertEqual(set(root.iterdir()), {script, caller, path})

    def test_serialization_lock_spans_reconciled_owner_execution(self):
        events = []
        self.reconcile_mock.side_effect = lambda req: events.append('reconcile') or {}
        real_acquire = wrapper._acquire_exclusion
        def acquire(req):
            events.append('lock')
            return real_acquire(req)
        real_run = FakeOwner.run
        def run(owner_instance):
            events.append('owner')
            return real_run(owner_instance)
        with mock.patch.object(wrapper, '_acquire_exclusion', side_effect=acquire), \
             mock.patch.object(FakeOwner, 'run', run):
            self.assertEqual(self.invoke(request)['status'], 'PASS')
        self.assertEqual(events, ['lock', 'reconcile', 'owner'])

    def test_dispatcher_reconciliation_collects_explicit_domains(self):
        self.reconcile.stop()
        try:
            with mock.patch.object(wrapper, '_dispatcher_processes', return_value=[]), \
                 mock.patch.object(wrapper, '_dispatcher_containers', return_value=[]), \
                 mock.patch.object(wrapper, '_dispatcher_leases', return_value=[]), \
                 mock.patch.object(wrapper, '_dispatcher_resources', return_value={'fresh': True}):
                result = wrapper._dispatcher_reconcile(request(Path(self.lock_dir)))
        finally:
            self.reconcile.start()
        self.assertEqual(set(result), {'processes', 'containers', 'leases', 'resources'})
        self.assertEqual(result['resources'], {'fresh': True})

    def test_non_tombstone_lease_blocks_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            old_root = wrapper.DISPATCHER_SCRATCH_ROOT
            wrapper.DISPATCHER_SCRATCH_ROOT = td
            try:
                (Path(td) / 'native-exact-build-lease-live.json').write_text(
                    '{"pid": 123, "starttime": "456"}')
                with self.assertRaisesRegex(wrapper.AdmissionError, 'non-tombstone lease'):
                    wrapper._dispatcher_leases(request(self.lock_dir))
            finally:
                wrapper.DISPATCHER_SCRATCH_ROOT = old_root

    def test_tombstone_with_live_owner_identity_blocks_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            old_root = wrapper.DISPATCHER_SCRATCH_ROOT
            wrapper.DISPATCHER_SCRATCH_ROOT = td
            try:
                start = wrapper._proc_starttime(os.getpid())
                (Path(td) / 'native-exact-build-lease-tombstone.json').write_text(
                    json.dumps({'tombstone': True, 'pid': os.getpid(), 'starttime': start}))
                with self.assertRaisesRegex(wrapper.AdmissionError, 'still live'):
                    wrapper._dispatcher_leases(request(self.lock_dir))
            finally:
                wrapper.DISPATCHER_SCRATCH_ROOT = old_root

    def test_unverifiable_dispatcher_observation_blocks_before_lock(self):
        self.reconcile.stop()
        try:
            with mock.patch.object(wrapper, '_dispatcher_processes',
                                   side_effect=wrapper.AdmissionError('process identity unverifiable')):
                with self.assertRaisesRegex(wrapper.AdmissionError, 'unverifiable'):
                    wrapper.run_request(request(self.lock_dir))
            self.assertTrue(Path(wrapper.OPERATIONAL_EXCLUSION_PATH).exists())
            Path(wrapper.OPERATIONAL_EXCLUSION_PATH).unlink()
        finally:
            self.reconcile.start()

    def test_dispatcher_reconciliation_is_required_before_exclusion(self):
        with mock.patch.object(wrapper, "_dispatcher_reconcile",
                               side_effect=wrapper.AdmissionError("unverifiable live owner")):
            with self.assertRaisesRegex(wrapper.AdmissionError, "unverifiable"):
                self.invoke(request)
        self.assertTrue(Path(wrapper.OPERATIONAL_EXCLUSION_PATH).exists())
        Path(wrapper.OPERATIONAL_EXCLUSION_PATH).unlink()
        self.assertEqual(FakeOwner.calls, 0)

    def test_fresh_exclusion_replaces_retired_tombstone(self):
        self.assertNotEqual(wrapper.OPERATIONAL_EXCLUSION_PATH,
                            wrapper.RETIRED_OPERATIONAL_EXCLUSION_PATH)
        self.assertTrue(wrapper.OPERATIONAL_EXCLUSION_PATH.endswith(
            "native-exact-candidate-operational-exclusion-scratch18.json"))
        self.assertTrue(wrapper.RETIRED_SCRATCH17_OPERATIONAL_EXCLUSION_PATH.endswith(
            "native-exact-candidate-operational-exclusion-scratch17.json"))
        self.assertTrue(wrapper.RETIRED_SCRATCH16_OPERATIONAL_EXCLUSION_PATH.endswith(
            "native-exact-candidate-operational-exclusion-scratch16.json"))
        for rejected_path in (
            wrapper.CONSUMED_EXPORTSET16_OPERATIONAL_EXCLUSION_PATH,
            wrapper.RETIRED_SCRATCH16_OPERATIONAL_EXCLUSION_PATH,
            wrapper.RETIRED_SCRATCH17_OPERATIONAL_EXCLUSION_PATH,
            wrapper.RETIRED_OPERATIONAL_EXCLUSION_PATH,
            wrapper.REVIEWED_OPERATIONAL_EXCLUSION_PATH,
            wrapper.SUPERSEDED_OPERATIONAL_EXCLUSION_PATH,
            wrapper.CLOSUREFIX_OPERATIONAL_EXCLUSION_PATH,
            wrapper.RUNTIMECLOSURE_OPERATIONAL_EXCLUSION_PATH,
            wrapper.OFFLINECWD_OPERATIONAL_EXCLUSION_PATH,
            wrapper.MEMORYMAP_OPERATIONAL_EXCLUSION_PATH,
            wrapper.MEMORYMAP_RELOCATED_OPERATIONAL_EXCLUSION_PATH,
            wrapper.MAPPINGBINDING_OPERATIONAL_EXCLUSION_PATH,
            wrapper.LIFECYCLEBINDING_OPERATIONAL_EXCLUSION_PATH,
            wrapper.OBJTOOLBINDING_OPERATIONAL_EXCLUSION_PATH,
            wrapper.RUNTIMEBLOB_OPERATIONAL_EXCLUSION_PATH,
            wrapper.SELFDIGEST_OPERATIONAL_EXCLUSION_PATH,
        ):
            old_request = request
            def rejected_request(source, path=rejected_path):
                value = old_request(source)
                value["operational_exclusion_path"] = path
                return value
            with self.assertRaisesRegex(wrapper.AdmissionError,
                                        "reviewed exact path"):
                self.invoke(rejected_request)
        self.assertEqual(FakeOwner.calls, 0)
        lock, record = wrapper._acquire_exclusion(
            {"operational_exclusion_path": wrapper.OPERATIONAL_EXCLUSION_PATH})
        self.assertTrue(lock.exists())
        self.assertEqual(record["request_sha256"], wrapper._request_hash(
            {"operational_exclusion_path": wrapper.OPERATIONAL_EXCLUSION_PATH}))
        lock.unlink()
        result = self.invoke(request)
        self.assertEqual(result["status"], "PASS")

    def test_request_hash_remains_bound_to_exact_fresh_path(self):
        request_with_fresh_path = {
            "operational_exclusion_path": wrapper.OPERATIONAL_EXCLUSION_PATH,
            "profile": "reviewed-pinned-profile",
        }
        request_with_consumed_path = dict(
            request_with_fresh_path,
            operational_exclusion_path=wrapper.CONSUMED_EXPORTSET16_OPERATIONAL_EXCLUSION_PATH,
        )
        self.assertNotEqual(wrapper._request_hash(request_with_fresh_path),
                            wrapper._request_hash(request_with_consumed_path))
        lock, record = wrapper._acquire_exclusion(request_with_fresh_path)
        try:
            self.assertEqual(record["request_sha256"],
                             wrapper._request_hash(request_with_fresh_path))
            self.assertNotEqual(record["request_sha256"],
                                wrapper._request_hash(request_with_consumed_path))
        finally:
            lock.unlink()

    def test_failed_minus_two_exclusion_is_rejected(self):
        old_request = request
        def failed_request(source):
            value = old_request(source)
            value["operational_exclusion_path"] = (
                wrapper.REVIEWED_OPERATIONAL_EXCLUSION_PATH)
            return value
        with self.assertRaisesRegex(wrapper.AdmissionError,
                                    "reviewed exact path"):
            self.invoke(failed_request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_failed_minus_three_exclusion_is_rejected(self):
        old_request = request
        def failed_request(source):
            value = old_request(source)
            value["operational_exclusion_path"] = (
                wrapper.SUPERSEDED_OPERATIONAL_EXCLUSION_PATH)
            return value
        with self.assertRaisesRegex(wrapper.AdmissionError,
                                    "reviewed exact path"):
            self.invoke(failed_request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_closurefix_four_exclusion_is_rejected(self):
        old_request = request
        def failed_request(source):
            value = old_request(source)
            value["operational_exclusion_path"] = (
                wrapper.CLOSUREFIX_OPERATIONAL_EXCLUSION_PATH)
            return value
        with self.assertRaisesRegex(wrapper.AdmissionError,
                                    "reviewed exact path"):
            self.invoke(failed_request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_existing_exclusion_fails_closed(self):
        lock = Path(wrapper.OPERATIONAL_EXCLUSION_PATH)
        lock.write_text("partial")
        with self.assertRaisesRegex(wrapper.AdmissionError, "already exists"):
            self.invoke(request)

    def test_exclusion_record_short_writes_are_completed(self):
        original_write = wrapper.os.write
        writes = []
        def short_write(fd, data):
            if len(data) > 1:
                chunk = data[:max(1, len(data) // 2)]
                writes.append(len(chunk))
                return original_write(fd, chunk)
            return original_write(fd, data)
        with mock.patch.object(wrapper.os, "write", side_effect=short_write):
            result = self.invoke(request)
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(len(writes), 1)

    def test_uncertain_owner_result_retains_exclusion(self):
        result = {"status": "PASS", "retired": True,
                  "cleanup_separately_required": True,
                  "terminal_container_info": {"Id": "retained"},
                  "terminal_container_info_current": True}
        with mock.patch.object(FakeOwner, "run", return_value=result):
            self.invoke(request)
        self.assertTrue(Path(wrapper.OPERATIONAL_EXCLUSION_PATH).exists())
        self.assertEqual(FakeOwner.provenance.ENV["GIT_OPTIONAL_LOCKS"], "0")

    def test_excess_aggregate_rejected_without_run(self):
        FakeOwner.measurement["aggregate_memory_required"] += 1
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_nonzero_memory_rejected_without_run(self):
        FakeOwner.measurement["memory_allocation_memory_backed_bytes"] = 1
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)
        self.assertEqual(FakeOwner.calls, 0)

    def test_wrong_limits_rejected_without_run(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)
            FakeOwner.LIMITS = dict(wrapper.EXPECTED_LIMITS, CpusetCpus="0-3")
            try:
                with self.assertRaises(wrapper.AdmissionError):
                    self.invoke(request)
            finally:
                FakeOwner.LIMITS = dict(wrapper.EXPECTED_LIMITS)
        self.assertEqual(FakeOwner.calls, 0)

    def test_wrong_launcher_argument_rejected_without_owner_load(self):
        with mock.patch.object(wrapper, "_load_owner") as load:
            with self.assertRaises(wrapper.AdmissionError):
                wrapper.run_request({"source_root": "/unused"}, "16.2159")
            load.assert_not_called()

    def test_tmpfs_root_rejected_without_run(self):
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(lambda source: {"source_root": str(source),
                                        "memory_allocation_roots": ["/tmpfs/source"]})
        self.assertEqual(FakeOwner.calls, 0)

    def test_second_measurement_is_guarded_before_run(self):
        original = FakeOwner.validate

        def mutate_after_first(self):
            original(self)
            if FakeOwner.validations > 1:
                self.measurement["aggregate_memory_required"] = 22548578304

        with mock.patch.object(FakeOwner, "validate", mutate_after_first):
            with self.assertRaises(wrapper.AdmissionError):
                self.invoke(request)
        self.assertEqual(FakeOwner.calls, 0)
        self.assertEqual(FakeOwner.validations, 2)

    def test_owner_and_provenance_are_loaded_from_candidate_package(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td)
            scripts = source / "scripts"
            scripts.mkdir()
            for name in ("native_rust_exact_build_container_owner.py",
                         "native_rust_exact_build_offline.py"):
                shutil.copy(ROOT / "scripts" / name, scripts / name)
            sentinel = types.ModuleType("native_rust_exact_build_offline")
            sentinel.__file__ = "/host/sentinel.py"
            with mock.patch.dict(sys.modules,
                                 {"native_rust_exact_build_offline": sentinel}):
                req = {"source_root": str(source),
                       "driver_path": str(scripts / "native_rust_exact_build_offline.py"),
                       "owner_path_sha256": hashlib.sha256((scripts / "native_rust_exact_build_container_owner.py").read_bytes()).hexdigest(),
                       "driver_path_sha256": hashlib.sha256((scripts / "native_rust_exact_build_offline.py").read_bytes()).hexdigest(),
                       "provenance_path_sha256": hashlib.sha256((scripts / "native_rust_exact_build_offline.py").read_bytes()).hexdigest()}
                loaded = wrapper._load_owner(req)
            self.assertNotEqual(loaded.provenance, sentinel)
            self.assertEqual(Path(loaded.provenance.__file__).resolve(),
                             (scripts / "native_rust_exact_build_offline.py").resolve())

    def test_owner_as_driver_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td); scripts = source / "scripts"; scripts.mkdir()
            owner = scripts / "native_rust_exact_build_container_owner.py"
            provenance = scripts / "native_rust_exact_build_offline.py"
            shutil.copy(ROOT / "scripts" / owner.name, owner)
            shutil.copy(ROOT / "scripts" / provenance.name, provenance)
            owner_hash = hashlib.sha256(owner.read_bytes()).hexdigest()
            prov_hash = hashlib.sha256(provenance.read_bytes()).hexdigest()
            with self.assertRaisesRegex(wrapper.AdmissionError, "driver_path must equal"):
                wrapper._load_owner({"source_root": str(source),
                    "driver_path": str(owner), "driver_path_sha256": owner_hash,
                    "owner_path_sha256": owner_hash, "provenance_path_sha256": prov_hash})

    def test_untrusted_candidate_is_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td); scripts = source / "scripts"; scripts.mkdir()
            owner = scripts / "native_rust_exact_build_container_owner.py"
            provenance = scripts / "native_rust_exact_build_offline.py"
            owner.write_text("raise RuntimeError('sentinel executed')\n")
            provenance.write_text("raise RuntimeError('provenance executed')\n")
            with self.assertRaisesRegex(wrapper.AdmissionError, "owner_path hash mismatch"):
                wrapper._load_owner({"source_root": str(source),
                    "owner_path_sha256": "0" * 64,
                    "provenance_path_sha256": "0" * 64})

    def test_ramfs_and_inconsistent_rows_rejected(self):
        FakeOwner.measurement["memory_allocation_roots"][0]["filesystem"] = "ramfs"
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)
        FakeOwner.measurement["memory_allocation_roots"][0]["filesystem"] = "ext4"
        FakeOwner.measurement["memory_allocation_roots"][0]["memory_effect_bytes"] = 1
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)

    def test_missing_total_rejected(self):
        del FakeOwner.measurement["memory_allocation_total_bytes"]
        with self.assertRaises(wrapper.AdmissionError):
            self.invoke(request)


if __name__ == "__main__":
    unittest.main()
