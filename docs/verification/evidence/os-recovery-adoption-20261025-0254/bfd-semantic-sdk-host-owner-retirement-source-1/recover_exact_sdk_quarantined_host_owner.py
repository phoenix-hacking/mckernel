"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact SDK quarantine HOST owner retirement using existing authority1 pidfd body.
No container or owned-record reconciliation; never replace/unlink/truncate mutex inode.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,subprocess,types
D=Path(__file__).resolve().parent
PROFILE=D/'EXACT-SDK-PIDFD-HOST-OWNER-RETIREMENT-PROFILE.json'
PROFILE_SHA='a44880bbf884e8590a0e324a937589a5d4befb667c5d00a03ccfcb6f9572be27'
raw=PROFILE.read_bytes();assert hashlib.sha256(raw).hexdigest()==PROFILE_SHA
p=json.loads(raw)
base=Path(p['primitive']['path']);assert hashlib.sha256(base.read_bytes()).hexdigest()==p['primitive']['sha256']
spec=importlib.util.spec_from_file_location('readonly_existing_authority1',base);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert (os.getuid(),os.getgid(),os.geteuid(),os.getegid())==(1000,1000,1000,1000) and os.sched_getaffinity(0)=={0} and os.uname().machine=='x86_64'
m.PID,m.START,m.PARENT=635880,'71676755',635879
m.ABSENT=set(p['docker_client_pids'])|set(p['known_prior_reader_pids']);m.PREFIX=D/'actual-host-owner-retirement-1'/'retained-sdk'
m.PROFILE=PROFILE;m.PROFILE_SHA=PROFILE_SHA
m.PREPARED=Path(str(m.PREFIX)+'.prepared.json');m.COMPLETE=Path(str(m.PREFIX)+'.complete.json');m.QUARANTINE=Path(str(m.PREFIX)+'.quarantine.json')
m.ORIGINAL_FAILURE_SHA256=p['failure_evidence']
PHASE_BEFORE=True
# Reuse exactly the accepted group census through the h990 AST adapter.
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
hraw=H.read_bytes();assert hashlib.sha256(hraw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
hs=importlib.util.spec_from_file_location('readonly_h990_group_census',H);h=importlib.util.module_from_spec(hs);hs.loader.exec_module(h)

def protected_inputs(_release,profile):
    result={}
    for expected in profile['protected_inputs']:
        row,_=m.file_identity(Path(expected['path']))
        if row!=expected:raise m.Refusal('fixed SDK input/record/status changed:'+expected['path'])
        result[row['path']]=row
    failed=[]
    for row in profile['owner_statuses']:
        value=m.read_json(Path(row['identity']['path']),row['identity']['sha256'])
        if value!=row['value']:raise m.Refusal('exact raw SDK client state changed')
        if value['state']=='failed':
            if not (value['pid']==636011 and value['error']=='bounded output inventory/type' and value['client_term_error']=='[Errno 1] Operation not permitted' and value['exit_code']==0):raise m.Refusal('unexpected failed client status')
            failed.append(value['pid'])
        elif value['state']!='exited' or value['exit_code']!=0:raise m.Refusal('unexpected other client status')
        if h.members(value['pid']):raise m.Refusal('known original client group still present')
    if failed!=[636011]:raise m.Refusal('exact one preserved failed wait-client required')
    for path,value in profile['record_values'].items():
        if m.read_json(Path(path))!=value or value.get('pid')!=635880 or value.get('starttime')!='71676755':raise m.Refusal('exact owned record relation changed')
    owner=m.read_json(Path(next(row['path'] for row in profile['protected_inputs'] if row['path'].endswith('/owner-receipt.json'))))
    if (owner['retired'] is not False or owner['cleanup_status']!='UNCERTAIN_RECORDS_RETAINED' or owner['error']!='bounded output inventory/type' or owner['retirement_error']!='Docker client retirement unproven'):raise m.Refusal('actual failed SDK receipt differs')
    q=m.read_json(Path(next(row['path'] for row in profile['protected_inputs'] if row['path'].endswith('.root-lock-quarantine.json'))))
    if q!={'schema':'mckernel.tool-image-rebind-root-quarantine.v1','status':'QUARANTINED_ROOT_LOCK_HELD','pid':635880,'root_lock':[27,4],'reason':'core-entered-without-proven-successful-retirement'}:raise m.Refusal('original quarantine marker differs')
    if PHASE_BEFORE:
        # Metadata only; do not read any descriptor contents.
        fdpath=Path('/proc/635880/fd/6');meta=fdpath.stat();named=Path('/run/lock/mckernel-development.lock').lstat()
        if (meta.st_dev,meta.st_ino,meta.st_uid,meta.st_gid,meta.st_mode,meta.st_size,meta.st_nlink)!=(27,4,0,0,0o100644,0,1) or (named.st_dev,named.st_ino)!=(27,4) or os.readlink(fdpath)!='/run/lock/mckernel-development.lock':raise m.Refusal('original owner FD6 permanent identity differs')
        locks=[line.split()[1:] for line in Path('/proc/635880/fdinfo/6').read_text().splitlines() if line.startswith('lock:')]
        if len(locks)!=1 or locks[0][1:]!=['FLOCK','ADVISORY','WRITE','635880','00:1b:4','0','EOF']:raise m.Refusal('original owner FD6 flock row differs')
        m.require_lock_holder(635880)
    return result

# Adapt only the exact publisher identity in the existing complete PROC scanner.
original_process_code=m.process_code
ownerpath=p['bound_guard']['source']
def process_code():
    code=original_process_code()
    old="    for arg in argv:\n"
    assert code.count(old)==1
    return code.replace(old,"    if "+repr(ownerpath)+" in argv: return True\n"+old,1)
original_validate=m.validate_process_report
# Existing validator body is reused with only its historical exe literal repinned.
node=next(n for n in ast.parse(base.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='validate_process_report')
code=ast.get_source_segment(base.read_text(),node).replace("'/usr/bin/python3.8'",repr(p['bound_guard']['exe']))
exec(compile(code,str(base),'exec'),m.__dict__)
def proc_bytes_bounded_eof(path, maximum=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        data = bytearray()
        while True:
            chunk = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not chunk:
                return bytes(data)
            data.extend(chunk)
            if len(data) > maximum:
                raise m.Refusal('proc observation exceeds bound')
    finally:
        os.close(fd)

m.proc_bytes=proc_bytes_bounded_eof
m.protected_inputs=protected_inputs;m.process_code=process_code

original_snapshot=m.snapshot
def snapshot(label,release,profile,before):
    global PHASE_BEFORE
    PHASE_BEFORE=before
    return original_snapshot(label,release,profile,before)
m.snapshot=snapshot

def bind_release(path,expected):
    release=m.read_json(path,expected)
    profile=m.read_json(PROFILE,PROFILE_SHA)
    if (release.get('schema')!='mckernel.bfd-semantic-sdk.exact-pidfd-host-owner-retirement.release.v1' or release.get('status')!='PASS_EXECUTION_RELEASE' or
        type(release.get('execution_count')) is not int or release['execution_count']!=1 or release.get('profile_sha256')!=PROFILE_SHA or
        release.get('readonly_acceptance')!=profile['readonly_acceptance'] or release.get('fetched_source_verified') is not True or
        not m.re.fullmatch('[0-9a-f]{40}',str(release.get('source_checkpoint',''))) or not release.get('author')):
        raise m.Refusal('exact current SDK one-shot HOST-only retirement release required')
    acceptance=m.read_json(Path(profile['readonly_acceptance']['path']),profile['readonly_acceptance']['sha256'])
    if (acceptance.get('schema')!='mckernel.bfd-semantic-sdk.quarantine-held-owner.independent-readonly-acceptance.v1' or
        acceptance.get('status')!='PASS_READONLY_HELD_OWNER_PROOF' or acceptance.get('reviewer')!='/root/recovery_review' or
        acceptance.get('implementation_ownership') is not False or acceptance.get('owner')!=[635880,'71676755'] or
        acceptance.get('permanent_mutex')!=[27,4] or acceptance.get('sole_mutex_holder')!=635880 or
        acceptance.get('container_id')!=profile['retirement_proof']['container']['id'] or acceptance.get('container_stopped_exit_code')!=1 or
        acceptance.get('stdout_sha256')!=profile['readonly_stdout']['sha256'] or acceptance.get('whole_join_sha256')!=profile['readonly_whole_join']['sha256'] or
        acceptance.get('failed_wait_status_preserved') is not True or acceptance.get('execution_authority') is not False):
        raise m.Refusal('genuine actual held-owner readonly acceptance binding required')
    files={str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),str(PROFILE):PROFILE_SHA,
           str(base):p['primitive']['sha256'],str(H):'990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'}
    if release.get('files_sha256')!=files:raise m.Refusal('exact source/profile/dependency map required')
    review=m.read_json(Path(release['source_review']['path']),release['source_review']['sha256'])
    if (review.get('decision')!='PASS_SOURCE' or review.get('implementation_ownership') is not False or not review.get('reviewer') or
        review['reviewer']==release['author'] or review.get('files_sha256')!=files or review.get('profile_sha256')!=PROFILE_SHA or
        review.get('source_checkpoint')!=release['source_checkpoint']):raise m.Refusal('independent exact current SDK source review required')
    execution=m.read_json(Path(release['execution_review']['path']),release['execution_review']['sha256'])
    payload={key:value for key,value in release.items() if key!='execution_review'}
    if (execution.get('decision')!='PASS_EXECUTION' or execution.get('implementation_ownership') is not False or not execution.get('reviewer') or
        execution['reviewer']==release['author'] or execution.get('reviewed_release_payload_sha256')!=m.sha(m.canonical(payload))):
        raise m.Refusal('independent exact HOST-only execution release required')
    for original,digest in profile['failure_evidence'].items():
        if m.file_identity(Path(original))[0]['sha256']!=digest:raise m.Refusal('preserved failure evidence changed')
    for fixed in (m.PREPARED,m.COMPLETE,m.QUARANTINE):
        if os.path.lexists(fixed):raise m.Refusal('one-shot retirement already materialized')
    if os.path.lexists(m.PREFIX.parent):raise m.Refusal('fresh recovery metadata directory required')
    m.PREFIX.parent.mkdir(mode=0o700)
    return release,profile
m.bind_release=bind_release
if __name__=='__main__':
    raise SystemExit(m.main())
