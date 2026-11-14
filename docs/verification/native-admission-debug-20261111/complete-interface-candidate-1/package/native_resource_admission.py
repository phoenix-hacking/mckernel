"""One named native physical-resource admission, separate from account data.

No import/constructor is an execution entrypoint. The verified supervisor owns
this object before initialization. It requires its genuine RootLease, a fresh
owning-controller session, the exact root-pinned reviewed native configuration,
the real DiagnosticOwner preflight and the actual kernel development FLOCK.
Only this new operation may be retired; retained historical scopes stay held.
"""
import fcntl
import base64
import sys
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import time
import native_current_owner
import root_bootstrap
import graph_producer
import runtime_binding

GIB=1024**3
# Existing real DiagnosticOwner.run/start and post-start command bounds.
OWNER_DEADLINE_SECONDS=360
POST_START_STATUS_SECONDS=5+4*10  # wait + three exact ps queries + inspect
FINAL_CAPTURE_SECONDS=3*3        # final wait, logs, inspect
OWNED_CLEANUP_SECONDS=15         # original bounded _cleanup attempt
RETIREMENT_RESERVE_SECONDS=FINAL_CAPTURE_SECONDS+OWNED_CLEANUP_SECONDS
COMPLETION_RESERVE_SECONDS=POST_START_STATUS_SECONDS+RETIREMENT_RESERVE_SECONDS
UNKNOWN=[]
EXPECTED=dict(mckernel_image='c66492d44e2e71a072114f637cd04dff5feb77bd2216c42ef69f7a56944c7a5f',
 payload='77e8dfe6f8089f18b22524ad474e057cb061d67501f9e9fdb4f391dd4790f45d',
 libc='b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4',
 loader='0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b')
MODULES=('04f5d3e0dbf0c70b7ff5aeb281fabda310751bc45c4916cb582575cf3f81155e',
 'ae67f463920ae6267710624139c56ef5dcfa8d1c60f4fc1a42f0e52604066696',
 'dc46a4f552776d6f9200cbdc8127882ea3f5d69d119f3e5b00672dce234eabcc')
CGROUP={'/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us':'100000',
 '/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us':'400000',
 '/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes':'12884901888',
 '/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy':'1',
 '/sys/fs/cgroup/pids/mckernel-dev/pids.max':'512'}
MEMBERS=('/sys/fs/cgroup/cpu/mckernel-dev/tasks',
 '/sys/fs/cgroup/memory/mckernel-dev/tasks','/sys/fs/cgroup/pids/mckernel-dev/tasks')


def need(ok,msg):
    if not ok:raise RuntimeError(msg)


def read_kernel(path):
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        raw=os.read(fd,4097);need(len(raw)<=4096,'kernel resource bound: '+path)
        return raw.decode('ascii').strip()
    finally:os.close(fd)


def physical_snapshot(require_empty):
    profile={path:read_kernel(path) for path in CGROUP}
    need(profile==CGROUP,'actual native cgroup profile differs')
    members={path:read_kernel(path) for path in MEMBERS}
    for path,value in members.items():
        need(all(x.isdigit() and int(x)>0 for x in value.split()),'native member record malformed: '+path)
    usage=int(read_kernel('/sys/fs/cgroup/memory/mckernel-dev/memory.usage_in_bytes'))
    pids=int(read_kernel('/sys/fs/cgroup/pids/mckernel-dev/pids.current'))
    need(usage>=0 and pids>=0,'native counters malformed')
    if require_empty:
        # Actual readable kernel counters/membership, never missing-path=>free.
        need(all(not x for x in members.values()) and usage==0 and pids==0,
             'native scope not positively idle')
    return dict(profile=profile,members=members,memory_usage_bytes=usage,pids=pids)


def file_identity(fd):
    s=os.fstat(fd)
    return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,mode=stat.S_IMODE(s.st_mode),nlink=s.st_nlink)


def current_flock(fd):
    st=os.fstat(fd);found=[]
    for line in Path('/proc/locks').read_text().splitlines():
        f=line.split()
        if len(f)<8 or f[1:4]!=['FLOCK','ADVISORY','WRITE']:continue
        major,minor,inode=f[5].split(':')
        if (int(major,16),int(minor,16),int(inode))==(os.major(st.st_dev),os.minor(st.st_dev),st.st_ino):
            found.append(int(f[4]))
    need(found==[os.getpid()],'actual current native development-lock owner differs')
    return found[0]


KIND='mckernel-native-signal-operation-v1'


class VerifiedNativeRequest:
    """Held root-pinned reviewed request, not a caller dict or an account grant.

    Root's later operation-specific review/admission must issue this immutable
    one-shot file; merely writing a source candidate issues nothing. Both the
    watchdog and supervisor independently hold and compare these exact bytes.
    """
    def __init__(self,path,expected_sha):
        self.fd=None;self.path=path;self.sha256=expected_sha
        self.fd,self.raw=root_bootstrap.pinned_root_file(path,expected_sha)
        self.identity=file_identity(self.fd)
        self.cfg=json.loads(self.raw,object_pairs_hook=native_current_owner.unique,
          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite native request')))
        cfg=self.cfg
        need(type(cfg) is dict and set(cfg)=={'kind','nonce','boot_id','caps','watchdog_pid',
          'watchdog_birth','runtime','owner','native','operation_root'},'named native request fields')
        need(cfg['kind']==KIND,'only named native signal request selected')
        root=cfg['operation_root']
        need(type(root) is dict and set(root)=={'device','inode','uid','mode','nlink'} and
             root['uid']==0 and root['mode']==0o700 and
             type(root['device']) is int and root['device']>=0 and
             all(type(root[k]) is int and root[k]>0 for k in ('inode','nlink')),
             'exact one-shot actual operation-root identity required')
        for k in ('nonce',):
            need(type(cfg[k]) is str and len(cfg[k])==64 and all(c in '0123456789abcdef' for c in cfg[k]),'fresh native nonce')
        need(type(cfg['watchdog_pid']) is int and cfg['watchdog_pid']>1 and
          type(cfg['watchdog_birth']) is str and cfg['watchdog_birth'].isdigit(),'native watchdog identity')
        need(type(cfg['runtime']) is dict and set(cfg['runtime'])=={'path','sha256'},'native runtime pin')
        need(type(cfg['owner']) is dict and set(cfg['owner'])=={'path','sha256'},'genuine owner source pin')
        runtime_binding.verify_current(cfg['runtime']['path'],cfg['runtime']['sha256'])
        self.verify()

    def verify(self):
        need(self.fd is not None and file_identity(self.fd)==self.identity,'native request fd changed')
        fd,raw=root_bootstrap.pinned_root_file(self.path,self.sha256)
        try:need(file_identity(fd)==self.identity and raw==self.raw,'native request path changed')
        finally:os.close(fd)
        cfg=self.cfg;caps=cfg['caps']
        need(type(caps) is dict and set(caps)=={'utc','boot','mono','boot_id'} and
          caps['boot_id']==cfg['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'native request current boot')
        for k,now in [('utc',time.time()),('boot',time.clock_gettime(time.CLOCK_BOOTTIME)),('mono',time.monotonic())]:
            need(type(caps[k]) in (int,float) and math.isfinite(caps[k]) and now<caps[k]<=now+600,
                 'native one-shot clock domain expired or unbounded')
        # Do not trust a mutated decoded dict, even in this owning process.
        need(json.loads(self.raw,object_pairs_hook=native_current_owner.unique)==cfg,'native request decoded fields changed')
        return self


class VerifiedResourceScope:
    """Consume exact7f7 reviewed arithmetic, never an approved/native-free flag.

    Native12 is static nonadditive capacity. Prior678ab already retired only
    R3 process-memory4; R3 persistent/source, scratch21 and mutex27:4 remain.
    Fresh actual native claim/FLOCK/kernel/current-account checks are separate.
    """
    FACTS_SHA='7f7f4f58c733d6f42d631a1821241e3a632b823e981236038b03e675bdd4e362'
    def __init__(self,binding,request):
        self.fd=None;self.source_fds=[]
        need(type(binding) is dict and set(binding)=={'path','sha256'} and
          binding['sha256']==self.FACTS_SHA,'exact reviewed current retained-scope facts missing')
        self.fd,self.raw=root_bootstrap.pinned_root_file(binding['path'],binding['sha256'])
        self.binding=dict(binding);self.request=request
        value=json.loads(self.raw,object_pairs_hook=native_current_owner.unique)
        need(value.get('schema')=='mckernel.native-retained-memory-scope-source-review.v1',
             'actual source-scope review schema')
        facts=value['source_input_facts_for_actual_native_admission']
        rows=facts['retained_memory_rows']
        need([(r['id'],r['kind'],r['bytes'],r['status']) for r in rows]==[
          ('original_install_dfd0a93f','retained_memory_charge',4*GIB,'UNKNOWN_RETAINED'),
          ('V2_unknown_parent','retained_memory_charge',2*GIB,'UNKNOWN_RETAINED'),
          ('native_cpu2_5','retained_native_capacity',12*GIB,'HELD_CAPACITY_NOT_CURRENT_OPERATION_PROOF')],
          'actual remaining install4/V2_2/staticnative12 rows differ')
        need(facts['retained_total_bytes']==18*GIB and
          facts['retained_other_than_native_capacity_bytes']==6*GIB,
          'actual retained18 arithmetic differs')
        r3=facts['R3_memory_row']
        need(r3['issued_bytes']==4*GIB and r3['current_process_charge_bytes']==0 and
          r3['disposition_source']['sha256']=='678ab265971ff032a82e204d1739ab6feb56d3969b607403bacf443a8fb0f231',
          'prior R3 process-only disposition changed')
        held=facts['persistent_nonmemory_UNKNOWN_rows']
        need([(r['id'],r['status']) for r in held]==[
          ('R3_nonce8c12_persistent_custody','UNKNOWN_PRESERVED'),
          ('R3_source_exclusion','UNKNOWN_PRESERVED'),('scratch21','HELD_PRESERVED'),
          ('mutex27:4','HELD_PRESERVED')] and held[0]['additional_memory_bytes'] is None,
          'persistent/source/scratch/mutex outcomes must remain unchanged')
        # The static native pool is counted once. This is only accounting; no
        # resource state, source permission or current operation follows from it.
        self.required_bytes=facts['retained_total_bytes']+4*GIB+4*GIB
        self.value=value

    def verify(self):
        self.request.verify()
        fd,raw=root_bootstrap.pinned_root_file(self.binding['path'],self.binding['sha256'])
        try:need(file_identity(fd)==file_identity(self.fd) and raw==self.raw,'resource scope changed')
        finally:os.close(fd)
        return self


class NativeCompletion:
    """Minted only from this admission's real terminal owner, never caller JSON."""
    def __init__(self,admission,owner,result):
        need(type(admission) is NativeAdmission and owner is admission.owner and
          admission.state=='RUNNING','native terminal owner binding')
        need(owner.absent and owner.lock is None and (not owner.create_issued or owner.create_completed) and
          not owner.backend.children.pending and not owner.backend.children.final_reap_records,
          'actual native owner not positively retired')
        self.admission,self.owner,self.result=admission,owner,result
        self.nonce=admission.nonce;self.physical=physical_snapshot(True)
        self.functional_pass=owner.failure is None


class NativeAdmission:
    def __init__(self,root_fd,lease,request,owner_module):
        self.state='INITIALIZING';self.root_fd=root_fd;self.lease=lease
        self.client=None;self.owner=None;self.development_fd=None;self.claim_fd=None;self.package_fd=None;self.resource_scope=None
        self.open_fds=[];self.loader_fds=[];self.source_members=[];self.failure=None;self.completion=None
        need(os.getuid()==os.geteuid()==0,'actual root native owner required')
        need(type(lease) is graph_producer.RootLease and lease.root_fd==root_fd,
             'genuine inherited RootLease required')
        need(type(request) is VerifiedNativeRequest,'root-pinned typed native request required')
        request.verify();self.request=request;cfg=request.cfg
        need(cfg['watchdog_pid']==os.getppid() and
          native_current_owner.birth(os.getppid())==cfg['watchdog_birth'] and
          lease.nonce==cfg['nonce'],'actual inherited watchdog/request/nonce join')
        actual_root=file_identity(root_fd)
        need(actual_root==cfg['operation_root'],'request/actual operation root differs')
        lease.verify();self.nonce=lease.nonce;self.cfg=cfg;self.config_sha=request.sha256
        self.caps=dict(cfg['caps']);self.boot_id=cfg['boot_id']
        need(owner_module.__file__==cfg['owner']['path'] and
          hashlib.sha256(Path(owner_module.__file__).read_bytes()).hexdigest()==cfg['owner']['sha256'],
          'actual verified owner module differs')
        spec=cfg['native']
        need(type(spec) is dict and set(spec)=={'manifest','attempt_parent','source_manifest',
          'source_package','profile','scope','controller','deadline_seconds'},'native config shape')
        self.deadline_seconds=spec['deadline_seconds']
        need(type(self.deadline_seconds) is int and self.deadline_seconds==OWNER_DEADLINE_SECONDS,
             'exact supported native owner duration360 required')
        need(spec['profile']=={'cpus':[2,3,4,5],'memory_bytes':12*GIB,'memory_swap_bytes':12*GIB,
          'pids':512,'network':'none','heavy_jobs':1},'exact native execution profile')
        # A static capacity label is not an allocated operation. The new Root-
        # reviewed request selects the existing reserved pool; old install4/V2,
        # scratch21/mutex/UNKNOWN are neither reused nor released by this object.
        self.resource_scope=VerifiedResourceScope.__new__(VerifiedResourceScope)
        self.resource_scope.__init__(spec['scope'],request)
        self._clocks(required_seconds=self.deadline_seconds+COMPLETION_RESERVE_SECONDS)
        package=spec['source_package']
        need(type(package) is dict and set(package)=={'path','device','inode','uid','mode'},
             'actual immutable package generation identity')
        need(owner_module.normal_source_generation(package['path']),
             'named immutable package path')
        import inplace_custody
        self.package_fd=inplace_custody.open_exact(package['path'])
        self.open_fds.append(self.package_fd)
        ps=os.fstat(self.package_fd)
        need(stat.S_ISDIR(ps.st_mode) and ps.st_uid==0 and stat.S_IMODE(ps.st_mode)&0o022==0 and
             inplace_custody.flags(self.package_fd)&inplace_custody.IMMUTABLE and
             {'device':ps.st_dev,'inode':ps.st_ino,'uid':ps.st_uid,'mode':stat.S_IMODE(ps.st_mode)}==
             {k:package[k] for k in ('device','inode','uid','mode')},'named source generation changed')
        self._registered_loader()
        controller=spec['controller']
        need(type(controller) is dict and set(controller)=={'path','pid','birth','source_sha256'},
             'actual owning controller channel config')
        self.client=native_current_owner.CurrentOwnerSession.__new__(native_current_owner.CurrentOwnerSession)
        self.client.__init__(controller['path'],controller['pid'],controller['birth'],
                             controller['source_sha256'],self.nonce,self.config_sha)
        self._clocks(required_seconds=self.deadline_seconds+COMPLETION_RESERVE_SECONDS)
        self._capacity()
        self.initial=physical_snapshot(True)
        manifest=spec['manifest']
        need(type(manifest) is dict and set(manifest)=={'path','sha256'},'native manifest ref')
        self.owner_module=owner_module
        # Real canonical owner/preflight validates all artifacts, source hashes,
        # staging/finalmap/QEMU inputs. No dummy provider/backend is accepted.
        self.owner=_bound_owner(owner_module,self,spec['attempt_parent'],manifest)
        self.retained=owner_module.DiagnosticOwner._preflight(self.owner)
        self._named_manifest(self.owner.manifest)
        self.client.revalidate()
        self._clocks(required_seconds=self.deadline_seconds+COMPLETION_RESERVE_SECONDS)
        self.claim_fd=os.open('NATIVE-CLAIM-'+self.nonce+'.jsonl',
          os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
        self.open_fds.append(self.claim_fd)
        self._record('REGISTERED_BEFORE_RESOURCE_ACQUISITION')
        self._clocks(required_seconds=self.deadline_seconds+COMPLETION_RESERVE_SECONDS)
        owner_module.DiagnosticOwner._acquire(self.owner)
        self.development_fd=self.owner.lock;self.development_identity=file_identity(self.development_fd)
        need(self.development_identity['uid']==0 and self.development_identity['nlink']==1,
             'real development FLOCK identity')
        current_flock(self.development_fd);physical_snapshot(True)
        self.state='CLAIMED';self._record('HELD_ACTUAL_EXCLUSIVE_NEW_OPERATION')

    def _registered_loader(self):
        # These are the actual normal supervisor_argv positions, not a new
        # caller-selected sys.path or an unregistered source-loader fallback.
        need(len(sys.argv)==5 and sys.argv[0]=='-c','registered supervisor inline argv')
        fd,raw=root_bootstrap.pinned_root_file(sys.argv[2],sys.argv[3]);self.loader_fds.append(fd)
        loader=json.loads(raw,object_pairs_hook=native_current_owner.unique)
        need(type(loader) is dict and set(loader)=={'kind','modules','extra_files',
          'operation_config_path','operation_config_sha','runtime'} and
          loader['kind']=='mckernel-native-signal-loader-v1' and
          loader['operation_config_path']==self.request.path and
          loader['operation_config_sha']==self.request.sha256 and loader['runtime']==self.cfg['runtime'],
          'actual immutable loader/request binding')
        original=('ownership_latch','custody_protocol_v2','graph_observations','pidfd_compat','runtime_binding',
          'pidfd_custody','deferred_fork','inplace_custody','immutable_epoch','adapter','materializer',
          'source_freeze','split_inventory','union_server_guarded','graph_producer','graph_server',
          'operation_supervisor','supervisor_entry')
        named=('native_current_owner','native_diagnostic_container_owner','native_resource_admission',
          'native_source_binding','compositor','operation_watchdog')
        need(type(loader['modules']) is dict and set(loader['modules'])==set(original+named),
             'complete actual original18 plus named dependencies required')
        need(loader['modules']['supervisor_entry']['path']==sys.argv[4], 'actual selected entry source')
        for name in original+named:
            ref=loader['modules'][name]
            need(type(ref) is dict and set(ref)=={'path','sha256'},'actual module source pin')
            mf,_=root_bootstrap.pinned_root_file(ref['path'],ref['sha256']);self.loader_fds.append(mf)
            need(name in sys.modules and sys.modules[name].__file__==ref['path'],
                 'actual verified module origin differs: '+name)
            self.source_members.append(ref['path'])
        local=os.path.dirname(loader['modules']['materializer']['path'])
        extras=loader['extra_files']
        need(set(extras)=={os.path.join(local,n) for n in
          ('verify_scripts_fd.py','verified_owner_loader.py','union_owner.py','root_owner_entry.py')},
          'exact registered checker/parent lineage source set')
        for path,sha in extras.items():
            ef,_=root_bootstrap.pinned_root_file(path,sha);self.loader_fds.append(ef);self.source_members.append(path)
        actual_bootstrap=base64.b64decode(sys.argv[1],validate=True)
        bootstrap_path=os.path.join(self.cfg['native']['source_package']['path'],'root_bootstrap.py')
        bf,body=root_bootstrap.pinned_root_file(bootstrap_path,hashlib.sha256(actual_bootstrap).hexdigest())
        self.loader_fds.append(bf);self.source_members.append(bootstrap_path)
        need(body==actual_bootstrap,'executed parent-verified bootstrap source differs')
        self.loader=loader;self.loader_sha256=sys.argv[3]

    def _clocks(self,required_seconds=0):
        need(type(required_seconds) in (int,float) and math.isfinite(required_seconds) and
             required_seconds>=0,'finite required native work allowance')
        self.request.verify()
        need(type(self.caps) is dict and set(self.caps)=={'utc','boot','mono','boot_id'} and
          self.caps['boot_id']==self.boot_id==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'native current boot/caps')
        remaining=[]
        for k,now in [('utc',time.time()),('boot',time.clock_gettime(time.CLOCK_BOOTTIME)),('mono',time.monotonic())]:
            need(type(self.caps[k]) in (int,float) and math.isfinite(self.caps[k]) and
              now<self.caps[k]<=now+600 and now+required_seconds<=self.caps[k],
              'native finite one-shot clock/work allowance')
            remaining.append(self.caps[k]-now)
        return min(remaining)

    def work_timeout(self,timeout,start=False):
        need(type(timeout) in (int,float) and math.isfinite(timeout) and timeout>0,
             'finite native command timeout')
        required=(self.deadline_seconds+COMPLETION_RESERVE_SECONDS if start else
                  RETIREMENT_RESERVE_SECONDS)
        left=self._clocks(required_seconds=required)
        # Reserve exact owned capture+cleanup time. The real owner still owns
        # command timeout/retirement and the watchdog retains all uncertainty.
        allowed=min(timeout,left-RETIREMENT_RESERVE_SECONDS)
        need(allowed>0,'native work allowance exhausted before command')
        return allowed

    def _capacity(self):
        rows=[x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')]
        self.resource_scope.verify()
        required=self.resource_scope.required_bytes
        need(required>=26*GIB and len(rows)==1 and int(rows[0].split()[1])*1024>=required,
             'actual shared/native memory headroom for every retained scope')
        for path,floor in [('/home/holden/mckernel',16*GIB),('/home/holden/mckernel-work/scratch',12*GIB)]:
            fs=os.statvfs(path);need(fs.f_bavail*fs.f_frsize>=floor,'actual host/scratch floor: '+path)

    def _named_manifest(self,manifest):
        for name,sha in EXPECTED.items():need(manifest['artifacts'][name]['sha256']==sha,'matched native artifact: '+name)
        need(tuple(x['sha256'] for x in manifest['modules'])==MODULES,'matched native099 modules')
        need(manifest['payload']['argv']==['/bin/mcexec','-t','1','0','/apps/signal.alternate-repeat'] and
          manifest['payload']['cwd']=='/case/work' and manifest['payload']['env']==
          {'PATH':'/usr/bin:/bin','COKERNEL_PATH':'/apps','LANG':'C','LC_ALL':'C','TZ':'UTC'},
          'only exact selected signal operation')

    def _record(self,status):
        row=dict(status=status,nonce=self.nonce,config_sha256=self.config_sha,
          scope='CURRENT_NAMED_NATIVE_OPERATION_ONLY',native_pool_reservation='RETAINED',
          root_lease_sha256=self.lease.lease_sha256,pid=os.getpid(),
          birth=native_current_owner.birth(os.getpid()),boot_id=self.boot_id)
        raw=(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n').encode()
        n=0
        while n<len(raw):
            wrote=os.write(self.claim_fd,raw[n:]);need(wrote>0,'native claim journal');n+=wrote
        os.fsync(self.claim_fd);os.fsync(self.root_fd)

    def verify(self,cleanup=False,required_seconds=RETIREMENT_RESERVE_SECONDS):
        self.lease.verify()
        need(self.state in ('CLAIMED','SOURCE_HELD','RUNNING','TERMINAL_CLEAN'),
             'native operation admission no longer live')
        need(file_identity(self.development_fd)==self.development_identity,'native resource lease changed')
        current_flock(self.development_fd)
        package=self.cfg['native']['source_package']
        import inplace_custody
        ps=os.fstat(self.package_fd);named=inplace_custody.open_exact(package['path'])
        try:
            ns=os.fstat(named)
            need((ps.st_dev,ps.st_ino)==(ns.st_dev,ns.st_ino)==(package['device'],package['inode']) and
                 inplace_custody.flags(self.package_fd)&inplace_custody.IMMUTABLE,
                 'native source generation custody changed')
        finally:os.close(named)
        if not cleanup:
            self._clocks(required_seconds=required_seconds)
            self.resource_scope.verify();self.client.revalidate()
            # A controller/account round trip can consume the whole allowance.
            # A timely account reply is not permission after any native cap.
            self._clocks(required_seconds=required_seconds)
        return self

    def source_held(self,source):
        self.verify();need(self.state=='CLAIMED' and source.admission is self and source.state=='HELD',
             'genuine selected source custody required')
        self.source=source;self.state='SOURCE_HELD';self._record('SOURCE_HELD')

    def launch(self,source):
        self.verify(required_seconds=self.deadline_seconds+COMPLETION_RESERVE_SECONDS)
        need(self.state=='SOURCE_HELD' and source is self.source,'source/native lifetime')
        source.verify()
        self._clocks(required_seconds=self.deadline_seconds+COMPLETION_RESERVE_SECONDS)
        self.state='RUNNING';self._record('NATIVE_RUNNING')
        result=None;primary=None
        try:
            result=self.owner_module.execute_owner(self.owner,deadline=self.deadline_seconds)
        except BaseException as error:
            primary=error;self.failure=error
        finally:
            # execute_owner retains uncertain container/children and never proves
            # cleanup from timeout or direct wait alone. Only actual clean owner
            # can mint this current-operation terminal object.
            if self.owner.absent and self.owner.lock is None and not self.owner.backend.children.pending and not self.owner.backend.children.final_reap_records:
                self.completion=NativeCompletion(self,self.owner,result)
                self.state='TERMINAL_CLEAN';self._record('NATIVE_TERMINAL_CLEAN')
            else:self.retain_unknown('native owner/container restoration unresolved')
        if primary is not None:
            # A failed functional result with positively retired resources still
            # carries completion for source restoration; do not lose it on raise.
            if self.completion is not None:self.completion.failure=primary
            else:raise primary
        return self.completion

    def release(self,completion,source):
        need(type(completion) is NativeCompletion and completion is self.completion and
          completion.admission is self and source is self.source and source.state=='CLOSED_RESTORED' and
          self.state=='TERMINAL_CLEAN','actual current native/source completion required')
        self.verify(cleanup=True);physical_snapshot(True)
        self._record('CURRENT_OPERATION_NATIVE_AND_SOURCE_POSITIVELY_RESTORED_RELEASE_INTENT')
        import signal
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,self.owner_module.OWNER_SIGNALS)
        self.release_errors=[]
        try:
            fd=self.development_fd
            # Do not retry an ambiguous numeric close. The exact new resource
            # lease is released only after native+source positive completion.
            fcntl.flock(fd,fcntl.LOCK_UN)
            self.development_fd=None;self.development_historical_fd=fd
            try:os.close(fd)
            except BaseException as error:self.release_errors.append(('development_fd',error))
            try:self._record('CURRENT_RESOURCE_FLOCK_RELEASED_HISTORICAL_SCOPES_RETAINED')
            except BaseException as error:self.release_errors.append(('release_receipt',error))
            try:self.client.close()
            except BaseException as error:self.release_errors.append(('controller_channel',error))
            scope_handles=[('scope_source_'+str(n),fd) for n,fd in enumerate(self.resource_scope.source_fds)]
            scope_handles.append(('scope_fd',self.resource_scope.fd))
            scope_handles.extend(('loader_'+str(n),fd) for n,fd in enumerate(self.loader_fds))
            for name,handle in [('package_fd',self.package_fd),('request_fd',self.request.fd),('claim_fd',self.claim_fd)]+scope_handles:
                if handle is None:continue
                # Each handle's attempt is retained before close; no retry on
                # interrupted/failed closure and no loss of the original error.
                if name=='request_fd':self.request.fd=None
                elif name=='scope_fd':self.resource_scope.fd=None
                elif name.startswith('scope_source_'):self.resource_scope.source_fds[int(name.rsplit('_',1)[1])]=None
                elif name.startswith('loader_'):self.loader_fds[int(name.rsplit('_',1)[1])]=None
                else:setattr(self,name,None)
                try:os.close(handle)
                except BaseException as error:self.release_errors.append((name,error))
            if self.release_errors:
                self.state='RESOURCE_RELEASED_CLOSURE_UNKNOWN'
                if self not in UNKNOWN:UNKNOWN.append(self)
                raise native_current_owner.ChannelCleanupError(None,self.release_errors)
            self.state='RELEASED'
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        return completion

    def retain_unknown(self,error):
        self.failure=error;self.state='UNKNOWN_RETAINED'
        if self not in UNKNOWN:UNKNOWN.append(self)
        if self.claim_fd is not None:
            try:self._record('UNKNOWN_RETAINED')
            except BaseException:pass


def _bound_owner(module,admission,parent,manifest):
    class BoundOwner(module.DiagnosticOwner):
        def _preflight(self):
            admission.verify();admission.source.verify()
            return admission.retained
        def _acquire(self):
            admission.verify();self.lock=admission.development_fd
            self.lock_identity=dict(admission.development_identity)
            # DiagnosticOwner uses dev/ino keys in its real owner evidence.
            self.lock_identity['dev']=self.lock_identity.pop('device')
            self.lock_identity['ino']=self.lock_identity.pop('inode')
        def _release(self):
            module.need(self.absent and not self.backend.children.pending and
              not self.backend.children.final_reap_records and (not self.create_issued or self.create_completed),
              'cannot return uncertain native container custody')
            admission.verify(cleanup=True)
            # Return only the borrow; root admission keeps the actual FLOCK until
            # positive physical and source restoration. No early global release.
            self.lock=None
        def _profile(self,row,image):
            super()._profile(row,image)
            if row.get('State',{}).get('Status')=='created' and admission.source.effective is None:
                admission.source.observe_effective(row)
                admission.plan.accept_effective()
            elif admission.source.effective is not None:
                # Later exited/cleanup observations keep the exact created
                # source/mount commitment; they never mint a new launch grant.
                admission.source.verify(cleanup=self.cleaning)
        def _call(self,*args,**kwargs):
            if self.cleaning:
                need(args and type(args[0]) is list and args[0] and
                     args[0][0] in ('ps','inspect','stop','kill','wait','logs','rm'),
                     'revocation permits only actual owned bounded retirement commands')
            admission.verify(cleanup=self.cleaning)
            start=bool(args and args[0] and args[0][0]=='start')
            if start:
                need(admission.source.effective is not None and admission.plan.effective_accepted,
                     'actual source/effective view required before native start')
            if not self.cleaning:
                timeout=kwargs.get('timeout',args[1] if len(args)>1 else 10)
                timeout=admission.work_timeout(timeout,start=start)
                if len(args)>1:args=(args[0],timeout)+args[2:]
                else:kwargs['timeout']=timeout
            return super()._call(*args,**kwargs)
    owner=BoundOwner(parent,manifest=manifest['path'],manifest_sha256=manifest['sha256'],
                     nonce=admission.nonce[:32])
    owner.admission_owner_module=module
    owner.owner_repo,owner.owner_scratch,owner.owner_image=module.REPO,module.SCRATCH,module.IMAGE
    owner.source_package=admission.cfg['native']['source_package']['path']
    need(module.normal_source_generation(owner.source_package),
         'exact root-owned named source generation required')
    owner.admitted_source_paths=tuple(sorted(set(module.SOURCE_HASHES)|{module.SELF,module.IMAGE_RECORD}))
    # Veto only; this callback grants nothing. The actual typed admission was
    # established above from root/current/kernel evidence before owner launch.
    owner.backend.admission_check=lambda:admission.verify(cleanup=owner.cleaning)
    return owner


class NativeParentRetirement:
    """Parent's independent readback of its one actual joined native child.

    A direct wait or terminal JSON alone never suffices. Root also checks the
    new child identity, real private owner results/direct-command waits, exact
    restored-source journal/inodes/flags, current native counters and actual
    absence of the development FLOCK. No historical outcome is retired.
    """
    def __init__(self, watchdog):
        self.watchdog=watchdog;self.request=watchdog.native_request
        need(type(self.request) is VerifiedNativeRequest and
             watchdog.wait_status is not None and os.WIFEXITED(watchdog.wait_status),
             'exact current direct native supervisor join required')
        need(file_identity(watchdog.root_fd)==self.request.cfg['operation_root'] and
             self.request.cfg['watchdog_pid']==os.getpid() and
             native_current_owner.birth(os.getpid())==self.request.cfg['watchdog_birth'],
             'actual current parent/root scope differs')
        nonce=self.request.cfg['nonce']
        raw=self._root_record('NATIVE-OPERATION-TERMINAL-'+nonce+'.json')
        terminal=json.loads(raw,object_pairs_hook=native_current_owner.unique)
        need(terminal.get('kind')=='named-native-operation-terminal-v1' and
             terminal.get('nonce')==nonce and terminal.get('config_sha256')==self.request.sha256 and
             terminal.get('supervisor_pid')==watchdog.pid and
             terminal.get('supervisor_birth')==watchdog.birth and
             terminal.get('current_resource_state')=='RELEASED' and
             terminal.get('source_state')=='CLOSED_RESTORED' and terminal.get('container_absent') is True,
             'genuine current child terminal/source/resource record missing')
        if terminal.get('container') is None:
            need(terminal.get('create_issued') is False and terminal.get('functional_pass') is False,
                 'no-container completion requires no issued create and failed work')
        else:
            need(type(terminal.get('container')) is str and len(terminal['container'])==64 and
                 all(x in '0123456789abcdef' for x in terminal['container']) and
                 terminal.get('create_completed') is True, 'actual new container identity')
        self.terminal=terminal
        self._restored_sources(nonce)
        self._owner_records(nonce,terminal)
        self.physical=physical_snapshot(True)
        # Read the exact development lock inode and actual kernel lock table;
        # do not acquire/release it or infer freedom from a missing pathname.
        module=sys.modules['native_diagnostic_container_owner']
        fd=os.open(module.LOCK,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        try:
            identity=file_identity(fd)
            need(identity==terminal['development_lock_identity'],'native lock inode changed')
            for line in Path('/proc/locks').read_text().splitlines():
                fields=line.split()
                if len(fields)<8 or fields[1:4]!=['FLOCK','ADVISORY','WRITE']:continue
                major,minor,inode=fields[5].split(':')
                need((int(major,16),int(minor,16),int(inode))!=
                     (os.major(identity['device']),os.minor(identity['device']),identity['inode']),
                     'native development FLOCK still held by an actual owner')
        finally:os.close(fd)
        self.state='CURRENT_NATIVE_AND_SOURCE_RESTORED'

    def _root_record(self,name):
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=self.watchdog.root_fd)
        try:
            st=os.fstat(fd)
            need(stat.S_ISREG(st.st_mode) and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o600 and
                 st.st_nlink==1 and 0<st.st_size<=2*1024*1024,'actual private root terminal record')
            raw=os.read(fd,st.st_size+1)
            need(len(raw)==st.st_size and file_identity(fd)==file_identity_from_stat(st),
                 'native terminal record changed')
            return raw
        finally:os.close(fd)

    def _restored_sources(self,nonce):
        import inplace_custody
        spec=self.request.cfg['native']['source_manifest']
        fd,raw=root_bootstrap.pinned_root_file(spec['path'],spec['sha256'])
        try:manifest=json.loads(raw,object_pairs_hook=native_current_owner.unique)
        finally:os.close(fd)
        rows=manifest['sources'];expected={r['host'] for r in rows}
        raw=self._root_record('NATIVE-SOURCE-FLAGS-'+nonce+'.jsonl')
        events=[json.loads(line,object_pairs_hook=native_current_owner.unique) for line in raw.splitlines()]
        plan={};restored={}
        for row in events:
            if set(row)=={'path','device','inode','old_flags'}:
                need(row['path'] not in plan,'source prior-flags repeated');plan[row['path']]=row
            elif row.get('status')=='RESTORED_INODE':
                need(row.get('nonce')==nonce and row['path'] not in restored,
                     'source restored inode binding');restored[row['path']]=row
        need(set(plan)==set(restored)==expected and events[-1].get('status')=='RESTORED_CURRENT_SOURCE_CUT_ONLY',
             'every actual source prior flag must have positive restoration')
        for path in sorted(plan):
            prior=plan[path];after=restored[path]
            need((prior['device'],prior['inode'],prior['old_flags'])==
                 (after['device'],after['inode'],after['original_flags']), 'source restore/prior row differs')
            fd=inplace_custody.open_exact(path)
            try:
                st=os.fstat(fd)
                need((st.st_dev,st.st_ino)==(prior['device'],prior['inode']) and
                     inplace_custody.flags(fd)==prior['old_flags'],'actual source prior inode/flags not restored')
            finally:os.close(fd)

    def _owner_records(self,nonce,terminal):
        import inplace_custody
        module=sys.modules['native_diagnostic_container_owner']
        parent=Path(self.request.cfg['native']['attempt_parent'])
        evidence=parent.with_name(parent.name+'.owner-'+nonce[:32])
        fd=inplace_custody.open_exact(str(evidence))
        try:
            inplace_custody.root_private(fd)
            def read(name):
                opened=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
                try:
                    st=os.fstat(opened)
                    need(stat.S_ISREG(st.st_mode) and st.st_uid==0 and st.st_nlink==1 and
                         stat.S_IMODE(st.st_mode)==0o600 and st.st_size<=module.LIMIT,
                         'actual new native owner record')
                    raw=os.read(opened,st.st_size+1);need(len(raw)==st.st_size,'owner record read bound')
                    return module.strict_json(raw)
                finally:os.close(opened)
            owner=read('owner.json');result=read('result.json')
            need(owner['nonce']==nonce[:32] and owner['outer']['pid']==self.watchdog.pid and
                 str(owner['outer']['proc_starttime'])==self.watchdog.birth and
                 owner['owner_sha256']==self.request.cfg['owner']['sha256'], 'actual native owner/process/source join')
            need(result['container']==terminal['container'] and result['absence_verified'] is True and
                 result['lease_retained'] is False, 'actual native owner not positively absent')
            names=os.listdir(fd)
            import re
            commands=sorted(n for n in names if re.fullmatch(r'[0-9]+-[a-z]+\.json',n))
            need(bool(commands) and len(commands)<=4096,'actual bounded command records missing')
            # A previously unjoined command's old raw row stays intact; only
            # the genuine ledger's appended exact-birth final reap may join it.
            late={}
            for name in sorted(n for n in names if re.fullmatch(r'command-retirements-[0-9]+\.json',n)):
                updates=read(name);need(type(updates) is list,'actual late-reap row list')
                for update in updates:
                    initial,final=update['initial'],update['final']
                    keys=('pid','pgid','sid','proc_starttime')
                    need(all(initial.get(k)==final.get(k) for k in keys) and
                         final.get('reaped') is True and type(final.get('returncode')) is int,
                         'actual late direct wait differs')
                    key=tuple(initial.get(k) for k in keys)
                    need(key not in late,'duplicate late wait identity');late[key]=final
            sequences=[]
            for name in commands:
                sequences.append(int(name.split('-',1)[0]));row=read(name);record=row.get('command')
                need(type(record) is dict,'actual command ownership record missing')
                keys=('pid','pgid','sid','proc_starttime')
                if all(record.get(k) is None for k in keys):
                    need(record.get('reaped') is False and record.get('returncode') is None and
                         row.get('failure') is not None,'no-child command refusal source differs')
                    continue
                if record.get('reaped') is not True:
                    record=late.get(tuple(record.get(k) for k in keys))
                need(type(record) is dict and record.get('reaped') is True and
                     type(record.get('returncode')) is int and
                     all(type(record.get(k)) is int and record[k]>0 for k in keys),
                     'actual Docker direct-client wait missing')
            need(sorted(sequences)==list(range(1,len(sequences)+1)), 'actual command record sequence gap')
            need(result['status'] in ('PROTOCOL_PASS','FAIL'),'actual owner result status')
            if result['status']=='PROTOCOL_PASS':
                state=read('state.json')
                need(state.get('Status')=='exited' and state.get('ExitCode')==0 and
                     state.get('OOMKilled') is False,'actual native final state record missing')
            self.owner_result=result;self.command_count=len(commands)
        finally:os.close(fd)


def file_identity_from_stat(s):
    return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,mode=stat.S_IMODE(s.st_mode),nlink=s.st_nlink)
