"""Executable disposable tests; never launches QEMU or a heavy operation."""
import copy
import importlib.machinery
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

from scripts import qemu_guest_heavy_v1 as guest


class GuestHeavyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='guest-heavy-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.logs = self.root / 'logs'
        self.lock = self.root / 'heavy.lock'
        self.controller = guest.identity(os.getpid())
        self.qemu = {'pid': 9999999, 'starttime': '123', 'boot_id': guest.boot_id()}
        self.provider_name = 'scripts/native_rust_exact_disk_build_wrapper.py'
        self.request = {'controller': self.controller, 'sources': {self.provider_name: 'fixture'}, 'config': {
            'log_dir': str(self.logs), 'overlay': str(self.logs / 'guest-overlay.qcow2'),
            'qemu_argv': ['/fake/qemu', '-daemonize']}}
        self.common = types.SimpleNamespace(SHARED_HEAVY_LOCK_PATH=str(self.lock),
                                          HEAVY_ENTRY_CONTRACT_RELEASED=True)

    def admit(self):
        with mock.patch.object(guest, 'authenticate', return_value=(self.request, {self.provider_name: b'fixture'})), \
             mock.patch.object(guest, '_AUTHENTICATED_IDENTITIES', {self.provider_name: ()}), \
             mock.patch.object(guest, 'verify_source_identities'), \
             mock.patch.object(guest, 'provider', return_value=self.common), \
             mock.patch.object(guest, 'HEAVY_ENTRY_CONTRACT_RELEASED', True):
            guest.admit('request', 'a' * 64, 'b' * 40, {})

    def terminal_fixture(self):
        self.admit()
        record = guest.strict_json(self.lock.read_bytes())
        record['qemu'] = self.qemu
        update = self.root / 'fixture-update'
        guest.write_claim(update, record)
        os.replace(update, self.lock)
        guest.exclusive_write(self.logs / 'qemu-started.json', guest.encode(self.qemu))
        evidence = self.logs / 'guest-evidence'
        evidence.mkdir()
        data = b'actual application bytes\n'
        manifest = (guest.digest(data) + '  stdout\n').encode()
        (evidence / 'stdout').write_bytes(data)
        (evidence / 'SHA256SUMS').write_bytes(manifest)
        with tarfile.open(self.logs / 'guest-evidence.tar', 'w') as archive:
            for name, raw in [('stdout', data), ('SHA256SUMS', manifest)]:
                entry = tarfile.TarInfo(name); entry.size = len(raw)
                archive.addfile(entry, io.BytesIO(raw))
        sha = guest.digest((self.logs / 'guest-evidence.tar').read_bytes())
        (self.logs / 'guest-evidence.tar.sha256').write_text(sha + '  guest-evidence.tar\n')
        for name in guest.REQUIRED_LOGS:
            if name != 'run-status.json' and not (self.logs / name).exists():
                (self.logs / name).write_bytes(b'log\n')
        return {'cleanup_rc': 0, 'evidence_rc': 0, 'command_rc': 37}

    def test_source_release_requires_both_switches_before_mutation(self):
        self.assertTrue(guest.HEAVY_ENTRY_CONTRACT_RELEASED)
        for guest_switch, common_switch in ((False, True), (True, False), (False, False)):
            with self.subTest(guest=guest_switch, common=common_switch), \
                 mock.patch.object(guest, 'HEAVY_ENTRY_CONTRACT_RELEASED', guest_switch), \
                 mock.patch.object(self.common, 'HEAVY_ENTRY_CONTRACT_RELEASED', common_switch), \
                 mock.patch.object(guest, 'authenticate', return_value=(self.request, {self.provider_name: b'fixture'})), \
                 mock.patch.object(guest, '_AUTHENTICATED_IDENTITIES', {self.provider_name: ()}), \
                 mock.patch.object(guest, 'verify_source_identities'), \
                 mock.patch.object(guest, 'provider', return_value=self.common):
                with self.assertRaisesRegex(ValueError, 'not released'):
                    guest.admit('request', 'a' * 64, 'b' * 40, {})
                self.assertFalse(self.lock.exists())
                self.assertFalse(self.logs.exists())

    def test_lock_keeps_controller_not_transient_helper(self):
        self.admit()
        record = json.loads(self.lock.read_text())
        self.assertEqual(record['controller'], self.controller)
        self.assertEqual(record['qemu'], None)
        self.assertEqual(record['inode'], self.lock.stat().st_ino)

    def test_existing_lock_is_never_overwritten_or_output_created(self):
        self.lock.write_text('build claim')
        with self.assertRaises(FileExistsError):
            self.admit()
        self.assertEqual(self.lock.read_text(), 'build claim')
        self.assertFalse(self.logs.exists())

    def test_cross_kind_exclusion_uses_actual_common_provider(self):
        snapshot = guest.read_file(guest.PROVIDER)
        info = guest.PROVIDER.lstat()
        common = guest.provider(snapshot, guest.digest(snapshot),
                                (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
        with mock.patch.object(common, 'SHARED_HEAVY_LOCK_PATH', str(self.lock)), \
             mock.patch.object(common, 'HEAVY_ENTRY_CONTRACT_RELEASED', True):
            self.admit()
            original = self.lock.read_bytes()
            for kind in ('build', 'image', 'guest'):
                with self.assertRaises(common.AdmissionError):
                    common.acquire_heavy_operation({}, kind)
                self.assertEqual(self.lock.read_bytes(), original)

    def test_lock_fsync_failure_retains_claim_without_outputs(self):
        with mock.patch.object(guest.os, 'fsync', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.admit()
        self.assertTrue(self.lock.exists())
        self.assertFalse(self.logs.exists())

    def registration_patches(self):
        real_identity = guest.identity
        return (mock.patch.object(guest, 'identity', side_effect=lambda pid: self.qemu if pid == self.qemu['pid'] else real_identity(pid)),
                mock.patch.object(guest, 'qemu_command', return_value=([b'/fake/qemu', b'-daemonize'], '/fake/qemu')))

    def test_qemu_identity_atomically_appended_and_controller_preserved(self):
        self.admit(); original = json.loads(self.lock.read_text())
        identity_patch, command_patch = self.registration_patches()
        with identity_patch, command_patch:
            guest.register_qemu(str(self.logs), self.qemu['pid'])
        current = json.loads(self.lock.read_text())
        self.assertEqual(current['qemu'], self.qemu)
        self.assertEqual(current['controller'], original['controller'])
        self.assertNotEqual(current['inode'], original['inode'])
        self.assertEqual(current['inode'], self.lock.stat().st_ino)
        self.assertEqual(json.loads((self.logs / 'qemu-started.json').read_text()), self.qemu)
        guest.acquired(str(self.logs))

    def test_wrong_qemu_argv_never_changes_claim(self):
        self.admit(); original = self.lock.read_bytes()
        identity_patch, command_patch = self.registration_patches()
        with identity_patch, command_patch as command:
            command.return_value = ([b'wrong'], '/fake/qemu')
            with self.assertRaisesRegex(ValueError, 'argv'):
                guest.register_qemu(str(self.logs), self.qemu['pid'])
        self.assertEqual(self.lock.read_bytes(), original)

    def test_failed_atomic_registration_retains_old_claim_and_update(self):
        self.admit(); original = self.lock.read_bytes()
        identity_patch, command_patch = self.registration_patches()
        with identity_patch, command_patch, mock.patch.object(guest.os, 'replace', side_effect=OSError('replace failure')):
            with self.assertRaises(OSError):
                guest.register_qemu(str(self.logs), self.qemu['pid'])
        self.assertEqual(self.lock.read_bytes(), original)
        self.assertEqual(len(list(self.root.glob('*.update'))), 1)

    def test_duplicate_qemu_registration_retains_first_claim(self):
        self.admit()
        identity_patch, command_patch = self.registration_patches()
        with identity_patch, command_patch:
            guest.register_qemu(str(self.logs), self.qemu['pid'])
            original = self.lock.read_bytes()
            with self.assertRaisesRegex(ValueError, 'already registered'):
                guest.register_qemu(str(self.logs), self.qemu['pid'])
            self.assertEqual(self.lock.read_bytes(), original)

    def test_directory_fsync_failure_does_not_publish_result(self):
        status = self.terminal_fixture()
        with mock.patch.object(guest, 'fsync_dir', side_effect=OSError('directory fsync failure')):
            with self.assertRaises(OSError):
                guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())
        self.assertFalse((self.logs / 'heavy-operation-result.json').exists())

    def test_readback_changed_seal_does_not_release(self):
        status = self.terminal_fixture()
        original_read = guest.read_file
        def change_seal(path):
            if Path(path).name == 'evidence-seal.json':
                return b'{}'
            return original_read(path)
        with mock.patch.object(guest, 'read_file', side_effect=change_seal):
            with self.assertRaisesRegex(ValueError, 'seal readback'):
                guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())

    def test_exclusive_full_write_retries_short_writes(self):
        real_write = os.write
        with mock.patch.object(guest.os, 'write', side_effect=lambda fd, data: real_write(fd, data[:3])):
            guest.exclusive_write(self.root / 'short', b'0123456789')
        self.assertEqual((self.root / 'short').read_bytes(), b'0123456789')

    def test_zero_write_fails_and_retains_partial(self):
        with mock.patch.object(guest.os, 'write', return_value=0):
            with self.assertRaisesRegex(ValueError, 'no progress'):
                guest.exclusive_write(self.root / 'partial', b'x')
        self.assertTrue((self.root / 'partial').exists())

    def test_cleanup_failure_retains_claim(self):
        status = self.terminal_fixture(); status['cleanup_rc'] = 1
        with self.assertRaisesRegex(ValueError, 'cleanup or evidence'):
            guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())
        self.assertEqual(json.loads((self.logs / 'run-status.json').read_text()), status)

    def test_evidence_rc_failure_retains_claim(self):
        status = self.terminal_fixture(); status['evidence_rc'] = 2
        with self.assertRaisesRegex(ValueError, 'cleanup or evidence'):
            guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())

    def test_positive_seal_binds_archive_manifest_logs_and_failure_exit(self):
        status = self.terminal_fixture()
        guest.seal_and_release(str(self.logs), status)
        self.assertFalse(self.lock.exists())
        seal = json.loads((self.logs / 'evidence-seal.json').read_text())
        self.assertEqual(seal['status']['command_rc'], 37)
        self.assertEqual(set(seal['members']), set(guest.REQUIRED_LOGS) | {'guest-evidence/stdout'})
        result = json.loads((self.logs / 'heavy-operation-result.json').read_text())
        self.assertEqual(result['status'], 'RETIRED')
        self.assertEqual(result['evidence_seal_sha256'], guest.digest((self.logs / 'evidence-seal.json').read_bytes()))

    def test_missing_required_log_retains_claim(self):
        status = self.terminal_fixture(); (self.logs / 'serial.log').unlink()
        with self.assertRaises(FileNotFoundError):
            guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())

    def test_bad_archive_digest_retains_claim(self):
        status = self.terminal_fixture(); (self.logs / 'guest-evidence.tar.sha256').write_text('wrong')
        with self.assertRaisesRegex(ValueError, 'archive digest'):
            guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())

    def test_bad_manifest_retains_claim(self):
        status = self.terminal_fixture(); (self.logs / 'guest-evidence/stdout').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'manifest member'):
            guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())

    def test_overlay_presence_blocks_release(self):
        status = self.terminal_fixture(); (self.logs / 'guest-overlay.qcow2').touch()
        with self.assertRaisesRegex(ValueError, 'overlay remains'):
            guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())

    def test_seal_fsync_failure_retains_claim(self):
        status = self.terminal_fixture()
        real_sync = os.fsync
        def fail_seal(fd):
            if str(Path('/proc/self/fd', str(fd)).resolve()).endswith('evidence-seal.json'):
                raise OSError('seal fsync failure')
            real_sync(fd)
        with mock.patch.object(guest.os, 'fsync', side_effect=fail_seal):
            with self.assertRaises(OSError):
                guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())
        self.assertFalse((self.logs / 'heavy-operation-result.json').exists())

    def test_preexisting_seal_never_overwritten(self):
        status = self.terminal_fixture(); (self.logs / 'evidence-seal.json').write_bytes(b'original')
        with self.assertRaises(FileExistsError):
            guest.seal_and_release(str(self.logs), status)
        self.assertEqual((self.logs / 'evidence-seal.json').read_bytes(), b'original')
        self.assertTrue(self.lock.exists())

    def test_pid_reuse_blocks_signal_and_disappearance(self):
        reused = dict(self.qemu, starttime='124')
        with mock.patch.object(guest, 'identity', return_value=reused), \
             mock.patch.object(guest, 'pidfd_open') as opened:
            with self.assertRaisesRegex(ValueError, 'incarnation'):
                guest.retire_process(self.qemu, seconds=0)
            opened.assert_not_called()

    def test_pid_reuse_between_pidfd_and_signal_blocks_signal(self):
        reused = dict(self.qemu, starttime='124')
        with mock.patch.object(guest, 'identity', side_effect=[self.qemu, reused]), \
             mock.patch.object(guest, 'pidfd_open', return_value=777), \
             mock.patch.object(guest.os, 'close') as closed, \
             mock.patch.object(guest, 'pidfd_signal') as sent:
            with self.assertRaisesRegex(ValueError, 'incarnation'):
                guest.signal_exact(self.qemu, signal.SIGTERM)
            sent.assert_not_called(); closed.assert_called_once_with(777)

    def test_surviving_kill_is_not_retirement(self):
        with mock.patch.object(guest, 'process_state', return_value='same'), \
             mock.patch.object(guest, 'signal_exact') as sent:
            with self.assertRaisesRegex(ValueError, 'survives'):
                guest.retire_process(self.qemu, seconds=0)
            self.assertEqual(sent.call_args_list, [mock.call(self.qemu, signal.SIGTERM),
                                                  mock.call(self.qemu, signal.SIGKILL)])

    def test_post_kill_disappearance_is_required_and_observed(self):
        with mock.patch.object(guest, 'process_state', side_effect=['same', 'same', 'absent']), \
             mock.patch.object(guest, 'signal_exact') as sent:
            guest.retire_process(self.qemu, seconds=0)
            self.assertEqual(sent.call_count, 2)

    def test_controller_incarnation_change_blocks_seal(self):
        status = self.terminal_fixture()
        with mock.patch.object(guest, 'identity', return_value=dict(self.controller, starttime='wrong')):
            with self.assertRaisesRegex(ValueError, 'incarnation'):
                guest.seal_and_release(str(self.logs), status)
        self.assertTrue(self.lock.exists())

    def test_replaced_lock_inode_blocks_access(self):
        self.admit(); replacement = self.root / 'replacement'
        replacement.write_bytes(self.lock.read_bytes()); os.replace(replacement, self.lock)
        with self.assertRaisesRegex(ValueError, 'inode'):
            guest.acquired(str(self.logs))

    def test_tar_symlink_is_rejected_before_extraction(self):
        self.admit()
        with tarfile.open(self.logs / 'guest-evidence.tar', 'w') as archive:
            entry = tarfile.TarInfo('escape'); entry.type = tarfile.SYMTYPE; entry.linkname = '/tmp'
            archive.addfile(entry)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            guest.extract_evidence(str(self.logs))
        self.assertFalse((self.logs / 'guest-evidence').exists())


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='guest-auth-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(guest, 'ROOT', self.root).start()
        mock.patch.object(guest.os, 'getppid', return_value=os.getpid()).start()
        for name in guest.SOURCES:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(name.encode())
        snapshots = {name: (self.root / name).read_bytes() for name in guest.SOURCES}
        identities = {}
        for name in guest.SOURCES:
            info = (self.root / name).lstat()
            identities[name] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        mock.patch.object(guest, '_AUTHENTICATED_SOURCES', snapshots).start()
        mock.patch.object(guest, '_AUTHENTICATED_IDENTITIES', identities).start()
        image = self.root / 'image'; image.write_bytes(b'image')
        self.request_path = self.root / 'request.json'
        self.actual = {'controller_pid': os.getpid(), 'input_paths': [str(image)], 'config': {
            'cpus': '4', 'memory': '4096M', 'guest_cmd_timeout': '300', 'guest_cleanup_timeout': '30',
            'keep_running': '0', 'keep_overlay': '0', 'guest_cleanup': '1',
            'guest_cmd': 'app', 'guest_evidence_dir': '/tmp/evidence',
            'log_dir': str(self.root / 'logs'), 'overlay': str(self.root / 'logs/guest-overlay.qcow2'),
            'qemu_argv': ['/usr/bin/qemu', '-daemonize', '-nic', 'user,restrict=on']}}
        self.request = {'schema': 'mckernel.guest-heavy.v1', 'release': 'REVIEWED_EXECUTION',
                        'source_commit': 'a' * 40,
                        'sources': {name: guest.digest((self.root / name).read_bytes()) for name in guest.SOURCES},
                        'config': copy.deepcopy(self.actual['config']), 'controller': guest.identity(os.getpid()),
                        'inputs': [guest.file_binding(str(image))], 'limits': {'memory_bytes': 12 * 1024**3}}
        mock.patch.object(guest, 'observed_limits', return_value=self.request['limits']).start()
        self.git = mock.patch.object(guest, 'git', side_effect=self.git_read).start()

    def git_read(self, *args):
        if args[0] == 'for-each-ref':
            return b'refs/remotes/origin/main\n'
        return (self.root / args[1].split(':', 1)[1]).read_bytes()

    def authenticate(self):
        self.request_path.write_bytes(guest.encode(self.request))
        return guest.authenticate(str(self.request_path), guest.digest(self.request_path.read_bytes()),
                                  'b' * 40, self.actual)[0]

    def test_positive_exact_request(self):
        self.assertEqual(self.authenticate(), self.request)

    def test_empty_request_rejected(self):
        self.request = {}
        with self.assertRaisesRegex(ValueError, 'fields'):
            self.authenticate()

    def test_unknown_field_rejected(self):
        self.request['extra'] = True
        with self.assertRaisesRegex(ValueError, 'fields'):
            self.authenticate()

    def test_wrong_helper_hash_rejected(self):
        self.request['sources']['scripts/qemu_guest_heavy_v1.py'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            self.authenticate()

    def test_wrong_config_rejected_without_rewriting_request(self):
        self.request['config']['cpus'] = '2'
        original = copy.deepcopy(self.request)
        with self.assertRaisesRegex(ValueError, 'configuration mismatch'):
            self.authenticate()
        self.assertEqual(self.request, original)

    def test_wrong_controller_rejected(self):
        self.request['controller']['starttime'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'controller binding'):
            self.authenticate()

    def test_changed_image_rejected(self):
        (self.root / 'image').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'input binding'):
            self.authenticate()

    def test_unfetched_commit_rejected(self):
        self.git.side_effect = lambda *args: b''
        with self.assertRaisesRegex(ValueError, 'fetched origin'):
            self.authenticate()

    def test_request_blob_mismatch_rejected(self):
        original = self.git_read
        self.git.side_effect = lambda *args: b'{}' if args[0] == 'show' and args[1].endswith(':request.json') else original(*args)
        with self.assertRaisesRegex(ValueError, 'fetched blob'):
            self.authenticate()

    def test_mismatched_limits_rejected(self):
        self.request['limits'] = {'test': 'other'}
        with self.assertRaisesRegex(ValueError, 'resource profile'):
            self.authenticate()

    def test_existing_output_root_rejected(self):
        (self.root / 'logs').mkdir()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.authenticate()

    def test_guest_memory_above_bound_rejected(self):
        self.request['config']['memory'] = self.actual['config']['memory'] = '13G'
        with self.assertRaisesRegex(ValueError, 'memory exceeds'):
            self.authenticate()

    def test_unbounded_cleanup_rejected(self):
        self.request['config']['guest_cleanup_timeout'] = self.actual['config']['guest_cleanup_timeout'] = '0'
        with self.assertRaisesRegex(ValueError, 'deadlines'):
            self.authenticate()

    def test_helper_after_load_substitution_cannot_authenticate_new_disk_bytes(self):
        name = 'scripts/qemu_guest_heavy_v1.py'
        replacement = b'raise RuntimeError("substituted helper")\n'
        (self.root / name).write_bytes(replacement)
        self.request['sources'][name] = guest.digest(replacement)
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            self.authenticate()

    def test_identical_bytes_replaced_after_load_are_rejected_by_identity(self):
        target = self.root / 'scripts/qemu_guest_heavy_v1.py'
        replacement = self.root / 'replacement'
        replacement.write_bytes(target.read_bytes())
        os.replace(replacement, target)
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            self.authenticate()

    def test_direct_loaded_helper_without_bootstrap_snapshot_is_rejected(self):
        with mock.patch.object(guest, '_AUTHENTICATED_SOURCES', None):
            with self.assertRaisesRegex(ValueError, 'bootstrap snapshot'):
                self.authenticate()


class ProviderSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='guest-provider-snapshot-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'provider.py'
        self.source = b'VALUE = "verified snapshot"\n'
        self.path.write_bytes(self.source)
        info = self.path.stat()
        self.identity = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        self.patch = mock.patch.object(guest, 'PROVIDER', self.path)
        self.patch.start(); self.addCleanup(self.patch.stop)

    def test_source_loader_and_module_cache_cannot_substitute_executed_provider(self):
        malicious = types.ModuleType('guest_heavy_provider_snapshot')
        malicious.VALUE = 'substituted module cache'
        with mock.patch.dict(sys.modules, {'guest_heavy_provider_snapshot': malicious}), \
             mock.patch.object(importlib.machinery.SourceFileLoader, 'get_code',
                               return_value=compile('VALUE="substituted loader"', '<poison>', 'exec')) as loader, \
             mock.patch.object(importlib.machinery.SourceFileLoader, 'exec_module') as execute:
            first = guest.provider(self.source, guest.digest(self.source), self.identity)
            first.VALUE = 'changed first namespace'
            second = guest.provider(self.source, guest.digest(self.source), self.identity)
        loader.assert_not_called(); execute.assert_not_called()
        self.assertEqual(second.VALUE, 'verified snapshot')
        self.assertIsNot(second, malicious)
        self.assertIsNot(first, second)

    def test_provider_snapshot_mismatch_is_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, 'snapshot hash'):
            guest.provider(b'raise RuntimeError("executed bad bytes")', guest.digest(self.source), self.identity)

    def test_provider_path_replacement_rejected_without_loading_replacement(self):
        replacement = self.path.parent / 'replacement'
        replacement.write_bytes(b'raise RuntimeError("executed replacement")')
        os.replace(replacement, self.path)
        with self.assertRaisesRegex(ValueError, 'path/identity changed'):
            guest.provider(self.source, guest.digest(self.source), self.identity)

    def test_provider_never_reopens_source_after_authentication(self):
        with mock.patch.object(guest, 'read_file', side_effect=AssertionError('reopened source')), \
             mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('reopened source')):
            result = guest.provider(self.source, guest.digest(self.source), self.identity)
        self.assertEqual(result.VALUE, 'verified snapshot')


class GitAuthorityTests(unittest.TestCase):
    """Real Git objects/refs only in disposable repositories; no network."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='guest-git-authority-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root = self.directory / 'trusted'
        self.foreign = self.directory / 'foreign'
        self.environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C',
                            'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                            'GIT_AUTHOR_NAME': 'fixture', 'GIT_AUTHOR_EMAIL': 'fixture@invalid',
                            'GIT_COMMITTER_NAME': 'fixture', 'GIT_COMMITTER_EMAIL': 'fixture@invalid'}
        for root in (self.root, self.foreign):
            subprocess.run(['/usr/bin/git', 'init', '-q', str(root)], env=self.environment, check=True)
        self.trusted_commit = self.make_commit(self.root, b'trusted request and source\n')
        self.foreign_commit = self.make_commit(self.foreign, b'foreign request and source\n')
        self.run_git(self.root, 'update-ref', 'refs/remotes/origin/main', self.trusted_commit)
        self.run_git(self.foreign, 'update-ref', 'refs/remotes/origin/main', self.foreign_commit)
        self.patch = mock.patch.object(guest, 'ROOT', self.root)
        self.patch.start(); self.addCleanup(self.patch.stop)

    def run_git(self, root, *args, data=None):
        return subprocess.check_output(['/usr/bin/git', '--git-dir=' + str(root / '.git'),
                                        '--work-tree=' + str(root), *args], input=data,
                                       stderr=subprocess.PIPE, env=self.environment)

    def make_commit(self, root, content):
        blob = self.run_git(root, 'hash-object', '-w', '--stdin', data=content).decode().strip()
        tree = self.run_git(root, 'mktree', data=('100644 blob ' + blob + '\trequest.json\n').encode()).decode().strip()
        return self.run_git(root, 'commit-tree', tree, data=b'disposable authority fixture\n').decode().strip()

    def assert_trusted(self):
        guest.fetched(self.trusted_commit)
        self.assertEqual(guest.git('show', self.trusted_commit + ':request.json'), b'trusted request and source\n')
        with self.assertRaises((ValueError, subprocess.CalledProcessError)):
            guest.fetched(self.foreign_commit)
        with self.assertRaises(subprocess.CalledProcessError):
            guest.git('cat-file', '-e', self.foreign_commit + '^{commit}')

    def test_ambient_repository_and_object_overrides_cannot_redirect_authority(self):
        overrides = {
            'GIT_DIR': str(self.foreign / '.git'), 'GIT_WORK_TREE': str(self.foreign),
            'GIT_COMMON_DIR': str(self.foreign / '.git'),
            'GIT_OBJECT_DIRECTORY': str(self.foreign / '.git/objects'),
            'GIT_ALTERNATE_OBJECT_DIRECTORIES': str(self.foreign / '.git/objects'),
            'GIT_NAMESPACE': 'foreign', 'GIT_INDEX_FILE': str(self.foreign / 'index'),
            'GIT_CEILING_DIRECTORIES': str(self.root), 'GIT_DISCOVERY_ACROSS_FILESYSTEM': '0',
            'GIT_EXEC_PATH': str(self.foreign), 'GIT_REPLACE_REF_BASE': 'refs/foreign/',
            'GIT_NO_REPLACE_OBJECTS': '0', 'GIT_PAGER': 'false',
        }
        for name, value in overrides.items():
            with self.subTest(variable=name), mock.patch.dict(os.environ, {name: value}):
                self.assert_trusted()
        with mock.patch.dict(os.environ, overrides):
            self.assert_trusted()

    def test_ambient_config_overrides_are_not_consumed(self):
        bad_config = self.directory / 'bad-config'
        bad_config.write_text('invalid Git configuration must never be read\n')
        overrides = {'GIT_CONFIG': str(bad_config), 'GIT_CONFIG_SYSTEM': str(bad_config),
                     'GIT_CONFIG_GLOBAL': str(bad_config), 'GIT_CONFIG_NOSYSTEM': '0',
                     'GIT_CONFIG_PARAMETERS': 'not a valid quoted parameter',
                     'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'include.path',
                     'GIT_CONFIG_VALUE_0': str(bad_config), 'XDG_CONFIG_HOME': str(self.foreign),
                     'PAGER': 'false', 'LD_PRELOAD': '/no/such/ambient-library.so'}
        for name, value in overrides.items():
            with self.subTest(variable=name), mock.patch.dict(os.environ, {name: value}):
                self.assert_trusted()
        with mock.patch.dict(os.environ, overrides):
            self.assert_trusted()

    def test_path_git_shim_is_never_executed(self):
        marker = self.directory / 'shim-executed'
        shim = self.directory / 'git'
        shim.write_text('#!/bin/sh\necho shim > "' + str(marker) + '"\nprintf "forged bytes\\n"\n')
        shim.chmod(0o755)
        with mock.patch.dict(os.environ, {'PATH': str(self.directory)}):
            self.assert_trusted()
        self.assertFalse(marker.exists())

    def test_replace_refs_cannot_substitute_source_blob_or_commit_ancestry(self):
        replacement = self.make_commit(self.root, b'forged replacement\n')
        self.run_git(self.root, 'update-ref', 'refs/replace/' + self.trusted_commit, replacement)
        self.assertEqual(self.run_git(self.root, 'show', self.trusted_commit + ':request.json'),
                         b'forged replacement\n')
        self.assert_trusted()
        # Replacement of the original blob itself is also disabled.
        original_blob = self.run_git(self.root, '--no-replace-objects', 'rev-parse',
                                     self.trusted_commit + ':request.json').decode().strip()
        replacement_blob = self.run_git(self.root, 'hash-object', '-w', '--stdin',
                                        data=b'forged blob replacement\n').decode().strip()
        self.run_git(self.root, 'update-ref', 'refs/replace/' + original_blob, replacement_blob)
        self.assert_trusted()

    def test_verifier_subprocess_has_only_fixed_executable_repo_and_environment(self):
        with mock.patch.object(guest.subprocess, 'check_output', return_value=b'') as called:
            guest.git('show', self.trusted_commit + ':request.json')
        args, kwargs = called.call_args
        self.assertEqual(args[0][:5], ['/usr/bin/git', '--no-pager', '--no-replace-objects',
                                      '--git-dir=' + str(self.root / '.git'), '--work-tree=' + str(self.root)])
        self.assertEqual(kwargs['env'], {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C',
                                        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_SYSTEM': '/dev/null',
                                        'GIT_CONFIG_GLOBAL': '/dev/null'})


class BootstrapSnapshotTests(unittest.TestCase):
    run_git = GitAuthorityTests.run_git
    make_commit = GitAuthorityTests.make_commit

    def setUp(self):
        GitAuthorityTests.setUp(self)
        repository = Path(__file__).resolve().parents[2]
        shell_source = (repository / 'scripts/qemu-mckernel-guest.sh').read_text()
        bootstrap = shell_source[shell_source.index('heavy_helper() {'):shell_source.index('acquire_heavy_operation() {')]
        self.runner = self.root / 'scripts/qemu-mckernel-guest.sh'
        self.helper = self.root / 'scripts/qemu_guest_heavy_v1.py'
        self.runner.parent.mkdir()
        self.runner.write_text('#!/bin/bash\nset -eu\nHEAVY_HELPER="' + str(self.helper) + '"\n'
                               'HEAVY_OPERATION_REQUEST="$1"\nHEAVY_REQUEST_SHA256="$2"\n'
                               'HEAVY_FETCHED_COMMIT="$3"\n' + bootstrap + "\nheavy_helper '' --help\n")
        for relative in guest.SOURCES:
            if relative != 'scripts/qemu-mckernel-guest.sh':
                (self.root / relative).write_bytes((repository / relative).read_bytes())
        self.run_git(self.root, 'add', 'scripts')
        tree = self.run_git(self.root, 'write-tree').decode().strip()
        source_commit = self.run_git(self.root, 'commit-tree', tree, data=b'bootstrap source fixture\n').decode().strip()
        self.request_path = self.root / 'request.json'
        request = {'schema': 'mckernel.guest-heavy.v1', 'release': 'REVIEWED_EXECUTION',
                   'source_commit': source_commit,
                   'sources': {name: guest.digest((self.root / name).read_bytes()) for name in guest.SOURCES}}
        self.request_path.write_bytes(guest.encode(request))
        self.run_git(self.root, 'add', 'request.json')
        tree = self.run_git(self.root, 'write-tree').decode().strip()
        self.commit = self.run_git(self.root, 'commit-tree', tree, '-p', source_commit,
                                   data=b'bootstrap request fixture\n').decode().strip()
        self.run_git(self.root, 'update-ref', 'refs/remotes/origin/main', self.commit)
        self.request_hash = guest.digest(self.request_path.read_bytes())

    def bootstrap(self, environment=None):
        return subprocess.run(['/bin/bash', str(self.runner), str(self.request_path), self.request_hash, self.commit],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
                              env=environment or os.environ.copy())

    def test_real_inline_bootstrap_executes_production_helper_snapshot(self):
        result = self.bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b'usage: qemu_guest_heavy_v1.py', result.stdout)

    def test_modified_helper_rejected_before_any_helper_code_executes(self):
        self.helper.write_text('raise RuntimeError("UNVERIFIED_HELPER_EXECUTED")\n')
        result = self.bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'source differs from fetched released bytes', result.stderr)
        self.assertNotIn(b'UNVERIFIED_HELPER_EXECUTED', result.stderr)

    def test_symlink_helper_rejected_without_execution(self):
        replacement = self.root / 'replacement.py'
        replacement.write_text('raise RuntimeError("UNVERIFIED_HELPER_EXECUTED")\n')
        self.helper.unlink(); self.helper.symlink_to(replacement)
        result = self.bootstrap()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b'UNVERIFIED_HELPER_EXECUTED', result.stderr)

    def test_poisoned_helper_cache_and_pythonpath_are_not_executed(self):
        poison = self.root / 'poison'; poison.mkdir()
        (poison / 'json.py').write_text('raise RuntimeError("PYTHONPATH_EXECUTED")\n')
        # Timestamp/size-valid CPython 3.8 cache: an ordinary SourceFileLoader
        # would use this code instead of the authenticated source file.
        writer = '''import importlib.util, marshal, pathlib, struct, sys
p = pathlib.Path(sys.argv[1]); info = p.stat()
cache = pathlib.Path(importlib.util.cache_from_source(str(p)))
cache.parent.mkdir(exist_ok=True)
code = compile('raise RuntimeError("BYTECODE_CACHE_EXECUTED")', str(p), 'exec')
cache.write_bytes(importlib.util.MAGIC_NUMBER + struct.pack('<III', 0, int(info.st_mtime), info.st_size) + marshal.dumps(code))
'''
        subprocess.run(['/usr/bin/python3', '-I', '-S', '-B', '-c', writer, str(self.helper)], check=True)
        environment = dict(os.environ, PYTHONPATH=str(poison), PYTHONHOME=str(poison))
        result = self.bootstrap(environment)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b'usage: qemu_guest_heavy_v1.py', result.stdout)
        self.assertNotIn(b'CACHE_EXECUTED', result.stderr)
        self.assertNotIn(b'PYTHONPATH_EXECUTED', result.stderr)


class ShellAdmissionTests(unittest.TestCase):
    def test_shell_cleanup_failure_status_cannot_report_success(self):
        runner = Path(__file__).resolve().parents[1] / 'qemu-mckernel-guest.sh'
        source = runner.read_text()
        cleanup = source[source.index('cleanup() {'):source.index('trap cleanup EXIT')]
        with tempfile.TemporaryDirectory(prefix='guest-shell-cleanup-') as raw:
            root = Path(raw); overlay = root / 'overlay'; overlay.touch()
            setup = '''
DRY_RUN=0; HEAVY_ACQUIRED=1; SSH_READY=1; GUEST_CLEANUP=1
GUEST_CLEANUP_TIMEOUT=1; SSH_ARGS=(); GUEST_CLEANUP_CMD=cleanup
HEAVY_HELPER=helper; LOG_DIR="$1"; OVERLAY="$1/overlay"
GUEST_CLEANUP_LOG="$1/cleanup.log"; evidence_rc=0; command_rc=0
timeout() { return 17; }
heavy_helper() {
    if [ "$2" = stop ]; then return 0; fi
    if [ "$2" = seal ]; then printf '%s' "$1" > "$LOG_DIR/status"; return 1; fi
    return 99
}
'''
            result = subprocess.run(['bash', '-c', setup + cleanup + '\ncleanup\n', 'cleanup-test', str(root)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads((root / 'status').read_text())['cleanup_rc'], 17)
            self.assertIn(b'shared claim retained', result.stderr)

    def test_empty_request_has_no_launch_overlay_or_evidence_mutation(self):
        with tempfile.TemporaryDirectory(prefix='guest-shell-admit-') as raw:
            root = Path(raw); binaries = root / 'bin'; binaries.mkdir()
            image = root / 'image'; image.write_bytes(b'image')
            request = root / 'request'; request.write_text('{}')
            marker = root / 'mutation'
            for name in ('qemu-system-x86_64', 'qemu-img', 'cloud-localds'):
                path = binaries / name
                path.write_text('#!/bin/sh\nif [ "$1" = info ]; then echo "file format: qcow2"; exit 0; fi\necho mutation >> "' + str(marker) + '"\nexit 99\n')
                path.chmod(0o755)
            runner = Path(__file__).resolve().parents[1] / 'qemu-mckernel-guest.sh'
            result = subprocess.run(['bash', str(runner), '--image', str(image), '--accel', 'tcg',
                                     '--log-dir', str(root / 'logs'), '--heavy-operation-request', str(request)],
                                    env=dict(os.environ, PATH=str(binaries) + ':' + os.environ['PATH']),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            self.assertFalse((root / 'logs').exists())


if __name__ == '__main__':
    unittest.main()
