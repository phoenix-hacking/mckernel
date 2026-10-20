"""Focused disposable owner protocol checks; no real Docker/root/compiler."""
import copy
import importlib.util
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import native_running_external_modules_owner as m


class FakeAdmissionClient:
    def __init__(self, log, signals):
        self.log=log;self.client_retirement_unproven=False;self.group_checks=[]
    def observe(self):
        capture=self.log.parent/'command-001';capture.mkdir()
        (capture/'status.json').write_text(json.dumps(dict(state='exited',exit_code=0,pid=900000)))
        return {'mock':'fixed observer report'}
    def check_all_client_groups(self):pass


def admitted(request, request_path, historical_observe):
    historical_observe()
    return {'historical_leases':{}}


class FakeDocker:
    def __init__(self, request, evidence, failure=None):
        self.request, self.evidence, self.failure = request, evidence, failure
        self.client_retirement_unproven = False
        self.calls = []
        self.created = False
        self.name = 'mckernel-external-' + request['nonce']
        self.cid = 'c' * 64
        self.info = profile_fixture(request, self.name, self.cid)
        self.prep = dict(closure=[dict(path='source.rs', sha256='a' * 64)])

    def call(self, args, **kwargs):
        self.calls.append(list(args))
        capture = self.evidence / ('command-%03d' % len(self.calls))
        capture.mkdir()
        (capture / 'status.json').write_text(json.dumps(dict(state='exited', exit_code=0, pid=100000+len(self.calls))))
        out = ''
        if args[:2] == ['image', 'inspect']:
            out = json.dumps([dict(Id=m.IMAGE, Architecture='amd64')])
        elif args[0] == 'create':
            self.created = True
            if self.failure == 'create-uncertain': raise RuntimeError('create reply lost')
            out = self.cid + '\n'
        elif args[0] == 'inspect':
            if self.failure == 'foreign':
                other = copy.deepcopy(self.info); other['Id'] = 'd' * 64
                out = json.dumps([other])
            else:
                out = json.dumps([self.info])
        elif args[0] == 'start':
            self.info['State'].update(Status='exited', Running=False, ExitCode=1 if self.failure=='build' else 0)
            candidate = Path(self.request['candidate_root'])
            (candidate / 'evidence').mkdir()
            artifacts = {}
            for key in ('ihk', 'ihk-smp-x86_64', 'mcctrl'):
                raw = ('module-' + key).encode();path = candidate / 'modules' / (key+'.ko');path.write_bytes(raw)
                artifacts[key] = dict(bytes=len(raw), sha256=m.sha(raw), compiler_binding=dict(sources=['source.rs']))
            receipt = dict(status='BUILD_ARTIFACT_CHECKS_PASS', make_returncode=0, preparation_sha256=m.PREPARATION_SHA,
                           source_sha256={'source.rs': 'a'*64}, application_acceptance=False, production_acceptance=False,
                           artifacts=artifacts)
            receipt.update(baseline_source_sha=m.CANDIDATE, source_candidate_sha=m.SOURCE_CANDIDATE,
                           source_provenance=dict(baseline_source_sha=m.CANDIDATE, source_candidate_sha=m.SOURCE_CANDIDATE,
                             closure_sha256=m.sha(json.dumps(receipt['source_sha256'],sort_keys=True,separators=(',',':')).encode())))
            (candidate / 'evidence/receipt.json').write_text(json.dumps(receipt))
        elif args[0] == 'wait':
            if self.failure == 'exit-mismatch': self.info['State']['ExitCode']=1
            if self.failure == 'timeout':
                self.client_retirement_unproven = True
                raise RuntimeError('docker command timed out: wait')
            out = '1\n' if self.failure == 'build' else '0\n'
        elif args[0] == 'logs': out = 'retained original driver log\n'
        elif args[0] == 'rm':
            if self.failure == 'remove': raise RuntimeError('owned removal uncertain')
            self.created = False;out = self.cid + '\n'
        elif args[0] == 'ps':
            if self.created: out = self.cid + '\n'
        return subprocess.CompletedProcess(args, 0, out, '')


def profile_fixture(request, name, cid):
    control = dict(m.host.LIMITS, Privileged=False, ReadonlyRootfs=True, CapDrop=['ALL'],
                   SecurityOpt=['no-new-privileges'], Init=True, PidMode='', IpcMode='private',
                   Devices=[], DeviceRequests=[], Binds=[], CapAdd=[], CgroupParent='',
                   Tmpfs={'/tmp':'rw,nodev,nosuid,size=256m'}, AutoRemove=False,
                   RestartPolicy={'Name':'no','MaximumRetryCount':0})
    return dict(Id=cid, Name='/'+name, Image=m.IMAGE, Path='/usr/bin/python3', Args=list(m.COMMAND),
                Config=dict(User='1000:1000', Entrypoint=['/usr/bin/python3'], Cmd=list(m.COMMAND),
                            Labels={'mckernel.owner':request['nonce']}), HostConfig=control,
                Mounts=[dict(Type='bind',Source=s,Destination=t,RW=not ro) for s,t,ro in m.mounts(request)],
                State=dict(Status='created',Running=False,Pid=0,OOMKilled=False,ExitCode=0))


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in ('ROOT','LEASE','COMMON'):
            self.patch(name, self.root if name=='ROOT' else self.root/name.lower())
        self.shared_path=self.root/'shared'
        patch=mock.patch.object(m.shared,'SHARED_HEAVY_LOCK_PATH',str(self.shared_path));patch.start();self.addCleanup(patch.stop)
        self.request=dict(nonce='b'*32, candidate_root=str(self.root/'candidate'), input_root=str(self.root/'inputs'),
                          owner_evidence_root=str(self.root/'owner'), request_path=str(self.root/'request.json'),
                          preparation=dict(path='/fixture/preparation',sha256=m.PREPARATION_SHA), timeout=1800,
                          terminal_policy='remove-owned-terminal')
        (self.root/'candidate/modules').mkdir(parents=True)
        self.evidence=self.root/'owner'
        self.authority=dict(request=dict(path=self.request['request_path'],sha256='a'*64),source_sha256={'owner':'f'*64})

    def patch(self,name,value):
        patch=mock.patch.object(m,name,value);patch.start();self.addCleanup(patch.stop)

    def run_owner(self,failure=None, archive_failure=False):
        docker=FakeDocker(self.request,self.evidence,failure)
        def acquire(request,kind):
            self.assertEqual(kind,'build')
            return m.shared._acquire_lock(self.shared_path,request,kind)
        original=m.guard._write_new
        def write(path,*args,**kwargs):
            if archive_failure and Path(path).name=='common.record.raw': raise OSError('partial archival failure')
            return original(path,*args,**kwargs)
        with mock.patch.object(m.shared,'acquire_heavy_operation',side_effect=acquire), \
             mock.patch.object(m,'bound',return_value=docker.prep), \
             mock.patch.object(m.guard,'_write_new',side_effect=write):
            result=m.run_owner(self.request,docker,None,{},self.authority)
        return result,docker

    def guarded_normal_adapter(self, condition):
        fake=FakeDocker(self.request,self.evidence)
        fd=os.open(self.root/'normal-adapter-lock',os.O_RDWR|os.O_CREAT,0o600)
        class Quarantined(BaseException):pass
        def core_call(transport,args,**kwargs):
            return fake.call(args,**kwargs)
        def members(transport,pgid):
            last=fake.calls[-1][0] if fake.calls else None
            if condition in ('survivor','unreadable') and last=='wait':
                if condition=='unreadable':raise PermissionError('normal-exit group census unreadable')
                return [900001]
            if condition=='late-old-group' and pgid==100001 and len(fake.calls)>7:
                return [900002]
            if condition=='cleanup-client' and last=='rm':return [900003]
            return []
        def acquire(request,kind):return m.shared._acquire_lock(self.shared_path,request,kind)
        with mock.patch.object(m.guard,'_development_lock',return_value=fd), \
             mock.patch.object(m,'authenticate',return_value=(self.request,dict(source_sha256={}))), \
             mock.patch.object(m,'validate_request',side_effect=admitted), \
             mock.patch.object(m,'HistoricalObserverClient',FakeAdmissionClient), \
             mock.patch.object(m,'bound',return_value=fake.prep), \
             mock.patch.object(m.shared,'acquire_heavy_operation',side_effect=acquire), \
             mock.patch.object(m.host.Docker,'call',new=core_call), \
             mock.patch.object(m.ExternalDocker,'_surviving_group_members',new=members), \
             mock.patch.object(m.guard,'quarantine_root_lock',side_effect=Quarantined) as quarantine:
            if condition=='empty':
                result=m.guarded_execute(self.root/'request','a'*64,self.root/'release','b'*64)
                quarantine.assert_not_called()
                self.assertEqual(result['status'],'PASS')
                checks=result['client_group_checks']
                self.assertTrue(checks and all(row['empty'] for row in checks))
                final_paths={row['status_path'] for row in checks if row['stage']=='final-all-clients'}
                self.assertEqual(final_paths,{str(path) for path in self.evidence.glob('command-*/status.json')})
                for path in (m.LEASE,m.COMMON,self.shared_path):self.assertFalse(path.exists())
                with self.assertRaises(OSError):os.fstat(fd)
            else:
                try:
                    with self.assertRaises(Quarantined):
                        m.guarded_execute(self.root/'request','a'*64,self.root/'release','b'*64)
                    quarantine.assert_called_once();os.fstat(fd)
                    for path in (m.LEASE,m.COMMON,self.shared_path):self.assertTrue(path.is_file())
                    self.assertFalse((self.evidence/'ownership-archive.json').exists())
                    receipt=json.loads((self.evidence/'owner-receipt.json').read_bytes())
                    self.assertFalse(receipt['retired'])
                    self.assertTrue(any(not row['empty'] for row in receipt['client_group_checks']))
                    if condition!='cleanup-client':self.assertFalse(any(call[0]=='rm' for call in fake.calls))
                    else:self.assertTrue(any(call[0]=='rm' for call in fake.calls))
                finally:os.close(fd)
        return fake

    def test_normal_joined_empty_groups_preserve_positive_guarded_path(self):
        self.guarded_normal_adapter('empty')

    def test_normal_exit_survivor_prevents_remove_and_quarantines_records(self):
        self.guarded_normal_adapter('survivor')

    def test_normal_exit_unreadable_census_prevents_remove_and_quarantines_records(self):
        self.guarded_normal_adapter('unreadable')

    def test_final_recheck_catches_earlier_normal_client_descendant(self):
        self.guarded_normal_adapter('late-old-group')

    def test_cleanup_client_survivor_prevents_record_release_and_quarantines(self):
        self.guarded_normal_adapter('cleanup-client')

    def test_exact_profile_accepts_mount_reordering(self):
        info=profile_fixture(self.request,'name','c'*64)
        info['Mounts'].reverse();m.profile(info,self.request,'name',self.request['nonce'],'c'*64)
        for key,value in [('MemorySwap',0),('Privileged',True),('Devices',[{'PathOnHost':'/dev/kvm'}])]:
            changed=copy.deepcopy(info);changed['HostConfig'][key]=value
            with self.subTest(field=key),self.assertRaises(RuntimeError):m.profile(changed,self.request,'name',self.request['nonce'],'c'*64)
        info['Mounts'].append(copy.deepcopy(info['Mounts'][0]))
        with self.assertRaises(m.Refusal):m.profile(info,self.request,'name',self.request['nonce'],'c'*64)

    def test_foreign_container_never_receives_retirement_mutation(self):
        docker=FakeDocker(self.request,self.evidence,'foreign');self.evidence.mkdir()
        transport=m.BoundDocker(docker,'mckernel-external-'+self.request['nonce'],self.request['nonce']);transport.cid='c'*64
        with self.assertRaises(m.Refusal):m.host.retire(transport,transport.name,self.request['nonce'])
        self.assertFalse(any(call[0] in ('stop','kill','rm') for call in docker.calls))

    def test_positive_build_and_owned_cleanup_archive_records_then_release(self):
        result,docker=self.run_owner()
        self.assertEqual(result['status'],'PASS');self.assertTrue(result['retired'])
        self.assertEqual(result['cleanup_status'],'PASS_OWNED_REMOVAL_AND_RECORD_RELEASE')
        self.assertFalse(result['cleanup_separately_required'])
        for path in (m.LEASE,m.COMMON,self.shared_path):self.assertFalse(path.exists())
        for name in ('lease.record.raw','common.record.raw','shared.record.raw','ownership-archive.json',
                     'record-release-authorized.json','record-release-complete.json'):
            self.assertTrue((self.evidence/name).is_file())
        self.assertFalse(docker.created)
        self.assertTrue((self.evidence/'container.log').read_text().startswith('retained original'))

    def test_compile_failure_has_honest_successful_cleanup(self):
        result,docker=self.run_owner('build')
        self.assertEqual(result['status'],'FAIL');self.assertEqual(result['build_status'],'FAIL')
        self.assertTrue(result['retired']);self.assertEqual(result['cleanup_status'],'PASS_OWNED_REMOVAL_AND_RECORD_RELEASE')
        self.assertFalse(m.LEASE.exists())

    def test_terminal_exit_mismatch_cannot_be_cleanup_success(self):
        result,docker=self.run_owner('exit-mismatch')
        self.assertFalse(result['retired']);self.assertEqual(result['status'],'FAIL')
        self.assertIn('exit code unproven',result['retirement_error'])
        self.assertFalse(any(call[0]=='rm' for call in docker.calls))
        for path in (m.LEASE,m.COMMON,self.shared_path):self.assertTrue(path.exists())

    def test_timeout_client_uncertainty_retains_all_records(self):
        result,docker=self.run_owner('timeout')
        self.assertEqual(result['status'],'FAIL');self.assertFalse(result['retired'])
        self.assertIn('timed out',result['error'])
        for path in (m.LEASE,m.COMMON,self.shared_path):self.assertTrue(path.is_file())
        self.assertFalse(any(call[0]=='rm' for call in docker.calls))

    def test_create_reply_uncertainty_can_only_retire_exact_created_container(self):
        result,docker=self.run_owner('create-uncertain')
        self.assertEqual(result['status'],'FAIL');self.assertTrue(result['retired'])
        self.assertEqual(result['cleanup_status'],'PASS_OWNED_REMOVAL_AND_RECORD_RELEASE')
        self.assertIn('reply lost',result['error'])
        self.assertFalse(any(call[0]=='start' for call in docker.calls))

    def test_removal_uncertainty_retains_all_records(self):
        result,docker=self.run_owner('remove')
        self.assertFalse(result['retired']);self.assertEqual(result['status'],'FAIL')
        for path in (m.LEASE,m.COMMON,self.shared_path):self.assertTrue(path.is_file())

    def test_partial_archive_failure_releases_no_record(self):
        result,docker=self.run_owner(archive_failure=True)
        self.assertFalse(result['retired']);self.assertIn('archival failure',result['retirement_error'])
        for path in (m.LEASE,m.COMMON,self.shared_path):self.assertTrue(path.is_file())
        self.assertTrue((self.evidence/'lease.record.raw').exists())
        self.assertFalse((self.evidence/'record-release-authorized.json').exists())

    def test_stale_common_rejected_before_any_client(self):
        m.COMMON.write_text('historical failure')
        docker=FakeDocker(self.request,self.evidence)
        with mock.patch.object(m.shared,'acquire_heavy_operation',side_effect=lambda r,k:m.shared._acquire_lock(self.shared_path,r,k)):
            with self.assertRaises(RuntimeError):m.run_owner(self.request,docker,None,{},self.authority)
        self.assertEqual(docker.calls,[]);self.assertEqual(m.COMMON.read_text(),'historical failure')

    def test_foreign_or_changed_record_blocks_archive(self):
        path=self.root/'record';record=dict(pid=os.getpid(),starttime=m.image._proc_starttime(os.getpid()),nonce='a'*32)
        path.write_text(json.dumps(record));path.chmod(0o600)
        m.record_snapshot(path,record)
        with self.assertRaises(m.Refusal):m.record_snapshot(path,dict(record,nonce='b'*32))

    def test_admission_rejection_never_constructs_docker(self):
        with mock.patch.object(m.host,'Docker') as docker,self.assertRaises(m.Refusal):
            m.validate_request({},self.root/'request.json')
        docker.assert_not_called()

    def test_full_fresh_request_admission_and_exact_negative_inputs(self):
        nonce='e'*32
        candidate=self.root/('nsd-c-'+nonce)
        inputs=self.root/('nsd-i-'+nonce)
        for path in (candidate/'modules',candidate/'home',candidate/'tmp',inputs):path.mkdir(parents=True,exist_ok=True)
        closure=[]
        for index in range(60):
            raw=('source%d'%index).encode();name='source%d.rs'%index
            (candidate/'modules'/name).write_bytes(raw)
            closure.append(dict(path=name,sha256=m.sha(raw),bytes=len(raw)))
        prep=dict(baseline_candidate=m.CANDIDATE,tool_image=m.IMAGE,closure=closure,references={})
        for index in range(13):
            raw=('reference%d'%index).encode();name='reference%d'%index
            (inputs/name).write_bytes(raw)
            prep['references'][name]=dict(retained_copy='/retained/'+name,sha256=m.sha(raw),bytes=len(raw))
        prep_path=self.root/'preparation.json';prep_raw=json.dumps(prep).encode();prep_path.write_bytes(prep_raw)
        (inputs/'preparation.json').write_bytes(prep_raw)
        driver=self.root/'driver.py';driver.write_bytes(b'# frozen driver')
        basis=self.root/'basis';basis.mkdir()
        request_path=self.root/'request.json';request_path.write_text('{}')
        request=dict(schema='mckernel.native-running-external-modules-request.v1',candidate_sha=m.CANDIDATE,image_id=m.IMAGE,
                     nonce=nonce,request_path=str(request_path),preparation=dict(path=str(prep_path),sha256=m.sha(prep_raw)),
                     driver=dict(path=str(driver),sha256=m.host.digest(driver)),input_root=str(inputs),candidate_root=str(candidate),
                     owner_evidence_root=str(self.root/('nsd-o-'+nonce)),lease_path=str(m.LEASE),
                     common_exclusion_path=str(m.COMMON),basis_identity=m.node(basis),candidate_identity=m.node(candidate),
                     input_identity=m.node(inputs),boot_id=m.BOOT,timeout=1800,disk_budget_bytes=512*2**20,
                     capture_budget_bytes=64*2**20,terminal_policy='remove-owned-terminal')
        with mock.patch.object(m,'PREPARATION',prep_path),mock.patch.object(m,'PREPARATION_SHA',m.sha(prep_raw)), \
             mock.patch.object(m,'DRIVER',driver),mock.patch.object(m,'BASIS',basis), \
             mock.patch.object(m.image,'COMMON_EXCLUSION',str(self.root/'foreign-image')), \
             mock.patch.object(m.host,'OPERATIONAL_EXCLUSION_PATH',str(self.root/'foreign-native')), \
             mock.patch.object(m,'live_admission',return_value={'mount':'bound'}), \
             mock.patch.object(m.host,'measure',return_value={'floors':'pass'}) as measured, \
             mock.patch.object(m.host,'Docker') as docker, \
             mock.patch.object(m,'validate_historical_report',return_value={}):
            self.assertEqual(m.validate_request(request,request_path,historical_observe=lambda:{})['resources'],{'floors':'pass'})
            reserve=(512+64)*2**20
            measured.assert_called_once_with('/',str(self.root),16*2**30+reserve,12*2**30+reserve)
            for key,value in [('timeout',True),('image_id','foreign'),('nonce','old'),('terminal_policy','retain-terminal'),
                               ('disk_budget_bytes',0),('lease_path','/foreign')]:
                changed=copy.deepcopy(request);changed[key]=value
                with self.subTest(field=key),self.assertRaises(m.Refusal):m.validate_request(changed,request_path)
            (candidate/'home/stale').write_text('original stale input')
            with self.assertRaises(m.Refusal):m.validate_request(request,request_path)
            (candidate/'home/stale').unlink()
            (inputs/'unbound').write_text('unexpected')
            with self.assertRaises(m.Refusal):m.validate_request(request,request_path)
            docker.assert_not_called()

    def test_exact_independent_release_source_and_execution_bindings(self):
        request=dict(nonce='b'*32,terminal_policy='remove-owned-terminal',driver=dict(sha256='f'*64))
        sources={name:'f'*64 for name in m.SOURCES}
        release=dict(schema='mckernel.native-running-external-modules-release.v1',status='PASS_EXECUTION_RELEASE',
                     execution_count=1,request=dict(path='/request',sha256='a'*64),nonce=request['nonce'],
                     historical_observer=dict(path=str(m.HISTORICAL_OBSERVER),sha256=m.HISTORICAL_OBSERVER_SHA,
                         prefix=list(m.HISTORICAL_PREFIX),timeout_seconds=30),
                     boot_id=m.BOOT,fetched_source_verified=True,terminal_policy=request['terminal_policy'],
                     source_sha256=sources,author='/author',source_review=dict(path='/source',sha256='c'*64),
                     execution_review=dict(path='/execution',sha256='d'*64))
        def bound(ref):
            if ref['path']=='/request':return request
            if ref['path']=='/release':return release
            if ref['path']=='/source':return dict(decision='PASS_SOURCE',implementation_ownership=False,
                                                reviewer='/reviewer',source_sha256=sources)
            return dict(decision='PASS_EXECUTION',implementation_ownership=False,reviewer='/reviewer',
                        reviewed_release_payload_sha256=m.sha(m.canonical({k:v for k,v in release.items() if k!='execution_review'})))
        with mock.patch.object(m,'bound',side_effect=bound),mock.patch.object(m,'safe_path',side_effect=lambda p,*a:Path(p)), \
             mock.patch.object(m.host,'digest',return_value='f'*64),mock.patch.object(m.host,'Docker') as docker:
            self.assertEqual(m.authenticate(Path('/request'),'a'*64,Path('/release'),'b'*64),(request,release))
            for key,value in [('execution_count',True),('fetched_source_verified',False),('author','/reviewer')]:
                old=release[key];release[key]=value
                with self.subTest(field=key),self.assertRaises(m.Refusal):m.authenticate(Path('/request'),'a'*64,Path('/release'),'b'*64)
                release[key]=old
            docker.assert_not_called()

    def test_all_four_root_guard_signals_use_existing_latch(self):
        import signal
        previous={number:signal.getsignal(number) for number in m.guard.DEFERRED_SIGNALS}
        with m.DeferredSignals() as latch:
            for number in previous:self.assertEqual(signal.getsignal(number),latch.receive)
            latch.receive(signal.SIGHUP,None)
            with self.assertRaises(m.host.OwnerInterrupted):latch.check()
        self.assertEqual({number:signal.getsignal(number) for number in previous},previous)

    def test_missing_guard_release_never_enters_owner(self):
        fd=os.open(self.root/'fake-root-lock',os.O_RDWR|os.O_CREAT,0o600)
        with mock.patch.object(m.guard,'_development_lock',return_value=fd), \
             mock.patch.object(m,'authenticate',side_effect=m.Refusal('not released')), \
             mock.patch.object(m,'run_owner') as owner, \
             mock.patch.object(m.guard,'quarantine_root_lock') as quarantine, self.assertRaises(m.Refusal):
            m.guarded_execute(self.root/'request','a'*64,self.root/'release','b'*64)
        owner.assert_not_called();quarantine.assert_not_called()
        with self.assertRaises(OSError):os.fstat(fd)

    def test_root_quarantine_on_postflight_uncertainty(self):
        fd=os.open(self.root/'fake-root-lock',os.O_RDWR|os.O_CREAT,0o600);self.addCleanup(os.close,fd)
        class Quarantined(BaseException):pass
        with mock.patch.object(m.guard,'_development_lock',return_value=fd), \
             mock.patch.object(m,'authenticate',return_value=(self.request,dict(source_sha256={}))), \
             mock.patch.object(m,'validate_request',side_effect=admitted), \
             mock.patch.object(m,'HistoricalObserverClient',FakeAdmissionClient), \
             mock.patch.object(m,'run_owner',return_value=dict(retired=False)), \
             mock.patch.object(m.host,'Docker',return_value=mock.Mock(client_retirement_unproven=False)), \
             mock.patch.object(m.guard,'quarantine_root_lock',side_effect=Quarantined) as hold, \
             self.assertRaises(Quarantined):
            m.guarded_execute(self.root/'request','a'*64,self.root/'release','b'*64)
        hold.assert_called_once();os.fstat(fd)

    def historical_fixture(self):
        actual_root=Path('/home/holden/mckernel-work/scratch')
        with mock.patch.object(m,'ROOT',actual_root):
            contract,raw=m.historical_source()
        rows=[]
        for suffix,inode,size,digest,pid,start,evidence in contract['LEASES']:
            rows.append(dict(path=str(self.root/('native-exact-build-lease-'+suffix+'.json')),
                             sha256=digest,device=1828,inode=inode,size=size,pid=pid,starttime=start,
                             evidence_sha256=contract['EVIDENCE_BINDINGS'][evidence][1]))
        report=dict(schema='mckernel.historical-lease-observation.v1',boot_id=m.BOOT,status='PASS_READ_ONLY',
                    leases=rows,authority=dict(historical_boot_id=contract['HISTORICAL_BOOT'],
                    historical_device=contract['HISTORICAL_DEVICE'],current_device=1828,filesystem_uuid=m.UUID,
                    block_device='/dev/loop36',uuid_proof='ext4-primary-superblock-pread-1024-at-1024'))
        metadata={row['path']:dict(device=1828,inode=row['inode'],size=row['size'],mode=stat.S_IFREG|0o600,
                    uid=0,gid=0,nlink=1,mtime_ns=1,ctime_ns=2) for row in rows}
        return contract,raw,report,metadata

    def test_exact_seven_historical_observer_report_and_metadata(self):
        contract,raw,report,metadata=self.historical_fixture()
        with mock.patch.object(m,'historical_source',return_value=(contract,raw)), \
             mock.patch.object(m,'historical_paths',return_value=[Path(p) for p in metadata]), \
             mock.patch.object(m,'historical_metadata',side_effect=lambda p:metadata[str(p)]), \
             mock.patch.object(m.image,'_proc_starttime',side_effect=FileNotFoundError):
            result=m.validate_historical_report(report)
            self.assertEqual(len(result['leases']),7)
            self.assertEqual(result['observer_sha256'],m.HISTORICAL_OBSERVER_SHA)

    def test_historical_unknown_changed_live_and_unreadable_rejected(self):
        contract,raw,report,metadata=self.historical_fixture()
        for failure in ('unknown','hash','inode','live','unreadable','boot','uuid','report'):
            changed=copy.deepcopy(report);meta=copy.deepcopy(metadata)
            paths=[Path(p) for p in metadata]
            if failure=='unknown':paths.append(self.root/'native-exact-build-lease-eighth.json')
            if failure=='hash':changed['leases'][0]['sha256']='0'*64
            if failure=='inode':meta[changed['leases'][0]['path']]['inode']+=1
            if failure=='boot':changed['boot_id']='foreign'
            if failure=='uuid':changed['authority']['filesystem_uuid']='foreign'
            if failure=='report':changed={}
            def observe_meta(p):
                if failure=='unreadable':raise PermissionError('unreadable lease')
                return meta[str(p)]
            with self.subTest(failure=failure), \
                 mock.patch.object(m,'historical_source',return_value=(contract,raw)), \
                 mock.patch.object(m,'historical_paths',return_value=paths), \
                 mock.patch.object(m,'historical_metadata',side_effect=observe_meta), \
                 mock.patch.object(m.image,'_proc_starttime',return_value=report['leases'][0]['starttime'] if failure=='live' else None), \
                 self.assertRaises((m.Refusal,PermissionError)):
                m.validate_historical_report(changed)

    def test_historical_source_digest_mismatch_rejected(self):
        with mock.patch.object(m.shared,'_stable_file_bytes',side_effect=RuntimeError('digest differs')), \
             self.assertRaises(RuntimeError):m.historical_source()

    def test_fixed_observer_transport_and_normal_group_census(self):
        _,raw,report,_=self.historical_fixture()
        evidence=self.root/'admission';evidence.mkdir()
        transport=m.HistoricalObserverClient(evidence/'observer.log',None)
        def core_call(client,args,**kwargs):
            self.assertEqual(client.command_prefix,m.HISTORICAL_PREFIX)
            self.assertEqual(args,['-c',raw.decode()]);self.assertEqual(kwargs,{'timeout':30})
            capture=evidence/'command-001';capture.mkdir()
            (capture/'status.json').write_text(json.dumps(dict(state='exited',exit_code=0,pid=987654)))
            return subprocess.CompletedProcess(args,0,json.dumps(report),'')
        with mock.patch.object(m,'historical_source',return_value=({},raw)), \
             mock.patch.object(m.host.Docker,'call',new=core_call), \
             mock.patch.object(transport,'_surviving_group_members',return_value=[]):
            self.assertEqual(transport.observe(),report)
        self.assertTrue(transport.group_checks)
        self.assertFalse(transport.client_retirement_unproven)
        with self.assertRaises(m.Refusal):transport.call(['arbitrary'])
        status={};transport._record_client_exit(-9,status)
        self.assertTrue(transport.client_retirement_unproven)
        self.assertTrue(status['client_retirement_unproven'])

    def test_normal_observer_survivor_and_unreadable_census_latch(self):
        _,raw,report,_=self.historical_fixture()
        for condition in ('survivor','unreadable'):
            evidence=self.root/condition;evidence.mkdir()
            transport=m.HistoricalObserverClient(evidence/'observer.log',None)
            def core_call(client,args,**kwargs):
                capture=evidence/'command-001';capture.mkdir()
                (capture/'status.json').write_text(json.dumps(dict(state='exited',exit_code=0,pid=987654)))
                return subprocess.CompletedProcess(args,0,json.dumps(report),'')
            def census(pid):
                if condition=='unreadable':raise PermissionError('observer census unreadable')
                return [987655]
            with self.subTest(condition=condition), \
                 mock.patch.object(m,'historical_source',return_value=({},raw)), \
                 mock.patch.object(m.host.Docker,'call',new=core_call), \
                 mock.patch.object(transport,'_surviving_group_members',side_effect=census), \
                 self.assertRaises(m.Refusal):transport.observe()
            self.assertTrue(transport.client_retirement_unproven)

    def test_observer_final_group_recheck_prevents_owned_removal(self):
        docker=FakeDocker(self.request,self.evidence)
        admission=self.root/'admission';admission.mkdir()
        observer=FakeAdmissionClient(admission/'observer.log',None);observer.observe()
        def final_census():observer.client_retirement_unproven=True
        observer.check_all_client_groups=final_census
        def acquire(request,kind):return m.shared._acquire_lock(self.shared_path,request,kind)
        with mock.patch.object(m.shared,'acquire_heavy_operation',side_effect=acquire), \
             mock.patch.object(m,'bound',return_value=docker.prep):
            result=m.run_owner(self.request,docker,None,{},self.authority,admission_client=observer)
        self.assertFalse(result['retired'])
        self.assertFalse(any(call[0]=='rm' for call in docker.calls))
        for path in (m.LEASE,m.COMMON,self.shared_path):self.assertTrue(path.is_file())

    def test_uncertain_observer_before_build_quarantines_root(self):
        fd=os.open(self.root/'observer-root-lock',os.O_RDWR|os.O_CREAT,0o600)
        class Quarantined(BaseException):pass
        class Uncertain(FakeAdmissionClient):
            def observe(client):
                client.client_retirement_unproven=True
                raise RuntimeError('observer group unreadable')
        try:
            with mock.patch.object(m.guard,'_development_lock',return_value=fd), \
                 mock.patch.object(m,'authenticate',return_value=(self.request,dict(source_sha256={}))), \
                 mock.patch.object(m,'validate_request',side_effect=admitted), \
                 mock.patch.object(m,'HistoricalObserverClient',Uncertain), \
                 mock.patch.object(m,'run_owner') as owner, \
                 mock.patch.object(m.guard,'quarantine_root_lock',side_effect=Quarantined) as hold, \
                 self.assertRaises(Quarantined):
                m.guarded_execute(self.root/'request','a'*64,self.root/'release','b'*64)
            hold.assert_called_once();owner.assert_not_called();os.fstat(fd)
            for path in (m.LEASE,m.COMMON,self.shared_path):self.assertFalse(path.exists())
        finally:os.close(fd)

    def test_poll_measure_failure_and_cleanup_signal_latch(self):
        latch=mock.Mock();poll=m.PollSignals(latch,self.request)
        with mock.patch.object(m,'measure',side_effect=m.Refusal('floor failed')),self.assertRaises(m.Refusal):poll.check()
        poll.cleaning=True;latch.reset_mock();poll.check();latch.check.assert_not_called()


if __name__=='__main__':unittest.main()
