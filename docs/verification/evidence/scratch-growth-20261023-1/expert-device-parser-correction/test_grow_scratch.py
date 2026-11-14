"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Pure mocks: no root, loop, filesystem, Docker, guest or ownership mutation.
"""
import importlib.util
import copy
import json
import os
import stat
from contextlib import ExitStack
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('growth', Path(__file__).with_name('grow_scratch.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class GrowthTests(unittest.TestCase):
    def run_case(self, fail_observation=None, fail_command=None, output='', last_device='/dev/loop36',
                 capacity_fail=None, changed_features=False):
        commands, observations, capacities = [], [], []
        def run(argv, timeout=20):
            commands.append(argv)
            if len(commands) == fail_command:
                raise g.Stop('mock command failure')
            return output if len(commands) == 3 else '', ''
        def observe(sizes):
            observations.append(sizes)
            if len(observations) == fail_observation:
                raise g.Stop('mock snapshot failure')
            return dict(device=last_device if len(observations) == 4 else '/dev/loop36', devnum=1828,
                        allocated=102264397824,
                        header=dict(g.required_header(sizes[2]), **{'Filesystem features':
                                    'changed' if changed_features and len(observations) == 4 else ' '.join(g.FEATURES)}))
        def capacity(allocated):
            capacities.append(allocated)
            if len(capacities) == capacity_fail:
                raise g.Stop('mock capacity failure')
        try:
            g.execute_steps(run, observe, capacity)
            error = None
        except g.Stop as exc:
            error = exc
        return commands, observations, capacities, error

    def test_success_exact_order_and_geometry(self):
        commands, observations, capacities, error = self.run_case()
        self.assertIsNone(error)
        self.assertEqual(commands, [
            ['/usr/bin/truncate', '--size=152471339008', '--', str(g.BACKING)],
            ['/usr/sbin/losetup', '--set-capacity', '/dev/loop36'],
            ['/usr/sbin/resize2fs', '/dev/loop36', '37224448']])
        self.assertEqual(observations, [(g.OLD, g.OLD, 28835840), (g.TARGET, g.OLD, 28835840),
                                        (g.TARGET, g.TARGET, 28835840), (g.TARGET, g.TARGET, 37224448)])
        self.assertEqual(len(capacities), 4)

    def test_each_snapshot_failure_stops_successors(self):
        for observation in range(1, 5):
            with self.subTest(observation=observation):
                commands, _, _, error = self.run_case(fail_observation=observation)
                self.assertIsNotNone(error)
                self.assertEqual(len(commands), observation - 1)

    def test_each_command_failure_stops_successors(self):
        for command in range(1, 4):
            with self.subTest(command=command):
                commands, observations, _, error = self.run_case(fail_command=command)
                self.assertIsNotNone(error)
                self.assertEqual(len(commands), command)
                self.assertEqual(len(observations), command)

    def test_initial_capacity_failure_prevents_truncate(self):
        commands, _, _, error = self.run_case(capacity_fail=1)
        self.assertEqual(commands, [])
        self.assertIsNotNone(error)

    def test_final_capacity_failure_is_not_success(self):
        self.assertIsNotNone(self.run_case(capacity_fail=4)[3])

    def test_intermediate_capacity_failure_stops_next_mutation(self):
        for stage in (2, 3):
            commands, _, _, error = self.run_case(capacity_fail=stage)
            self.assertEqual(len(commands), stage - 1)
            self.assertIsNotNone(error)

    def test_fallback_indication_fails(self):
        for output in ('falling back to old-style resize', 'fallback', 'ERROR', 'resize failed',
                       'Old resize interface requested.', 'Performing an on-line resize of /dev/loop83'):
            with self.subTest(output=output):
                commands, observations, _, error = self.run_case(output=output)
                self.assertEqual(len(commands), 3)
                self.assertEqual(len(observations), 3)
                self.assertIsNotNone(error)

    def test_final_loop_change_fails(self):
        self.assertIsNotNone(self.run_case(last_device='/dev/loop37')[3])

    def test_feature_change_fails(self):
        self.assertIsNotNone(self.run_case(changed_features=True)[3])

    def test_header_duplicate_refused(self):
        with self.assertRaises(g.Stop):
            g.parse_header('Block count: 1\nBlock count: 2\n')

    def test_bound_json_duplicates_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'input.json'
            raw = b'{"status":1,"status":2}'
            path.write_bytes(raw)
            with self.assertRaises(g.Stop):
                g.load_bound(path, g.digest(raw))

    def test_host_budget_counts_entire_sparse_gap(self):
        from types import SimpleNamespace
        allocated = 102264397824
        needed = 16 * 2**30 + (g.TARGET - allocated) + 2**30
        def values(path):
            return SimpleNamespace(f_bavail=needed - 1 if path == g.BACKING.parent else 12 * 2**30, f_frsize=1)
        with patch.object(g.os, 'statvfs', side_effect=values):
            with self.assertRaises(g.Stop):
                g.capacity(allocated, 2**30, 0)
        with patch.object(g.os, 'statvfs', return_value=SimpleNamespace(f_bavail=needed, f_frsize=1)):
            g.capacity(allocated, 2**30, 0)

    def test_missing_budget_refused(self):
        with self.assertRaises(g.Stop):
            g.capacity(102264397824, 0, 0)

    def test_capture_timeout_retains_child_and_lock(self):
        class TimedOutChild:
            pid = 123456
            def wait(self, timeout):
                raise g.subprocess.TimeoutExpired('mock', timeout)
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(g.subprocess, 'Popen', return_value=TimedOutChild()) as launch:
                with patch.object(g, 'starttime', return_value='1234'):
                    with self.assertRaises(g.Stop):
                        g.Runner(Path(temporary), 41)(['/mock/command'])
            self.assertEqual(launch.call_args.kwargs['pass_fds'], (41,))
            self.assertTrue((Path(temporary) / '001.uncertain.json').exists())
            self.assertFalse((Path(temporary) / '001.terminal.json').exists())

    def test_capture_nonzero_is_failure(self):
        class FailedChild:
            pid = 123456
            def wait(self, timeout):
                return 1
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(g.subprocess, 'Popen', return_value=FailedChild()):
                with patch.object(g, 'starttime', return_value='1234'):
                    with self.assertRaises(g.Stop):
                        g.Runner(Path(temporary), 41)(['/mock/command'])
            self.assertTrue((Path(temporary) / '001.terminal.json').exists())

    def test_actual_inherited_flock_lifetime_after_timeout(self):
        """Real unprivileged temp-file flock/child only; no real storage commands."""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            (path / 'test.lock').write_bytes(b'')
            fd = os.open(path / 'test.lock', os.O_RDONLY)
            competitor = os.open(path / 'test.lock', os.O_RDONLY)
            pid = None
            try:
                g.fcntl.flock(fd, g.fcntl.LOCK_EX | g.fcntl.LOCK_NB)
                with self.assertRaises(g.Stop):
                    g.Runner(path, fd)(['/usr/bin/python3', '-c', 'import time; time.sleep(0.3)'], timeout=0.03)
                pid = json.loads((path / '001.started.json').read_text())['pid']
                os.close(fd)
                fd = None
                with self.assertRaises(BlockingIOError):
                    g.fcntl.flock(competitor, g.fcntl.LOCK_EX | g.fcntl.LOCK_NB)
                self.assertEqual(os.waitpid(pid, 0)[0], pid)
                pid = None
                g.fcntl.flock(competitor, g.fcntl.LOCK_EX | g.fcntl.LOCK_NB)
            finally:
                if pid is not None:
                    os.waitpid(pid, 0)
                if fd is not None:
                    os.close(fd)
                os.close(competitor)


class StorageFixture:
    """Synthetic kernel/command metadata; actual snapshot/main guards execute.

    Only tiny ordinary temp files, the existing helper's O_EXCL shared record,
    and a temp-file flock are real. No root or storage command runs.
    """
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.backing = self.root / 'scratch.ext4'
        self.mount = self.root / 'scratch'
        self.lock = self.root / 'development.lock'
        self.out = self.root / 'host-preparation' / 'capture'
        self.backing.write_bytes(b'fixture only')
        self.mount.mkdir()
        self.lock.write_bytes(b'')
        self.out.mkdir(parents=True)
        self.device = '/dev/loop83'
        self.devnum = os.makedev(7, 83)
        self.file_size, self.device_size, self.blocks = g.OLD, g.OLD, g.OLD_BLOCKS
        self.back_ino, self.back_dev = 47468427, '259:2'
        self.mount_dev = self.devnum
        self.mutex_ino, self.mutex_dev = 4, 27
        self.header_override = {}
        self.header_missing = set()
        self.features = ' '.join(g.FEATURES)
        self.commands, self.mutations = [], []
        self.lockfd = None
        self.original_stat, self.original_fstat, self.original_open = os.stat, os.fstat, os.open
        self.installed = {p: g.digest(Path(p).read_bytes()) for p in ('/usr/sbin/resize2fs', '/usr/sbin/dumpe2fs')}

    def __enter__(self):
        self.stack = ExitStack()
        for name, value in [('BACKING', self.backing), ('MOUNT', self.mount), ('LOCK', self.lock),
                            ('SHARED', self.mount / 'mckernel-heavy-operation.lock')]:
            self.stack.enter_context(patch.object(g, name, value))
        self.stack.enter_context(patch.object(g.os, 'stat', side_effect=self.stat))
        self.stack.enter_context(patch.object(g.os, 'fstat', side_effect=self.fstat))
        self.stack.enter_context(patch.object(g.os, 'open', side_effect=self.open))
        self.stack.enter_context(patch.object(g, 'scalar', side_effect=self.scalar))
        self.stack.enter_context(patch.object(g.os, 'geteuid', return_value=0))
        self.stack.enter_context(patch.object(g.os, 'sched_getaffinity', return_value={7}))
        self.stack.enter_context(patch.object(g.os, 'statvfs', return_value=SimpleNamespace(f_bavail=200 * 2**30, f_frsize=1)))
        self.stack.enter_context(patch.object(g, 'Runner', side_effect=lambda out, fd: self.run))
        return self

    def __exit__(self, *args):
        self.stack.close()
        if self.lockfd is not None:
            os.close(self.lockfd)
        self.temporary.cleanup()

    def stat(self, path, *args, **kwargs):
        if str(path) == str(self.backing):
            return SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_dev=66306, st_ino=47468427,
                                   st_uid=0, st_gid=0, st_size=self.file_size, st_blocks=199735152)
        if str(path) == self.device:
            return SimpleNamespace(st_mode=stat.S_IFBLK | 0o600, st_rdev=self.devnum)
        if str(path) == str(self.mount):
            return SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_dev=self.mount_dev)
        if str(path) == str(self.lock):
            return SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_dev=self.mutex_dev, st_ino=self.mutex_ino)
        return self.original_stat(path, *args, **kwargs)

    def fstat(self, fd):
        if fd == self.lockfd:
            return self.stat(self.lock)
        return self.original_fstat(fd)

    def open(self, path, *args, **kwargs):
        fd = self.original_open(path, *args, **kwargs)
        if str(path) == str(self.lock):
            self.lockfd = fd
        return fd

    def scalar(self, path):
        path = str(path)
        fixed = {'/proc/version_signature': 'fixture-vendor-kernel',
                 '/proc/sys/kernel/random/boot_id': 'fixture-boot'}
        if path in fixed:
            return fixed[path]
        for suffix, value in [('loop/backing_file', str(self.backing)), ('loop/offset', '0'),
                              ('loop/sizelimit', '0'), ('queue/logical_block_size', '512'),
                              ('queue/physical_block_size', '512'), ('size', str(self.device_size // 512)),
                              ('errors_count', '0'), ('warning_count', '0')]:
            if path.endswith('/' + suffix):
                return value
        raise AssertionError('unexpected scalar read: ' + path)

    def run(self, argv, timeout=20):
        self.commands.append(argv)
        if argv[0] == '/usr/bin/findmnt':
            return json.dumps({'filesystems': [dict(source=self.device, target=str(self.mount), fstype='ext4',
                                                    uuid=g.UUID, options='rw,nosuid,nodev,relatime')]}), ''
        if argv[0] == '/usr/sbin/losetup' and '--list' in argv:
            return json.dumps({'loopdevices': [dict(name=self.device, offset=0, sizelimit=0, autoclear=True, ro=False,
                                                    **{'maj:min': '7:83', 'back-file': str(self.backing),
                                                       'back-ino': self.back_ino, 'back-maj:min': self.back_dev})]}), ''
        if argv[0] == '/usr/sbin/dumpe2fs':
            header = dict(g.required_header(self.blocks), **{'Filesystem features': self.features})
            header.update(self.header_override)
            for key in self.header_missing:
                header.pop(key, None)
            return '\n'.join(k + ': ' + v for k, v in header.items()), ''
        self.mutations.append(argv)
        if argv[0] == '/usr/bin/truncate':
            self.file_size = g.TARGET
        elif argv[0] == '/usr/sbin/losetup' and '--set-capacity' in argv:
            self.device_size = g.TARGET
        elif argv[0] == '/usr/sbin/resize2fs':
            self.blocks = g.NEW_BLOCKS
        else:
            raise AssertionError('unexpected command: ' + repr(argv))
        return '', ''

    def write_bound(self, name, value):
        path = self.root / name
        raw = g.canonical(value)
        path.write_bytes(raw)
        return dict(path=str(path), sha256=g.digest(raw))

    def release(self, mutate=None, qualification_mutate=None, retirement_mutate=None):
        qualification = dict(status='PASS_NATIVE_EXT4_GROWTH_110_TO_142', uuid=g.UUID,
                             expected_reserved_blocks=g.RESERVE, kernel_vendor_binding_verified=True,
                             resize2fs_vendor_binding_verified=True, geometry=copy.deepcopy(g.GEOMETRY),
                             kernel_release=os.uname().release, kernel_version_signature='fixture-vendor-kernel',
                             resize2fs_sha256=self.installed['/usr/sbin/resize2fs'],
                             dumpe2fs_sha256=self.installed['/usr/sbin/dumpe2fs'])
        if qualification_mutate:
            qualification_mutate(qualification)
        retirement = dict(status='PASS_POSITIVE_RETIREMENT', boot_id='fixture-boot', observed_epoch=time.time(),
                          scratch_writers=[], qemu_tasks=[], docker_tasks=[], live_leases=[],
                          active_110gib_consumers_reconciled=True, protected_scratch21_unchanged=True)
        if retirement_mutate:
            retirement_mutate(retirement)
        release = dict(status='PASS_EXECUTION_RELEASE', scope=g.SCOPE, execution_count=1, author='fixture-author',
                       source_sha256=g.digest(Path(g.__file__).read_bytes()), capture_directory=str(self.out),
                       historical_128m_attempt_disposition='NOT_EXECUTED_RESOLVED',
                       stock_resize2fs_fallback_risk_explicitly_accepted=True,
                       filesystem_qualification=self.write_bound('qualification.json', qualification),
                       retirement=self.write_bound('retirement.json', retirement), host_extra_bytes=2**30,
                       scratch_extra_bytes=0)
        if mutate:
            mutate(release)
        review = dict(decision='PASS_EXECUTION', implementation_ownership=False, reviewer='fixture-reviewer',
                      reviewed_release_payload_sha256=g.digest(g.canonical(release)))
        release['independent_review'] = self.write_bound('review.json', review)
        pointer = self.write_bound('release.json', release)
        return ['--release', pointer['path'], '--release-sha256', pointer['sha256']]


class ActualGuardFixtureTests(unittest.TestCase):
    def test_actual_snapshot_all_four_stages(self):
        with StorageFixture() as f:
            for sizes in [(g.OLD, g.OLD, g.OLD_BLOCKS), (g.TARGET, g.OLD, g.OLD_BLOCKS),
                          (g.TARGET, g.TARGET, g.OLD_BLOCKS), (g.TARGET, g.TARGET, g.NEW_BLOCKS)]:
                f.file_size, f.device_size, f.blocks = sizes
                self.assertEqual(g.snapshot(f.run, sizes)['device'], '/dev/loop83')
            self.assertFalse(f.mutations)

    def test_actual_snapshot_backing_inode_device_and_mount_binding(self):
        for field, invalid in [('back_ino', 47468428), ('back_dev', '259:3'), ('mount_dev', os.makedev(7, 84))]:
            with self.subTest(field=field), StorageFixture() as f:
                setattr(f, field, invalid)
                with self.assertRaises(g.Stop):
                    g.snapshot(f.run, (g.OLD, g.OLD, g.OLD_BLOCKS))
                self.assertFalse(f.mutations)

    def test_actual_snapshot_missing_required_fields_fail(self):
        for key in [*g.required_header(g.OLD_BLOCKS), 'Filesystem features']:
            with self.subTest(key=key), StorageFixture() as f:
                f.header_missing.add(key)
                with self.assertRaises(g.Stop):
                    g.snapshot(f.run, (g.OLD, g.OLD, g.OLD_BLOCKS))

    def test_actual_snapshot_unsupported_features_fail(self):
        for features in [' '.join(x for x in g.FEATURES if x != 'resize_inode'),
                         ' '.join(g.FEATURES) + ' meta_bg']:
            with self.subTest(features=features), StorageFixture() as f:
                f.features = features
                with self.assertRaises(g.Stop):
                    g.snapshot(f.run, (g.OLD, g.OLD, g.OLD_BLOCKS))

    def test_actual_snapshot_gdt_exact_before_and_after(self):
        for blocks, bad in [(g.OLD_BLOCKS, '1014'), (g.NEW_BLOCKS, '1018')]:
            with self.subTest(blocks=blocks), StorageFixture() as f:
                f.blocks = blocks
                f.header_override['Reserved GDT blocks'] = bad
                with self.assertRaises(g.Stop):
                    g.snapshot(f.run, (g.OLD, g.OLD, blocks))

    def test_actual_main_root_lock_shared_record_and_all_snapshots(self):
        with StorageFixture() as f:
            g.main(f.release())
            self.assertEqual(len(f.mutations), 3)
            self.assertTrue((f.out / 'result.json').exists())
            record = json.loads(g.SHARED.read_text())
            self.assertEqual(record['schema'], 'mckernel.heavy-operation.v1')
            self.assertEqual(record['kind'], 'scratch-growth-maintenance')
            self.assertEqual(record['inode'], g.SHARED.stat().st_ino)
            competitor = f.original_open(f.lock, os.O_RDONLY)
            try:
                with self.assertRaises(BlockingIOError):
                    g.fcntl.flock(competitor, g.fcntl.LOCK_EX | g.fcntl.LOCK_NB)
            finally:
                os.close(competitor)

    def test_actual_main_bad_lock_identity_stops_before_shared_acquisition(self):
        for field, bad in [('mutex_dev', 28), ('mutex_ino', 5)]:
            with self.subTest(field=field), StorageFixture() as f:
                setattr(f, field, bad)
                with self.assertRaises(g.Stop):
                    g.main(f.release())
                self.assertFalse(g.SHARED.exists())
                self.assertFalse(f.mutations)

    def test_actual_main_invalid_geometry_qualification_stops_before_lock(self):
        with StorageFixture() as f:
            with self.assertRaises(g.Stop):
                g.main(f.release(qualification_mutate=lambda q: q['geometry'].update(reserved_gdt_after=1018)))
            self.assertIsNone(f.lockfd)
            self.assertFalse(f.mutations)

    def test_actual_main_stale_or_nonretired_receipt_stops_before_shared(self):
        for change in [lambda r: r.update(observed_epoch=time.time() - 61),
                       lambda r: r.update(docker_tasks=[2036]),
                       lambda r: r.update(protected_scratch21_unchanged=False)]:
            with self.subTest(change=change), StorageFixture() as f:
                with self.assertRaises(g.Stop):
                    g.main(f.release(retirement_mutate=change))
                self.assertFalse(g.SHARED.exists())
                self.assertFalse(f.mutations)

    def test_actual_main_live_identity_failure_retains_shared_without_mutation(self):
        with StorageFixture() as f:
            f.back_ino = 47468428
            with self.assertRaises(g.Stop):
                g.main(f.release())
            self.assertTrue(g.SHARED.exists())
            self.assertTrue((f.out / 'failure.json').exists())
            self.assertFalse(f.mutations)

    def test_actual_main_existing_shared_is_never_replaced(self):
        with StorageFixture() as f:
            original = b'original retained ownership\n'
            g.SHARED.write_bytes(original)
            with self.assertRaises(Exception):
                g.main(f.release())
            self.assertEqual(g.SHARED.read_bytes(), original)
            self.assertFalse(f.mutations)


if __name__ == '__main__':
    unittest.main(verbosity=2)
