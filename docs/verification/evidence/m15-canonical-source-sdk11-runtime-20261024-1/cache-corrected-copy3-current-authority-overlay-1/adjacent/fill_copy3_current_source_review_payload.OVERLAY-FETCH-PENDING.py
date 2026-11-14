"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
ROOT metadata only: exact existing query export/reviewed release flow specialized for target tools.
No owner/query/compiler/SDK imports or execution; core runtime source remains unchanged.
"""
from pathlib import Path
import hashlib,json,os,stat,sys,time,re
D=Path(__file__).parent
R=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1')
P = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/late-current-physical-preparation-1/actual-copy3-current-binding-1')
A = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/late-current-physical-preparation-1/actual-copy3-current-binding-1/admission-preparation-1')
PINS = {'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/RELEASE.ROOT.PENDING-NO-CLOCK-NO-APPROVAL.json': '6250c121463162e1e61d5ea9567307a92dc55a46cf4c4ff78190331730854892', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/REQUEST.ROOT.FINAL.json': '08518322d3121354ccbffbead70072ed763102b859b7e9283b440b7ca503f6ea', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json': '0936a5a2639fb0825ca773b52af142af170c94ad5096d67c9f15fc3d8688a355', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/ROOT-RECORDED-INDEPENDENT-CORRECTED-SOURCE-APPROVAL.json': '2167d890bf59c633531ab7a97f0620e9535a35f5785d7806c249d42efb882754', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/ROOT-FETCHED-CACHE-CORRECTED-SOURCE-PROOF.json': '4d1da90e7e52c1495df458f79c49a520afaf6fef12e23b2153c8aeea2febaf00', '/home/holden/mckernel/docs/verification/evidence/m15-target-tools-libdwarf-source-20261024-1/RETENTION.json': '96ee0b574831b93135c04677b108226bf7f333c27bd3c6110b7e197ea1d2eb16', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/EXACT-CACHE-CORRECTED-SOURCE-DELTA.INPUTS.json': 'c1be6825fe1502efe8590fb1cff1f1c467b81fb15fa151f4bc060618e11d02d7', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/late-current-physical-preparation-1/actual-copy3-current-binding-1/admission-preparation-1/run_root_sdk_readonly_admission.py': '618762b968032f3dc57067f5cb5aa698ea092de25e5e076ffa1ceecf9425ce22', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/late-current-physical-preparation-1/actual-copy3-current-binding-1/admission-preparation-1/capture_root_sdk_readonly_admission_once.py': '5d625437e6904e95cf0c30447cc00fff283380d8d1222066d6cbaea0e6511dd4', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/late-current-physical-preparation-1/actual-copy3-current-binding-1/admission-preparation-1/QUERY-INPUTS.ROOT.json': 'eb922386afaf5fdc19992e927dd629a8e5b14ab02bea25f4d3893119b06b1783', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/late-current-physical-preparation-1/actual-copy3-current-binding-1/ROOT-OWNER-ENTRY.PENDING.json': '6d97501aaade7903eee60b828a3d000a6120dde86ee8f5f8a6631a0701d26ea1', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-M14-copy3-normal-failure-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json': 'ca8334ef5308302e46b3e1f079c408144df03c1b998c5c80b105a36e84335378', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-M14-copy3-normal-failure-postjoin-1/CURRENT-LIVE-POSTJOIN.json': '6d375e684a8eb443124c683fb25c0c298afcc7f0a4819ebb67b824bcbcc0d6d2'}
PHYSICAL_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-M14-copy3-normal-failure-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json')
POSTJOIN_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-M14-copy3-normal-failure-postjoin-1/CURRENT-LIVE-POSTJOIN.json')
REQUEST_SHA = '08518322d3121354ccbffbead70072ed763102b859b7e9283b440b7ca503f6ea'
SOURCE_APPROVAL_PATH=R/'ROOT-RECORDED-INDEPENDENT-CORRECTED-SOURCE-APPROVAL.json'
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
if sys.argv[1]=='--prepare-review-payload':
    assert len(sys.argv)==4
    SOURCE_APPROVAL_SHA=sys.argv[3]
else:
    prior_payload,_,_=read(D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json')
    assert prior_payload['source_review']['path']==str(SOURCE_APPROVAL_PATH)
    SOURCE_APPROVAL_SHA=prior_payload['source_review']['sha256']
assert re.fullmatch('[0-9a-f]{64}',SOURCE_APPROVAL_SHA)
source_review,_,_=read(SOURCE_APPROVAL_PATH,SOURCE_APPROVAL_SHA)
source_map=pinned(R/'ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json')
historical_retention=pinned(Path('/home/holden/mckernel/docs/verification/evidence/m15-target-tools-libdwarf-source-20261024-1/RETENTION.json'))
retention=pinned(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/EXACT-CACHE-CORRECTED-SOURCE-DELTA.INPUTS.json'))
physical=pinned(PHYSICAL_PATH);postjoin=pinned(POSTJOIN_PATH)
assert request['nonce']==base['nonce']=='1315033c6e40480ea1b61cf8159c0c19'
assert base['request']==dict(path=str(R/'REQUEST.ROOT.FINAL.json'),sha256=REQUEST_SHA)
assert source_review['decision']=='PASS_SOURCE' and source_review['implementation_ownership'] is False
assert source_review['source_sha256']==source_map['source_sha256']==base['source_sha256'] and source_review['reviewer']!=base['author']
assert source_review['reviewed_ready_sha256']=='4356b66cb70d0ad140806807ad42d2788508d0fbba1a47d2f04af66066ba191b'
assert physical['status']=='PASS_ACTUAL_M14_COPY3_NORMAL_FAILED_IMAGE_PHYSICAL_RETIREMENT' and physical['artifact_native_acceptance'] is False
assert postjoin['status']=='ACCEPTED_NON_NULL' and postjoin['physical_acceptance']['sha256']==PINS[str(PHYSICAL_PATH)]
assert postjoin['original_workload_status']=='FAIL' and postjoin['artifact_native_acceptance'] is False
assert base['execution_review'] is None and base['status']=='PENDING_FRESH_ADMISSION_PUBLICATION_AND_INDEPENDENT_EXECUTION_REVIEW'
assert base['source_review'] is None and base['aggregate_review'] is None
base['source_review']=dict(path=str(SOURCE_APPROVAL_PATH),sha256=SOURCE_APPROVAL_SHA)
base['aggregate_review']={'CPU1_excluded': True, 'control_monitor_bytes': 4026531840, 'full_campaign_required_bytes': 25501368320, 'heavy_CPUs': [2, 3, 4, 5], 'heavy_memory_bytes': 12884901888, 'host_reserve_bytes': 4294967296, 'memory_available': None, 'one_heavy': True, 'ordinary_CPUs': [0, 6], 'ordinary_memory_each': 2147483648, 'scratch_actual': None, 'scratch_required': None}
E=D/'root-query-export-1';payload_path=D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json'
FETCHED_COMMIT='c76ed1355b80d9fbe59c63d59b5dfe503965639b'
FETCHED_TREE=None
fetched_path=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/ROOT-FETCHED-CACHE-CORRECTED-SOURCE-PROOF.json')
if sys.argv[1]=='--prepare-review-payload':
    assert len(sys.argv)==4
    expected_fetch_sha=sys.argv[2]
else:
    assert len(sys.argv)==4
    pending,_,_=read(payload_path);assert pending['fetched_source_proof']['path']==str(fetched_path)
    expected_fetch_sha=pending['fetched_source_proof']['sha256']
assert re.fullmatch('[0-9a-f]{64}',expected_fetch_sha)
fetched,fetched_ref,_=read(fetched_path,expected_fetch_sha)
assert fetched['status']=='PASS_FETCHED_COMMIT_AND_LOCAL_BLOB_VERIFICATION'
assert fetched['archive_members_verified']==18 and len(fetched['files'])==6
assert fetched['base66_fetched_source_proof']=={'bytes': 6319, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/selected-source-1/publication-admission-preparation-1/ROOT-FETCHED-CANONICAL-SOURCE-PROOF.json', 'sha256': '8841640212c494bfc5aa1ac2d497534950abe4b58ec386fa395e585ae8e4e5a6'}
assert expected_fetch_sha=='4d1da90e7e52c1495df458f79c49a520afaf6fef12e23b2153c8aeea2febaf00'
assert FETCHED_COMMIT is not None and fetched['commit']==fetched['fetched_commit']==FETCHED_COMMIT
base66,_,_=read(fetched['base66_fetched_source_proof']['path'],fetched['base66_fetched_source_proof']['sha256'])
assert base66['status']=='PASS_FETCHED_NINE_RETIREMENT_AND_CANONICAL_SDK11_DELTA_MEMBERS' and base66['target_members']==66
assert historical_retention['archive_sha256']=='ea2bbabe4f6b881eb12e4096e80ab3e8b4e08dc53073ed1c255b9e306521cd0b' and historical_retention['archive_bytes']==187411
assert len(historical_retention['members'])==14
assert retention['member_count']==18 and len(retention['members'])==18
retained={x['path']:x for x in retention['members'].values()}
for path,expected in ((str(R/'REQUEST.ROOT.FINAL.json'),REQUEST_SHA),(str(R/'ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json'),PINS[str(R/'ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json')]),(source_map['owner']['path'],source_map['owner']['sha256']),(source_map['driver']['path'],source_map['driver']['sha256'])):
    assert retained[path]['sha256']==expected
# Only an actual fetched currentphysical/query overlay permits payload publication.
CURRENT_OVERLAY_FETCHED_PROOF=None
assert CURRENT_OVERLAY_FETCHED_PROOF is not None, 'genuine fetched COPY3 currentauthority overlay required'
overlay,overlay_ref,_=read(CURRENT_OVERLAY_FETCHED_PROOF['path'],CURRENT_OVERLAY_FETCHED_PROOF['sha256'])
assert overlay['status']=='PASS_FETCHED_CANONICAL_SDK11_COPY3_CURRENT_AUTHORITY_OVERLAY'
assert overlay['base_source_proof']=={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/ROOT-FETCHED-CACHE-CORRECTED-SOURCE-PROOF.json', 'sha256': '4d1da90e7e52c1495df458f79c49a520afaf6fef12e23b2153c8aeea2febaf00', 'bytes': 2361}
assert overlay['current_physical']=={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-M14-copy3-normal-failure-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json', 'sha256': 'ca8334ef5308302e46b3e1f079c408144df03c1b998c5c80b105a36e84335378', 'bytes': 788} and overlay['current_postjoin']=={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-M14-copy3-normal-failure-postjoin-1/CURRENT-LIVE-POSTJOIN.json', 'sha256': '6d375e684a8eb443124c683fb25c0c298afcc7f0a4819ebb67b824bcbcc0d6d2', 'bytes': 1622}
assert overlay['query_source']=={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/late-current-physical-preparation-1/actual-copy3-current-binding-1/admission-preparation-1/run_root_sdk_readonly_admission.py', 'sha256': '618762b968032f3dc57067f5cb5aa698ea092de25e5e076ffa1ceecf9425ce22', 'bytes': 40257} and overlay['query_inputs']=={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/selected-source-1/publication-admission-preparation-1/late-current-physical-preparation-1/actual-copy3-current-binding-1/admission-preparation-1/QUERY-INPUTS.ROOT.json', 'sha256': 'eb922386afaf5fdc19992e927dd629a8e5b14ab02bea25f4d3893119b06b1783', 'bytes': 340}
assert overlay['member_count']==15 and overlay['retirement_members']==9
assert overlay['commit']==overlay['fetched_commit'] and re.fullmatch('[0-9a-f]{40}',overlay['commit']) and re.fullmatch('[0-9a-f]{40}',overlay['tree'])

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
    base.update(current_authority_source_proof={k:overlay_ref[k] for k in ('path','sha256')},status='PASS_EXECUTION_RELEASE',fetched_source_verified=True,fetched_source_proof={k:fetched_ref[k] for k in ('path','sha256')},
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
    entry_ref=write(R/'ROOT-OWNER-ENTRY.FINAL.LIBDWARF1.json',entry)
    print(json.dumps(dict(status='REVIEWED_RELEASE_PUBLISHED_OWNER_NOT_EXECUTED',release=release_ref,ordinary_entry=entry_ref,query_age_seconds=now-query['at'])))
