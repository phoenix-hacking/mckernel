import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[2] / 'docs/verification/evidence/native-exact-scratch18-image-attempt3-cleanup-20261001.py'

def load():
    spec = importlib.util.spec_from_file_location('interrupt_cleanup', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Crash(BaseException):
    pass

class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name) / 'scratch'
        root.mkdir(mode=0o700)
        self.m.ROOT = root
        self.m.DEVICE = root.stat().st_dev
        self.m.UID, self.m.GID = os.getuid(), os.getgid()
        for name in ('ATTEMPT', 'SHARED', 'MUTEX', 'PLAN', 'JOURNAL', 'CAPTURE', 'OUTPUT', 'EVIDENCE', 'LEASE'):
            setattr(self.m, name, root / name.lower())
        self.m.RECORDS = {}
        for path in (self.m.ATTEMPT, self.m.SHARED):
            raw = ('original-' + path.name).encode()
            path.write_bytes(raw)
            path.chmod(0o600)
            self.m.RECORDS[path] = (self.m.digest(raw), path.stat().st_ino, len(raw))
        self.m.OUTPUT.mkdir(mode=0o700)
        (self.m.OUTPUT / 'output').mkdir(mode=0o700)
        (self.m.OUTPUT / 'evidence').mkdir(mode=0o700)
        self.m.EVIDENCE.mkdir(mode=0o700)
        self.m.TERMINAL = self.m.EVIDENCE / 'terminal'
        self.m.TERMINAL.write_bytes(b'original-terminal')
        self.m.TERMINAL.chmod(0o600)
        self.m.TERMINAL_INODE = self.m.TERMINAL.stat().st_ino
        self.m.TERMINAL_SIZE = self.m.TERMINAL.stat().st_size
        self.m.TERMINAL_SHA = self.m.digest(self.m.TERMINAL.read_bytes())
        self.m.DIRS = {p: (p.stat().st_ino, p.stat().st_nlink) for p in (self.m.OUTPUT, self.m.EVIDENCE)}
        self.real = {name: getattr(self.m, name) for name in ('protected_files', 'capture_logs', 'validate_container_profile')}
        for name in self.real:
            patch = mock.patch.object(self.m, name)
            patch.start()
            self.addCleanup(patch.stop)
        self.census_patch = mock.patch.object(self.m, 'census', return_value=False)
        self.census = self.census_patch.start()
        self.addCleanup(self.census_patch.stop)

    def snapshot(self):
        return {str(p.relative_to(self.m.ROOT)): (p.lstat().st_ino, p.lstat().st_mtime_ns,
                p.read_bytes() if p.is_file() else None) for p in self.m.ROOT.rglob('*')}

    def test_default_read_only(self):
        before = self.snapshot()
        self.assertEqual(self.m.recover()['status'], 'PASS_VALIDATE_ONLY')
        self.assertEqual(self.snapshot(), before)

    def test_execute_then_immutable_terminal_replay(self):
        self.assertEqual(self.m.recover(True)['status'], 'PASS_EXECUTED')
        before = self.snapshot()
        for execute in (False, True, True):
            self.assertEqual(self.m.recover(execute)['status'], 'PASS_TERMINAL_REPLAY')
        self.assertEqual(before, self.snapshot())
        self.assertEqual(len(self.m.JOURNAL.read_bytes().splitlines()), 9)
        self.assertTrue(self.m.MUTEX.exists())
        self.assertTrue(self.m.TERMINAL.exists())
        for path, archive in zip((self.m.ATTEMPT,self.m.SHARED), self.m.ARCHIVE_NAMES):
            saved = self.m.ROOT / archive
            self.assertEqual((self.m.digest(saved.read_bytes()), saved.stat().st_ino, saved.stat().st_size), self.m.RECORDS[path])
            self.assertFalse(path.exists())

    def test_crash_after_every_exchange_release_frontier_and_resume(self):
        # Independent temporary fixtures for every mutation frontier.
        for index in range(2):
            for stage in ('before_exchange', 'exchange', 'after_exchange', 'release', 'rmdir', 'after_release'):
                with self.subTest(index=index, stage=stage):
                    case = CleanupTests(methodName='test_default_read_only')
                    case.setUp()
                    try:
                        m = case.m
                        real_append = m.Transaction.append
                        real_rename = m.rename_exchange
                        real_rmdir = m.os.rmdir
                        def append(tx, plan, rows, event, move):
                            real_append(tx, plan, rows, event, move)
                            if move == index and event == stage:
                                raise Crash()
                        def rename(fd, path, destination):
                            real_rename(fd, path, destination)
                            if stage == 'exchange' and path == (m.ATTEMPT,m.SHARED)[index].name:
                                raise Crash()
                        def rmdir(path, **kw):
                            real_rmdir(path, **kw)
                            if stage == 'rmdir' and path == (m.ATTEMPT,m.SHARED)[index].name:
                                raise Crash()
                        with mock.patch.object(m.Transaction, 'append', append), mock.patch.object(m, 'rename_exchange', rename), \
                             mock.patch.object(m.os, 'rmdir', rmdir):
                            with self.assertRaises(Crash):
                                m.recover(True)
                        before = case.snapshot()
                        self.assertEqual(m.recover()['status'], 'PASS_VALIDATE_ONLY')
                        self.assertEqual(case.snapshot(), before)
                        self.assertEqual(m.recover(True)['status'], 'PASS_EXECUTED')
                        self.assertEqual(len(m.JOURNAL.read_bytes().splitlines()), 9)
                    finally:
                        case.doCleanups()

    def test_crash_after_plan_and_empty_journal_creation(self):
        for name in ('PLAN', 'JOURNAL'):
            case = CleanupTests(methodName='test_default_read_only')
            case.setUp()
            try:
                m = case.m
                real = m.Transaction.create
                def create(tx, filename, data):
                    real(tx, filename, data)
                    if filename == getattr(m, name).name:
                        raise Crash()
                with mock.patch.object(m.Transaction, 'create', create):
                    with self.assertRaises(Crash):
                        m.recover(True)
                self.assertEqual(m.recover(True)['status'], 'PASS_EXECUTED')
            finally:
                case.doCleanups()

    def test_unbound_preparation_crash_refuses_and_keeps_all_active_records(self):
        real = self.m.os.mkdir
        def mkdir(path, *args, **kw):
            real(path,*args,**kw)
            if path == self.m.ARCHIVE_NAMES[0]: raise Crash()
        with mock.patch.object(self.m.os,'mkdir',mkdir):
            with self.assertRaises(Crash): self.m.recover(True)
        for path, binding in self.m.RECORDS.items():
            self.assertEqual((self.m.digest(path.read_bytes()),path.stat().st_ino,path.stat().st_size),binding)
        before = self.snapshot()
        with self.assertRaisesRegex(self.m.Refusal,'unbound-sentinel-preparation'):
            self.m.recover(True)
        self.assertEqual(before,self.snapshot())

    def test_v1_synthetic_plan_pollution_retained_and_refused(self):
        self.m.PLAN.write_bytes(b'{"schema":"native-exact-scratch18-interrupt-cleanup-v1","records":["/tmp/foreign"]}\n')
        self.m.PLAN.chmod(0o600)
        self.m.JOURNAL.write_bytes(b'{"event":"complete"}\n')
        self.m.JOURNAL.chmod(0o600)
        tx = self.m.Transaction()
        try: tx.lock(True)
        finally: tx.close()
        before = self.snapshot()
        with self.assertRaisesRegex(self.m.Refusal,'plan-sentinel-binding'):
            self.m.recover(True)
        self.assertEqual(before,self.snapshot())
        self.census.assert_not_called()

    def test_concurrent_mutex_refuses(self):
        tx = self.m.Transaction()
        try:
            tx.lock(True)
            for execute in (False, True):
                with self.assertRaisesRegex(self.m.Refusal, 'busy'):
                    self.m.recover(execute)
        finally:
            tx.close()
        self.assertEqual(self.m.recover(True)['status'], 'PASS_EXECUTED')

    def test_crash_after_complete_never_appends_again(self):
        real = self.m.Transaction.append
        def append(tx, plan, rows, event, index):
            real(tx, plan, rows, event, index)
            if event == 'complete': raise Crash()
        with mock.patch.object(self.m.Transaction, 'append', append):
            with self.assertRaises(Crash): self.m.recover(True)
        before = self.snapshot()
        self.assertEqual(self.m.recover(True)['status'], 'PASS_TERMINAL_REPLAY')
        self.assertEqual(before, self.snapshot())

    def test_early_or_out_of_order_disappearance_refuses(self):
        self.m.SHARED.unlink()
        with self.assertRaises(FileNotFoundError):
            self.m.recover(True)
        self.assertTrue(self.m.ATTEMPT.exists())
        self.assertTrue(self.m.ATTEMPT.exists())

    def test_foreign_mutex_refuses(self):
        self.m.MUTEX.write_bytes(b'foreign')
        self.m.MUTEX.chmod(0o600)
        with self.assertRaisesRegex(self.m.Refusal, 'mutex-binding'):
            self.m.recover(True)
        self.census.assert_not_called()

    def test_mutated_record_refuses_before_rename(self):
        self.m.SHARED.write_bytes(b'wrong')
        with self.assertRaises(self.m.Refusal):
            self.m.recover(True)
        self.assertTrue(self.m.ATTEMPT.exists())

    def test_symlink_records_state_mutex_and_ancestor_refuse(self):
        for attr in ('ATTEMPT','MUTEX','PLAN','JOURNAL'):
            path = getattr(self.m, attr)
            original = path.read_bytes() if path.exists() else None
            if path.exists(): path.unlink()
            path.symlink_to(self.m.TERMINAL)
            with self.assertRaises((OSError,self.m.Refusal)):
                self.m.recover(True)
            path.unlink()
            if original is not None:
                # Exact original inode cannot be restored; use fresh fixture below.
                path.write_bytes(original)
                path.chmod(0o600)
                st = path.stat()
                self.m.RECORDS[path] = (self.m.digest(original), st.st_ino, st.st_size)
        root = self.m.ROOT
        moved = root.with_name('moved')
        root.rename(moved)
        root.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(OSError):
            self.m.recover()

    def test_ancestor_replacement_during_transaction_refuses(self):
        tx = self.m.Transaction()
        try:
            moved = self.m.ROOT.with_name('moved')
            self.m.ROOT.rename(moved)
            self.m.ROOT.mkdir()
            with self.assertRaisesRegex(self.m.Refusal, 'ancestor-replaced'):
                tx.lock(True)
        finally:
            tx.close()

    def test_mutex_replacement_during_transaction_refuses(self):
        tx = self.m.Transaction()
        try:
            tx.lock(True)
            self.m.MUTEX.rename(self.m.ROOT/'old-mutex')
            self.m.MUTEX.touch(mode=0o600)
            with self.assertRaisesRegex(self.m.Refusal, 'mutex-replaced'):
                tx.pinned()
        finally:
            tx.close()

    def completed(self):
        self.m.recover(True)
        return [json.loads(line) for line in self.m.JOURNAL.read_bytes().splitlines()]

    def test_forged_complete_and_every_chain_field_refused(self):
        rows = self.completed()
        raw = self.m.JOURNAL.read_bytes()
        variants = [[rows[-1]], rows+[rows[-1]], rows[:2]+rows[4:]]
        for key, value in [('hash','f'*64),('previous','f'*64),('plan_sha256','f'*64),
                           ('sequence',99),('event','complete'),('index',3)]:
            bad = [dict(x) for x in rows]
            bad[0][key] = value
            variants.append(bad)
        for variant in variants:
            self.m.JOURNAL.write_bytes(b''.join(self.m.canonical(x)+b'\n' for x in variant))
            with self.assertRaises(self.m.Refusal): self.m.recover(True)
        self.m.JOURNAL.write_bytes(raw)
        self.assertEqual(self.m.recover()['status'], 'PASS_TERMINAL_REPLAY')

    def test_torn_journal_refuses_without_mutation(self):
        self.completed()
        self.m.JOURNAL.write_bytes(self.m.JOURNAL.read_bytes()[:-1])
        before = self.snapshot()
        with self.assertRaisesRegex(self.m.Refusal, 'torn-journal'):
            self.m.recover(True)
        self.assertEqual(before, self.snapshot())

    def test_changed_plan_refused(self):
        self.completed()
        plan = json.loads(self.m.PLAN.read_bytes())
        plan['records'][0][1] = 'f'*64
        self.m.PLAN.write_bytes(self.m.canonical(plan)+b'\n')
        with self.assertRaisesRegex(self.m.Refusal, 'plan-binding'):
            self.m.recover(True)

    def test_terminal_preserves_new_regular_owner_and_refuses_changed_evidence(self):
        self.completed()
        self.m.ATTEMPT.write_bytes(b'reappeared')
        self.m.ATTEMPT.chmod(0o600)
        before = self.snapshot()
        self.assertEqual(self.m.recover(True)['status'],'PASS_TERMINAL_REPLAY')
        self.assertEqual(self.snapshot(),before)
        self.m.ATTEMPT.unlink()
        self.m.TERMINAL.write_bytes(b'changed')
        with self.assertRaises(self.m.Refusal): self.m.recover(True)

    def test_census_failure_prevents_records_removal(self):
        self.census.side_effect = self.m.Refusal('census-failed')
        with self.assertRaises(self.m.Refusal): self.m.recover(True)
        for path in self.m.RECORDS: self.assertTrue(path.exists())
        self.assertFalse(self.m.PLAN.exists())

    def test_record_replacement_before_final_check_refuses(self):
        real = self.m.Transaction.append
        def append(tx, plan, rows, event, index):
            real(tx, plan, rows, event, index)
            if event == 'before_exchange' and index == 0:
                self.m.ATTEMPT.write_bytes(b'replaced')
        with mock.patch.object(self.m.Transaction, 'append', append):
            with self.assertRaises(self.m.Refusal): self.m.recover(True)
        self.assertTrue(self.m.ATTEMPT.exists())
        self.assertTrue(self.m.SHARED.exists())

    def test_adversarial_replacement_after_final_check_is_retained(self):
        real = self.m.rename_exchange
        foreign = b'foreign-live-owner-do-not-delete'
        original = self.m.ROOT / 'original-attempt-preserved'
        def rename(fd, source, destination):
            if source == self.m.ATTEMPT.name:
                self.m.ATTEMPT.rename(original)
                self.m.ATTEMPT.write_bytes(foreign)
                self.m.ATTEMPT.chmod(0o600)
            real(fd, source, destination)
        with mock.patch.object(self.m,'rename_exchange',rename):
            with self.assertRaisesRegex(self.m.Refusal,'file-binding'):
                self.m.recover(True)
        quarantine = self.m.ROOT / self.m.ARCHIVE_NAMES[0]
        self.assertEqual(quarantine.read_bytes(), foreign)
        self.assertEqual(original.stat().st_ino,self.m.RECORDS[self.m.ATTEMPT][1])
        self.assertTrue(self.m.SHARED.exists())
        self.assertTrue(self.m.SHARED.exists())
        rows = [json.loads(line) for line in self.m.JOURNAL.read_bytes().splitlines()]
        self.assertEqual([row['event'] for row in rows],['before_exchange'])
        self.assertTrue(self.m.ATTEMPT.is_dir())
        with self.assertRaises(FileExistsError):
            os.open(self.m.ATTEMPT,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with self.assertRaisesRegex(self.m.Refusal,'file-binding'):
            self.m.recover(True)
        self.assertEqual(quarantine.read_bytes(), foreign)

    def test_late_shared_replacement_keeps_active_sentinel_and_foreign_archive(self):
        real = self.m.rename_exchange
        saved = self.m.ROOT/'original-shared'
        def exchange(fd,source,destination):
            if source == self.m.SHARED.name:
                self.m.SHARED.rename(saved)
                self.m.SHARED.write_bytes(b'new-owner')
                self.m.SHARED.chmod(0o600)
            real(fd,source,destination)
        with mock.patch.object(self.m,'rename_exchange',exchange):
            with self.assertRaisesRegex(self.m.Refusal,'file-binding'):
                self.m.recover(True)
        self.assertTrue(self.m.SHARED.is_dir())
        with self.assertRaises(FileExistsError):
            os.open(self.m.SHARED,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        self.assertEqual((self.m.ROOT/self.m.ARCHIVE_NAMES[1]).read_bytes(),b'new-owner')
        self.assertEqual(saved.stat().st_ino,self.m.RECORDS[self.m.SHARED][1])
        self.assertEqual(len(self.m.JOURNAL.read_bytes().splitlines()),5)
        with self.assertRaisesRegex(self.m.Refusal,'file-binding'):
            self.m.recover(True)
        self.assertTrue(self.m.SHARED.is_dir())

    def test_raced_regular_owner_at_rmdir_preserved_and_resume_succeeds(self):
        real = self.m.os.rmdir
        saved = self.m.ROOT/'retained-shared-sentinel'
        def rmdir(path, **kw):
            if path == self.m.SHARED.name:
                self.m.SHARED.rename(saved)
                self.m.SHARED.write_bytes(b'fresh-owner')
                self.m.SHARED.chmod(0o600)
            real(path, **kw)
        with mock.patch.object(self.m.os,'rmdir',rmdir):
            with self.assertRaises(NotADirectoryError): self.m.recover(True)
        self.assertEqual(self.m.SHARED.read_bytes(),b'fresh-owner')
        self.assertEqual(len(self.m.JOURNAL.read_bytes().splitlines()),7)
        self.assertEqual(self.m.recover(True)['status'],'PASS_EXECUTED')
        before = self.snapshot()
        self.assertEqual(self.m.recover(True)['status'],'PASS_TERMINAL_REPLAY')
        self.assertEqual(before,self.snapshot())

    def test_fresh_owner_immediately_after_release_is_preserved(self):
        real = self.m.os.rmdir
        def rmdir(path, **kw):
            real(path, **kw)
            if path == self.m.SHARED.name:
                fd = os.open(self.m.SHARED,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                os.write(fd,b'new-ordinary-owner')
                os.close(fd)
        with mock.patch.object(self.m.os,'rmdir',rmdir):
            self.assertEqual(self.m.recover(True)['status'],'PASS_EXECUTED')
        self.assertEqual(self.m.SHARED.read_bytes(),b'new-ordinary-owner')

    def test_exchange_capability_regular_file_and_empty_directory(self):
        # Real kernel capability check, isolated in this fixture filesystem.
        sentinel = self.m.ROOT/'capability-sentinel'
        sentinel.mkdir(mode=0o700)
        sentinel_inode = sentinel.stat().st_ino
        original_inode = self.m.ATTEMPT.stat().st_ino
        fd = os.open(self.m.ROOT,os.O_RDONLY|os.O_DIRECTORY)
        try:
            self.m.rename_exchange(fd,self.m.ATTEMPT.name,sentinel.name)
            self.assertTrue(self.m.ATTEMPT.is_dir())
            self.assertEqual(self.m.ATTEMPT.stat().st_ino,sentinel_inode)
            self.assertEqual(sentinel.stat().st_ino,original_inode)
            with self.assertRaises(FileExistsError):
                os.open(self.m.ATTEMPT,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            self.m.rename_exchange(fd,self.m.ATTEMPT.name,sentinel.name)
            self.assertEqual(self.m.ATTEMPT.stat().st_ino,original_inode)
        finally:
            os.close(fd)

    def test_terminal_requires_all_exact_archives(self):
        self.completed()
        archive = self.m.ROOT / self.m.ARCHIVE_NAMES[1]
        archive.write_bytes(b'mutated-original')
        with self.assertRaisesRegex(self.m.Refusal,'file-binding'):
            self.m.recover(True)
        archive.unlink()
        with self.assertRaises(FileNotFoundError):
            self.m.recover()

    def test_release_without_durable_authorization_is_refused(self):
        real = self.m.Transaction.append
        def append(tx,plan,rows,event,index):
            real(tx,plan,rows,event,index)
            if event == 'after_exchange' and index == 0: raise Crash()
        with mock.patch.object(self.m.Transaction,'append',append):
            with self.assertRaises(Crash): self.m.recover(True)
        self.m.ATTEMPT.rmdir()
        with self.assertRaisesRegex(self.m.Refusal,'unauthorized-sentinel-release'):
            self.m.recover(True)

    def test_nonempty_or_replaced_sentinel_refused(self):
        real = self.m.Transaction.append
        def append(tx,plan,rows,event,index):
            real(tx,plan,rows,event,index)
            if event == 'after_exchange' and index == 0: raise Crash()
        with mock.patch.object(self.m.Transaction,'append',append):
            with self.assertRaises(Crash): self.m.recover(True)
        (self.m.ATTEMPT/'foreign').write_bytes(b'preserve')
        with self.assertRaisesRegex(self.m.Refusal,'sentinel-binding'):
            self.m.recover(True)
        self.assertEqual((self.m.ATTEMPT/'foreign').read_bytes(),b'preserve')

    def test_foreign_empty_directory_detected_before_rmdir_refuses(self):
        real = self.m.Transaction.append
        saved = self.m.ROOT/'preserved-original-sentinel'
        replacement = self.m.ROOT/'foreign-empty-directory'
        replacement.mkdir(mode=0o700)
        replacement_inode = replacement.stat().st_ino
        def append(tx,plan,rows,event,index):
            real(tx,plan,rows,event,index)
            if event == 'release' and index == 0:
                self.m.ATTEMPT.rename(saved)
                replacement.rename(self.m.ATTEMPT)
        with mock.patch.object(self.m.Transaction,'append',append):
            with self.assertRaisesRegex(self.m.Refusal,'sentinel-binding'):
                self.m.recover(True)
        self.assertTrue(self.m.ATTEMPT.is_dir())
        self.assertEqual(self.m.ATTEMPT.stat().st_ino,replacement_inode)
        self.assertTrue(saved.is_dir())

    def test_publisher_census_rechecked_before_every_rmdir(self):
        real = self.m.os.rmdir
        last_count = 0
        releases = []
        def rmdir(path,**kw):
            nonlocal last_count
            self.assertGreater(self.census.call_count,last_count)
            last_count = self.census.call_count
            releases.append(path)
            real(path,**kw)
        with mock.patch.object(self.m.os,'rmdir',rmdir):
            result = self.m.recover(True)
        self.assertEqual(releases,[self.m.ATTEMPT.name,self.m.SHARED.name])
        self.assertEqual(result['publisher_contract'],self.m.PUBLISHER_CONTRACT)
        self.assertEqual(json.loads(self.m.PLAN.read_bytes())['publisher_contract'],self.m.PUBLISHER_CONTRACT)

    def test_concurrent_publisher_before_release_keeps_sentinel(self):
        real = self.m.Transaction.append
        def append(tx,plan,rows,event,index):
            real(tx,plan,rows,event,index)
            if event == 'release' and index == 0:
                self.census.side_effect = self.m.Refusal('concurrent-build-or-cleanup-publisher')
        with mock.patch.object(self.m.Transaction,'append',append):
            with self.assertRaisesRegex(self.m.Refusal,'concurrent-build-or-cleanup-publisher'):
                self.m.recover(True)
        self.assertTrue(self.m.ATTEMPT.is_dir())
        self.assertEqual(len(self.m.JOURNAL.read_bytes().splitlines()),3)

    def report(self, rows):
        return {'schema':'scratch18.proc.v1','uid':0,'boot_id':self.m.BOOT_ID,
                'challenge':'challenge','caller':[42,'99'],'publishers':[],
                'snapshots':[[[1,0,'1'],[42,1,'99'],*rows],[[1,0,'1'],[42,1,'99'],*rows]]}

    def test_process_report_accepts_only_authenticated_full_shape(self):
        good = self.report([])
        self.m.validate_process_report(good, 'challenge', [42,'99'])
        for key,value in [('uid',1000),('boot_id','other'),('challenge','other'),('snapshots',[[],[]]),
                          ('caller',[43,'99']),('publishers',[[17,'99','/usr/bin/make']])]:
            bad = dict(good, **{key:value})
            with self.assertRaises(self.m.Refusal): self.m.validate_process_report(bad,'challenge',[42,'99'])

    def test_owner_reuse_known_survivor_and_recursive_descendants_refuse(self):
        for rows in ([[self.m.OWNER_PID,1,'2']],
                     [[99, self.m.OWNER_PID,'2'],[100,99,'3'],[101,100,'4']]):
            with self.assertRaises(self.m.Refusal):
                self.m.validate_process_report(self.report(rows),'challenge',[42,'99'])

    def test_bad_process_rows_refuse(self):
        for row in ([True,0,'1'],[2,-1,'1'],[2,1,'x'],[1,0,'2'],[2,1], 'bad'):
            with self.assertRaises(self.m.Refusal):
                self.m.validate_process_report(self.report([row]),'challenge',[42,'99'])

    def test_sudo_environment_fixed_and_privileged_errors_refuse(self):
        with mock.patch.dict(os.environ, {'PATH':'evil','PYTHONPATH':'evil','HOME':'evil',
                                         'SUDO_ASKPASS':'/configured/helper'}, clear=True):
            self.assertEqual(self.m.sudo_environment(), {'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C',
                                                       'SUDO_ASKPASS':'/configured/helper'})
            for rc,out,err in [(1,b'',b'failure'),(0,b'',b'warning'),(0,b'x'*(self.m.LIMIT+1),b'')]:
                result = subprocess.CompletedProcess([],rc,out,err)
                with mock.patch.object(self.m.subprocess,'run',return_value=result):
                    with self.assertRaises(self.m.Refusal): self.m.run_privileged(['/usr/bin/true'])

    def test_proc_observer_strict_read_and_parse_failures(self):
        class Reader:
            def __init__(self, value): self.value=value
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,*args): return self.value
        good = b'1 (comm with ) embedded) S '+b'0 '*18+b'1 '+b'0 '*30
        for value in (OSError('permission denied'), b'bad-stat', b'1 (x) S x',
                      good.replace(b' S ',b' ! '), good[:-2]+b'x ', good):
            def opened(path, *args):
                if path.endswith('boot_id'): return Reader(self.m.BOOT_ID)
                if path.endswith('cmdline'): return Reader(b'/usr/bin/python3\0cleanup.py\0')
                if isinstance(value,Exception): raise value
                return Reader(value)
            with mock.patch('os.geteuid',return_value=0),mock.patch('os.listdir',return_value=['1']), \
                 mock.patch('builtins.open',side_effect=opened),mock.patch('os.readlink',return_value='/usr/bin/python3'), \
                 mock.patch('sys.argv',['script','challenge','1','1']):
                if value is good:
                    namespace = {}
                    with mock.patch('builtins.print') as printed:
                        exec(self.m.PROC_CODE,namespace)
                    self.m.validate_process_report(json.loads(printed.call_args.args[0]),'challenge',[1,'1'])
                    for exe,argv in (('/usr/bin/make',['make','-j4']),('/usr/bin/python3',['python3','-I',
                                     '/repo/native-exact-scratch18-interrupt-cleanup-20261001.py']),
                                     ('/usr/bin/python3',['python3','/repo/native_rust_exact_disk_build_wrapper.py']),
                                     ('/usr/bin/docker',['docker','run','image'])):
                        self.assertTrue(namespace['publisher'](exe,argv))
                    self.assertFalse(namespace['publisher']('/usr/bin/python3',['python3','scripts/run_os_goal.py']))
                else:
                    with self.assertRaises((OSError,ValueError)):
                        exec(self.m.PROC_CODE,{})

    def test_container_absence_requires_successful_inventory(self):
        self.census_patch.stop()
        with mock.patch.object(self.m,'process_absent'), mock.patch.object(self.m,'docker',return_value=b''):
            self.assertFalse(self.m.census())
        with mock.patch.object(self.m,'process_absent'), mock.patch.object(self.m,'docker',side_effect=self.m.Refusal('failed')):
            with self.assertRaises(self.m.Refusal): self.m.census()
        self.census_patch.start()

    def test_container_exact_exited_identity_and_pid_required(self):
        self.census_patch.stop()
        row = {'ID':self.m.CONTAINER,'Names':self.m.CONTAINER_NAME,'Labels':'mckernel.owner='+self.m.OWNER_NONCE,'State':'exited'}
        item = {'Id':self.m.CONTAINER,'Name':'/'+self.m.CONTAINER_NAME,
                'Config':{'Labels':{'mckernel.owner':self.m.OWNER_NONCE}},
                'State':{'Status':'exited','ExitCode':0,'Running':False,'Pid':0,'OOMKilled':False}}
        for pid in (0,4):
            item['State']['Pid']=pid
            with mock.patch.object(self.m,'process_absent'), mock.patch.object(self.m,'docker',
                 side_effect=[json.dumps(row).encode()+b'\n',json.dumps([item]).encode()]):
                if pid == 0: self.assertTrue(self.m.census())
                else:
                    with self.assertRaises(self.m.Refusal): self.m.census()
        self.census_patch.start()

    def test_concurrent_active_container_refused(self):
        self.census_patch.stop()
        row = {'ID':'a'*64,'Names':'another-build','Labels':'','State':'running'}
        with mock.patch.object(self.m,'process_absent'),mock.patch.object(self.m,'docker',return_value=json.dumps(row).encode()+b'\n'):
            with self.assertRaisesRegex(self.m.Refusal,'concurrent-active-container'):
                self.m.census()
        self.census_patch.start()

    def test_no_caller_state_path_cli(self):
        with self.assertRaises(SystemExit): self.m.main(['--state-file','/tmp/injected'])

    def test_absent_image_lease_and_exact_work_layout_are_mandatory(self):
        before = self.snapshot()
        for path in (self.m.LEASE, self.m.OUTPUT / 'unexpected-output'):
            path.write_bytes(b'foreign')
            path.chmod(0o600)
            with self.assertRaises(self.m.Refusal):
                self.m.recover(True)
            self.assertTrue(self.m.ATTEMPT.is_file())
            self.assertTrue(self.m.SHARED.is_file())
            self.assertEqual(path.read_bytes(), b'foreign')
            path.unlink()
        for name, value in before.items():
            if value[2] is not None:
                self.assertEqual(self.snapshot()[name], value)
            else:
                # This test itself creates/removes an entry in OUTPUT.
                self.assertEqual(self.snapshot()[name][0], value[0])

    def test_successful_exited_state_is_exact(self):
        self.census_patch.stop()
        row = {'ID': self.m.CONTAINER, 'Names': self.m.CONTAINER_NAME,
               'Labels': 'mckernel.owner=' + self.m.OWNER_NONCE, 'State': 'exited'}
        original = {'Status': 'exited', 'ExitCode': 0, 'Running': False, 'Pid': 0, 'OOMKilled': False}
        for key, value in (('Status', 'created'), ('ExitCode', 1), ('ExitCode', True),
                           ('Running', True), ('Pid', 12), ('Pid', False), ('OOMKilled', True)):
            item = {'Id': self.m.CONTAINER, 'Name': '/' + self.m.CONTAINER_NAME,
                    'Config': {'Labels': {'mckernel.owner': self.m.OWNER_NONCE}},
                    'State': dict(original, **{key: value})}
            with self.subTest(key=key, value=value), mock.patch.object(self.m, 'process_absent'), mock.patch.object(self.m, 'docker',
                    side_effect=[json.dumps(row).encode(), json.dumps([item]).encode()]):
                with self.assertRaisesRegex(self.m.Refusal, 'retirement-binding'):
                    self.m.census()
        self.census_patch.start()

    def test_exact_successful_receipt_profile_and_all_fields(self):
        item = {key: {'bound': key} for key in ('Created', 'Path', 'Args', 'Image', 'Config', 'HostConfig', 'Mounts', 'State')}
        item['Mounts'] = [{'Source': '/one', 'Destination': '/first', 'RW': False,
                           'Propagation': 'rprivate', 'nested': {'field': 1}},
                          {'Source': '/two', 'Destination': '/second', 'RW': True}]
        item.update(Id=self.m.CONTAINER, Name='/' + self.m.CONTAINER_NAME)
        receipt = {'status': 'PASS', 'retired': True, 'container_id': self.m.CONTAINER,
                   'container_name': self.m.CONTAINER_NAME, 'owner_nonce': self.m.OWNER_NONCE,
                   'cleanup_separately_required': True, 'terminal_container_info': item}
        raw = json.dumps(receipt).encode()
        self.m.TERMINAL.write_bytes(raw)
        self.m.TERMINAL_SHA = self.m.digest(raw)
        self.m.TERMINAL_SIZE = len(raw)
        self.real['validate_container_profile'](item)
        for key in item:
            with self.subTest(key=key), self.assertRaisesRegex(self.m.Refusal, 'container-profile-binding'):
                self.real['validate_container_profile'](dict(item, **{key: 'replacement'}))
        self.real['validate_container_profile'](dict(item, Mounts=list(reversed(item['Mounts']))))
        first, second = item['Mounts']
        for mounts in ([dict(first, RW=True), second],
                       [dict(first, nested={'field': 2}), second],
                       [dict(first, added='field'), second],
                       [{k: v for k, v in first.items() if k != 'Propagation'}, second],
                       [first], [first, second, {'Source': '/third'}],
                       [first, first], [first, second, first]):
            with self.subTest(mounts=mounts), self.assertRaisesRegex(self.m.Refusal, 'container-profile-binding:Mounts'):
                self.real['validate_container_profile'](dict(item, Mounts=mounts))

    def test_protected_files_reject_content_hardlink_and_parent_symlink(self):
        path = self.m.EVIDENCE / 'protected'
        path.write_bytes(b'original')
        path.chmod(0o600)
        self.m.PROTECTED = {path: (8, 0o600, self.m.digest(b'original'))}
        self.real['protected_files']()
        path.write_bytes(b'changed!')
        with self.assertRaises(self.m.Refusal): self.real['protected_files']()
        path.write_bytes(b'original')
        alias = self.m.ROOT / 'hardlink'
        os.link(path, alias)
        with self.assertRaises(self.m.Refusal): self.real['protected_files']()
        alias.unlink()
        alias.symlink_to(self.m.EVIDENCE, target_is_directory=True)
        self.m.PROTECTED = {alias / path.name: (8, 0o600, self.m.digest(b'original'))}
        with self.assertRaises(OSError): self.real['protected_files']()

    def test_exact_container_removed_without_force_and_resume_after_rm_crash(self):
        present = [True]
        self.census.side_effect = lambda: present[0]
        calls = []
        def remove(args):
            calls.append(args)
            self.assertEqual(args, ['rm', '--', self.m.CONTAINER])
            present[0] = False
            raise Crash()
        with mock.patch.object(self.m, 'docker', side_effect=remove):
            with self.assertRaises(Crash): self.m.recover(True)
        self.assertEqual(calls, [['rm', '--', self.m.CONTAINER]])
        self.assertTrue(self.m.ATTEMPT.is_file())
        self.assertTrue(self.m.SHARED.is_file())
        with mock.patch.object(self.m, 'docker') as docker:
            self.assertEqual(self.m.recover(True)['status'], 'PASS_EXECUTED')
            docker.assert_not_called()

    def test_bound_client_pids_absent_in_both_privileged_snapshots(self):
        caller = [123, '456']
        for pid in self.m.WAITER_PIDS:
            for snapshot in (0, 1):
                report = {'schema': 'scratch18.proc.v1', 'uid': 0, 'boot_id': self.m.BOOT_ID,
                          'challenge': 'test', 'caller': caller, 'publishers': [],
                          'snapshots': [[[1, 0, '1'], [123, 1, '456']], [[1, 0, '1'], [123, 1, '456']]]}
                report['snapshots'][snapshot].append([pid, 1, '99'])
                with self.subTest(pid=pid, snapshot=snapshot), self.assertRaisesRegex(self.m.Refusal, 'owner-waiter'):
                    self.m.validate_process_report(report, 'test', caller)

    def log_fixture(self, raw):
        attempt = self.m.EVIDENCE / 'attempt'
        attempt.mkdir(mode=0o700)
        path = attempt / 'container.log'
        path.write_bytes(raw)
        path.chmod(0o600)

    def test_docker_stderr_only_capture_matches_owner_bytes(self):
        self.log_fixture(b'container stderr\n')
        result = subprocess.CompletedProcess([], 0, b'', b'container stderr\n')
        with mock.patch.object(self.m.subprocess, 'run', return_value=result) as run:
            self.real['capture_logs'](True, execute=False)
            self.assertFalse(self.m.CAPTURE.exists())
            self.real['capture_logs'](True, execute=True)
        self.assertEqual(self.m.CAPTURE.read_bytes(), b'container stderr\n')
        self.assertEqual(run.call_args.args[0], ['/usr/bin/sudo', '-A', '/usr/bin/docker',
                         '--host=unix:///var/run/docker.sock', 'logs', '--', self.m.CONTAINER])

    def test_docker_mixed_capture_is_stdout_then_stderr(self):
        self.log_fixture(b'out\nerr\n')
        result = subprocess.CompletedProcess([], 0, b'out\n', b'err\n')
        with mock.patch.object(self.m.subprocess, 'run', return_value=result):
            self.real['capture_logs'](True, execute=True)
        self.assertEqual(self.m.CAPTURE.read_bytes(), b'out\nerr\n')

    def test_docker_logs_nonzero_mismatch_and_combined_oversize_refuse(self):
        self.log_fixture(b'expected')
        for code, stdout, stderr, reason in ((1, b'expected', b'', 'failed-or-oversize'),
                                           (0, b'', b'wrong', 'mismatch'),
                                           (0, b'12345', b'6789', 'failed-or-oversize')):
            result = subprocess.CompletedProcess([], code, stdout, stderr)
            with self.subTest(code=code, reason=reason), mock.patch.object(self.m, 'LIMIT', 8), \
                 mock.patch.object(self.m.subprocess, 'run', return_value=result):
                with self.assertRaisesRegex(self.m.Refusal, reason):
                    self.real['capture_logs'](True, execute=True)
            self.assertFalse(self.m.CAPTURE.exists())
            self.assertTrue(self.m.ATTEMPT.is_file())
            self.assertTrue(self.m.SHARED.is_file())

    def test_nonlog_observers_still_reject_stderr(self):
        result = subprocess.CompletedProcess([], 0, b'valid', b'container stderr')
        with mock.patch.object(self.m.subprocess, 'run', return_value=result):
            for observer in (self.m.run_privileged, self.m.run_privileged_large):
                with self.assertRaisesRegex(self.m.Refusal, 'privileged-observer-failed'):
                    observer(['/usr/bin/docker', 'inspect', self.m.CONTAINER])

    def test_success_artifacts_keep_bytes_inodes_and_modes_across_cleanup(self):
        artifacts = []
        for name in ('mckernel.img', 'mckernel.img.map', 'mckernel_rust.o'):
            path = self.m.OUTPUT / 'output' / name
            path.write_bytes(('retained ' + name).encode())
            path.chmod(0o755 if name.endswith('.img') else 0o644)
            artifacts.append(path)
        self.m.PROTECTED = {p: (p.stat().st_size, p.stat().st_mode & 0o777,
                               self.m.digest(p.read_bytes())) for p in artifacts}
        self.m.PROTECTED_IDENTITIES = {p: (p.stat().st_dev, p.stat().st_ino) for p in artifacts}
        before = {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mode) for p in artifacts}
        with mock.patch.object(self.m, 'protected_files', side_effect=self.real['protected_files']):
            self.assertEqual(self.m.recover(True)['status'], 'PASS_EXECUTED')
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_mode) for p in artifacts})
        original = artifacts[0]
        replacement = original.with_suffix('.replacement')
        replacement.write_bytes(original.read_bytes())
        replacement.chmod(original.stat().st_mode & 0o777)
        replacement.replace(original)
        with self.assertRaisesRegex(self.m.Refusal, 'protected-evidence-identity'):
            self.real['protected_files']()

if __name__ == '__main__':
    unittest.main()
