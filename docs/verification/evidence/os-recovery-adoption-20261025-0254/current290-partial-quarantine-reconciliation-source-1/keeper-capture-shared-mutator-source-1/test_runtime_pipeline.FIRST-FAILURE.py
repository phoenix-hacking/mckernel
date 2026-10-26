"""Functional OS/private fixture tests only; no security testing."""
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import types
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('runtime',HERE/'runtime_pipeline.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


class RuntimeTests(unittest.TestCase):
    def test_null_deadscan_fails_closed_without_install(self):
        with self.assertRaisesRegex(ValueError,'approved-deadscan-delta-unbound'):
            r.install_deadscan(types.SimpleNamespace(),None,None)

    def test_adapter_failure_retains_raw_copy_before_io(self):
        ops=object.__new__(r.PipelineOps)
        raw=types.SimpleNamespace(fd=88,pidfd=77,verified=False,error='unknown old actor',proof=None)
        ops.custody_module=types.SimpleNamespace(acquire_exact_standby=lambda:raw)
        ops.raw_hold=None
        with mock.patch.object(r,'SafeLocalCustody',side_effect=OSError('postcopy-fstat-failure')):
            hold=ops.acquire()
        self.assertIs(ops.raw_hold,raw)
        self.assertFalse(hold.verified)
        self.assertEqual((hold.fd,hold.pidfd),(88,77))
        self.assertIn('postcopy-fstat-failure',hold.error)

    def test_serve_adapter_failure_quarantines_with_raw_hold(self):
        class StopQuarantine(Exception): pass
        ops=types.SimpleNamespace(raw_hold=object(),publish=mock.Mock(),dump_diagnostics=mock.Mock(),
                                  quarantine_wait=mock.Mock(side_effect=StopQuarantine))
        keeper=object.__new__(r.PipelineKeeper);keeper.ops=ops;keeper.custody=None
        keeper.start=mock.Mock(side_effect=OSError('postcopy-adapter-setup'))
        with self.assertRaises(StopQuarantine): keeper.serve(lambda:None)
        self.assertEqual(keeper.state,'HELD_QUARANTINE')
        ops.quarantine_wait.assert_called_once()

    def fixture_tests(self):
        path=r.PREVIOUS/'test_keeper_phase_adoption.py'
        result=json.loads((r.PREVIOUS/'RESULT.json').read_bytes())
        ref=next(x for x in result['source'] if Path(x['path']).name==path.name)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),ref['sha256'])
        spec=importlib.util.spec_from_file_location('frozen23fixtures',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.HERE=HERE
        return module

    def run_borrowed_fixture(self,run_mutator):
        staged=self.fixture_tests()
        completed=[]
        class StopFixture(Exception): pass
        real_close=os.close
        deliberately_closed=set()
        def close(fd):
            try: return real_close(fd)
            except OSError as error:
                if error.errno!=errno.EBADF or fd not in deliberately_closed: raise
        def replacement(p,m,configured,custody,receipt,packet,archive):
            m._PROCESS_CENSUS_DELTA_MANIFEST={'fixture':True}
            m._DEADSCAN_DELTA_MANIFEST={'fixture':True}
            m.validate_transaction_inherited_lock=lambda fd: (_ for _ in ()).throw(AssertionError('legacy dead caller lock validation'))
            # This fixture supplies real original record metadata from private
            # files; its logical release/plan are rebuilt BEFORE adoption.
            records=[]
            for path,archive_name in zip(m.owned_record_paths(),m.ARCHIVE_NAMES):
                actual=path.parent/archive_name if path==m.ATTEMPT else path
                row=m.observe_identity(actual);row['path']=str(path);records.append(row)
            m.RELEASE['observation']['retained_exclusions']=records
            plan=json.loads(configured['raw_plan']);plan['release_sha256']=p.digest(m.canonical(m.RELEASE))
            configured['raw_plan']=m.canonical(plan)+b'\n';m.PLAN.write_bytes(configured['raw_plan'])
            m.JOURNAL.write_bytes(b'')
            seed=m.Transaction();seed.fd,seed.chain=m.directory(m.ROOT);seed.nfd,seed.namespace_chain=m.directory(m.NAMESPACE);seed.mfd=None
            rows=[]
            try:
                for event in ('before_exchange','after_exchange','release','after_release'):seed.append(plan,rows,event,0)
            finally:real_close(seed.fd);real_close(seed.nfd)
            configured['raw_journal']=m.JOURNAL.read_bytes()
            custody.proof={'old_actor':packet['old_actor'],'custody':{'lock':p.description_lock_rows(os.getpid(),custody.fd)[0]}}
            original_quarantine=m.QUARANTINE.read_bytes();original_common=(m.ATTEMPT.parent/m.ARCHIVE_NAMES[0]).stat()
            tx=r.BorrowedTransaction.create(m,p,custody,configured,receipt,packet,archive)
            self.assertNotEqual(tx.rfd,custody.fd)
            self.assertTrue(tx.root_lock_inherited)
            m.validate_transaction_inherited_lock(tx.rfd)
            keeper_fd=custody.fd
            probe=os.open(m.ROOT_LOCK,os.O_RDONLY)
            try:
                with self.assertRaises(BlockingIOError):fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
                if run_mutator:
                    m.census=lambda:False  # No real container/observer in a private filesystem fixture.
                    m.capture_logs=lambda *args,**kwargs:None
                    m.terminal_result=lambda status,plan:dict(status=status)
                    tx.mutation_authorized=True
                    result=tx.run_shared()
                    self.assertEqual(result['status'],'PASS_EXECUTED')
                    self.assertTrue(m.JOURNAL.read_bytes().startswith(configured['raw_journal']))
                    self.assertEqual(len(m.JOURNAL.read_bytes().splitlines()),9)
                    self.assertFalse(m.SHARED.exists())
                    self.assertTrue((m.SHARED.parent/m.ARCHIVE_NAMES[1]).is_file())
                else:
                    with self.assertRaisesRegex(ValueError,'shared-mutator-one-call-only'):tx.run_shared()
                    tx.close()
                    self.assertEqual(m.JOURNAL.read_bytes(),configured['raw_journal'])
                self.assertIsNone(tx.rfd)
                self.assertEqual(m.QUARANTINE.read_bytes(),original_quarantine)
                after=(m.ATTEMPT.parent/m.ARCHIVE_NAMES[0]).stat()
                for key in ('st_ino','st_dev','st_size','st_mtime_ns','st_ctime_ns'):
                    self.assertEqual(getattr(after,key),getattr(original_common,key))
                self.assertFalse(m.ATTEMPT.exists())
                os.fstat(keeper_fd)
                with self.assertRaises(BlockingIOError):fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
                # Retire only the old PRIVATE fixture's original descriptor,
                # then observe the keeper alone still retaining the same OFD.
                fn=custody.verify_held_after_exit
                closure=dict(zip(fn.__code__.co_freevars,fn.__closure__))
                holder=closure['holder'].cell_contents
                real_close(holder);deliberately_closed.add(holder)
                with self.assertRaises(BlockingIOError):fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
                real_close(keeper_fd);deliberately_closed.add(keeper_fd)
                fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
                completed.append(True)
            finally:real_close(probe)
            raise StopFixture()
        with mock.patch.object(staged.phase,'bootstrap_held_transaction',side_effect=replacement),mock.patch.object(os,'close',side_effect=close):
            with self.assertRaises(StopFixture):
                staged.BootstrapRealFileTests('test_held_bootstrap_original_plan_and_protected_files').test_held_bootstrap_original_plan_and_protected_files()
        self.assertEqual(completed,[True])

    def test_borrowed_close_preserves_real_private_keeper_lock_until_final_release(self):
        self.run_borrowed_fixture(False)

    def test_real_shared_only_mutator_preserves_common_quarantine_and_journal_prefix(self):
        self.run_borrowed_fixture(True)


if __name__=='__main__':unittest.main(verbosity=2)
