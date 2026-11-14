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

    def run_borrowed_fixture(self,run_mutator,fail_guard=False):
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
            m.read_bounded=staged.phase.original_engine(p).read_bounded
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
            armed=[]
            def effect_guard():
                if armed: raise ValueError('fixture-launcher-stop-before-effect')
            tx=r.BorrowedTransaction.create(m,p,custody,configured,receipt,packet,archive,effect_guard)
            self.assertNotEqual(tx.rfd,custody.fd)
            self.assertTrue(tx.root_lock_inherited)
            m.validate_transaction_inherited_lock(tx.rfd)
            keeper_fd=custody.fd
            probe=os.open(m.ROOT_LOCK,os.O_RDONLY)
            try:
                with self.assertRaises(BlockingIOError):fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
                if fail_guard:
                    armed.append(True)
                    tx.mutation_authorized=True
                    with self.assertRaisesRegex(ValueError,'fixture-launcher-stop-before-effect'):tx.run_shared()
                    self.assertEqual(m.JOURNAL.read_bytes(),configured['raw_journal'])
                elif run_mutator:
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

    def test_stop_guard_prevents_shared_effect_and_keeps_keeper_copy(self):
        self.run_borrowed_fixture(False,True)

    def test_launcher_guard_reads_actual_binding_and_refuses_stop(self):
        ops=object.__new__(r.PipelineOps)
        original_read=Path.read_bytes
        proof=json.loads(r.CUTOFF_PROOF.read_bytes())
        for changed in ({'phase':'stopped'},{'stop_reason':'external stop'},{'credit_budget_error':'credit guard hold'},
                        {'thread_id':'different-thread'}):
            value=dict(thread_id=proof['thread_id'],phase='running',stop_reason=None,credit_budget_error=None)
            value.update(changed)
            def read(path):
                return json.dumps(value).encode() if path==r.LAUNCHER_STATE else original_read(path)
            with self.subTest(changed=changed),mock.patch.object(Path,'read_bytes',read),mock.patch.object(r.old.LocalOps,'clock_check'):
                with self.assertRaisesRegex(ValueError,'launcher-stopped-or-credit-service-guard-hold'):ops.clock_check()

    def test_successor_launch_changes_only_exact_clock_and_adapter_predicates(self):
        staged=self.fixture_tests();packet=staged.packet()
        packet.update(window_id=r.WINDOW_ID,custody_adapter=r.CUSTODY_ADAPTER,
                      fixed_cutoffs=list(r.FIXED_CUTOFFS))
        original=(r.old.WALL_CUTOFF,r.old.MONOTONIC_CUTOFF,r.old.BOOT_CUTOFF)
        self.assertTrue(r.require_launch(packet,'f'*64) is None)
        keeper=r.PipelineKeeper(packet,'f'*64,object())
        self.assertEqual(keeper.state,'NOT_ACQUIRED')
        self.assertEqual((r.old.WALL_CUTOFF,r.old.MONOTONIC_CUTOFF,r.old.BOOT_CUTOFF),original)
        for changed in ({'fixed_cutoffs':list(original)}, {'custody_adapter':None},
                        {'window_id':'earlier-window'}, {'old_actor':{}}):
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                r.require_launch(dict(packet,**changed),'f'*64)

    def test_new_clock_binding_ignores_expired_frozen_clock_and_honors_each_new_clock(self):
        ops=object.__new__(r.PipelineOps)
        original_read=Path.read_bytes;proof=json.loads(r.CUTOFF_PROOF.read_bytes())
        def read(path):
            if path==r.LAUNCHER_STATE:
                return json.dumps(dict(thread_id=proof['thread_id'],phase='running',stop_reason=None,
                                       credit_budget_error=None)).encode()
            return original_read(path)
        for exceeded in (None,0,1,2):
            clocks=[value-1 for value in r.FIXED_CUTOFFS]
            if exceeded is not None:clocks[exceeded]=r.FIXED_CUTOFFS[exceeded]
            with self.subTest(exceeded=exceeded),mock.patch.object(Path,'read_bytes',read), \
                 mock.patch.object(r.time,'time',return_value=clocks[0]), \
                 mock.patch.object(r.time,'monotonic',return_value=clocks[1]), \
                 mock.patch.object(r.time,'clock_gettime',return_value=clocks[2]), \
                 mock.patch.object(r.old.LocalOps,'clock_check',side_effect=AssertionError('expired clock reused')):
                if exceeded is None:ops.clock_check()
                else:
                    with self.assertRaisesRegex(ValueError,'keeper-fixed-parent-window-ended'):ops.clock_check()

    def test_outer_absence_requires_exact_typed_enoent_and_keeps_join_unknown(self):
        target=Path('/proc/1060802/stat')
        with mock.patch.object(Path,'read_bytes',side_effect=FileNotFoundError(errno.ENOENT,'gone',str(target))):
            proof=r.absent_outer()
        self.assertEqual(proof['historical_join'],'UNKNOWN')
        for effect in (PermissionError(errno.EACCES,'denied',str(target)),
                       FileNotFoundError(errno.ENOENT,'gone','/proc/other/stat')):
            with self.subTest(effect=effect),mock.patch.object(Path,'read_bytes',side_effect=effect),self.assertRaises((ValueError,PermissionError)):
                r.absent_outer()
        with mock.patch.object(Path,'read_bytes',return_value=b'exists'),self.assertRaisesRegex(ValueError,'no-longer-absent'):
            r.absent_outer()

    def retirement_receipt(self):
        return dict(schema='mckernel.current290.retirement-current-absence.v1',operation=r.ADOPT_OPERATION,
                    target={'fixture':True},pidfd_exit_ready=True,
                    original_outer=dict(pid=1060802,starttime='80309549',current_state='ABSENT_EXACT_STAT_ENOENT',
                                        historical_join='UNKNOWN_UNAVAILABLE'),
                    sudo=dict(pid=1060803,starttime='80309553',pgid=1060803,parent_before_retirement=1311),
                    protected_state_unchanged=True,only_old_root_actor_signalled=True,
                    historical_join_limitation_explicitly_accepted=True,
                    physical_observation=dict(author='/root',boot_id='fixture-boot',window_id=r.WINDOW_ID,
                         root_and_sudo_absent=True,original_groups_zero_members=True,
                         no_surviving_original_capture_control_children=True,original_capture_control_children=[]))

    def test_new_retirement_contract_never_synthesizes_historical_join(self):
        receipt=self.retirement_receipt();p=types.SimpleNamespace(ROOT_ACTOR={'fixture':True},BOOT='fixture-boot')
        with mock.patch.object(r,'current_retirement_absence',return_value=True) as observe, \
             mock.patch.object(r.phase,'require_retirement_and_joins',side_effect=AssertionError('legacy JOIN gate')):
            self.assertTrue(r.require_retirement_receipt(p,receipt,dict(window_id=r.WINDOW_ID)))
            observe.assert_called_once_with(receipt)
            receipt['original_outer']['historical_join']=True
            with self.assertRaisesRegex(ValueError,'join-must-remain-unknown'):
                r.require_retirement_receipt(p,receipt,dict(window_id=r.WINDOW_ID))

    def test_current_absence_private_proc_fixture_rejects_late_group_and_live_child(self):
        # All /proc paths and iteration are virtual: no production census runs.
        receipt=self.retirement_receipt()
        receipt['physical_observation']['original_capture_control_children']=[dict(pid=700,starttime='10')]
        root=Path('/proc');member=root/'900';statpath=member/'stat'
        def read(path):
            if path==statpath:return b'900 (fixture) '+b' '.join([b'S',b'1',str(group[0]).encode()]+[b'0']*47)
            if str(path).startswith('/proc/'):
                if live_child[0] and path==root/'700'/'stat':return b'alive'
                raise FileNotFoundError(errno.ENOENT,'gone',str(path))
            raise AssertionError(path)
        group=[900];live_child=[False]
        with mock.patch.object(Path,'read_bytes',read),mock.patch.object(Path,'iterdir',return_value=iter([member])):
            self.assertTrue(r.current_retirement_absence(receipt))
        group[0]=1060803
        with mock.patch.object(Path,'read_bytes',read),mock.patch.object(Path,'iterdir',return_value=iter([member])), \
             self.assertRaisesRegex(ValueError,'group-still-present'):
            r.current_retirement_absence(receipt)
        live_child[0]=True
        with mock.patch.object(Path,'read_bytes',read),self.assertRaisesRegex(ValueError,'process-still-present:700'):
            r.current_retirement_absence(receipt)

    def test_successor_custody_keeps_frozen_binding_and_rechecks_exact_reparent(self):
        module=types.ModuleType('private-custody')
        module.PID,module.START,module.PARENT,module.PARENT_START,module.PGID=1060806,'80309560',1060803,'80309553',1060803
        module.GRANT_SHA='grant';module.IDENTITIES=Path('/fixture/identities');module.IDENTITIES_SHA='ids'
        commands={1060806:b'/home/holden/anaconda3/bin/python3\0fixture.py\0',1060803:b'sudo\0fixture\0'}
        grant=dict(argv=['sudo','/home/holden/anaconda3/bin/python3','fixture.py'])
        ids=dict(processes=[dict(pid=pid,cmdline_sha256=hashlib.sha256(raw).hexdigest()) for pid,raw in commands.items()])
        fixturep=types.SimpleNamespace(BOOT='fixture-boot',PREPARATION=Path('/fixture'),SOURCE=Path('/fixture/source'),
                   SOURCE_SHA='source',RELEASE_SHA='release',need=r.need,strict=json.loads)
        fixturep.pinned_bytes=lambda path,*args:json.dumps(ids if path==module.IDENTITIES else grant).encode()
        calls=[]
        def process(p,pid,start,parent=None,pgid=None):
            calls.append((pid,start,parent,pgid))
            return dict(pid=pid,starttime=start,parent=parent,pgid=pgid,command=commands[pid])
        module.process=process
        frozen=mock.Mock(side_effect=AssertionError('frozen outer-alive predicate invoked'))
        module.actor_binding=frozen
        module.adoption=lambda:fixturep
        exec('def acquire_exact_standby():\n    return actor_binding(adoption())',module.__dict__)
        composed=r.successor_custody(module)
        with mock.patch.object(r.os,'geteuid',return_value=0), \
             mock.patch.object(Path,'read_text',return_value='fixture-boot'), \
             mock.patch.object(r,'absent_outer',return_value=dict(state='ABSENT_EXACT_STAT_ENOENT')) as absent:
            result=composed.acquire_exact_standby()
        self.assertIs(module.actor_binding,frozen)
        frozen.assert_not_called();self.assertEqual(absent.call_count,2)
        self.assertIn((1060806,'80309560',1060803,1060803),calls)
        self.assertIn((1060803,'80309553',1311,1060803),calls)
        self.assertEqual(result[2]['state'],'ABSENT_EXACT_STAT_ENOENT')

    def test_shared_preflight_survivor_holds_custody_without_consuming_mutation(self):
        keeper=object.__new__(r.PipelineKeeper)
        keeper.state='PHASE_BOOTSTRAP_READY_CUSTODY_HELD';keeper.packet=dict(window_id=r.WINDOW_ID)
        keeper.tx=types.SimpleNamespace(context_manifest={})
        keeper.custody=types.SimpleNamespace(verify_held_after_exit=mock.Mock())
        grant=dict(borrowed_context_sha256=r.sha(r.canonical({})),old_plan_sha256='plan',old_journal_sha256='journal')
        keeper.ops=types.SimpleNamespace(mutation_consumed=False,clock_check=mock.Mock(),
             require_operation=mock.Mock(return_value=grant),p=types.SimpleNamespace(PLAN_CANONICAL_SHA='plan',JOURNAL_SHA='journal'),
             retirement_receipt={},publish=mock.Mock())
        with mock.patch.object(r,'require_retirement_receipt',side_effect=ValueError('late-control-survivor')):
            with self.assertRaisesRegex(ValueError,'late-control-survivor'):keeper.finish_shared({})
        self.assertFalse(keeper.ops.mutation_consumed)
        keeper.ops.publish.assert_not_called()
        keeper.custody.verify_held_after_exit.assert_called_once()

    def test_full_raw_capture_including_timeout_preserves_bytes(self):
        for timeout in (False,True):
            with self.subTest(timeout=timeout):
                ops=object.__new__(r.PipelineOps);ops.capture_sequence=0
                out=b'o'*6000;err=b'e'*9000;captures={}
                def run(*args,**kwargs):
                    if timeout:raise r.subprocess.TimeoutExpired(args[0],1,output=out,stderr=err)
                    return types.SimpleNamespace(stdout=out,stderr=err,returncode=0)
                ops.engine=types.SimpleNamespace(subprocess=types.SimpleNamespace(run=run))
                ops.publish_bytes=lambda name,raw:captures.setdefault(name,raw)
                ops.publish=lambda name,value:captures.setdefault(name,value)
                ops.install_raw_capture()
                if timeout:
                    with self.assertRaises(r.subprocess.TimeoutExpired):ops.engine.subprocess.run(['/fixture-only'])
                else:ops.engine.subprocess.run(['/fixture-only'])
                self.assertEqual(captures['ROOT-COMMAND-0000.stdout'],out)
                self.assertEqual(captures['ROOT-COMMAND-0000.stderr'],err)

    def test_real_shared_only_mutator_preserves_common_quarantine_and_journal_prefix(self):
        self.run_borrowed_fixture(True)


if __name__=='__main__':unittest.main(verbosity=2)
