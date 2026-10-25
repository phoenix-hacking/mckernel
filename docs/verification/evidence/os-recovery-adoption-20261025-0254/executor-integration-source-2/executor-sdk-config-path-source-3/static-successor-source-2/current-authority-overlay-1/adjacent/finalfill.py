"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
ROOT metadata only: exact existing query export/reviewed release flow specialized for target tools.
No owner/query/compiler/SDK imports or execution; core runtime source remains unchanged.
"""
from pathlib import Path
import hashlib,json,os,stat,sys,time,re
COHORT_AUTHORITY = None
assert isinstance(COHORT_AUTHORITY,dict), 'genuine new sourceapproval/fetched/overlay data fill required before effects'
D=Path(__file__).parent
R = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2')
P = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2')
A = D/'admission-preparation-final-3'
PINS = {'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/0/stdout': 'bb590c25363d85b13891e32488fb8908b7f57516800fc6866fad4786691c1b3b', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/0/WHOLE-JOIN.json': 'a8cf67e3c903967e91c4afaa19d62f92f62c3499a4849a52410525bb9b5255be', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/1/stdout': 'b6a7299d619b90f259266c81ce7854f9d7b8ba4a0268e43472be9ddfddbc3e2b', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/1/WHOLE-JOIN.json': '2b7dd253ba77884258fbba28429cc6586d438721c7841c39250d1f734f58890d', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/actual-helpers-postjoin-1/0/stdout': 'cefc273b7d75ba8ed0db9a335e252218f10523a47d68f1995d6afdb3fc60ea9f', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/actual-helpers-postjoin-1/0/WHOLE-JOIN.json': '6c88fdd3e4c919332d339714f1c18ad3ae6b4987c137b6213ca3e09276c20290', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/readonly_precommand_failure_current_proc.py': '8e1fc7a311033477545d159fbc4b1908509929778427087582179056a474ab5b', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/readonly_precommand_failure_mutex_physical.py': 'b3a4c546e18fae0cc7d0618eadc86b2bb50cefc7affd35298b36a63536de9d79', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/readonly_precommand_failure_helpers_postjoin.ACTUAL-CAPTURES.NOT-RELEASED.py': '2186f550e42afa56eeec739e07e1e63526eeaaa25c8bcabf8085fd6d22ba579a', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/7058-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json': '6e32c7c54e30fd7a4d51cc892cd37396f6cbd85f4e211ff0770329db4edb8b3a', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/EXACT-PRECOMMAND-FAILURE-POSTFLIGHT.INPUTS.json': '7042f15da517b0822b7a84df1bcebdaab2ee777ed5592cf2b538f5dfc7245971', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/ROOT-REPORTED-ACTUAL-OWNER-TOOL-TERMINAL.json': '852ea997a6995978ced0778ac1d6ea1c6d54779ba116e879ab2ae7a96374b62a', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/REQUEST.FRESH-CONFIG-CORRECTED.SOURCE-ONLY.json': '8a1af031860a78fbd729af2cf1b3f78606c372c2288910af6c9f5e2f551c0ab4', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/EXACT-ELEVEN-SOURCE-MAP.FRESH-CONFIG-CORRECTED.json': 'dd1dcba5e5e790e963e652766e1fa72bcd791a56a932c6bc99f32616b5a9a896', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/admission-preparation-final-3/run_root_sdk_readonly_admission.py': 'e2baa80982d2d9eb35c0a2811d5723f8e05a6aa84854696dfebb315f0c0fd48b', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/admission-preparation-final-3/QUERY-INPUTS.ROOT.json': '5addd24898e3105da515a7777b59b55aa2ea22da0cce6a11582592d8caf5047a', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/ROOT-OWNER-ENTRY.PENDING.json': '0ea43e855e3bf357be00e8e76ea9b3e9acb7c8fb4fa9885a606e6c91179d5bc4', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/RELEASE.ROOT.PENDING-NO-CLOCK-NO-APPROVAL.json': '62398841b963af1ab4dda28defa21d01c8826a0d5a0cd97a60196e26a77ce0e2', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-RECORDED-CORRECTED-EXECUTOR52F7-SOURCE-REVIEW.json': '8adaefca96b55ebdefb6d517e4c37744d3f9d61274ff387a0e709b6f3c2be8c5'}
PHYSICAL_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/1/stdout')
POSTJOIN_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/actual-helpers-postjoin-1/0/stdout')
REQUEST_SHA = '8a1af031860a78fbd729af2cf1b3f78606c372c2288910af6c9f5e2f551c0ab4'
SOURCE_APPROVAL_PATH = Path(COHORT_AUTHORITY['source_approval']['path'])
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
request=pinned(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/REQUEST.FRESH-CONFIG-CORRECTED.SOURCE-ONLY.json'))
if sys.argv[1]=='--prepare-review-payload':
    assert len(sys.argv)==4
    SOURCE_APPROVAL_SHA=sys.argv[3]
else:
    prior_payload,_,_=read(D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json')
    assert prior_payload['source_review']['path']==str(SOURCE_APPROVAL_PATH)
    SOURCE_APPROVAL_SHA=prior_payload['source_review']['sha256']
assert re.fullmatch('[0-9a-f]{64}',SOURCE_APPROVAL_SHA)
source_review,_,_=read(SOURCE_APPROVAL_PATH,SOURCE_APPROVAL_SHA)
source_map=pinned(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/EXACT-ELEVEN-SOURCE-MAP.FRESH-CONFIG-CORRECTED.json'))
assert request['nonce']==base['nonce']=='52f76375b2944beeabbc456aa483ed8a'
assert base['request']==dict(path=str(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/REQUEST.FRESH-CONFIG-CORRECTED.SOURCE-ONLY.json')),sha256=REQUEST_SHA)
assert SOURCE_APPROVAL_SHA==COHORT_AUTHORITY['source_approval']['sha256']
assert source_review==COHORT_AUTHORITY['source_approval_expected']
assert source_review['schema']=='mckernel.m15.executor.sdk11.owner-consumable-source-review.v1'
assert source_review['decision']=='PASS_SOURCE' and source_review['reviewer']=='/root/recovery_review' and source_review['implementation_ownership'] is False
assert source_review['request_sha256']==REQUEST_SHA and source_review['source_map_sha256']=='dd1dcba5e5e790e963e652766e1fa72bcd791a56a932c6bc99f32616b5a9a896'
assert source_review['source_sha256']==source_map['source_sha256']==base['source_sha256']
assert source_review['execution_release'] is False and source_review['sdk_execution'] is False and source_review['native_acceptance'] is False
primary_source_approval,primary_ref,_=read('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-RECORDED-CORRECTED-EXECUTOR52F7-SOURCE-REVIEW.json','8adaefca96b55ebdefb6d517e4c37744d3f9d61274ff387a0e709b6f3c2be8c5')
assert primary_ref=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-RECORDED-CORRECTED-EXECUTOR52F7-SOURCE-REVIEW.json', 'bytes': 1180, 'sha256': '8adaefca96b55ebdefb6d517e4c37744d3f9d61274ff387a0e709b6f3c2be8c5'} and primary_source_approval=={'status': 'PASS_SOURCE_DATA_CORRECTION', 'reviewer': '/root/recovery_review', 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'at': '2026-10-25T06:00:29.197745+00:00', 'ready_sha256': '007a88612e7915d5cb83f57c8a2ac8dc68310862b476d0611d258990e04259fb', 'request_sha256': '8a1af031860a78fbd729af2cf1b3f78606c372c2288910af6c9f5e2f551c0ab4', 'map_sha256': 'dd1dcba5e5e790e963e652766e1fa72bcd791a56a932c6bc99f32616b5a9a896', 'manifest_sha256': 'c57ecf1deacb66c43a0cb894c3a257da1750b784cd387b157d105a930995c925', 'owner_sha256': '22ff30ec69053d9022e5ce755c37c8d6abce774e91c4eed19bc26e5f12d6f357', 'driver_sha256': '8543093fbfa216a69de29fcec0866370fca1f53409afe67540fa33c03e1b3cc0', 'changes': 'CONFIG literal points to exact actually mounted preparation; owner function/class AST unchanged; request input namespace corrected to actual PREPARATION.parent; exact15pins match. Four host config controls passed.', 'query_source_status': 'Separate syntax correction and full-source parse required before query release; original9849 preserved unrun.', 'execution_authority': False, 'SDK_native_acceptance': False}
assert primary_source_approval['status']=='PASS_SOURCE_DATA_CORRECTION' and primary_source_approval['execution_authority'] is False
assert source_review['primary_source_approval_sha256']==primary_ref['sha256']
assert source_review['fetched_source_proof_sha256']==COHORT_AUTHORITY['fetched_source_proof']['sha256']
assert source_review['source15_archive_sha256']=='645581453aafdf3c09ff99219b18e3ca1dffaca8af17884e053c696db121c06e'
assert source_review['commit']==COHORT_AUTHORITY['fetched_commit'] and source_review['reviewer']!=base['author']
assert base['execution_review'] is None and base['status']=='PENDING_FRESH_ADMISSION_PUBLICATION_AND_INDEPENDENT_EXECUTION_REVIEW'
assert base['source_review'] is None and base['aggregate_review'] is None
assert base['current_physical'] is None and base['current_live_postjoin'] is None and base['fetched_source_verified'] is False
physical=pinned(PHYSICAL_PATH);postjoin=pinned(POSTJOIN_PATH)
def current_bound(ref):
    raw,actual,_=load_raw(ref['path'],ref['sha256'])
    assert actual==ref
    return json.loads(raw)

def current_join(label,stdout_label,pid,start):
    j=current_bound(CURRENT_REFS[label])
    assert j['returncode']==0 and all(j[k] is True for k in ('direct_child_joined','group_absent','closed_streams'))
    assert j['pid']==pid and str(j['start'])==start
    assert j['error'] is None and j['retirement_error'] is None and j['timed_out'] is False
    assert j['remaining_group_members']==j['unexpected_group_members']==[]
    out=j['captures']['stdout'];expected=CURRENT_REFS[stdout_label]
    assert {k:out[k] for k in ('path','sha256')}=={k:expected[k] for k in ('path','sha256')} and out['size']==expected['bytes']
    err=j['captures']['stderr'];raw,_,_=load_raw(err['path'],err['sha256']);assert len(raw)==err['size']==0
    return j

def current_bound_raw(ref):
    raw,actual,_=load_raw(ref['path'],ref['sha256']);assert actual==ref
    return raw
# Latest7058 normal retirement is distinct from retained historical M14/COPY evidence.
CURRENT_REFS = {'proc_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/0/stdout', 'bytes': 41905, 'sha256': 'bb590c25363d85b13891e32488fb8908b7f57516800fc6866fad4786691c1b3b'}, 'proc_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/0/WHOLE-JOIN.json', 'bytes': 1467, 'sha256': 'a8cf67e3c903967e91c4afaa19d62f92f62c3499a4849a52410525bb9b5255be'}, 'physical_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/1/stdout', 'bytes': 43509, 'sha256': 'b6a7299d619b90f259266c81ce7854f9d7b8ba4a0268e43472be9ddfddbc3e2b'}, 'physical_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/1/WHOLE-JOIN.json', 'bytes': 1465, 'sha256': '2b7dd253ba77884258fbba28429cc6586d438721c7841c39250d1f734f58890d'}, 'postjoin_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/actual-helpers-postjoin-1/0/stdout', 'bytes': 45869, 'sha256': 'cefc273b7d75ba8ed0db9a335e252218f10523a47d68f1995d6afdb3fc60ea9f'}, 'postjoin_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/actual-helpers-postjoin-1/0/WHOLE-JOIN.json', 'bytes': 1519, 'sha256': '6c88fdd3e4c919332d339714f1c18ad3ae6b4987c137b6213ca3e09276c20290'}, 'proc_source': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/readonly_precommand_failure_current_proc.py', 'bytes': 7914, 'sha256': '8e1fc7a311033477545d159fbc4b1908509929778427087582179056a474ab5b'}, 'physical_source': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/readonly_precommand_failure_mutex_physical.py', 'bytes': 9626, 'sha256': 'b3a4c546e18fae0cc7d0618eadc86b2bb50cefc7affd35298b36a63536de9d79'}, 'postjoin_source': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/removed-shape-and-candidate-identity-source-revision-2/readonly_precommand_failure_helpers_postjoin.ACTUAL-CAPTURES.NOT-RELEASED.py', 'bytes': 13507, 'sha256': '2186f550e42afa56eeec739e07e1e63526eeaaa25c8bcabf8085fd6d22ba579a'}, 'independent_current': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/7058-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json', 'bytes': 1787, 'sha256': '6e32c7c54e30fd7a4d51cc892cd37396f6cbd85f4e211ff0770329db4edb8b3a'}, 'manifest': {'bytes': 73789, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/EXACT-PRECOMMAND-FAILURE-POSTFLIGHT.INPUTS.json', 'sha256': '7042f15da517b0822b7a84df1bcebdaab2ee777ed5592cf2b538f5dfc7245971'}, 'direct_terminal': {'bytes': 1815, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/current-precommand-failure-physical-postflight-source-1/ROOT-REPORTED-ACTUAL-OWNER-TOOL-TERMINAL.json', 'sha256': '852ea997a6995978ced0778ac1d6ea1c6d54779ba116e879ab2ae7a96374b62a'}}
CURRENT_EXPECTED_INDEPENDENT = {'schema': 'mckernel.m15.executor.precommand-failure.current-acceptance.v1', 'status': 'PASS', 'reviewer': '/root/recovery_review', 'implementation_ownership': False, 'physical_accepted': True, 'current_live_postjoin_accepted': True, 'owner': {'pid': 544882, 'starttime': '70398463'}, 'runtime_nonce': '7058a5d1d2294d719c6c64cec6738ed3', 'operation_lease_nonce': '77ff7266402049ea80907137b833ec0e', 'manifest_sha256': '7042f15da517b0822b7a84df1bcebdaab2ee777ed5592cf2b538f5dfc7245971', 'physical_stdout_sha256': 'b6a7299d619b90f259266c81ce7854f9d7b8ba4a0268e43472be9ddfddbc3e2b', 'physical_join_sha256': '2b7dd253ba77884258fbba28429cc6586d438721c7841c39250d1f734f58890d', 'postjoin_stdout_sha256': 'cefc273b7d75ba8ed0db9a335e252218f10523a47d68f1995d6afdb3fc60ea9f', 'postjoin_whole_join_sha256': '6c88fdd3e4c919332d339714f1c18ad3ae6b4987c137b6213ca3e09276c20290', 'current_reader_identity': {'pid': 552409, 'starttime': '70515127', 'boot_id': '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'}, 'joined_direct_child': {'pid': 552406, 'starttime': '70515121', 'returncode': 0, 'group_absent': True}, 'owner_clients': 14, 'admission_clients': 1, 'prior_helpers': 4, 'client_births': None, 'inner_command_births': [], 'permanent_mutex_free_before': True, 'permanent_mutex_free_after': True, 'terminal_evidence_unchanged': True, 'original_workload_status': 'FAIL', 'SDK_commands_executed': 0, 'artifact_native_acceptance': False, 'heavy_execution_released': False, 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual7058 normal-retirement physical and current helper postjoin evidence only.', 'recorded_at': '2026-10-25T05:56:24.612547+00:00'}
current_proc=current_bound(CURRENT_REFS['proc_stdout'])
current_physical=current_bound(CURRENT_REFS['physical_stdout'])
current_postjoin=current_bound(CURRENT_REFS['postjoin_stdout'])
current_independent=current_bound(CURRENT_REFS['independent_current'])
current_manifest=current_bound(CURRENT_REFS['manifest'])
current_terminal=current_bound(CURRENT_REFS['direct_terminal'])
for key in ('proc_source','physical_source','postjoin_source'):current_bound_raw(CURRENT_REFS[key])
assert current_independent==CURRENT_EXPECTED_INDEPENDENT
assert current_independent['status']=='PASS' and current_independent['implementation_ownership'] is False
assert current_independent['reviewer']=='/root/recovery_review' and current_independent['physical_accepted'] is True and current_independent['current_live_postjoin_accepted'] is True
assert current_independent['heavy_execution_released'] is False and current_independent['artifact_native_acceptance'] is False
assert current_independent['owner']=={'pid':544882,'starttime':'70398463'} and current_independent['runtime_nonce']=='7058a5d1d2294d719c6c64cec6738ed3'
assert current_independent['operation_lease_nonce']=='77ff7266402049ea80907137b833ec0e'
assert current_independent['manifest_sha256']==CURRENT_REFS['manifest']['sha256']
assert current_independent['physical_stdout_sha256']==CURRENT_REFS['physical_stdout']['sha256'] and current_independent['physical_join_sha256']==CURRENT_REFS['physical_join']['sha256']
assert current_independent['postjoin_stdout_sha256']==CURRENT_REFS['postjoin_stdout']['sha256'] and current_independent['postjoin_whole_join_sha256']==CURRENT_REFS['postjoin_join']['sha256']
assert current_independent['current_reader_identity']==current_postjoin['current_reader_identity']
for value,identity in ((current_proc,{'boot_id':base['boot_id'],'pid':550935,'starttime':'70505046'}),(current_physical,{'boot_id':base['boot_id'],'pid':550940,'starttime':'70505075'}),(current_postjoin,{'boot_id':base['boot_id'],'pid':552409,'starttime':'70515127'})):
    assert value['current_reader_identity']==identity and value['owner']==current_independent['owner']
    assert value['manifest']==CURRENT_REFS['manifest'] and value['direct_terminal']==CURRENT_REFS['direct_terminal']
    assert value['client_births'] is None and value['inner_command_births']==[] and value['SDK_commands_executed']==0 and value['original_workload_status']=='FAIL'
    proc=value['proc'];assert proc['schema']=='fp-save-image.proc.v2' and proc['status']=='COMPLETE' and proc['uid']==0 and proc['boot_id']==base['boot_id']
    assert proc['failure'] is None and proc['publishers']==[] and len(proc['snapshots'])==2
    assert all(not any(row[0]==544882 for row in sweep) for sweep in proc['snapshots'])
assert current_proc['schema']==current_physical['schema']=='mckernel.m15.executor.precommand-failure.physical-readback.v1'
assert current_proc['status']=='PASS_M15_EXECUTOR_PRECOMMAND_FAILURE_EXACT_PROC' and current_proc['owner_client_count']==14 and current_proc['admission_client_count']==1
assert current_physical['status']=='PASS_M15_EXECUTOR_PRECOMMAND_FAILURE_MUTEX_HELD_CURRENT_PHYSICAL'
assert current_physical['container_absent']=={'id':'dd1882645eac95aaf7a3fc7c4f36a2ed36c048a8c3b8d80d39e0794117e9aef0','name':'mckernel-external-7058a5d1d2294d719c6c64cec6738ed3','nonce':'7058a5d1d2294d719c6c64cec6738ed3'}
assert current_physical['installed_artifacts']==[] and current_physical['artifact_native_acceptance'] is False
assert current_physical['owner_clients']==current_postjoin['owner_clients']==14 and current_physical['admission_clients']==current_postjoin['admission_clients']==1
assert current_physical['root_lock']==current_postjoin['root_lock']=={'device': 27, 'gid': 0, 'inode': 4, 'mode': '0o644', 'nlink': 1, 'path': '/run/lock/mckernel-development.lock', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'uid': 0}
assert current_physical['absence_paths']==current_postjoin['absence_paths']==['/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json', '/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json', '/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json']
assert current_postjoin['schema']=='mckernel.m15.executor.precommand-failure.postjoin-readback.v1'
assert current_postjoin['status']=='PASS_M15_EXECUTOR_PRECOMMAND_FAILURE_CURRENT_HELPERS_POSTJOIN_MUTEX_FREE'
assert current_postjoin['known_prior_helpers']==[{'pid': 550935, 'role': 'proc-python', 'starttime': '70505046'}, {'pid': 550932, 'role': 'proc-sudo', 'starttime': '70505039'}, {'pid': 550940, 'role': 'physical-python', 'starttime': '70505075'}, {'pid': 550937, 'role': 'physical-sudo', 'starttime': '70505068'}]
assert current_postjoin['prior_captures']=={k:CURRENT_REFS[k] for k in ('proc_stdout','proc_join','physical_stdout','physical_join')}
assert current_postjoin['permanent_mutex_free_before'] is True and current_postjoin['permanent_mutex_free_after'] is True and current_postjoin['flock_acquired'] is False and current_postjoin['terminal_evidence_unchanged'] is True
assert all(not any(row[0] in {550935,550932,550940,550937} for row in sweep) for sweep in current_postjoin['proc']['snapshots'])
current_join('proc_join','proc_stdout',550932,'70505039')
current_join('physical_join','physical_stdout',550937,'70505068')
current_join('postjoin_join','postjoin_stdout',552406,'70515121')


base['source_review']=dict(path=str(SOURCE_APPROVAL_PATH),sha256=SOURCE_APPROVAL_SHA)
base['source_approval_primary']={k:primary_ref[k] for k in ('path','sha256')}
base['aggregate_review']={'CPU1_excluded': True, 'control_monitor_bytes': 4026531840, 'full_campaign_required_bytes': 25501368320, 'heavy_CPUs': [2, 3, 4, 5], 'heavy_memory_bytes': 12884901888, 'host_reserve_bytes': 4294967296, 'memory_available': None, 'one_heavy': True, 'ordinary_CPUs': [0, 6], 'ordinary_memory_each': 2147483648, 'scratch_actual': None, 'scratch_required': None}
E=D/'root-query-export-1';payload_path=D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json'
FETCHED_SOURCE_PROOF = COHORT_AUTHORITY['fetched_source_proof']
fetched,fetched_ref,_=read(FETCHED_SOURCE_PROOF['path'],FETCHED_SOURCE_PROOF['sha256'])
assert fetched_ref==FETCHED_SOURCE_PROOF and fetched==COHORT_AUTHORITY['fetched_source_expected']
assert re.fullmatch('[0-9a-f]{40}',source_review['commit']) and source_review['commit']==COHORT_AUTHORITY['fetched_commit']
assert sys.argv[1]!='--prepare-review-payload' or sys.argv[2]==FETCHED_SOURCE_PROOF['sha256']
source15={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/EXACT-SOURCE15-CONFIG-CORRECTED-INPUTS.json', 'bytes': 8891, 'sha256': 'c57ecf1deacb66c43a0cb894c3a257da1750b784cd387b157d105a930995c925'}
manifest,manifest_ref,_=read(source15['path'],source15['sha256']);assert manifest_ref==source15
assert manifest['member_count']==len(manifest['members'])==15 and manifest['no_object_or_binary_build_outputs'] is True
for row in manifest['members'].values():
    raw,actual,_=load_raw(row['path'],row['sha256']);assert actual==row
assert {k[len('executor-runtime/'):]:v['sha256'] for k,v in manifest['members'].items() if k.startswith('executor-runtime/')}==base['source_sha256']
assert manifest['actual_request']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/REQUEST.FRESH-CONFIG-CORRECTED.SOURCE-ONLY.json', 'bytes': 3966, 'sha256': '8a1af031860a78fbd729af2cf1b3f78606c372c2288910af6c9f5e2f551c0ab4'} and manifest['actual11map']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/EXACT-ELEVEN-SOURCE-MAP.FRESH-CONFIG-CORRECTED.json', 'bytes': 3480, 'sha256': 'dd1dcba5e5e790e963e652766e1fa72bcd791a56a932c6bc99f32616b5a9a896'}
CURRENT_OVERLAY_FETCHED_PROOF = COHORT_AUTHORITY['overlay_fetched_proof']
overlay,overlay_ref,_=read(CURRENT_OVERLAY_FETCHED_PROOF['path'],CURRENT_OVERLAY_FETCHED_PROOF['sha256'])
assert overlay_ref==CURRENT_OVERLAY_FETCHED_PROOF and overlay==COHORT_AUTHORITY['overlay_fetched_expected']
assert overlay['status']=='PASS_FETCHED_SELECTED_INSTALL_CURRENT_AUTHORITY_OVERLAY'
assert overlay['source_proof']==FETCHED_SOURCE_PROOF
assert overlay['current_physical']==CURRENT_REFS['physical_stdout'] and overlay['current_postjoin']==CURRENT_REFS['postjoin_stdout']
assert overlay['query_source']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/admission-preparation-final-3/run_root_sdk_readonly_admission.py', 'bytes': 48795, 'sha256': 'e2baa80982d2d9eb35c0a2811d5723f8e05a6aa84854696dfebb315f0c0fd48b'} and overlay['query_inputs']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/static-successor-source-2/admission-preparation-final-3/QUERY-INPUTS.ROOT.json', 'bytes': 329, 'sha256': '5addd24898e3105da515a7777b59b55aa2ea22da0cce6a11582592d8caf5047a'}
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
