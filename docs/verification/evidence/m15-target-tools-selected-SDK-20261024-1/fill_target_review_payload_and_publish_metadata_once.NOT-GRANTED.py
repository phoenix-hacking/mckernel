"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
ROOT metadata only: exact existing query export/reviewed release flow specialized for target tools.
No owner/query/compiler/SDK imports or execution; core runtime source remains unchanged.
"""
from pathlib import Path
import hashlib,json,os,stat,sys,time,re
D=Path(__file__).parent
R=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1')
P=R/'publication-admission-preparation-1'
A=P/'admission-preparation-1'
PINS={'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1/RELEASE.ROOT.PENDING-NO-CLOCK-NO-APPROVAL.json': 'f2bce32227ae27510e1b005f19ee7fecaa2c9dab35d05a8bc0347ced0c90e4a6', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1/publication-admission-preparation-1/ROOT-OWNER-ENTRY.PENDING.json': '2370baafbab97eec5926007cd9a139bc0d6d9224d1aea232dbba8311441c0bba', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1/REQUEST.ROOT.FINAL.json': '3807ec805fe4d8ad0f205b0a0782df3392d7cfbffc5b85332ded1f0bf57dac53', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1/ROOT-RECORDED-GENUINE-TARGET-SOURCE-APPROVAL.json': 'f9a626417ede1d3d125999263cf1348aabb1091e28f8b4317381ae99d3f06ad8', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1/ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json': '30a5be79a7b19d864a5dd4deee1e007d61467e6d51ab39f5570c532b93a69d64', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1/publication-admission-preparation-1/admission-preparation-1/run_root_sdk_readonly_admission.py': 'be5e81460f1c57f6fc06548cb7ed01dc25744d1f64d6d00f5e1aa7f18cfdac32', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1/publication-admission-preparation-1/admission-preparation-1/capture_root_sdk_readonly_admission_once.py': '5d625437e6904e95cf0c30447cc00fff283380d8d1222066d6cbaea0e6511dd4', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1/publication-admission-preparation-1/admission-preparation-1/QUERY-INPUTS.ROOT.json': '34951dfe60b688d2d43dbd3287263f7824bcf9d372a8485261a833bd820fcab4', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-retained10-five-suffix-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json': 'd28b7a873a47f462bf06b4df4f6e0230b0190f45bcba3b7341da4bd8a6228b64', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-retained10-five-suffix-postjoin-1/CURRENT-LIVE-POSTJOIN.json': '22aa8d692203423bd795770227af1221f4e6eec4f88b8c24c6ef53b658294206', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/default-selector-coherent-successor-1/target-toolchain-cache-qualified-source-1/actual-SDK-DSO-bound-target-plan-1/owner-materialization-preparation-1/three-input-RO-completion-1/publication-admission-preparation-1/SOURCE-RETENTION.json': '5b7d688b8199a7bc4a614c7b189de956fad7555e63aa1ac1ab2fa864f2e29c87'}
PHYSICAL_PATH=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-retained10-five-suffix-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json')
POSTJOIN_PATH=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-retained10-five-suffix-postjoin-1/CURRENT-LIVE-POSTJOIN.json')
REQUEST_SHA='3807ec805fe4d8ad0f205b0a0782df3392d7cfbffc5b85332ded1f0bf57dac53'
SOURCE_APPROVAL_SHA='f9a626417ede1d3d125999263cf1348aabb1091e28f8b4317381ae99d3f06ad8'
MAX=32*2**20
FIELDS=('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')

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

assert os.getuid()==os.geteuid()==0 and len(sys.argv) in (3,4)
assert sys.argv[1] in ('--prepare-review-payload','--publish-reviewed-release')
base=pinned(R/'RELEASE.ROOT.PENDING-NO-CLOCK-NO-APPROVAL.json')
entry=pinned(P/'ROOT-OWNER-ENTRY.PENDING.json')
request=pinned(R/'REQUEST.ROOT.FINAL.json')
source_review=pinned(R/'ROOT-RECORDED-GENUINE-TARGET-SOURCE-APPROVAL.json')
source_map=pinned(R/'ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json')
retention=pinned(P/'SOURCE-RETENTION.json')
physical=pinned(PHYSICAL_PATH);postjoin=pinned(POSTJOIN_PATH)
assert request['nonce']==base['nonce']=='8f5f2bea145c4ec8b88193fa3a70a58e'
assert base['request']==dict(path=str(R/'REQUEST.ROOT.FINAL.json'),sha256=REQUEST_SHA)
assert source_review['decision']=='PASS_SOURCE' and source_review['implementation_ownership'] is False
assert source_review['source_sha256']==source_map['source_sha256']==base['source_sha256'] and source_review['reviewer']!=base['author']
assert source_review['final_ready_sha256']=='4c6540298d89c4d45c45615f16ebb23c1a491f0cb79407aeb3a2c5eee9be0c8f'
assert physical['status']=='PASS_ACTUAL_M15_SDK_LIBRARY_SUFFIX_PHYSICAL_RETIREMENT' and physical['artifact_native_acceptance'] is False
assert postjoin['status']=='ACCEPTED_NON_NULL' and postjoin['physical_acceptance']['sha256']==PINS[str(PHYSICAL_PATH)]
assert postjoin['original_workload_status']=='PASS' and postjoin['artifact_native_acceptance'] is False
assert base['execution_review'] is None and base['status']=='PENDING_FRESH_ADMISSION_PUBLICATION_AND_INDEPENDENT_EXECUTION_REVIEW'
assert base['source_review'] is None and base['aggregate_review'] is None
base['source_review']=dict(path=str(R/'ROOT-RECORDED-GENUINE-TARGET-SOURCE-APPROVAL.json'),sha256=SOURCE_APPROVAL_SHA)
base['aggregate_review']={'CPU1_excluded': True, 'control_monitor_bytes': 4026531840, 'full_campaign_required_bytes': 25501368320, 'heavy_CPUs': [2, 3, 4, 5], 'heavy_memory_bytes': 12884901888, 'host_reserve_bytes': 4294967296, 'memory_available': None, 'one_heavy': True, 'ordinary_CPUs': [0, 6], 'ordinary_memory_each': 2147483648, 'scratch_actual': None, 'scratch_required': None}
E=D/'root-query-export-1';payload_path=D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json'
fetched_path=P/'ROOT-FETCHED-TARGET-TOOLS-SOURCE-VERIFICATION.json'
if sys.argv[1]=='--prepare-review-payload':
    assert len(sys.argv)==3
    expected_fetch_sha=sys.argv[2]
else:
    assert len(sys.argv)==4
    pending,_,_=read(payload_path);assert pending['fetched_source_proof']['path']==str(fetched_path)
    expected_fetch_sha=pending['fetched_source_proof']['sha256']
assert re.fullmatch('[0-9a-f]{64}',expected_fetch_sha)
fetched,fetched_ref,_=read(fetched_path,expected_fetch_sha)
assert fetched['status']=='PASS_FETCHED_TARGET_TOOLS_SOURCE_MEMBERS' and fetched['member_count']==106
assert re.fullmatch('[0-9a-f]{40}',fetched['commit']) and fetched['archive_sha256']==retention['archive']['sha256']
assert fetched['root_request_sha256']==REQUEST_SHA and fetched['source_review_sha256']==SOURCE_APPROVAL_SHA
assert fetched['source_map_sha256']==PINS[str(R/'ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json')]
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
    base.update(status='PASS_EXECUTION_RELEASE',fetched_source_verified=True,fetched_source_proof={k:fetched_ref[k] for k in ('path','sha256')},
        current_physical=dict(path=str(PHYSICAL_PATH),sha256=PINS[str(PHYSICAL_PATH)]),current_live_postjoin=dict(path=str(POSTJOIN_PATH),sha256=PINS[str(POSTJOIN_PATH)]),
        actual_query={k:outrefs['ADMISSION.json'][k] for k in ('path','sha256')},actual_query_whole_join={k:outrefs['WHOLE-JOIN.json'][k] for k in ('path','sha256')},
        actual_query_stdout={k:outrefs['stdout'][k] for k in ('path','sha256')},query_export=export,
        readonly_query_source=dict(path=str(A/'run_root_sdk_readonly_admission.py'),sha256=PINS[str(A/'run_root_sdk_readonly_admission.py')]),
        readonly_query_capture_source=dict(path=str(A/'capture_root_sdk_readonly_admission_once.py'),sha256=PINS[str(A/'capture_root_sdk_readonly_admission_once.py')]))
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
    entry_ref=write(R/'ROOT-OWNER-ENTRY.FINAL.TARGET1.json',entry)
    print(json.dumps(dict(status='REVIEWED_RELEASE_PUBLISHED_OWNER_NOT_EXECUTED',release=release_ref,ordinary_entry=entry_ref,query_age_seconds=now-query['at'])))
