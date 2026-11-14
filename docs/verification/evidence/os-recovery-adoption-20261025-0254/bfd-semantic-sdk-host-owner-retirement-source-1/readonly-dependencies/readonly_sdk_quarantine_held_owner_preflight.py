"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Two readonly authority1 snapshots in the original-owner-held phase. No signals,
pidfd, flock, unlock, container mutation or record mutation is invoked here.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,subprocess,types
D=Path(__file__).resolve().parent
PROFILE=D.parent/'EXACT-HELD-OWNER-READONLY-PROFILE.json'
PROFILE_SHA='a5eccc0f5f8e8ff96b0a4d56f308d60a17109532875e7f62f2a556aa33ed0d04'
raw=PROFILE.read_bytes();assert hashlib.sha256(raw).hexdigest()==PROFILE_SHA
p=json.loads(raw)
base=Path(p['primitive']['path']);assert hashlib.sha256(base.read_bytes()).hexdigest()==p['primitive']['sha256']
spec=importlib.util.spec_from_file_location('readonly_existing_authority1',base);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7}
m.PID,m.START,m.PARENT=635880,'71676755',635879
m.ABSENT=set(p['docker_client_pids']);m.PREFIX=D/'actual-readonly-preflight-2'/'retained-sdk'
assert m.PREFIX.parent.is_dir()
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
def root_readonly(argv):
    # Root entry is independently granted once; no nested sudo or mutation args.
    if argv[:4]!=['/usr/bin/python3','-I','-B','-c'] and argv[:3]!=['/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect'] and argv[:3]!=['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps']:raise m.Refusal('readonly argv outside fixed snapshot grammar')
    result=subprocess.run(argv,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30,check=False)
    if result.returncode or result.stderr or len(result.stdout)>m.SMALL_LIMIT:raise m.Refusal('fixed root readonly subprocess failed')
    return result.stdout
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
m.protected_inputs=protected_inputs;m.process_code=process_code;m.root_readonly=root_readonly
first=m.snapshot('before1',{},p,True)
second=m.snapshot('before2',{},p,True)
if first['inputs']!=second['inputs']:raise m.Refusal('retained SDK inputs changed across snapshots')
m.guard_identity(p);m.require_lock_holder(635880)
result=dict(schema='mckernel.bfd-semantic-sdk.quarantine-held-owner.readonly-proof.v1',status='PASS_ACTUAL_READONLY_ORIGINAL_QUARANTINE_OWNER_HELD',owner=p['owner'],profile_sha256=PROFILE_SHA,before=[first,second],known_client_groups_absent=p['docker_client_pids'],failed_wait_status_preserved=True,original_mutex_inode_preserved=[27,4],rootlock_holder=635880,signals_sent=0,container_mutations=0,records_mutated=0,retirement_acceptance=False,workload_acceptance=False,reader_identity={'pid':os.getpid(),'starttime':m.proc_stat(os.getpid())[19],'boot_id':m.BOOT})
print(json.dumps(result,sort_keys=True))
