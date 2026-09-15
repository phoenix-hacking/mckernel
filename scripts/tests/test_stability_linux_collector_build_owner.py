"""Executable contract tests for the root/UID1000 build owner.

No Docker, production lock, guest, or heavy build is used here.  The tests
exercise lifecycle predicates and the reviewed recovery implementation with
small deterministic fakes.
"""
import importlib.util
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
               'Config': {'Hostname': 'c' * 12, 'Labels': {'mckernel.collector.owner': nonce}, 'User': '1000:1000',
                          'Image': owner.IMAGE_ID, 'WorkingDir': '/work',
                          'Entrypoint': [owner.PYTHON],
                          'Cmd': ['-B', '/workspace/docs/verification/evidence/stability-linux-collector-rebuild-20260915.py'],
                          'Tty': False, 'OpenStdin': False,
                          'Env': ['TMPDIR=/work/tmp', 'HOME=/tmp', 'PYTHONDONTWRITEBYTECODE=1']},
               'HostConfig': {'NetworkMode': 'none', 'Privileged': False, 'ReadonlyRootfs': True,
                              'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'],
                              'Memory': 12884901888, 'MemorySwap': 12884901888,
                              'NanoCpus': 4000000000, 'CpusetCpus': '2-5', 'PidsLimit': 512,
                              'CgroupParent': '/mckernel-dev', 'Init': True,
                              'Ulimits': [{'Hard': 0, 'Name': 'core', 'Soft': 0},
                                          {'Hard': 4096, 'Name': 'nofile', 'Soft': 4096}],
                              'PidMode': '', 'IpcMode': 'private', 'UTSMode': '', 'UsernsMode': '', 'Runtime': 'runc',
                              'AutoRemove': False, 'PublishAllPorts': False,
                              'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0},
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
        for mutate in (
                lambda value: value['Config'].__setitem__('User', '0:0'),
                lambda value: value['Config']['Env'].append('LD_PRELOAD=/tmp/x'),
                lambda value: value['HostConfig'].__setitem__('PidMode', 'host'),
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
