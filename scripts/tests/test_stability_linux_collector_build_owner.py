"""Executable contract tests for the root/UID1000 build owner.

No Docker, production lock, guest, or heavy build is used here.  The tests
exercise lifecycle predicates and the reviewed recovery implementation with
small deterministic fakes.
"""
import importlib.util
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).parents[2]
OWNER = ROOT / 'docs/verification/evidence/stability-linux-collector-build-owner-20260915.py'
spec = importlib.util.spec_from_file_location('collector_build_owner', OWNER)
owner = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner)
reviewed = owner.reviewed_owner()


class OwnerContractTests(unittest.TestCase):
    def test_exact_uid1000_create_profile(self):
        nonce = 'a' * 32
        argv = owner.expected_create(nonce, Path('/scratch/build-mount'))
        self.assertEqual(argv[:7], [owner.DOCKER, 'create', '--pull=never', '--init', '--name', 'mckernel-collector-' + nonce, '--label'])
        self.assertIn('mckernel.collector.owner=' + nonce, argv)
        self.assertIn('--cpus=4', argv); self.assertIn('--cpuset-cpus=2-5', argv)
        self.assertIn('--memory=12g', argv); self.assertIn('--memory-swap=12g', argv)
        self.assertIn('--pids-limit=512', argv); self.assertIn('--cap-drop=ALL', argv)
        self.assertIn('--security-opt=no-new-privileges', argv)
        self.assertIn('--read-only', argv); self.assertIn('--network=none', argv)
        self.assertIn('--user=1000:1000', argv); self.assertNotIn('--group-add=1000', argv)
        self.assertEqual(argv[argv.index('--entrypoint=/usr/bin/python3') + 1], owner.IMAGE_ID)
        self.assertEqual(argv[-1], '/workspace/docs/verification/evidence/stability-linux-collector-rebuild-20260915.py')

    def test_full_inspect_accepts_exact_lifecycle_and_rejects_drift(self):
        nonce = 'b' * 32; config = {'nonce': nonce, 'name': 'mckernel-collector-' + nonce,
                                      'container_id': 'c' * 64, 'mount': '/scratch/build-mount'}
        row = {'Id': 'c' * 64, 'Name': '/' + config['name'], 'Image': owner.IMAGE_ID,
               'Path': owner.PYTHON,
               'Args': ['-B', '/workspace/docs/verification/evidence/stability-linux-collector-rebuild-20260915.py'],
               'Config': {'Hostname': 'c' * 12, 'Labels': {'mckernel.collector.owner': nonce}, 'User': '1000:1000',
                          'Image': owner.IMAGE_ID, 'WorkingDir': '/work',
                          'Entrypoint': [owner.PYTHON],
                          'Cmd': ['-B', '/workspace/docs/verification/evidence/stability-linux-collector-rebuild-20260915.py'],
                          'Tty': False, 'OpenStdin': False, 'StdinOnce': False,
                          'AttachStdin': False, 'Domainname': '',
                          'Env': ['TMPDIR=/work/tmp', 'HOME=/tmp', 'PYTHONDONTWRITEBYTECODE=1']},
               'HostConfig': {'NetworkMode': 'none', 'Privileged': False, 'ReadonlyRootfs': True,
                              'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'], 'GroupAdd': [],
                              'Memory': 12884901888, 'MemorySwap': 12884901888,
                              'NanoCpus': 4000000000, 'CpusetCpus': '2-5', 'PidsLimit': 512,
                              'CgroupParent': '/mckernel-dev', 'Init': True,
                              'PidMode': '', 'UTSMode': '', 'UsernsMode': '', 'IpcMode': 'private',
                              'Runtime': 'runc', 'AutoRemove': False, 'PublishAllPorts': False,
                              'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0},
                              'CgroupnsMode': '',
                              'ShmSize': 67108864, 'OomKillDisable': False,
                              'MemorySwappiness': -1, 'OomScoreAdj': 0,
                              'LogConfig': {'Type': 'json-file', 'Config': {}},
                              'Ulimits': [{'Hard': 0, 'Name': 'core', 'Soft': 0},
                                          {'Hard': 4096, 'Name': 'nofile', 'Soft': 4096}],
                              'Tmpfs': {'/tmp': 'rw,nodev,nosuid,size=256m'},
                              'MaskedPaths': ['/proc/kcore', '/proc/keys', '/proc/latency_stats', '/proc/timer_list', '/proc/scsi', '/sys/firmware'],
                              'ReadonlyPaths': ['/proc/bus', '/proc/fs', '/proc/irq', '/proc/sys', '/proc/sysrq-trigger'],
                              'Mounts': [{'Type': 'bind', 'Source': str(owner.REPO), 'Target': '/workspace', 'ReadOnly': True},
                                         {'Type': 'bind', 'Source': config['mount'], 'Target': '/work', 'ReadOnly': False}]},
               'Mounts': [{'Type': 'bind', 'Source': str(owner.REPO), 'Destination': '/workspace', 'RW': False, 'Propagation': 'rprivate'},
                          {'Type': 'bind', 'Source': config['mount'], 'Destination': '/work', 'RW': True, 'Propagation': 'rprivate'}],
               'NetworkSettings': {'Networks': {'none': {'IPAddress': '', 'GlobalIPv6Address': '',
                                                           'Gateway': '', 'IPv6Gateway': '', 'MacAddress': ''}}}}
        owner.full_build_inspect(row, config)
        groupadd_none = copy.deepcopy(row); groupadd_none['HostConfig']['GroupAdd'] = None
        owner.full_build_inspect(groupadd_none, config)
        for mutate in (
                lambda value: value.__setitem__('Path', '/bin/sh'),
                lambda value: value.__setitem__('Args', ['-c', 'id']),
                lambda value: value['Config'].__setitem__('User', '0:0'),
                lambda value: value['Config']['Env'].append('LD_PRELOAD=/tmp/x'),
                lambda value: value['Config']['Env'].append('COLLECTOR_EXTRA=1'),
                lambda value: value['HostConfig'].__setitem__('PidMode', 'host'),
                lambda value: value['HostConfig'].__setitem__('GroupAdd', ['1000']),
                lambda value: value['HostConfig'].__setitem__('UnreviewedHostSetting', True),
                lambda value: value['HostConfig'].__setitem__('LogConfig', {'Type': 'syslog', 'Config': {}}),
                lambda value: value['HostConfig'].__setitem__('OomKillDisable', True),
                lambda value: value['HostConfig'].__setitem__('DeviceCgroupRules', ['c *:* rwm']),
                lambda value: value['HostConfig']['Mounts'].__setitem__(0, {'Source': '/bad', 'Target': '/workspace', 'ReadOnly': True}),
                lambda value: value['Mounts'].__setitem__(0, {**value['Mounts'][0], 'RW': True}),
        ):
            drift = json.loads(json.dumps(row)); mutate(drift)
            with self.assertRaises(ValueError): owner.full_build_inspect(drift, config)

    def test_lookup_rejects_name_label_ambiguity(self):
        class Commands:
            def run(self, label, argv, *args, **kwargs):
                return (b'a' * 64 + b'\n', {'status': 'COMPLETED'})
        config = {'nonce': 'd' * 32, 'name': 'mckernel-collector-' + 'd' * 32, 'container_id': None}
        with self.assertRaises(ValueError): owner.lookup(Commands(), config, 'ambiguous')

    def test_commands_requires_complete_streams_and_records_crash(self):
        with tempfile.TemporaryDirectory() as td:
            host = Path(td)
            real_regular = owner.regular
            class Supervisor:
                def run_supervised(self, argv, **kwargs):
                    attempt = Path(kwargs['attempt_dir']); attempt.mkdir()
                    for stream in ('stdout', 'stderr'):
                        (attempt / (stream + '.bin')).write_bytes(b'')
                    return {'status': 'COMPLETED', 'cleanup_complete': True, 'raw_wait_status': 0,
                            'application_acceptance': False,
                            'payload_monotonic_started': 1.0,
                            'payload_monotonic_deadline': 2.0,
                            'payload_completion_observed_monotonic': 1.5,
                            'streams': {s: {'eof': True, 'truncated': False, 'bytes_observed': 0,
                                           'bytes_retained': 0, 'discarded_observed_bytes': 0,
                                           'discarded_observed_bytes': 0,
                                           'artifact': {'sha256': owner.digest(attempt / (s + '.bin')), 'size': 0}}
                                       for s in ('stdout', 'stderr')}}
            def regular_probe(path, maximum=owner.MAX_FILE):
                if str(path) == owner.DOCKER:
                    return b'', {'path': str(path), 'sha256': 'x'}
                return real_regular(path, maximum)
            with mock.patch.object(owner, 'regular', side_effect=regular_probe):
                # The Docker identity probe is mocked; stream checks remain real.
                commands = owner.Commands(host, Supervisor())
                commands.docker_identity = real_regular(Path(owner.DOCKER).resolve(strict=True), 64 * 1024 * 1024)[1]
            commands.run('good', [owner.DOCKER, 'inspect', 'x'])

            class Truncated(Supervisor):
                def run_supervised(self, argv, **kwargs):
                    report = super().run_supervised(argv, **kwargs)
                    report['streams']['stderr']['truncated'] = True
                    return report
            with self.assertRaises(ValueError):
                owner.Commands(host, Truncated()).run('incomplete', [owner.DOCKER, 'inspect', 'x'])

    def test_reviewed_recovery_absence_and_failed_cleanup_are_distinct(self):
        class EmptyCommands:
            def __init__(self, host): self.number = 0; self.host = Path(host); self.deadline = None
            def run(self, label, argv, *args, **kwargs):
                self.number += 1
                return b'', {'status': 'COMPLETED', 'cleanup_complete': True, 'raw_wait_status': 0,
                             'payload_monotonic_started': 1.0,
                             'payload_monotonic_deadline': 2.0,
                             'payload_completion_observed_monotonic': 1.5,
                             'streams': {'stdout': {'eof': True, 'truncated': False, 'bytes_observed': 0,
                                                    'bytes_retained': 0, 'discarded_observed_bytes': 0,
                                                    'discarded_observed_bytes': 0,
                                                    'artifact': {'sha256': 'unused', 'size': 0}},
                                        'stderr': {'eof': True, 'truncated': False, 'bytes_observed': 0,
                                                   'bytes_retained': 0, 'discarded_observed_bytes': 0,
                                                   'discarded_observed_bytes': 0,
                                                   'artifact': {'sha256': 'unused', 'size': 0}}}}
        with tempfile.TemporaryDirectory() as td:
            journal = []
            config = {'nonce': 'e' * 32, 'name': 'mckernel-collector-' + 'e' * 32, 'container_id': None}
            result = reviewed.recover_cleanup(EmptyCommands(td), config, 'test', max_passes=1,
                                              sleeper=lambda _: None, journal=journal.append)
            self.assertTrue(result['absence_verified']); self.assertTrue(result['evidence_complete']); self.assertTrue(journal)

            class CrashingCommands:
                number = 0
                host = Path(td)
                deadline = None
                def run(self, label, argv, *args, **kwargs): raise RuntimeError('simulated Docker crash')
            failed = reviewed.recover_cleanup(CrashingCommands(), config, 'crash', max_passes=2,
                                               sleeper=lambda _: None)
            self.assertFalse(failed['absence_verified']); self.assertTrue(failed['evidence_complete'])
            self.assertIsNotNone(failed['first_failure'])

    def _synthetic_build_record(self, mount):
        """Create a complete, host-only record for the verifier's positive path."""
        mount = Path(mount)
        output = mount / 'stability-linux-collector-build-20260915-2'
        output.mkdir(parents=True)

        def artifact(path, data):
            path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return {'path': str(path), 'size': len(data),
                    'sha256': hashlib.sha256(data).hexdigest()}

        def existing(path):
            data = Path(path).read_bytes()
            return {'path': str(path), 'size': len(data),
                    'sha256': hashlib.sha256(data).hexdigest()}

        helper_path = '/workspace/docs/verification/evidence/stability-linux-collector-rebuild-20260915.py'
        record = {
            'schema_version': 1,
            'started_utc': '2026-09-15T00:00:00+00:00',
            'finished_utc': '2026-09-15T00:01:00+00:00',
            'status': 'PASS_LINUX_COLLECTOR_REBUILD_SHA9_BUILDER_NEGATIVE_ONLY',
            'application_acceptance': False, 'backend_enabled': False,
            'guest_execution': False, 'root_positive_execution': False,
            'scope': 'Pinned Linux collector rebuild after retained close_range/EPERM root failure; SHA9 and builder rejection only',
            'phase': 'builder-negative',
            'helper': {'path': helper_path, 'size': (ROOT / helper_path[11:]).stat().st_size,
                       'sha256': owner.HELPER_SHA},
            'inputs': [], 'compiler_dependencies': [], 'compiled_outputs': [],
            'commands': [], 'loader_dependencies': [
                {'path': '/lib64/libc.so.6', 'size': 2339896,
                 'sha256': 'b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4'},
                {'path': '/lib64/ld-linux-x86-64.so.2', 'size': 930600,
                 'sha256': '0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b'},
            ],
            'clean_launch_requirement': 'root execution must bind close_fds, empty pass_fds and nofile=4096:4096',
        }

        for relative in owner.PINNED_INPUTS:
            source = ROOT / relative
            if relative.startswith('scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/'):
                retained = output / 'source/linux-sealed-v1' / Path(relative).name
            elif relative in ('scripts/tests/fixtures/application-collector-v1/request.c',
                              'scripts/tests/fixtures/application-collector-v1/request.h'):
                retained = output / 'source' / Path(relative).name
            else:
                retained = output / 'supervisor.py'
            original = dict(existing(source), path='/workspace/' + relative)
            retained_id = artifact(retained, source.read_bytes())
            retained_id['path'] = '/work/stability-linux-collector-build-20260915-2/' + str(retained.relative_to(output))
            record['inputs'].append({'original': original, 'retained': retained_id})
        artifact(output / 'helper.py', (ROOT / 'docs/verification/evidence/stability-linux-collector-rebuild-20260915.py').read_bytes())

        # Keep both container namespaces represented.  The retained path is
        # deliberately compiler-inputs/<absolute-container-path>.
        deps_by_depfile = {}
        for index in range(176):
            if index < 16:
                original_path = '/work/stability-linux-collector-build-20260915-2/project-%03d.h' % index
            else:
                original_path = '/usr/include/collector/project-%03d.h' % index
            data = ('compiler dependency %03d\n' % index).encode('ascii')
            retained = output / 'compiler-inputs' / original_path.lstrip('/')
            retained_id = artifact(retained, data)
            retained_id['path'] = '/work/stability-linux-collector-build-20260915-2/compiler-inputs/' + original_path.lstrip('/')
            depfile = '/work/stability-linux-collector-build-20260915-2/%s.d' % (
                ('request', 'sha256', 'collector', 'fixture', 'sha256_harness')[index % 5])
            row = {'original': {'path': original_path, 'size': len(data),
                                'sha256': hashlib.sha256(data).hexdigest()},
                   'retained': retained_id}
            record['compiler_dependencies'].append(row)
            deps_by_depfile.setdefault(depfile, []).append(original_path)

        root = '/work/stability-linux-collector-build-20260915-2'
        def p(name): return root + '/' + name
        outputs = []
        for name in ('request', 'sha256', 'collector', 'fixture', 'sha256_harness'):
            for suffix in ('.o', '.d'):
                data = ('output %s%s\n' % (name, suffix)).encode('ascii')
                if suffix == '.d':
                    members = []
                    for depfile, paths in deps_by_depfile.items():
                        if depfile == p(name + '.d'):
                            members = paths
                    data = (name + '.o: ' + ' '.join(members) + '\n').encode('ascii')
                output_id = artifact(output / (name + suffix), data)
                output_id['path'] = p(name + suffix)
                outputs.append(output_id)
        for name in ('linux-collector', 'fixture', 'sha256-harness'):
            for suffix in ('', '.map'):
                output_id = artifact(output / (name + suffix),
                                     ('output %s%s\n' % (name, suffix)).encode('ascii'))
                output_id['path'] = p(name + suffix)
                outputs.append(output_id)
        record['compiled_outputs'] = outputs

        builder_inputs = []
        for relative in ('linux-collector', 'fixture', 'supervisor.py',
                         'source/linux-sealed-v1/run_collector_tests.py'):
            identity = existing(output / relative)
            builder_inputs.append({'path': p(relative), 'size_bytes': identity['size'],
                                   'sha256': identity['sha256']})

        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
               'TZ': 'UTC', 'TMPDIR': '/work/stability-linux-collector-build-20260915-2/tmp'}
        labels = ['compiler-version'] + ['compile-' + name for name in
                  ('request', 'sha256', 'collector', 'fixture', 'sha256_harness')]
        labels += [phase + '-' + name for name in ('linux-collector', 'fixture', 'sha256-harness')
                   for phase in ('link', 'elf', 'disassembly', 'loader')]
        labels += ['sha9', 'builder-negative']
        argv = [[owner.PYTHON.replace('python3', 'gcc'), '--version']]
        for name, source in (('request', 'source/request.c'), ('sha256', 'source/linux-sealed-v1/sha256.c'),
                             ('collector', 'source/linux-sealed-v1/collector.c'), ('fixture', 'source/linux-sealed-v1/fixture.c'),
                             ('sha256_harness', 'source/linux-sealed-v1/sha256_harness.c')):
            argv.append(['/usr/bin/gcc', '-std=c11', '-D_GNU_SOURCE', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
                         '-fno-pie', '-MD', '-MF', p(name + '.d'), '-c', p(source), '-o', p(name + '.o')])
        for name, objects in (('linux-collector', ('request.o', 'sha256.o', 'collector.o')),
                              ('fixture', ('fixture.o',)), ('sha256-harness', ('sha256.o', 'sha256_harness.o'))):
            argv.append(['/usr/bin/gcc', '-no-pie'] + [p(obj) for obj in objects] +
                        ['-Wl,-Map=' + p(name + '.map'), '-o', p(name)])
            argv.append(['/usr/bin/readelf', '-h', '-l', '-d', p(name)])
            argv.append(['/usr/bin/objdump', '-d', p(name)])
            argv.append(['/usr/bin/ldd', p(name)])
        argv.extend([[p('sha256-harness')], ['/usr/bin/python3', '-B', p('source/linux-sealed-v1/run_collector_tests.py'),
                     '--collector', p('linux-collector'), '--fixture', p('fixture'), '--supervisor', p('supervisor.py'),
                     '--attempt-root', p('builder-negative'), '--builder-only']])
        sha9 = b'PASS empty\nPASS abc\nPASS multi-56\nPASS boundary-55\nPASS boundary-56\nPASS boundary-63\nPASS boundary-64\nPASS boundary-65\nPASS rejected-update-preserves-state\n'
        builder = b'PASS builder-identity\nRETAINED ' + (root + '/builder-negative').encode('ascii') + b'\n'
        inner = json.dumps({'schema_version': 1, 'kind': 'actual-linux-sealed-collector-infrastructure-tests',
                            'status': 'PASS_INFRASTRUCTURE_ONLY', 'application_acceptance': False,
                            'backend_enabled': False, 'uid': 1000, 'euid': 1000,
                            'cases': [{'case': 'builder-identity', 'observed_status': 'BLOCKED',
                                       'status': 'PASS_INFRASTRUCTURE_ONLY'}],
                            'inputs': builder_inputs}, sort_keys=True).encode() + b'\n'
        for label, command in zip(labels, argv):
            content = sha9 if label == 'sha9' else builder if label == 'builder-negative' else b''
            stream_rows = {}
            collection_dir = output / (label + '-collection')
            for stream in ('stdout', 'stderr'):
                stream_content = content if stream == 'stdout' else b''
                stream_rows[stream] = {'eof': True, 'truncated': False,
                    'bytes_observed': len(stream_content), 'bytes_retained': len(stream_content),
                    'discarded_observed_bytes': 0, 'limit_bytes': 0,
                    'artifact': artifact(collection_dir / (stream + '.bin'), stream_content)}
                stream_rows[stream]['artifact']['path'] = p(label + '-collection/' + stream + '.bin')
            limit = 65536 if label == 'sha9' else 8 * 1024 * 1024
            timeout = 10.0 if label == 'sha9' else 60.0 if label == 'builder-negative' else 120.0
            for stream in stream_rows.values():
                stream['limit_bytes'] = limit
            report = {'schema_version': 1, 'status': 'COMPLETED', 'cleanup_complete': True,
                      'raw_wait_status': 0, 'application_acceptance': False,
                      'payload_monotonic_started': 1.0, 'payload_monotonic_deadline': 2.0,
                      'payload_completion_observed_monotonic': 1.5,
                      'argv': command, 'cwd': root, 'env': dict(env),
                      'uid': 1000, 'gid': 1000, 'groups': [1000], 'stdin': {'kind': 'devnull'},
                      'stdin_path': None, 'wait_status': {'kind': 'exited', 'code': 0},
                      'descendants': [], 'descendant_records_omitted': 0,
                      'stdout_limit_bytes': limit, 'stderr_limit_bytes': limit,
                      'timeout_seconds': timeout, 'cleanup_timeout_seconds': 15.0,
                      'streams': stream_rows}
            row = {'label': label, 'argv': command, 'environment': env, 'collection': report}
            if label == 'builder-negative':
                artifact(output / 'builder-negative/result.json', inner)
            record['commands'].append(row)
        record['sha_cases'] = 9; record['builder_cases'] = 1
        return record

    def test_verify_build_record_accepts_complete_positive_record_and_rejects_mutations(self):
        with tempfile.TemporaryDirectory() as td:
            mount = Path(td) / 'mount'; host = Path(td) / 'host'
            mount.mkdir(); host.mkdir(); record = self._synthetic_build_record(mount)
            output = mount / 'stability-linux-collector-build-20260915-2'
            (output / 'record.json').write_text(json.dumps(record) + '\n')
            verified, identity = owner.verify_build_record(mount, host)
            self.assertEqual(verified['status'], record['status'])
            self.assertEqual(identity['sha256'], owner.digest(output / 'record.json'))
            self.assertEqual(json.loads((host / 'build-record.json').read_text()), record)
            inner_original = (output / 'builder-negative/result.json').read_bytes()
            mutations = []
            duplicate = copy.deepcopy(record); duplicate['compiler_dependencies'][0]['original']['path'] = duplicate['compiler_dependencies'][1]['original']['path']; mutations.append(('duplicate dependency', duplicate))
            missing = copy.deepcopy(record); missing['compiler_dependencies'].pop(); mutations.append(('missing dependency', missing))
            trunc = copy.deepcopy(record); trunc['commands'][0]['collection']['streams']['stdout']['truncated'] = True; mutations.append(('stream truncation', trunc))
            discard = copy.deepcopy(record); discard['commands'][0]['collection']['streams']['stderr']['discarded_observed_bytes'] = 1; mutations.append(('stream discard', discard))
            argv_change = copy.deepcopy(record); argv_change['commands'][0]['argv'][0] = '/bad/gcc'; mutations.append(('argv substitution', argv_change))
            cwd_change = copy.deepcopy(record); cwd_change['commands'][0]['cwd'] = '/tmp'; mutations.append(('cwd substitution', cwd_change))
            env_change = copy.deepcopy(record); env_change['commands'][0]['environment']['PATH'] = '/bad'; mutations.append(('env substitution', env_change))
            path_change = copy.deepcopy(record); path_change['commands'][0]['collection']['streams']['stdout']['artifact']['path'] = '/tmp/foreign.bin'; mutations.append(('path substitution', path_change))
            depfile_change = copy.deepcopy(record); depfile_change['compiler_dependencies'][0]['original']['path'] = '/usr/include/not-in-depfile.h'; mutations.append(('depfile membership', depfile_change))
            loader_change = copy.deepcopy(record); loader_change['loader_dependencies'][0]['sha256'] = 'f' * 64; mutations.append(('loader identity', loader_change))
            inner_change = copy.deepcopy(record); mutations.append(('builder inner result', inner_change))
            for label, altered in mutations:
                with self.subTest(label=label):
                    (output / 'record.json').write_text(json.dumps(altered) + '\n')
                    if label == 'builder inner result':
                        (output / 'builder-negative/result.json').write_text('{}\n')
                    with self.assertRaises(ValueError): owner.verify_build_record(mount, host)
                    if label == 'builder inner result':
                        (output / 'builder-negative/result.json').write_bytes(inner_original)

            bounded_mutations = (
                ('completion after deadline',
                 lambda value: value['commands'][0]['collection'].__setitem__('payload_completion_observed_monotonic', 2.0),
                 'exclusive deadline'),
                ('boolean raw wait status',
                 lambda value: value['commands'][0]['collection'].__setitem__('raw_wait_status', False),
                 'build command result'),
                ('boolean discarded counter',
                 lambda value: value['commands'][0]['collection']['streams']['stdout'].__setitem__('discarded_observed_bytes', False),
                 'plain stream counter'),
            )
            for label, mutate, message in bounded_mutations:
                with self.subTest(label=label):
                    altered = copy.deepcopy(record); mutate(altered)
                    (output / 'record.json').write_text(json.dumps(altered) + '\n')
                    with self.assertRaisesRegex(ValueError, message):
                        owner.verify_build_record(mount, host)

    def test_build_record_rejects_any_acceptance_or_count_drift(self):
        with tempfile.TemporaryDirectory() as td:
            mount = Path(td); output = mount / 'stability-linux-collector-build-20260915-2'; output.mkdir()
            record = {'status': 'PASS_LINUX_COLLECTOR_REBUILD_SHA9_BUILDER_NEGATIVE_ONLY',
                      'application_acceptance': True, 'backend_enabled': False,
                      'guest_execution': False, 'root_positive_execution': False}
            (output / 'record.json').write_text(json.dumps(record) + '\n')
            with self.assertRaises(ValueError): owner.verify_build_record(mount, mount)

    def test_source_contains_root_recovery_gates(self):
        source = OWNER.read_text()
        for text in ('reviewed_owner()', 'os.chown(mount, 1000, 1000)', 'fcntl.LOCK_EX | fcntl.LOCK_NB',
                     "'--user=1000:1000'", "'DISARM ' + nonce + ' ' + config['container_id']",
                     'recover_cleanup', 'os.waitpid(watch.pid, os.WNOHANG)', 'original-tree-inventory.json',
                     'application_acceptance'):
            self.assertIn(text, source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
