"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Two readonly existing snapshots after independently accepted host retirement. No signals,
pidfd, flock, unlock, container mutation or record mutation is invoked here.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,subprocess,types
D=Path(__file__).resolve().parent
PROFILE=D/'EXACT-SDK-POST-RETIREMENT-CURRENT-FREE-READONLY-PROFILE.json'
PROFILE_SHA='4ff62cfc202e2e178c4c605c0486a529ebd18b6779c38404cb33f4b7edd967c2'
raw=PROFILE.read_bytes();assert hashlib.sha256(raw).hexdigest()==PROFILE_SHA
p=json.loads(raw)
base=Path(p['primitive']['path']);assert hashlib.sha256(base.read_bytes()).hexdigest()==p['primitive']['sha256']
spec=importlib.util.spec_from_file_location('readonly_existing_authority1',base);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7}
m.PID,m.START,m.PARENT=635880,'71676755',635879
m.ABSENT=set(p['required_absent_pids']);m.PREFIX=D/'actual-current-free-readonly-1'/'retained-sdk'
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
    if h.members(650468):raise m.Refusal('retired recovery helper group still present')
    if failed!=[636011]:raise m.Refusal('exact one preserved failed wait-client required')
    for path,value in profile['record_values'].items():
        if m.read_json(Path(path))!=value or value.get('pid')!=635880 or value.get('starttime')!='71676755':raise m.Refusal('exact owned record relation changed')
    owner=m.read_json(Path(next(row['path'] for row in profile['protected_inputs'] if row['path'].endswith('/owner-receipt.json'))))
    if (owner['retired'] is not False or owner['cleanup_status']!='UNCERTAIN_RECORDS_RETAINED' or owner['error']!='bounded output inventory/type' or owner['retirement_error']!='Docker client retirement unproven'):raise m.Refusal('actual failed SDK receipt differs')
    q=m.read_json(Path(next(row['path'] for row in profile['protected_inputs'] if row['path'].endswith('.root-lock-quarantine.json'))))
    if q!={'schema':'mckernel.tool-image-rebind-root-quarantine.v1','status':'QUARANTINED_ROOT_LOCK_HELD','pid':635880,'root_lock':[27,4],'reason':'core-entered-without-proven-successful-retirement'}:raise m.Refusal('original quarantine marker differs')
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

acceptance=m.read_json(Path(p['process_recovery_acceptance']['path']),p['process_recovery_acceptance']['sha256'])
if (acceptance.get('schema')!='mckernel.sdk.host-owner-retirement.independent-acceptance.v1' or acceptance.get('status')!='PASS_HOST_PROCESS_RECOVERY_ONLY' or acceptance.get('implementation_ownership') is not False or acceptance.get('reviewer')!='/root/recovery_review' or acceptance.get('target')!={'pid':635880,'starttime':'71676755'} or acceptance.get('pidfd_exit_positive') is not True or acceptance.get('replacement_holder')!={'pid':650468,'starttime':'71895197','mutex_device':27,'mutex_inode':4} or acceptance.get('container_cleanup_accepted') is not False or acceptance.get('record_reconciliation_accepted') is not False):raise m.Refusal('actual independent process-only retirement acceptance required')
complete=m.read_json(Path(p['process_recovery_complete']['path']),p['process_recovery_complete']['sha256'])
if complete['status']!='COMPLETE_PROCESS_RECOVERY' or complete['sole_signal']!={'syscall':424,'signal':9,'returncode':0} or complete['exit_proof']['pidfd_exit_ready'] is not True or complete['replacement_root_lock']!=[27,4]:raise m.Refusal('actual pidfd process recovery completion differs')

def require_mutex_free():
    row,raw=m.file_identity(Path('/run/lock/mckernel-development.lock'),keep=True,maximum=0)
    expected=dict(path='/run/lock/mckernel-development.lock',device=27,inode=4,size=0,mode=420,uid=0,gid=0,nlink=1,sha256=hashlib.sha256(b'').hexdigest())
    if row!=expected or raw!=b'' or m.lock_rows()!=[]:raise m.Refusal('unchanged permanent27:4 must be FREE')
    return row
# Reuse snapshot body exactly outside its explicit held->free phase branch.
node=next(n for n in ast.parse(base.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='snapshot')
code=ast.get_source_segment(base.read_text(),node)
old="""    if before:
        guard_identity(profile)
        locks = require_lock_holder(PID)
    else:
        boot_check()
        locks = require_lock_holder(os.getpid())
"""
assert code.count(old)==1
code=code.replace(old,"    boot_check()\n    require_mutex_free()\n    locks = []\n",1)
m.require_mutex_free=require_mutex_free
exec(compile(code,str(base),'exec'),m.__dict__)
# The only files published are the six fresh private raw snapshots; make them
# readable by their existing ordinary evidence owner without extra root copies.
original_publish=m.publish
def publish_capture(path,raw):
    if path.parent!=m.PREFIX.parent or not path.name.startswith(m.PREFIX.name+'.'):raise m.Refusal('fixed new capture path required')
    original_publish(path,raw)
    os.chown(path,1000,1000,follow_symlinks=False)
m.publish=publish_capture
before=require_mutex_free()
first=m.snapshot('current1',{},p,False)
second=m.snapshot('current2',{},p,False)
after=require_mutex_free()
if first['inputs']!=second['inputs'] or before!=after:raise m.Refusal('preserved inputs or permanent mutex changed')
print(json.dumps(dict(schema='mckernel.bfd-semantic-sdk.post-host-retirement.current-free-readonly-proof.v1',status='PASS_ACTUAL_CURRENT_POSTJOIN_MUTEX_FREE_RECORDS_RETAINED',profile_sha256=PROFILE_SHA,process_recovery_acceptance=p['process_recovery_acceptance'],before=[first,second],root_mutex_before=before,root_mutex_after=after,required_absent_pids=p['required_absent_pids'],failed_ledger_preserved=True,container_retained=True,three_records_retained=True,signals_sent=0,root_mutex_flock_operations=0,container_record_cleanup=False,heavy_execution_released=False,reader_identity={'pid':os.getpid(),'starttime':m.proc_stat(os.getpid())[19],'boot_id':m.BOOT}),sort_keys=True))
