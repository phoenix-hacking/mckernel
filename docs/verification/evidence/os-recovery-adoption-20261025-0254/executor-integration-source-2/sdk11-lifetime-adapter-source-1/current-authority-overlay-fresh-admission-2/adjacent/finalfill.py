"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
ROOT metadata only: exact existing query export/reviewed release flow specialized for target tools.
No owner/query/compiler/SDK imports or execution; core runtime source remains unchanged.
"""
from pathlib import Path
import hashlib,json,os,stat,sys,time,re
D=Path(__file__).parent
R = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2')
P = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2')
A = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/admission-preparation-1')
PINS = {'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/namespace-path-correction-source-1/ROOT-NORMAL-CLEANUP-0521-RELEASE.ACTUAL.RELEASED.json': '110b6191dc0bf3172835657923f07aa68fc86d3e66d302464555c8ae6a063c35', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/namespace-path-correction-source-1/cleanup_current_retained_F03_image.SOURCE-ONLY.NOT-RELEASED.py': '0521202446ae694b90b5a80b57bd030f883af73f81fc32c2dcf92ad7c734f844', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/ROOT-RECORDED-INDEPENDENT-ACTUAL-CURRENT-POSTJOIN-ACCEPTANCE.json': '7d77715a48e09a3d1917a7057d06ea241e8f64068636992bb5c7a5715edb28a3', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/namespace-path-correction-source-1/actual-terminal-evidence-readable-readback-1/ROOT-TOOL-TERMINAL-AND-EXACT-RECORD-READBACK.json': 'f1b8582041aafa2c056d72e5dc0ae5a7cc48541d05959adf15abf390e7c17f2b', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/1/WHOLE-JOIN.json': '53390efec0fa57c254f4f04cb47bc4c2da8370693742528d2ea56ca761a6f2ea', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/readonly_current_terminal_mutex_physical.py': '331ae32ecc477284019a29431611a3d04b6e6154c5ce768c98f56012e35acae1', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/1/stdout': '26ca1a73e6c4c77f6aaa84ebee645538d56e5fea0b4639efaa42396fcdf74f10', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/0/WHOLE-JOIN.json': '6c397cebed43da7368e3ac1c9c6f6c03493b43f7386824dc04e8595b3f288017', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/readonly_current_helpers_postjoin.py': '7e5da049dcd7b84cdd68b86f4ca6429100692e3723e444a729b24cb10e6973d5', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/0/stdout': 'a50e932198d0cd0e44724c33fb91da16dc7845b5546c1566f1214462223d57bc', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/0/WHOLE-JOIN.json': '415c62ac1572ce4d2af32c16df7a9a60868e8068f63761b9dd8578101a3e10be', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/readonly_current_terminal_proc.py': '3854457269adb319a91ff5948863a015f70aa43cadb44a6f8e54168bfbbbe8ff', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/0/stdout': 'f14b880ce62c7a71ddc40a9bf20dda6833054ed23ba72beb4359bbcb2646678f', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/admission-preparation-1/run_root_sdk_readonly_admission.py': 'f34c0be23f993a2d765dae451e11994153ea87587f019d6093a1b6b0158c25dc', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/admission-preparation-1/QUERY-INPUTS.ROOT.json': '32ca7de65fa49e67b4ec7f4a2fa1609340a166cc2c3886d42d667b45e17988a9', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/RELEASE.ROOT.PENDING-NO-CLOCK-NO-APPROVAL.json': '6ee688810bd7aa4fcb03acc93e1a1f4225a4387968e48ca9b880fff3d230baef', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/ROOT-OWNER-ENTRY.PENDING.json': '62979f8172eb38246ac66da883396474d2ae4d6a86736fe3aa7b8b4d447490e0', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/REQUEST.FRESH-ADMISSION.SOURCE-ONLY.json': '19325f421683d1b46d2cbb31d309243f71b1cdc2082f2e942cb8a9bfc668df95', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/final-filled-source-1/ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json': 'aa90b5f7bfea70eead45d693a493af0c246b9e52e299f83b96a2461c92906139', '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-RECORDED-INDEPENDENT-EXECUTOR-OWNER-CONSUMABLE-SOURCE-REVIEW.json': '592f43de0a2aec0ae0d0e29111a31989247c0c6e57a19305bd402541a224f72c'}
PHYSICAL_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/1/stdout')
POSTJOIN_PATH = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/0/stdout')
REQUEST_SHA = '19325f421683d1b46d2cbb31d309243f71b1cdc2082f2e942cb8a9bfc668df95'
SOURCE_APPROVAL_PATH = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-RECORDED-INDEPENDENT-EXECUTOR-OWNER-CONSUMABLE-SOURCE-REVIEW.json')
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
request=pinned(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/REQUEST.FRESH-ADMISSION.SOURCE-ONLY.json'))
if sys.argv[1]=='--prepare-review-payload':
    assert len(sys.argv)==4
    SOURCE_APPROVAL_SHA=sys.argv[3]
else:
    prior_payload,_,_=read(D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json')
    assert prior_payload['source_review']['path']==str(SOURCE_APPROVAL_PATH)
    SOURCE_APPROVAL_SHA=prior_payload['source_review']['sha256']
assert re.fullmatch('[0-9a-f]{64}',SOURCE_APPROVAL_SHA)
source_review,_,_=read(SOURCE_APPROVAL_PATH,SOURCE_APPROVAL_SHA)
source_map=pinned(Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/final-filled-source-1/ACTUAL-FINAL-ELEVEN-SOURCE-MAP.json'))
assert request['nonce']==base['nonce']=='7058a5d1d2294d719c6c64cec6738ed3'
assert base['request']==dict(path=str(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/REQUEST.FRESH-ADMISSION.SOURCE-ONLY.json')),sha256=REQUEST_SHA)
assert SOURCE_APPROVAL_SHA=='592f43de0a2aec0ae0d0e29111a31989247c0c6e57a19305bd402541a224f72c'
assert source_review['schema']=='mckernel.m15.executor.sdk11.owner-consumable-source-review.v1'
assert source_review['reviewer']=='/root/recovery_review'
assert source_review['primary_source_approval_sha256']=='caeca42d8c7784fe5a1f59498492f90d93b85b3b51b923907d461a19fe052ce0'
assert source_review['fetched_source_proof_sha256']=='89814b13b5f0c77bc60961a88e872458701736833410a0232e6bc624661064e4'
assert source_review['request_sha256']=='4f267f659a2fa85e653bfb42e651317d6e961997a349c3b7c6bdf4a037da3c81' and source_review['source_map_sha256']=='aa90b5f7bfea70eead45d693a493af0c246b9e52e299f83b96a2461c92906139'
assert source_review['source15_archive_sha256']=='b8ec51d0e886b487c3214577e70eb54367a0c3ec8ad83dc97fd5fa91a436c222'
assert source_review['commit']=='07d803c4c7c5b0a6945becb746ca71ab5ca1df3e'
assert source_review['execution_release'] is False and source_review['sdk_execution'] is False and source_review['native_acceptance'] is False
primary_source_approval,primary_ref,_=read('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-RECORDED-INDEPENDENT-EXECUTOR-SDK11-SOURCE-APPROVAL.json','caeca42d8c7784fe5a1f59498492f90d93b85b3b51b923907d461a19fe052ce0')
assert primary_ref=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-RECORDED-INDEPENDENT-EXECUTOR-SDK11-SOURCE-APPROVAL.json', 'sha256': 'caeca42d8c7784fe5a1f59498492f90d93b85b3b51b923907d461a19fe052ce0', 'bytes': 1695}
assert source_review['decision']=='PASS_SOURCE' and source_review['implementation_ownership'] is False
assert source_review['source_sha256']==source_map['source_sha256']==base['source_sha256'] and source_review['reviewer']!=base['author']
assert base['execution_review'] is None and base['status']=='PENDING_FRESH_ADMISSION_PUBLICATION_AND_INDEPENDENT_EXECUTION_REVIEW'
assert base['source_review'] is None and base['aggregate_review'] is None
assert base['current_physical'] is None and base['current_live_postjoin'] is None and base['fetched_source_verified'] is False
physical=pinned(PHYSICAL_PATH);postjoin=pinned(POSTJOIN_PATH)
# Current F03 closure is a readonly terminal readback; original tool stdout/PID remain unavailable.
CURRENT_REFS = {'proc_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/0/stdout', 'sha256': 'f14b880ce62c7a71ddc40a9bf20dda6833054ed23ba72beb4359bbcb2646678f', 'bytes': 45483}, 'proc_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/0/WHOLE-JOIN.json', 'sha256': '415c62ac1572ce4d2af32c16df7a9a60868e8068f63761b9dd8578101a3e10be', 'bytes': 1300}, 'physical_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/1/stdout', 'sha256': '26ca1a73e6c4c77f6aaa84ebee645538d56e5fea0b4639efaa42396fcdf74f10', 'bytes': 47837}, 'physical_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/1/WHOLE-JOIN.json', 'sha256': '53390efec0fa57c254f4f04cb47bc4c2da8370693742528d2ea56ca761a6f2ea', 'bytes': 1301}, 'postjoin_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/0/stdout', 'sha256': 'a50e932198d0cd0e44724c33fb91da16dc7845b5546c1566f1214462223d57bc', 'bytes': 45508}, 'postjoin_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/0/WHOLE-JOIN.json', 'sha256': '6c397cebed43da7368e3ac1c9c6f6c03493b43f7386824dc04e8595b3f288017', 'bytes': 1294}, 'independent_current': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/ROOT-RECORDED-INDEPENDENT-ACTUAL-CURRENT-POSTJOIN-ACCEPTANCE.json', 'sha256': '7d77715a48e09a3d1917a7057d06ea241e8f64068636992bb5c7a5715edb28a3', 'bytes': 1348}, 'proc_source': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/readonly_current_terminal_proc.py', 'sha256': '3854457269adb319a91ff5948863a015f70aa43cadb44a6f8e54168bfbbbe8ff', 'bytes': 8866}, 'physical_source': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/standalone-terminal-evidence-source-1/readonly_current_terminal_mutex_physical.py', 'sha256': '331ae32ecc477284019a29431611a3d04b6e6154c5ce768c98f56012e35acae1', 'bytes': 11768}, 'postjoin_source': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/readonly_current_helpers_postjoin.py', 'sha256': '7e5da049dcd7b84cdd68b86f4ca6429100692e3723e444a729b24cb10e6973d5', 'bytes': 8518}, 'engine': {'bytes': 119427, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/namespace-path-correction-source-1/cleanup_current_retained_F03_image.SOURCE-ONLY.NOT-RELEASED.py', 'sha256': '0521202446ae694b90b5a80b57bd030f883af73f81fc32c2dcf92ad7c734f844'}, 'consumed_release': {'bytes': 305255, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/namespace-path-correction-source-1/ROOT-NORMAL-CLEANUP-0521-RELEASE.ACTUAL.RELEASED.json', 'sha256': '110b6191dc0bf3172835657923f07aa68fc86d3e66d302464555c8ae6a063c35'}, 'original_summary': {'bytes': 4698, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/namespace-path-correction-source-1/actual-terminal-evidence-readable-readback-1/ROOT-TOOL-TERMINAL-AND-EXACT-RECORD-READBACK.json', 'sha256': 'f1b8582041aafa2c056d72e5dc0ae5a7cc48541d05959adf15abf390e7c17f2b'}}

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

current_proc=current_bound(CURRENT_REFS['proc_stdout'])
current_physical=current_bound(CURRENT_REFS['physical_stdout'])
current_postjoin=current_bound(CURRENT_REFS['postjoin_stdout'])
current_independent=current_bound(CURRENT_REFS['independent_current'])
current_original=current_bound(CURRENT_REFS['original_summary'])
for key in ('proc_source','physical_source','postjoin_source','engine'):
    r=CURRENT_REFS[key];raw,actual,_=load_raw(r['path'],r['sha256']);assert actual==r
current_bound(CURRENT_REFS['consumed_release'])
assert current_original['original_tool']=={'session_id': 94729, 'exit': 0, 'observed_status': 'PASS_EXECUTED', 'observed_terminal': True, 'observed_container_absent': True, 'full_stdout_retained': False, 'tool_reported_original_token_count': 92949, 'original_cleanup_pid_birth': None, 'capture_limitation': 'Tool truncated original stdout. These five fresh stable readonly captures match exact hashes visible in original output; this is not reconstruction of original full result.'}
assert current_original['container_id']=='8755eabd5b130d062687e8de762089e1757ddce2503184a2d576496c2cba7d8b'
assert current_original['observed_canonical_plan_sha256']=='847f788a4e073dd32af5cb6bd0ff82959e8423aa0125e2fcd9fa8ce2e211a85f'
assert current_original['observed_canonical_release_sha256']=='96a67386603babca7fcef7719cc8db517f6a4b133f46f891b90c4814e2851072'
for value,identity in ((current_proc,{'boot_id': '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb', 'pid': 519211, 'starttime': '70039029'}),(current_physical,{'boot_id': '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb', 'pid': 519216, 'starttime': '70039056'}),(current_postjoin,{'boot_id': '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb', 'pid': 520757, 'starttime': '70057143'})):
    assert value['current_reader_identity']==identity and identity['boot_id']==base['boot_id']
    assert value['original_cleanup_identity'] is None and value['original_full_stdout'] is None
    assert value['stdout_capture_complete'] is False and value['artifact_native_acceptance'] is False and value['cleanup_replayed'] is False
    assert value['source_engine']==CURRENT_REFS['engine'] and value['original_execution_summary']==CURRENT_REFS['original_summary']
    p=value['proc'];assert p['schema']=='fp-save-image.proc.v2' and p['status']=='COMPLETE'
    assert p['uid']==0 and p['boot_id']==base['boot_id'] and p['failure'] is None
    assert p['publishers']==[] and len(p['snapshots'])==2
for value in (current_proc,current_physical):
    assert value['schema']=='mckernel.m14.current-retained-normal-retirement.terminal-readback.v1'
    assert value['status']=='PASS_READONLY_CURRENT_TERMINAL_VALIDATION'
    assert value['original_execution']==current_original['original_tool']
    assert value['consumed_cleanup_release']==CURRENT_REFS['consumed_release']
    assert value['exact_cleanup_argv_in_full_process_scan'] is True
    assert value['exact_original_cleanup_argv']==['/home/holden/anaconda3/bin/python3', '-I', '-B', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/namespace-path-correction-source-1/cleanup_current_retained_F03_image.SOURCE-ONLY.NOT-RELEASED.py', '--release', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/namespace-path-correction-source-1/ROOT-NORMAL-CLEANUP-0521-RELEASE.ACTUAL.RELEASED.json', '--release-sha256', '110b6191dc0bf3172835657923f07aa68fc86d3e66d302464555c8ae6a063c35', '--execute']
assert current_physical['root_lock']=={'device': 27, 'gid': 0, 'inode': 4, 'mode': '0o644', 'nlink': 1, 'path': '/run/lock/mckernel-development.lock', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'uid': 0}
assert current_physical['transaction_mutex']=={'device': 1828, 'gid': 1000, 'inode': 116852, 'mode': '0o600', 'nlink': 1, 'path': '/home/holden/mckernel-work/scratch/m14-current-F03-normal-retirement-20261025-1.mutex', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'uid': 1000}
assert current_physical['container_absent']=={'id': '8755eabd5b130d062687e8de762089e1757ddce2503184a2d576496c2cba7d8b', 'name': 'mckernel-image-218635b6fb44421fb6c6a76a3cb229c8', 'runtime_nonce': '376e6cf1b5d046fdaaa32fc23192c757'}
assert current_physical['controller_lease_nonce']=='10c01a3e8c7b48a8984aec14fe3762c3'
assert current_physical['preserved_inventory_rows']==622 and current_physical['preserved_selected_files']==67 and current_physical['journal_events']==9
assert current_physical['observed_terminal_records']==[{'device': 1828, 'gid': 1000, 'inode': 116856, 'mode': '0o600', 'nlink': 1, 'path': '/home/holden/mckernel-work/scratch/m14-current-F03-normal-retirement-20261025-1.plan.json', 'sha256': '3ebe5211e211087fc24c82db105c9481dd0c69cb081355f2c54f0b5cd1736763', 'size': 4129, 'uid': 1000}, {'device': 1828, 'gid': 1000, 'inode': 116855, 'mode': '0o600', 'nlink': 1, 'path': '/home/holden/mckernel-work/scratch/m14-current-F03-normal-retirement-20261025-1.journal.jsonl', 'sha256': '16cd807a81cab6db4a8d91c5da5de9804ca2cdeddb269a63db73d103aa597f5a', 'size': 2797, 'uid': 1000}, {'device': 1828, 'gid': 1000, 'inode': 116853, 'mode': '0o600', 'nlink': 1, 'path': '/home/holden/mckernel-work/scratch/m14-current-F03-normal-retirement-20261025-1.docker-logs.capture', 'sha256': '527b09f8bf700f7e10eb692ae471c4766c21985b5be6a5b05f0fd867e8d7b9ae', 'size': 9562, 'uid': 1000}, {'device': 66306, 'gid': 1000, 'inode': 59402135, 'mode': '0o600', 'nlink': 1, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/m14-current-F03-normal-retirement-20261025-1.attempt.archive', 'sha256': '0ebc1fa3fd02bdae98645f562da5d452b3675d7ef0e9af61c7c23af004a9b2d7', 'size': 271, 'uid': 1000}, {'device': 1828, 'gid': 1000, 'inode': 116848, 'mode': '0o600', 'nlink': 1, 'path': '/home/holden/mckernel-work/scratch/m14-current-F03-normal-retirement-20261025-1.shared.archive', 'sha256': '18a28026d4f78de7f4230962d6acefe02d6bc5eb7ff3e7781f17287ff5dacd5c', 'size': 268, 'uid': 1000}]
assert current_physical['canonical_plan_sha256']==current_original['observed_canonical_plan_sha256']
assert current_physical['canonical_release_sha256']==current_original['observed_canonical_release_sha256']
assert current_postjoin['schema']=='mckernel.m14.current-retained-normal-retirement.postjoin-readback.v1'
assert current_postjoin['status']=='PASS_READONLY_CURRENT_HELPERS_POSTJOIN_MUTEX_FREE'
assert current_postjoin['known_prior_helpers']==[{'pid': 519211, 'role': 'proc-python', 'starttime': '70039029'}, {'pid': 519216, 'role': 'physical-python', 'starttime': '70039056'}, {'pid': 519208, 'role': 'proc-sudo', 'starttime': '70039022'}, {'pid': 519213, 'role': 'physical-sudo', 'starttime': '70039049'}]
assert current_postjoin['prior_captures']=={k:CURRENT_REFS[k] for k in ('proc_stdout','proc_join','physical_stdout','physical_join')}
assert current_postjoin['root_lock']==current_physical['root_lock'] and current_postjoin['transaction_mutex']==current_physical['transaction_mutex']
assert current_postjoin['absence_paths']==current_physical['absence_paths']==['/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json', '/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json', '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/retained-validation-attempt-1/lease.json', '/home/holden/mckernel-work/scratch/m14-current-F03-normal-retirement-20261025-1.quarantine.json']
assert current_postjoin['permanent_mutex_free_before'] is True and current_postjoin['permanent_mutex_free_after'] is True
assert current_postjoin['flock_acquired'] is False and current_postjoin['terminal_evidence_unchanged'] is True
assert current_independent=={'schema': 'mckernel.m14.current-retained-normal-retirement.current-postjoin-acceptance.v1', 'status': 'PASS', 'reviewer': '/root/recovery_review', 'implementation_ownership': False, 'physical_accepted': True, 'current_live_postjoin_accepted': True, 'evidence_directory': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261024-2/m14-f02-contract-source-1/retained-validation-queue-source-1/current-retained-validator-postflight-source-1/current-helpers-postjoin-source-1/0', 'stdout_sha256': 'a50e932198d0cd0e44724c33fb91da16dc7845b5546c1566f1214462223d57bc', 'whole_join_sha256': '6c397cebed43da7368e3ac1c9c6f6c03493b43f7386824dc04e8595b3f288017', 'new_reader_identity': {'pid': 520757, 'starttime': '70057143', 'boot_id': '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'}, 'joined_direct_child': {'pid': 520754, 'starttime': '70057136', 'returncode': 0, 'group_absent': True}, 'prior_four_helpers_and_descendants_absent': True, 'permanent_mutex_free_before': True, 'permanent_mutex_free_after': True, 'terminal_evidence_unchanged': True, 'original_cleanup_identity': None, 'original_full_stdout': None, 'original_stdout_capture_complete': False, 'new_reader_capture_complete': True, 'heavy_execution_released': False, 'artifact_native_acceptance': False}
assert current_independent['stdout_sha256']==CURRENT_REFS['postjoin_stdout']['sha256']
assert current_independent['whole_join_sha256']==CURRENT_REFS['postjoin_join']['sha256']
assert current_independent['new_reader_identity']==current_postjoin['current_reader_identity']
current_join('proc_join','proc_stdout',519208,'70039022')
current_join('physical_join','physical_stdout',519213,'70039049')
current_join('postjoin_join','postjoin_stdout',520754,'70057136')

base['source_review']=dict(path=str(SOURCE_APPROVAL_PATH),sha256=SOURCE_APPROVAL_SHA)
base['source_approval_primary']={k:primary_ref[k] for k in ('path','sha256')}
base['aggregate_review']={'CPU1_excluded': True, 'control_monitor_bytes': 4026531840, 'full_campaign_required_bytes': 25501368320, 'heavy_CPUs': [2, 3, 4, 5], 'heavy_memory_bytes': 12884901888, 'host_reserve_bytes': 4294967296, 'memory_available': None, 'one_heavy': True, 'ordinary_CPUs': [0, 6], 'ordinary_memory_each': 2147483648, 'scratch_actual': None, 'scratch_required': None}
E=D/'root-query-export-1';payload_path=D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json'
FETCHED_SOURCE_PROOF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ACTUAL-FETCHED-CURRENT55-EXECUTOR-SOURCE15-07d803.json', 'sha256': '89814b13b5f0c77bc60961a88e872458701736833410a0232e6bc624661064e4', 'bytes': 11429}
fetched_path=Path(FETCHED_SOURCE_PROOF['path'])
if sys.argv[1]=='--prepare-review-payload':
    expected_fetch_sha=sys.argv[2]
else:
    pending,_,_=read(payload_path)
    assert pending['fetched_source_proof']=={k:FETCHED_SOURCE_PROOF[k] for k in ('path','sha256')}
    expected_fetch_sha=pending['fetched_source_proof']['sha256']
assert expected_fetch_sha==FETCHED_SOURCE_PROOF['sha256']
fetched,fetched_ref,_=read(fetched_path,expected_fetch_sha)
assert fetched_ref==FETCHED_SOURCE_PROOF
assert fetched['schema']=='mckernel.current55-executor-source15.fetched-verification.v1'
assert fetched['status']=='PASS_ACTUAL_FETCHED_BLOB_AND_ARCHIVE_MEMBERS'
assert fetched['commit']=='07d803c4c7c5b0a6945becb746ca71ab5ca1df3e' and fetched['tree']=='344f6f40541426d33aed1d233a565f07f8fc6efe'
assert fetched['source_approval'] is None and fetched['execution_release'] is None and fetched['sdk_execution'] is False and fetched['native_acceptance'] is False
assert len(fetched['canonical_files'])==7 and fetched['current55_archive']['members_verified']==794
assert fetched['executor_source15']['members_verified']==15 and len(fetched['executor_source15']['members'])==15 and len(fetched['executor_final_files'])==8
assert fetched['executor_source15']['archive_sha256']=='b8ec51d0e886b487c3214577e70eb54367a0c3ec8ad83dc97fd5fa91a436c222'
assert fetched['executor_source15']['receipt_sha256']=='ca3eaaba3c746104523705803c0d90a06729176e9122629849b9d8e0cedc704c'
for row in fetched['executor_source15']['members'].values():
    raw,actual,_=load_raw(row['path'],row['sha256']);assert actual==row
assert {k[len('executor-runtime/'):]:v['sha256'] for k,v in fetched['executor_source15']['members'].items() if k.startswith('executor-runtime/')}==base['source_sha256']
CURRENT_OVERLAY_FETCHED_PROOF=None
assert CURRENT_OVERLAY_FETCHED_PROOF is not None, 'genuine fetched currentauthority overlay required'
overlay,overlay_ref,_=read(CURRENT_OVERLAY_FETCHED_PROOF['path'],CURRENT_OVERLAY_FETCHED_PROOF['sha256'])
assert overlay_ref==CURRENT_OVERLAY_FETCHED_PROOF
assert overlay['status']=='PASS_FETCHED_SELECTED_INSTALL_CURRENT_AUTHORITY_OVERLAY'
assert overlay['source_proof']==FETCHED_SOURCE_PROOF
assert overlay['current_physical']==CURRENT_REFS['physical_stdout'] and overlay['current_postjoin']==CURRENT_REFS['postjoin_stdout']
assert overlay['query_source']=={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/admission-preparation-1/run_root_sdk_readonly_admission.py', 'sha256': 'f34c0be23f993a2d765dae451e11994153ea87587f019d6093a1b6b0158c25dc', 'bytes': 50989} and overlay['query_inputs']=={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/fresh-admission-source-2/admission-preparation-1/QUERY-INPUTS.ROOT.json', 'sha256': '32ca7de65fa49e67b4ec7f4a2fa1609340a166cc2c3886d42d667b45e17988a9', 'bytes': 342}
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
