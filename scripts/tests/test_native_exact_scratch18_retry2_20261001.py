"""Disposable preparation tests; no privileged observer, build, or guest."""
import concurrent.futures
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / 'docs/verification/evidence/native-exact-scratch18-retry2-20261001.py'

def load():
    spec = importlib.util.spec_from_file_location('retry2', SOURCE)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

class Retry2Tests(unittest.TestCase):
    def setUp(self):
        self.m = m = load()
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        m.REPO = self.root / 'repo'; m.REPO.mkdir()
        m.ROOT = self.root / 'scratch'; m.ROOT.mkdir()
        for name in ('REQUEST','ATTEMPT','SHARED','LEASE','OLD_LEASE','OUTPUT','EVIDENCE',
                     'OWNER_EVIDENCE','PREP_PLAN','PREP_JOURNAL','PREP_MUTEX'):
            setattr(m, name, m.ROOT / getattr(m, name).name)
        self.request = json.loads((REPO / m.TEMPLATE).read_bytes())
        production = '/home/holden/mckernel-work/scratch'
        for key, value in list(self.request.items()):
            if isinstance(value, str): self.request[key] = value.replace(production, str(m.ROOT))
            if isinstance(value, list): self.request[key] = [x.replace(production,str(m.ROOT)) for x in value]
        self.request['host_measure_root'] = '/dev/shm'
        self.request['scratch_measure_root'] = str(m.ROOT)
        source = Path(self.request['source_root']); (source/'scripts').mkdir(parents=True)
        Path(self.request['assets_root']).mkdir()
        for name in ('native_rust_exact_build_container_owner.py','native_rust_exact_build_offline.py'):
            (source/'scripts'/name).write_bytes((REPO/'scripts'/name).read_bytes())
        self.request['image_receipt'] = str(m.ROOT/'image.json')
        for key, data in [('image_receipt',{'status':'PASS','image_id':self.request['image_id']}),
                          ('input_manifest',{'candidate_sha':self.request['candidate_sha']})]:
            raw=m.canonical(data); Path(self.request[key]).write_bytes(raw)
            self.request[key+'_sha256']=m.sha(raw)
        m.CANONICAL_SHA256=m.sha(m.canonical(self.request))
        self.bound={}
        for relative in (*m.DEPENDENCIES,m.PACKET,m.TEST):
            path=m.REPO/relative; path.parent.mkdir(parents=True,exist_ok=True)
            raw=(REPO/relative).read_bytes()
            if relative==m.TEMPLATE: raw=m.canonical(self.request)+b'\n'
            path.write_bytes(raw); self.bound[relative]=raw
        m.DEPENDENCIES={p:m.sha(self.bound[p]) for p in m.DEPENDENCIES}
        self.commit='a'*40
        archives = ('native-exact-scratch18-interrupt-attempt.archive',
                    'native-exact-scratch18-interrupt-lease.archive',
                    'native-exact-scratch18-interrupt-shared.archive')
        self.plan={'schema':'scratch18.interrupt-cleanup.v5','root':str(m.ROOT),
                   'device':m.ROOT.stat().st_dev,
                   'mutex':[m.ROOT.stat().st_dev,0], 'publisher_contract':m.PUBLISHER_CONTRACT,
                   'terminal':['inspect-terminal.json','0'*64,0,0],
                   'records':[[p.name,a,'b'*64,123,99] for p,a in zip((m.ATTEMPT,m.OLD_LEASE,m.SHARED),archives)]}
        self.artifacts={
            'plan':m.ROOT/'native-exact-scratch18-interrupt-cleanup.plan.json',
            'journal':m.ROOT/'native-exact-scratch18-interrupt-cleanup.journal.jsonl',
            'terminal':m.ROOT/'mckernel-exact-candidate-scratch-18-evidence/inspect-terminal.json',
            'mutex':m.ROOT/'native-exact-scratch18-interrupt-cleanup.mutex',
            'attempt_archive':m.ROOT/archives[0],
            'lease_archive':m.ROOT/archives[1],
            'shared_archive':m.ROOT/archives[2]}
        for key,raw in [('terminal',b'{"State":{"Running":false}}\n'),('mutex',b''),
                        ('attempt_archive',b'a'*123),('lease_archive',b'b'*99),('shared_archive',b'c'*99)]:
            path=self.artifacts[key]; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw); path.chmod(0o600)
        self.plan['records'] = [[row[0], row[1], m.sha(self.artifacts[key].read_bytes()),
                                 self.artifacts[key].stat().st_ino, self.artifacts[key].stat().st_size]
                                for row, key in zip(self.plan['records'],
                                    ('attempt_archive','lease_archive','shared_archive'))]
        self.plan['mutex'] = [m.ROOT.stat().st_dev, self.artifacts['mutex'].stat().st_ino]
        self.plan['terminal'] = ['inspect-terminal.json', m.sha(self.artifacts['terminal'].read_bytes()),
                                 self.artifacts['terminal'].stat().st_ino, self.artifacts['terminal'].stat().st_size]
        previous=m.sha(m.canonical(self.plan)); lines=[]
        events=[(event,index) for index in range(3)
                for event in ('before_exchange','after_exchange','release','after_release')]+[('complete',3)]
        for sequence,(event,index) in enumerate(events):
            body={'event':event,'index':index,'sequence':sequence,'plan_sha256':m.sha(m.canonical(self.plan)),'previous':previous}
            previous=m.sha(m.canonical(body)); lines.append(m.canonical(dict(body,hash=previous))+b'\n')
        self.artifacts['plan'].write_bytes(m.canonical(self.plan)+b'\n')
        self.artifacts['journal'].write_bytes(b''.join(lines))
        self.artifacts['plan'].chmod(0o600); self.artifacts['journal'].chmod(0o600)
        self.publish_cleanup()
        patch=mock.patch.object(m,'git',side_effect=self.git); patch.start(); self.addCleanup(patch.stop)
        # Actual wrapper loader and BuildOwner.validate; external provenance
        # and capacity observations alone use fixtures.
        self.wrapper=m.module(m.WRAPPER,self.bound[m.WRAPPER])
        self.wrapper.OPERATIONAL_EXCLUSION_PATH=str(m.ATTEMPT)
        self.wrapper.SHARED_HEAVY_LOCK_PATH=str(m.SHARED)
        original=self.wrapper._load_owner; self.owner_validations=[]
        def owner(request):
            loaded=original(request); loaded.OPERATIONAL_EXCLUSION_PATH=str(m.ATTEMPT)
            loaded.validate_git_roots=lambda root: None
            loaded.validate_memory_allocation_roots=lambda root,roots: []
            loaded.provenance.verify_inputs=lambda *args: None
            loaded.measure=lambda *args,**kwargs: {'fixture':True}
            return loaded
        self.wrapper._load_owner=owner
        self.wrapper._check_measurement=lambda value,budget: self.owner_validations.append(value)
        patch=mock.patch.object(m,'module',return_value=self.wrapper); patch.start(); self.addCleanup(patch.stop)

    def publish_cleanup(self):
        m=self.m
        self.report={'schema':'mckernel.native-exact.scratch18-interrupt-cleanup-terminal.v1',
                     'result':'PASS_TERMINAL_REPLAY','acceptance_credit':False,
                     'cleanup_source':{},
                     'publisher_contract':m.PUBLISHER_CONTRACT,
                     'execution':{'journal_events':13,'container_absent':True},
                     'archives':{key:self.record(self.artifacts[key+'_archive']) for key in ('attempt','lease','shared')},
                     'transaction_records':{key:self.record(self.artifacts[key], False) for key in ('plan','journal','mutex')},
                     'active_paths_absent':[str(m.ATTEMPT),str(m.OLD_LEASE),str(m.SHARED)],
                     'preservation':{'terminal_inspect_sha256':self.m.sha(self.artifacts['terminal'].read_bytes())},
                     'capacity':{},'next':'prepare retry2'}
        self.publish_report()

    def publish_report(self):
        m=self.m; raw=m.canonical(self.report)+b'\n'
        (m.REPO/m.CLEANUP_PUBLICATION).write_bytes(raw); self.bound[m.CLEANUP_PUBLICATION]=raw

    def record(self,path,owner=True):
        st=path.stat()
        row = dict(path=str(path),device=st.st_dev,inode=st.st_ino,
                   mode=('%04o' % stat.S_IMODE(st.st_mode)),size=st.st_size,
                   sha256=self.m.sha(path.read_bytes()))
        if owner: row.update(uid=st.st_uid,gid=st.st_gid)
        return row

    def git(self,args):
        if args[0]=='rev-parse':return (self.commit+'\n').encode()
        if args[0]=='show':return self.bound[args[1].split(':',1)[1]]
        return b''

    def snapshot(self):
        return {str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_default_readiness_is_read_only_and_does_not_invent_request(self):
        before=self.snapshot(); result=self.m.admit(self.commit)
        self.assertEqual(result['status'],'PASS_PREPARATION_READY')
        self.assertFalse(result['request_exists']); self.assertFalse(self.m.REQUEST.exists())
        self.assertEqual(before,self.snapshot()); self.assertEqual(self.owner_validations,[])

    def test_production_shape_wrapper_owner_and_durable_preparation(self):
        m=self.m; result=m.admit(self.commit,True)
        self.assertEqual(result['status'],'PASS_PREPARED'); self.assertFalse(result['execution_released'])
        self.assertEqual(m.REQUEST.read_bytes(),m.canonical(self.request)+b'\n')
        self.assertEqual(result['request_sha256'],m.sha(m.REQUEST.read_bytes()))
        self.assertEqual(self.owner_validations,[{'fixture':True}]*2)
        self.assertEqual(json.loads(m.REQUEST.read_bytes())['lease_path'],str(m.LEASE))
        for path in (m.OUTPUT,m.EVIDENCE,m.OWNER_EVIDENCE):
            self.assertEqual(list(path.iterdir()),[]); self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o700)
        self.assertEqual(json.loads(m.PREP_JOURNAL.read_bytes().splitlines()[-1])['event'],'complete')
        before=self.snapshot()
        with self.assertRaises(m.Refusal):m.admit(self.commit,True)
        self.assertEqual(before,self.snapshot())

    def test_cli_has_no_execute_and_never_execs(self):
        with mock.patch.object(self.m.os,'execv') as execute,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):self.m.main(['--release-commit',self.commit,'--execute'])
            execute.assert_not_called()
        self.assertNotIn('wrapper_argv',self.m.__dict__)

    def test_exact_live_production_lease_and_paths(self):
        m=load(); request=json.loads((REPO/m.TEMPLATE).read_bytes())
        self.assertEqual(m.check_request(request),request)
        wrapper=m.module(m.WRAPPER,(REPO/m.WRAPPER).read_bytes())
        self.assertEqual(str(m.ATTEMPT),wrapper.OPERATIONAL_EXCLUSION_PATH)
        self.assertEqual(str(m.SHARED),wrapper.SHARED_HEAVY_LOCK_PATH)
        for relative,expected in m.DEPENDENCIES.items():self.assertEqual(m.sha((REPO/relative).read_bytes()),expected)

    def test_fetched_production_cleanup_publication_schema(self):
        """The real fetched 391ead36 publication is read-only and exact-shaped."""
        import subprocess
        raw = subprocess.check_output(['/usr/bin/git', 'show',
            '391ead36:docs/verification/evidence/native-exact-scratch18-interrupt-cleanup-terminal-20261001.json'],
            cwd=str(REPO))
        report = json.loads(raw)
        self.assertEqual(report['schema'], 'mckernel.native-exact.scratch18-interrupt-cleanup-terminal.v1')
        self.assertEqual(report['result'], 'PASS_TERMINAL_REPLAY')
        self.assertFalse(report['acceptance_credit'])
        self.assertEqual(report['execution']['journal_events'], 13)
        self.assertTrue(report['execution']['container_absent'])
        self.assertEqual(set(report['archives']), {'attempt','lease','shared'})
        self.assertEqual(set(report['transaction_records']), {'plan','journal','mutex'})
        self.assertEqual([Path(p).name for p in report['active_paths_absent']],
                         [self.m.ATTEMPT.name, self.m.OLD_LEASE.name, self.m.SHARED.name])

    def test_plan_preview_and_authenticated_plan_must_be_same_bytes(self):
        original = self.m.read_regular
        calls = [0]
        plan_path = self.artifacts['plan']
        altered = json.loads(plan_path.read_bytes())
        altered['terminal'][2] += 1
        changed = self.m.canonical(altered) + b'\n'
        def raced(path, record=None):
            if Path(path) == plan_path:
                calls[0] += 1
                if calls[0] == 2:
                    return changed
            return original(path, record)
        with mock.patch.object(self.m, 'read_regular', side_effect=raced):
            with self.assertRaisesRegex(self.m.Refusal, 'cleanup-plan-raced'):
                self.m.cleanup(self.commit)

    def test_cleanup_publication_requires_fetched_exact_blob(self):
        path=self.m.REPO/self.m.CLEANUP_PUBLICATION; path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(self.m.Refusal,'publication-blob'):self.m.admit(self.commit,True)
        self.assertFalse(self.m.PREP_MUTEX.exists())

    def test_each_cleanup_artifact_identity_and_hash(self):
        for section, keys in (('archives', ('attempt','lease','shared')),
                              ('transaction_records', ('plan','journal','mutex'))):
            for key in keys:
                for field in ('device','inode','mode','uid','gid','size','sha256'):
                    if field not in self.report[section][key]: continue
                    original=self.report[section][key][field]
                    self.report[section][key][field]=original+1 if isinstance(original,int) else ('0000' if field == 'mode' else '0'*64)
                    self.publish_report()
                    with self.subTest(key=key,field=field),self.assertRaises(self.m.Refusal):self.m.cleanup(self.commit)
                    self.report[section][key][field]=original
        self.publish_report()

    def test_cleanup_absence_includes_original_lease_and_dangling_symlinks(self):
        for path in (self.m.ATTEMPT,self.m.SHARED,self.m.OLD_LEASE,self.m.LEASE):
            path.symlink_to(self.root/'missing')
            with self.assertRaisesRegex(self.m.Refusal,'required-absent'):self.m.admit(self.commit,True)
            path.unlink()
        self.report['active_paths_absent'][-1]=str(self.m.LEASE); self.publish_report()
        with self.assertRaisesRegex(self.m.Refusal,'publication-schema'):self.m.cleanup(self.commit)

    def test_cleanup_journal_incomplete_corrupt_duplicate_or_torn(self):
        path=self.artifacts['journal']; original=path.read_bytes()
        for raw in (b'',b'\n'.join(original.splitlines()[:-1])+b'\n',original[:-1],original+original.splitlines(keepends=True)[-1],original.replace(b'"complete"',b'"no"')):
            path.write_bytes(raw);self.publish_cleanup()
            with self.assertRaises(self.m.Refusal):self.m.admit(self.commit,True)
        path.write_bytes(original);self.publish_cleanup()

    def test_cleanup_plan_record_order_required(self):
        self.plan['records'].reverse();self.artifacts['plan'].write_bytes(self.m.canonical(self.plan)+b'\n');self.publish_cleanup()
        with self.assertRaisesRegex(self.m.Refusal,'plan-records'):self.m.cleanup(self.commit)

    def test_fresh_targets_and_symlink_roots_reject_without_mutation(self):
        m=self.m
        for path in (m.REQUEST,m.OUTPUT,m.EVIDENCE,m.OWNER_EVIDENCE,m.PREP_MUTEX,m.PREP_PLAN,m.PREP_JOURNAL):
            path.symlink_to(self.root/'missing');before=self.snapshot()
            with self.assertRaises(m.Refusal):m.admit(self.commit,True)
            self.assertEqual(before,self.snapshot());path.unlink()
        link=self.root/'scratch-link';link.symlink_to(m.ROOT,target_is_directory=True)
        with self.assertRaises(OSError):m.directory(link)

    def test_request_replacement_is_refused_and_retained(self):
        m=self.m; original=m.Preparation.create
        def create(op,path,data):
            original(op,path,data)
            if path==m.REQUEST:
                path.rename(path.with_suffix('.old'));path.write_bytes(data)
        with mock.patch.object(m.Preparation,'create',create),self.assertRaises(m.Refusal):m.admit(self.commit,True)
        self.assertTrue(m.REQUEST.exists());self.assertNotIn(b'"complete"',m.PREP_JOURNAL.read_bytes())

    def test_root_replacement_refused_before_transaction_write(self):
        m=self.m; op=m.Preparation(); old=m.ROOT.with_name('old-scratch');m.ROOT.rename(old);m.ROOT.mkdir()
        try:
            with self.assertRaisesRegex(m.Refusal,'root-replaced'):op.create(m.PREP_PLAN,b'bad')
        finally:op.close()
        self.assertFalse((old/m.PREP_PLAN.name).exists())

    def test_ancestor_replacement_with_same_root_inode_refused(self):
        m=self.m; parent=self.root/'parent';parent.mkdir()
        m.ROOT=parent/'child';m.ROOT.mkdir();op=m.Preparation()
        old=self.root/'old-parent';parent.rename(old);parent.mkdir();(old/'child').rename(m.ROOT)
        try:
            with self.assertRaisesRegex(m.Refusal,'root-replaced'):op.pinned()
        finally:op.close()

    def test_symlink_and_hardlink_cleanup_artifacts_refused(self):
        path=self.artifacts['plan'];original=path.with_suffix('.retained');path.rename(original)
        path.symlink_to(original)
        with self.assertRaises(OSError):self.m.cleanup(self.commit)
        path.unlink();os.link(original,path)
        with self.assertRaisesRegex(self.m.Refusal,'artifact-shape'):self.m.cleanup(self.commit)

    def test_late_cleanup_or_source_change_refused(self):
        for target in ('cleanup','sources'):
            case=Retry2Tests();case.setUp()
            try:
                m=case.m;original=getattr(m,target);calls=[0]
                def changing(*args):
                    calls[0]+=1
                    if calls[0]>=2:raise m.Refusal('late-change')
                    return original(*args)
                with mock.patch.object(m,target,side_effect=changing),self.assertRaisesRegex(m.Refusal,'late-change'):
                    m.admit(case.commit,True)
                self.assertFalse(m.REQUEST.exists());self.assertTrue(m.PREP_PLAN.exists())
            finally:case.doCleanups()

    def test_every_crash_boundary_is_fail_closed(self):
        for count in range(1,9):
            with self.subTest(count=count):
                case=Retry2Tests();case.setUp()
                try:
                    m=case.m; original=m.Preparation.event; calls=[0]
                    def event(op,event,path):
                        original(op,event,path);calls[0]+=1
                        if calls[0]==count:raise RuntimeError('simulated-crash')
                    with mock.patch.object(m.Preparation,'event',event),self.assertRaises(RuntimeError):m.admit(case.commit,True)
                    before=case.snapshot()
                    with self.assertRaises(m.Refusal):m.admit(case.commit,True)
                    self.assertEqual(before,case.snapshot())
                finally:case.doCleanups()

    def test_concurrent_preparation_has_one_winner(self):
        m=self.m
        def run():
            try:return m.admit(self.commit,True)['status']
            except (ValueError,OSError):return 'REFUSED'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:run(),range(2)))
        self.assertEqual(sorted(results),['PASS_PREPARED','REFUSED'])

    def test_short_write_and_zero_progress(self):
        m=self.m;real=m.os.write
        with mock.patch.object(m.os,'write',side_effect=lambda fd,data:real(fd,data[:7])):
            self.assertEqual(m.admit(self.commit,True)['status'],'PASS_PREPARED')
        with mock.patch.object(m.os,'write',return_value=0),self.assertRaisesRegex(m.Refusal,'write-no-progress'):
            m.write_all(-1,b'abc')

    def test_wrapper_rejection_retains_partial_without_request(self):
        self.wrapper._check_measurement=mock.Mock(side_effect=ValueError('insufficient-capacity'))
        with self.assertRaisesRegex(ValueError,'insufficient-capacity'):self.m.admit(self.commit,True)
        self.assertTrue(self.m.PREP_PLAN.exists());self.assertFalse(self.m.REQUEST.exists())
        with self.assertRaises(self.m.Refusal):self.m.admit(self.commit,True)

    def test_sources_and_template_fetched_exact(self):
        m=self.m
        for relative in (*m.DEPENDENCIES,m.PACKET,m.TEST):
            path=m.REPO/relative;raw=path.read_bytes();path.write_bytes(raw+b'changed')
            with self.subTest(relative=relative),self.assertRaises(m.Refusal):m.sources(self.commit)
            path.write_bytes(raw)
        for invalid in ('a','A'*40,'0'*40):
            with self.assertRaises(m.Refusal):m.sources(invalid)

if __name__=='__main__':unittest.main()
