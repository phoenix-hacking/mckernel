"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing stable read/export/fresh-query/review-payload/final-publish lifecycle adapted to exact BFD domain.
Source only: COHORT_AUTHORITY remains NULL until actual source30/transport publication and independent source approval.
"""
from pathlib import Path
import hashlib,json,os,stat,sys,time,re
COHORT_AUTHORITY = None
D=Path(__file__).parent
R=D
P=D
A=D/'admission-preparation-1'
MAX=32*2**20
FIELDS=('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')
PINS = {'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/preclock-control-source-1/RELEASE.ROOT.PENDING-NO-CLOCK-NO-APPROVAL.json': '8b1373c9d9588e3ba656f23e20bb19c0ca5dff3f7ebd388a9e3d887789fd56a3', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/preclock-control-source-1/ROOT-OWNER-ENTRY.PENDING.json': '1ebfa4f436ee22c758781a4a911fa308e53e578e3ce532261e73fa290f533247', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/REQUEST.BFD-CC-CONTROL.PENDING-RELEASE.json': '1d9b4e5501a31b7a38307afbc442b7cc891f613c12b8880e9afca6756e26462c', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/EXACT-ELEVEN-CONTROL-RUNTIME-SOURCE-MAP.PREFIX-SOURCE-CORRECTED.json': 'ec3f5ef68fb2f0e3b021de4c2494f98d5bcee155d4f30b4be32f11ed186e8f56', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/EXACT-TWO-COMMAND-C-C-CONTROL-SOURCE25-SPEC.json': '011ca2e5e443086ce5a5a4891b161818050b37362b5880b59f3b8374e13a10ba', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/1/stdout': '42ccd9913d54c2b9443d3316f9c4db5099b3e7925fef8bbd5c0c634873243cb7', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/actual-helpers-postjoin-1/0/stdout': '20230e7edeb8bdbbf7b2c288b6142d91143f7aa334c9212fd876f9d28faefb07', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/preclock-control-source-1/admission-preparation-1/run_root_sdk_readonly_admission.py': '01e5d7cbd94657845ce8df0818349096b5e618b6648dc53ad31e2a7b73bbf362', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/preclock-control-source-1/admission-preparation-1/QUERY-INPUTS.ROOT.json': '8945bd36cdced15bfe9ec117bc424461dc66a7680b952c288f39206f0311a54c', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/BFD-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json': '3e1dc1150b51c43ab270558f68d22f3b4ed44299f969e4bc199283c45c1e68fc'}
REQUEST_SHA = '1d9b4e5501a31b7a38307afbc442b7cc891f613c12b8880e9afca6756e26462c'
PHYSICAL_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/1/stdout')
POSTJOIN_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/actual-helpers-postjoin-1/0/stdout')
def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def load_raw(path,expected=None):
    path=Path(path)
    assert path.is_absolute() and not any(p.is_symlink() for p in (path,*path.parents))
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        first=os.fstat(fd);assert stat.S_ISREG(first.st_mode) and first.st_nlink==1 and first.st_size<=MAX
        parts=[];size=0
        while True:
            part=os.read(fd,min(1048576,MAX+1-size))
            if not part:break
            parts.append(part);size+=len(part);assert size<=MAX
        last=os.fstat(fd);named=path.lstat()
        assert all(getattr(first,k)==getattr(last,k)==getattr(named,k) for k in FIELDS)
    finally:os.close(fd)
    raw=b''.join(parts);assert len(raw)==first.st_size
    digest=hashlib.sha256(raw).hexdigest()
    if expected is not None:assert digest==expected
    return raw,dict(path=str(path),sha256=digest,bytes=len(raw)),{k:getattr(first,k) for k in FIELDS}

def read(path,expected=None):
    raw,ref,meta=load_raw(path,expected);return json.loads(raw),ref,meta

def pinned(path):return read(path,PINS[str(path)])[0]

def write_raw(path,raw):
    assert not os.path.lexists(path)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        view=memoryview(raw)
        while view:
            n=os.write(fd,view);assert n>0;view=view[n:]
        os.fchown(fd,1000,1000);os.fsync(fd)
    finally:os.close(fd)
    return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def write(path,value):return write_raw(path,canonical(value))

def fresh(query):
    now=time.time();assert type(query['at']) in (int,float) and 0<=now-query['at']<=120
    return now

assert COHORT_AUTHORITY is not None, 'genuine fetched30/sourceapproval/currenttransport overlay required before root payload entry'
assert os.getuid()==os.geteuid()==0 and len(sys.argv) in (3,4)
assert sys.argv[1] in ('--prepare-review-payload','--publish-reviewed-release')
if sys.argv[1]=='--prepare-review-payload':
 assert len(sys.argv)==4 and sys.argv[2]==COHORT_AUTHORITY['fetched_source_proof']['sha256'] and sys.argv[3]==COHORT_AUTHORITY['source_approval']['sha256']
else:
 assert len(sys.argv)==4
base=pinned(R/'RELEASE.ROOT.PENDING-NO-CLOCK-NO-APPROVAL.json');entry=pinned(P/'ROOT-OWNER-ENTRY.PENDING.json')
request=pinned(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/REQUEST.BFD-CC-CONTROL.PENDING-RELEASE.json'));source_map=pinned(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/EXACT-ELEVEN-CONTROL-RUNTIME-SOURCE-MAP.PREFIX-SOURCE-CORRECTED.json'))
assert base['schema']=='mckernel.bfd-soleheavy-sdk-release.v1' and base['status'] is None and base['execution_count']==0
assert request['nonce']==base['nonce'] and base['request']=={'path':'/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/REQUEST.BFD-CC-CONTROL.PENDING-RELEASE.json','sha256':REQUEST_SHA} and base['source_sha256']==source_map
assert base['execution_review'] is None and base['source_review'] is None and base['fetched_source_verified'] is False
SOURCE_APPROVAL_PATH=Path(COHORT_AUTHORITY['source_approval']['path'])
SOURCE_APPROVAL_SHA=COHORT_AUTHORITY['source_approval']['sha256']
source_review,reviewref,_=read(SOURCE_APPROVAL_PATH,SOURCE_APPROVAL_SHA)
assert source_review==COHORT_AUTHORITY['source_approval_expected'] and source_review['decision']=='PASS_SOURCE' and source_review['implementation_ownership'] is False
assert source_review['source_sha256']==source_map and source_review['request_sha256']==REQUEST_SHA
assert source_review['reviewer'] and source_review['reviewer']!=COHORT_AUTHORITY['author'] and COHORT_AUTHORITY['author']=='/root'
FETCHED_SOURCE_PROOF=COHORT_AUTHORITY['fetched_source_proof'];fetched,fetched_ref,_=read(FETCHED_SOURCE_PROOF['path'],FETCHED_SOURCE_PROOF['sha256'])
assert fetched==COHORT_AUTHORITY['fetched_source_expected'] and fetched['status']=='PASS_ACTUAL_FETCHED_SOURCE'
assert fetched['commit']==fetched['fetched_commit'] and re.fullmatch('[0-9a-f]{40}',fetched['commit'])
assert fetched['source_member_count']==25 and fetched['source_spec']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/EXACT-TWO-COMMAND-C-C-CONTROL-SOURCE25-SPEC.json', 'sha256': '011ca2e5e443086ce5a5a4891b161818050b37362b5880b59f3b8374e13a10ba'}
manifest=pinned(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/EXACT-TWO-COMMAND-C-C-CONTROL-SOURCE25-SPEC.json'));assert manifest['member_count']==25 and fetched['source_members']==manifest['files']
assert {k[len('runtime/'):]:v['sha256'] for k,v in manifest['files'].items() if k.startswith('runtime/')}==source_map
CURRENT_OVERLAY_FETCHED_PROOF=COHORT_AUTHORITY['overlay_fetched_proof'];overlay,overlay_ref,_=read(CURRENT_OVERLAY_FETCHED_PROOF['path'],CURRENT_OVERLAY_FETCHED_PROOF['sha256'])
assert overlay==COHORT_AUTHORITY['overlay_fetched_expected'] and overlay['source_proof']==FETCHED_SOURCE_PROOF
assert overlay['query_source']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/preclock-control-source-1/admission-preparation-1/run_root_sdk_readonly_admission.py', 'bytes': 16411, 'sha256': '01e5d7cbd94657845ce8df0818349096b5e618b6648dc53ad31e2a7b73bbf362'} and overlay['query_inputs']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/preclock-control-source-1/admission-preparation-1/QUERY-INPUTS.ROOT.json', 'bytes': 417, 'sha256': '8945bd36cdced15bfe9ec117bc424461dc66a7680b952c288f39206f0311a54c'}
assert overlay['current_independent_acceptance']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/BFD-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json', 'bytes': 2478, 'sha256': '3e1dc1150b51c43ab270558f68d22f3b4ed44299f969e4bc199283c45c1e68fc'}
independent,_,_=read('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/BFD-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json','3e1dc1150b51c43ab270558f68d22f3b4ed44299f969e4bc199283c45c1e68fc');assert independent=={'schema': 'mckernel.m15.executor.bfd.qualifier-failure.current-acceptance.v1', 'status': 'PASS', 'reviewer': '/root/recovery_review', 'implementation_ownership': False, 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual BFD failed qualifier normal retirement physical and current postjoin only.', 'physical_acceptance': True, 'current_postjoin_acceptance': True, 'evidence_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1', 'evidence_sha256_by_relative_path': {'0/stdout': '5defa3d32fa74278a4ba605e3bb93dd52b9a1a798d82725eb0eec653420417ae', '0/WHOLE-JOIN.json': '70ad0a8c73d7bbfc7e896bd97e59e648babccd8187a214ff9ce9dbb1eb42b0e5', '1/stdout': '42ccd9913d54c2b9443d3316f9c4db5099b3e7925fef8bbd5c0c634873243cb7', '1/WHOLE-JOIN.json': 'e05025e859de98dbc78f0cd70c39f1583640a519dc3bd771f69fd0b21397870c', 'actual-helpers-postjoin-1/0/stdout': '20230e7edeb8bdbbf7b2c288b6142d91143f7aa334c9212fd876f9d28faefb07', 'actual-helpers-postjoin-1/0/WHOLE-JOIN.json': 'd9e07e033e4358d319abe5894e5db58c8d8a265971dd915f772398fbf38ba266'}, 'owner': [598507, '71107266'], 'prior_helpers': [[601242, '71146149'], [601239, '71146142'], [601247, '71146181'], [601244, '71146174']], 'postjoin_python': [602041, '71152456'], 'postjoin_sudo': [602038, '71152449'], 'runtime_nonce': '0ccec66ed738427296d4e7b6bff0b4c5', 'operation_lease_nonce': '39247d7fc921471f83db241bf1c837eb', 'container_id': '5a274c67bda1f55eb90346caf3e7e854332b65f78bfb8f5c8ef4dec96e61f936', 'protected_refs': 131, 'candidate': {'entries': 42, 'files': 38, 'bytes': 6682841}, 'original_workload_status': 'FAIL', 'qualifier_capture_count': 1, 'qualification_commands_recorded': 10, 'qualification_successful_prefix_count': 9, 'qualification_failure_rc': -6, 'inner_command_births_namespace': 'container', 'permanent_mutex': {'device': 27, 'inode': 4, 'free_before': True, 'free_after': True, 'flock_acquired': False}, 'native_acceptance': False, 'default_acceptance': False, 'SDK_acceptance': False, 'heavy_execution_released': False}
physical=pinned(PHYSICAL_PATH);postjoin=pinned(POSTJOIN_PATH)
assert physical['status']=='PASS_M15_EXECUTOR_BFD_QUALIFIER_FAILURE_MUTEX_HELD_CURRENT_PHYSICAL'
assert postjoin['status']=='PASS_M15_EXECUTOR_BFD_QUALIFIER_FAILURE_CURRENT_HELPERS_POSTJOIN_MUTEX_FREE'
assert physical['original_workload_status']==postjoin['original_workload_status']=='FAIL'
assert postjoin['permanent_mutex_free_before'] is True and postjoin['permanent_mutex_free_after'] is True and postjoin['flock_acquired'] is False
base.update(author=COHORT_AUTHORITY['author'],source_review={k:reviewref[k] for k in ('path','sha256')},execution_count=1,aggregate_review={})
E=D/'root-query-export-1';payload_path=D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json'
if sys.argv[1]=='--prepare-review-payload':
    assert not E.exists() and not payload_path.exists()
    query_path=A/'root-readonly-admission-preview-1/ADMISSION.json'
    query,qref,qmeta=read(query_path)
    join_path=A/'ROOT-READONLY-ADMISSION-WHOLE-JOIN.json';join,jref,jmeta=read(join_path)
    assert query['status']=='PASS_READONLY_SDK_CAPACITY_IDENTITY_IMAGE_ONLY'
    assert query['request_sha256']==REQUEST_SHA and query['target_calls']==query['container_create_calls']==0
    assert query['current_physical_acceptance']==PINS[str(PHYSICAL_PATH)] and query['current_postjoin']==PINS[str(POSTJOIN_PATH)]
    assert query['current_clearance_scope']==physical['status']
    assert join['returncode']==0 and all(join[k] is True for k in ('direct_child_joined','group_absent','closed_streams'))
    assert join['error'] is None and join['retirement_error'] is None and join['timed_out'] is False
    assert join['remaining_group_members']==join['unexpected_group_members']==[]
    rawout,oref,ometa=load_raw(join['captures']['stdout']['path'],join['captures']['stdout']['sha256'])
    rawerr,eref,emeta=load_raw(join['captures']['stderr']['path'],join['captures']['stderr']['sha256'])
    assert len(rawout)==join['captures']['stdout']['size'] and len(rawerr)==join['captures']['stderr']['size']==0
    summary=json.loads(rawout);assert summary['status']==query['status'] and summary['at']==query['at']
    assert summary['resources']==query['resources'] and summary['target_calls']==0
    resources=query['resources'];assert resources['memory_available']>=25501368320
    assert resources['host_free']>=resources['host_minimum_bytes'] and resources['scratch_free']>=resources['scratch_minimum_bytes']
    now=fresh(query)
    E.mkdir(mode=0o700);os.chown(E,1000,1000)
    exports=[]
    for label,path,expected in [('ADMISSION.json',query_path,qref['sha256']),('WHOLE-JOIN.json',join_path,jref['sha256']),('stdout',Path(oref['path']),oref['sha256']),('stderr',Path(eref['path']),eref['sha256'])]:
        raw,origin,meta=load_raw(path,expected);copy=write_raw(E/label,raw)
        exports.append(dict(origin=origin,origin_identity=meta,owned_export=copy))
    export=write(E/'ROOT-AUTHENTICATED-EXPORT.json',dict(status='ROOT_EXACT_RETAINED_QUERY_AND_WHOLE_JOIN_EXPORT',record_writer='/root',root_uid=os.geteuid(),exports=exports))
    outrefs={Path(x['owned_export']['path']).name:x['owned_export'] for x in exports}
    base.update(execution_release=True,current_authority_source_proof={k:overlay_ref[k] for k in ('path','sha256')},status='PASS_EXECUTION_RELEASE',fetched_source_verified=True,fetched_source_proof={k:fetched_ref[k] for k in ('path','sha256')},
        current_physical=dict(path=str(PHYSICAL_PATH),sha256=PINS[str(PHYSICAL_PATH)]),current_live_postjoin=dict(path=str(POSTJOIN_PATH),sha256=PINS[str(POSTJOIN_PATH)]),
        actual_query={k:outrefs['ADMISSION.json'][k] for k in ('path','sha256')},actual_query_whole_join={k:outrefs['WHOLE-JOIN.json'][k] for k in ('path','sha256')},
        actual_query_stdout={k:outrefs['stdout'][k] for k in ('path','sha256')},query_export=export,
        readonly_query_source=dict(path=str(A/'run_root_sdk_readonly_admission.py'),sha256=PINS[str(A/'run_root_sdk_readonly_admission.py')]),
        readonly_query_capture_source=None)
    base['aggregate_review'].update(memory_available=resources['memory_available'],scratch_actual=resources['scratch_free'],scratch_required=resources['scratch_minimum_bytes'])
    payload={k:v for k,v in base.items() if k!='execution_review'}
    payload_ref=write(payload_path,payload)
    print(json.dumps(dict(status='PAYLOAD_FOR_INDEPENDENT_REVIEW_NOT_EXECUTION_RELEASE',payload=payload_ref,reviewed_release_payload_sha256=hashlib.sha256(canonical(payload)).hexdigest(),query_export=export,query_age=now-query['at'],remaining_seconds=120-(now-query['at']))))
else:
    review_path=Path(sys.argv[2]);review,review_ref,_=read(review_path,sys.argv[3])
    payload,payload_ref,_=read(payload_path);query,_,_=read(payload['actual_query']['path'],payload['actual_query']['sha256']);now=fresh(query)
    assert payload['nonce']==request['nonce'] and payload['request']==base['request'] and payload['source_sha256']==base['source_sha256']
    assert payload['source_review']==base['source_review'] and payload['status']=='PASS_EXECUTION_RELEASE' and 'execution_review' not in payload
    assert review['decision']=='PASS_EXECUTION' and review['implementation_ownership'] is False
    assert review['reviewer'] and review['reviewer']!=payload['author']
    assert review['reviewed_release_payload_sha256']==hashlib.sha256(canonical(payload)).hexdigest()
    final=dict(payload,execution_review={k:review_ref[k] for k in ('path','sha256')})
    release_ref=write(R/'RELEASE.ROOT.FINAL.json',final)
    argv=entry['argv'];assert '--cpu=' not in ' '.join(argv) and entry['outer_timeout'] is None and entry['outer_CPU_rlimit'] is None
    assert argv[:3]==['/usr/bin/taskset','-c','7'] and '/usr/bin/sudo' not in argv
    argv[argv.index('--release-sha256')+1]=release_ref['sha256']
    entry.update(argv=argv,at=now,memory_available=query['resources']['memory_available'],query_age_seconds=now-query['at'],release_sha256=release_ref['sha256'],status='EXACT_INDEPENDENTLY_REVIEWED_ORDINARY_ENTRY_NOT_EXECUTED',source_only=False)
    entry_ref=write(R/'ROOT-OWNER-ENTRY.FINAL.LIBDWARF1.json',entry)
    print(json.dumps(dict(status='REVIEWED_RELEASE_PUBLISHED_OWNER_NOT_EXECUTED',release=release_ref,ordinary_entry=entry_ref,query_age_seconds=now-query['at'])))
