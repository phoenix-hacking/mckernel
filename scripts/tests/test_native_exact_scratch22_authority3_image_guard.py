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
import native_exact_scratch22_authority3_image_guard as guard


class GuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.lock = self.root / 'development.lock'; self.lock.touch(mode=0o644); self.lock.chmod(0o644)
        self.capture = self.root / 'guard-capture'
        self.owner_evidence = self.root / 'owner'; self.owner_evidence.mkdir()
        source, backup = self.root / 'source', self.root / 'backup'; source.mkdir(); backup.mkdir()
        self.shared, self.common = self.root / 'shared', self.root / 'common'
        self.request = {'candidate_sha': guard.CANDIDATE, 'image_id': 'sha256:' + '4' * 64,
                        'owner_evidence_root': str(self.owner_evidence), 'lease_path': str(self.root / 'lease'),
                        'common_exclusion_path': str(self.common), 'source_root': str(source),
                        'backup_root': str(backup), 'source_identity': guard.image._identity(source),
                        'backup_identity': guard.image._identity(backup)}
        self.info = {'Id': 'c' * 64, 'Name': '/mckernel-image-' + 'a' * 32,
                     'Image': self.request['image_id'], 'Mounts': [],
                     'State': {'Running': False, 'Status': 'exited', 'Pid': 0, 'OOMKilled': False},
                     'Config': {'Labels': {'mckernel.owner': 'b' * 32},
                                'User': '%d:%d' % (os.getuid(), os.getgid())},
                     'HostConfig': dict(guard.image.LIMITS, Privileged=False, ReadonlyRootfs=True,
                                        CapDrop=['ALL'], SecurityOpt=['no-new-privileges'], Init=True,
                                        IpcMode='private')}
        self.shared.touch(); shared_meta = self.shared.stat()
        shared_record = {'device': shared_meta.st_dev, 'inode': shared_meta.st_ino, 'owner': 'fixture'}
        self.shared.write_text(json.dumps(shared_record))
        self.common.touch(); common_meta = self.common.stat()
        self.common.write_text(json.dumps({'dev': common_meta.st_dev, 'inode': common_meta.st_ino,
            'request_sha256': hashlib.sha256(json.dumps(self.request, sort_keys=True).encode()).hexdigest(),
            'pid': os.getpid(), 'starttime': guard.image._proc_starttime(os.getpid()),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
        self.result = {'status': 'PASS', 'retired': True, 'terminal_container_retained': True,
                       'cleanup_separately_required': True, 'terminal_container_info_current': False,
                       'terminal_container_info': self.info, 'container_name': self.info['Name'][1:],
                       'container_id': self.info['Id'], 'owner_nonce': 'b' * 32,
                       'shared_heavy_operation': {'path': str(self.shared), 'record': shared_record}}
        self.write_receipt()
        self.docker = mock.Mock(client_retirement_unproven=False)
        self.docker.call.side_effect = lambda *args, **kwargs: self.inspect()
        patch = mock.patch.object(guard.image._SHARED_HEAVY_ENTRY_CONTRACT,
                                   'SHARED_HEAVY_LOCK_PATH', str(self.shared))
        patch.start(); self.addCleanup(patch.stop)

    def write_receipt(self):
        (self.owner_evidence / guard.image.OWNER_RECEIPT_NAME).write_text(json.dumps(self.result))

    def assert_locked(self):
        fd = os.open(self.lock, os.O_RDONLY)
        try:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)

    def inspect(self):
        self.assert_locked()
        return subprocess.CompletedProcess([], 0, json.dumps([self.info]), '')

    def run_guard(self, run=None):
        def owner_run():
            self.assert_locked()
            if run:
                run()
            return self.result
        with mock.patch.object(guard, 'authenticate', return_value=(self.request,
                {'guard_capture': str(self.capture), 'nonce': 'd' * 32})), mock.patch.object(
                guard, 'Docker', return_value=self.docker), mock.patch.object(
                guard.image, 'ImageOwner') as image_owner:
            image_owner.return_value.run.side_effect = owner_run
            return guard.guarded_execute(self.root / 'request', '1' * 64,
                self.root / 'release', '2' * 64, lock_path=self.lock,
                lock_identity=(self.lock.stat().st_dev, self.lock.stat().st_ino),
                lock_owner=(os.getuid(), os.getgid()))

    def test_stopped_retained_positive_case_releases_only_root_lock(self):
        proof = self.run_guard()
        self.assertEqual(proof['owner_status'], 'PASS')
        self.assertTrue(self.common.exists()); self.assertTrue(self.shared.exists())
        self.assertFalse(self.result['terminal_container_info_current'])
        fd = os.open(self.lock, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)

    def test_failed_owner_with_positive_terminal_can_return_fail(self):
        self.result['status'] = 'FAIL'; self.write_receipt()
        self.assertEqual(self.run_guard()['owner_status'], 'FAIL')

    def quarantined(self, mutation):
        class Quarantined(Exception):
            pass
        def quarantine(fd, path):
            self.assert_locked(); os.close(fd)
            raise Quarantined()
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        handlers = {number: signal.getsignal(number) for number in guard.DEFERRED_SIGNALS}
        try:
            with mock.patch.object(guard, 'quarantine_root_lock', side_effect=quarantine):
                with self.assertRaises(Quarantined):
                    self.run_guard(mutation)
        finally:
            for number, handler in handlers.items():
                signal.signal(number, handler)
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
        self.assertTrue(self.common.exists()); self.assertTrue(self.shared.exists())

    def test_unproven_client_quarantines_even_with_terminal_receipt(self):
        self.quarantined(lambda: setattr(self.docker, 'client_retirement_unproven', True))

    def test_missing_create_identity_quarantines(self):
        def mutation():
            self.result.pop('container_id'); self.write_receipt()
        self.quarantined(mutation)

    def test_running_current_container_quarantines(self):
        def mutation():
            self.info['State']['Running'] = True
        self.quarantined(mutation)

    def test_wrong_current_container_name_quarantines(self):
        def mutation():
            self.info['Name'] = '/mckernel-image-' + 'f' * 32
            self.write_receipt()
        self.quarantined(mutation)

    def test_proof_publication_failure_quarantines(self):
        real = guard._write_json
        def writer(path, value):
            if path.name == 'guard-result.json':
                raise OSError('fixture full capture')
            return real(path, value)
        with mock.patch.object(guard, '_write_json', side_effect=writer):
            self.quarantined(lambda: None)

    def test_four_signal_handlers_latch_through_owner_and_restore(self):
        handlers = {number: signal.getsignal(number) for number in guard.DEFERRED_SIGNALS}
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        def deliver():
            for number in guard.DEFERRED_SIGNALS:
                handler = signal.getsignal(number)
                self.assertTrue(callable(handler)); handler(number, None)
        proof = self.run_guard(deliver)
        self.assertEqual(proof['interrupted_signal'], guard.DEFERRED_SIGNALS[0])
        self.assertEqual(signal.pthread_sigmask(signal.SIG_BLOCK, set()), mask)
        self.assertEqual({number: signal.getsignal(number) for number in handlers}, handlers)


if __name__ == '__main__':
    unittest.main()
