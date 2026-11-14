"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Two readonly existing snapshots after independently accepted host retirement. No signals,
pidfd, flock, unlock, container mutation or record mutation is invoked here.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,subprocess,types
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-semantic-sdk-owner-lifecycle-diagnosis-source-1/manual-resume-20261025T212953-current-readonly-source-1')
PROFILE=D/'EXACT-SDK-POST-RECONCILIATION-CURRENT-FREE-READONLY-PROFILE.json'
PROFILE_SHA='35edb7296b3e82b9b57ed952d775ebd4727181432c78b6b072fcf57f4ac2e5d2'
raw=PROFILE.read_bytes();assert hashlib.sha256(raw).hexdigest()==PROFILE_SHA
p=json.loads(raw)
base=Path(p['primitive']['path']);assert hashlib.sha256(base.read_bytes()).hexdigest()==p['primitive']['sha256']
spec=importlib.util.spec_from_file_location('readonly_existing_authority1',base);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={7}
m.PID,m.START,m.PARENT=635880,'71676755',635879
m.ABSENT=set(p['required_absent_pids']);m.PREFIX=D/'actual-manual-resume-current-free-1'/'retained-sdk'
assert m.PREFIX.parent.is_dir()
# Reuse exactly the accepted group census through the h990 AST adapter.
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
hraw=H.read_bytes();assert hashlib.sha256(hraw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
hs=importlib.util.spec_from_file_location('readonly_h990_group_census',H);h=importlib.util.module_from_spec(hs);hs.loader.exec_module(h)

def protected_inputs(_release,profile):
    result={}
    for expected in profile['protected_inputs']:
        path=expected['path']
        if path in profile['archived_records']:
            if os.path.lexists(path):raise m.Refusal('reconciled owned record reappeared')
            archived=profile['archived_records'][path];row,raw=m.file_identity(Path(archived['path']),keep=True)
            if row!=archived or row['sha256']!=expected['sha256'] or row['size']!=expected['size']:raise m.Refusal('exact original record raw archive changed')
            result[path]={'active_absent':True,'raw_archive':row}
        else:
            row,_=m.file_identity(Path(path))
            if row!=expected:raise m.Refusal('fixed SDK input/status changed:'+path)
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
        archive=profile['archived_records'][path]
        if os.path.lexists(path) or m.read_json(Path(archive['path']),archive['sha256'])!=value or value.get('pid')!=635880 or value.get('starttime')!='71676755':raise m.Refusal('exact archived owned record relation changed')
    for expected in profile['cleanup_evidence']:
        if m.file_identity(Path(expected['path']))[0]!=expected:raise m.Refusal('actual cleanup evidence changed')
    for row in profile['cleanup_statuses']:
        value=m.read_json(Path(row['identity']['path']),row['identity']['sha256'])
        if value!=row['value'] or value['state']!='exited' or value['exit_code']!=0 or h.members(value['pid']):raise m.Refusal('fresh cleanup client state/group changed')
    for pid in profile['required_absent_pids']:
        if h.members(pid):raise m.Refusal('known owner/client/recovery/cleanup group remains')
    for path,wanted in profile['preserved_inventories'].items():
        if normal.metadata_inventory(Path(path))!=wanted:raise m.Refusal('full original candidate/evidence inventory changed')
    for path,wanted in profile['preserved_directory_identities'].items():
        if normal.observe_identity(Path(path))!=wanted:raise m.Refusal('retained candidate/evidence directory changed')
    mount=json.loads(subprocess.check_output(['/usr/bin/findmnt','-J','-T','/home/holden/mckernel-work/scratch','-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],timeout=10))['filesystems']
    if mount!=[profile['root_mount']]:raise m.Refusal('scratch mount/UUID changed')
    owner=m.read_json(Path(next(row['path'] for row in profile['protected_inputs'] if row['path'].endswith('/owner-receipt.json'))))
    if (owner['retired'] is not False or owner['cleanup_status']!='UNCERTAIN_RECORDS_RETAINED' or owner['error']!='bounded output inventory/type' or owner['retirement_error']!='Docker client retirement unproven'):raise m.Refusal('actual failed SDK receipt differs')
    q=m.read_json(Path(next(row['path'] for row in profile['protected_inputs'] if row['path'].endswith('.root-lock-quarantine.json'))))
    if q!={'schema':'mckernel.tool-image-rebind-root-quarantine.v1','status':'QUARANTINED_ROOT_LOCK_HELD','pid':635880,'root_lock':[27,4],'reason':'core-entered-without-proven-successful-retirement'}:raise m.Refusal('original quarantine marker differs')
    return result

# Adapt only the exact publisher identity in the existing complete PROC scanner.
original_process_code=m.process_code
ownerpaths=p['publisher_source_paths']
normal_ref=p['normal_cleanup_engine'];normal_spec=importlib.util.spec_from_file_location('accepted_normal_inventory',Path(normal_ref['path']));assert hashlib.sha256(Path(normal_ref['path']).read_bytes()).hexdigest()==normal_ref['sha256'];normal=importlib.util.module_from_spec(normal_spec);normal_spec.loader.exec_module(normal)
def process_code():
    code=original_process_code()
    old="    for arg in argv:\n"
    assert code.count(old)==1
    return code.replace(old,"    if any(path in argv for path in "+repr(ownerpaths)+"): return True\n"+old,1)
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
start=code.index("    raw = root_readonly(['/usr/bin/docker', '--host=unix:///var/run/docker.sock', 'inspect',")
end=code.index("    raw = root_readonly(['/usr/bin/docker', '--host=unix:///var/run/docker.sock', 'ps',",start)
code=code[:start]+code[end:]
old_target="    if (len(target) != 1 or target[0]['ID'] != container['id'] or\n            target[0].get('Names') != proof['owner']['container_name']):\n        raise Refusal('retained container inventory identity differs')"
assert code.count(old_target)==1
code=code.replace(old_target,"    if target:raise Refusal('reconciled CID/name/nonce reappeared')",1)

m.require_mutex_free=require_mutex_free
exec(compile(code,str(base),'exec'),m.__dict__)
# The only files published are the four fresh private raw snapshots; make them
# readable by their existing ordinary evidence owner without extra root copies.
original_publish=m.publish
def publish_capture(path,raw):
    if path.parent!=m.PREFIX.parent or not path.name.startswith(m.PREFIX.name+'.'):raise m.Refusal('fixed new capture path required')
    original_publish(path,raw)
    os.chown(path,1000,1000,follow_symlinks=False)
m.publish=publish_capture
cleanup=m.read_json(Path(p['cleanup_result']['path']),p['cleanup_result']['sha256'])
if cleanup.get('schema')!='mckernel.sdk.quarantine-owned-container-three-record-reconciliation.result.v1' or cleanup.get('status')!='PASS_EXACT_OWNED_CONTAINER_AND_THREE_RECORDS_RECONCILED' or cleanup.get('container_absent') is not True or set(cleanup.get('records_absent',[]))!=set(p['archived_records']) or cleanup.get('original_FAILED_ledger_preserved') is not True:raise m.Refusal('actual exact owned reconciliation result required')
join=m.read_json(Path(p['cleanup_direct_join']['path']),p['cleanup_direct_join']['sha256'])
if join.get('pid')!=661966 or str(join.get('start'))!='72094152' or join.get('returncode')!=0 or join.get('direct_child_joined') is not True:raise m.Refusal('genuine direct cleanup join required')
if p['cleanup_acceptance'] is None:raise m.Refusal('PENDING genuine independent actual reconciliation acceptance')
accepted=m.read_json(Path(p['cleanup_acceptance']['path']),p['cleanup_acceptance']['sha256'])
if accepted!=p['cleanup_acceptance_value']:raise m.Refusal('genuine exact independent actual cleanup acceptance changed')

# Supplemental bindings for the new, normally retired owner. The old profile and
# its 55 original protected inputs remain unchanged historical prerequisites.
NEWD=Path(__file__).resolve().parent
NEW_PROFILE=NEWD/'EXACT-SDK-A482-NORMAL-POSTJOIN-READONLY-PROFILE.json'
NEW_PROFILE_SHA='ef7ea750bbea4e6b1745f6f97dcb7223a3faeecc061b538e89dcf82bda8f4c69'
assert hashlib.sha256(NEW_PROFILE.read_bytes()).hexdigest()==NEW_PROFILE_SHA
new=json.loads(NEW_PROFILE.read_bytes())
assert new['owner']=={'pid':837426,'starttime':'76193932'}
assert new['required_absent_pids']==[837426,837457,837463,837473,837481,837489,837498,837506,837565,838414,838422,838430,838438,838446,838454,838462]
assert new['preserved_controllers']==[[842940,'76277874'],[842942,'76277881']]
assert not set(new['required_absent_pids']) & {842940,842942}
m.ABSENT |= set(new['required_absent_pids'])
m.PREFIX=NEWD/'actual-sdk-a482-new18h-postjoin-2'/'retained-sdk'
assert m.PREFIX.parent.is_dir()
# The inherited publisher census also matches this new operation's driver/owner.
assert len(new['source_paths'])==3 and len(set(new['source_paths']))==3
assert new['source_paths'][-1]=='/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/selected-bootstrap-correction-source-8/coherent-cxx-bound-retained11-suffix10-source-2/bfd_cxx_bound_retained11_suffix10_owner.py'
assert any(row['path']==new['source_paths'][-1] and row['sha256']=='542a78c4e5fca1ef0bfed6d41ea70d689c1a7284390ee4f858c705efaf4f0491' and row['size']==94697 for row in new['protected_inputs'])
ownerpaths.extend(new['source_paths'])
old_protected_inputs=protected_inputs

def new_value(key):
    row=new[key]
    if normal.observe_identity(Path(row['path']))!=row:raise m.Refusal('new SDK bound evidence identity changed:'+key)
    return m.read_json(Path(row['path']),row['sha256'])

def protected_current_inputs(release,profile):
    result=old_protected_inputs(release,profile)
    for wanted in new['protected_inputs']:
        if normal.observe_identity(Path(wanted['path']))!=wanted:raise m.Refusal('new SDK fixed input changed:'+wanted['path'])
        result[wanted['path']]=wanted
    for path,wanted in new['preserved_inventories'].items():
        if normal.metadata_inventory(Path(path))!=wanted:raise m.Refusal('new SDK candidate/evidence inventory changed')
    for path,wanted in new['preserved_directory_identities'].items():
        if normal.observe_identity(Path(path))!=wanted:raise m.Refusal('new SDK candidate/evidence directory changed')
    receipt=new_value('receipt')
    if receipt['retired'] is not True or receipt['cleanup_status']!='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' or receipt['status']!='FAIL' or receipt['error']!='BFD qualification artifact missing' or receipt['terminal_container_retained'] is not False or receipt['container_id']!=new['container_id'] or receipt['container_name']!=new['container_name'] or receipt['owner_nonce']!=new['nonce']:raise m.Refusal('actual normal SDK retirement receipt changed')
    postflight=new_value('postflight')
    if postflight['container_absent'] is not True or postflight['all_clients_reaped'] is not True or postflight['compiler_status']!='FAIL' or postflight['absence']!={'absent':True,'container_id':new['container_id'],'name':new['container_name'],'nonce':new['nonce'],'queries':['name','label','id']}:raise m.Refusal('normal SDK postflight differs')
    archive=new_value('ownership_archive');authorized=new_value('record_authorized');complete=new_value('record_complete')
    if complete!={'archive_sha256':new['ownership_archive']['sha256'],'nonce':new['nonce'],'status':'OWNED_RECORDS_RELEASED'} or authorized['archive_sha256']!=new['ownership_archive']['sha256'] or authorized['status']!='POSTFLIGHT_RELEASE_AUTHORIZED' or authorized['records']!=archive['records']:raise m.Refusal('normal SDK record release differs')
    if len(archive['records'])!=3 or set(new['archived_records'])!={row['path'] for row in archive['records']}:raise m.Refusal('exact three current SDK records required')
    for record in archive['records']:
        if os.path.lexists(record['path']):raise m.Refusal('normal SDK released active record reappeared')
        rawref=new['archived_records'][record['path']]
        if normal.observe_identity(Path(rawref['path']))!=rawref:raise m.Refusal('new raw record identity changed')
        raw=Path(rawref['path']).read_bytes()
        if len(raw)!=record['size'] or hashlib.sha256(raw).hexdigest()!=record['sha256'] or json.loads(raw)!=record['record'] or record['record']['pid']!=837426 or record['record']['starttime']!='76193932':raise m.Refusal('new archived raw owned record relation changed')
    joined=new_value('tool_join')
    if joined['owner_pid']!=837426 or joined['owner_starttime']!='76193932' or joined['session_id']!=88166 or joined['exit_code']!=1 or joined['tool_completion_observed'] is not True or joined['owner_receipt_retired'] is not True:raise m.Refusal('actual SDK tool completion binding differs')
    accepted=new_value('acceptance')
    if accepted['reviewer']!='/root/execution_review' or accepted['implementation_ownership'] is not False or accepted['status']!='PASS_NORMAL_RETIREMENT_EVIDENCE_CURRENT_POSTJOIN_PENDING' or accepted['owner']!=new['owner'] or accepted['container_id']!=new['container_id'] or accepted['owner_receipt_sha256']!=new['receipt']['sha256'] or accepted['postflight_sha256']!=new['postflight']['sha256'] or accepted['ownership_archive_sha256']!=new['ownership_archive']['sha256'] or accepted['release_authorized_sha256']!=new['record_authorized']['sha256'] or accepted['release_complete_sha256']!=new['record_complete']['sha256'] or accepted['cleanup_replay_required'] is not False:raise m.Refusal('independent actual normal retirement acceptance differs')
    for pid in new['required_absent_pids']:
        if h.members(pid):raise m.Refusal('current SDK owner/client group remains')
    # Raw statuses are also fixed byte inputs; retain explicit successful client semantics.
    statuses=[row for row in new['protected_inputs'] if row['path'].endswith('/status.json')]
    if len(statuses)!=15:raise m.Refusal('exact fifteen normal SDK clients required')
    seen=[]
    for row in statuses:
        value=m.read_json(Path(row['path']),row['sha256'])
        if value['state']!='exited' or value['exit_code']!=0:raise m.Refusal('normal SDK client did not exit zero')
        seen.append(value['pid'])
    if set(seen)!=set(new['required_absent_pids'])-{837426}:raise m.Refusal('normal SDK client identity set differs')
    for pid,start in new['preserved_controllers']:
        if m.proc_stat(pid)[19]!=start:raise m.Refusal('preserved current controller identity differs')
    return result

old_root_readonly=root_readonly

def current_root_readonly(argv):
    raw=old_root_readonly(argv)
    if argv[:3]==['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps']:
        for line in raw.splitlines():
            row=m.strict(line)
            if row.get('ID')==new['container_id'] or row.get('Names')==new['container_name'] or 'mckernel.owner='+new['nonce'] in row.get('Labels','').split(','):raise m.Refusal('new normal SDK CID/name/nonce reappeared')
    return raw

m.protected_inputs=protected_current_inputs;m.root_readonly=current_root_readonly
before=require_mutex_free()
first=m.snapshot('current1',{},p,False)
second=m.snapshot('current2',{},p,False)
after=require_mutex_free()
if first['inputs']!=second['inputs'] or before!=after:raise m.Refusal('historical/new inputs or permanent mutex changed')
print(json.dumps(dict(schema='mckernel.sdk.normal-retirement.current-postjoin-readonly-proof.v1',status='PASS_ACTUAL_CURRENT_POSTJOIN_NORMAL_RETIREMENT_MUTEX_FREE',profile_sha256=NEW_PROFILE_SHA,owner=new['owner'],normal_retirement_acceptance=new['acceptance'],tool_join=new['tool_join'],required_absent_pids=new['required_absent_pids'],historical_required_absent_pids=p['required_absent_pids'],historical_profile_sha256=PROFILE_SHA,historical_protected_input_count=len(p['protected_inputs']),current_protected_input_count=len(new['protected_inputs']),current_inventory_counts={path:len(rows) for path,rows in new['preserved_inventories'].items()},container_id=new['container_id'],container_absent=True,three_records_absent=True,current_candidate_and_evidence_preserved=True,source_workload_status='FAIL',source_workload_error='BFD qualification artifact missing',before=[first,second],root_mutex_before=before,root_mutex_after=after,signals_sent=0,root_mutex_flock_operations=0,cleanup_replayed=False,heavy_execution_released=False,native_acceptance=False,SDK_acceptance=False,preserved_controllers=new['preserved_controllers'],reader_identity={'pid':os.getpid(),'starttime':m.proc_stat(os.getpid())[19],'boot_id':m.BOOT}),sort_keys=True))
