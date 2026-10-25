"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact separately released SDK stopped-container/three-record reconciliation.
Existing SDK archive-before-release core and existing full normal cleanup census;
no owner replay, build, source repair, signal, status rewrite or lock replacement.
"""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,os,re,signal,stat,subprocess,time,types,uuid
D=Path(__file__).resolve().parent
PROFILE=D/'EXACT-OWNED-SDK-THREE-RECORD-RECONCILIATION-PROFILE.json'
PROFILE_SHA='e4a8e993a0efe4f6acddb005bdc25db8825a8f9d2ae445b21c2666a000ff85fc'
BASE=Path('/home/holden/mckernel/scripts/native_exact_scratch22_authority1_quarantine_recovery.py')
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='3fdb4dde4dbbd5d07d85d68c02e68d4aee3acca45dce12be3479f3252765abd6'
def module(path,name,sha):
    need(hashlib.sha256(path.read_bytes()).hexdigest()==sha,'exact existing module bytes')
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
def need(ok,message):
    if not ok:raise RuntimeError(message)
spec=importlib.util.spec_from_file_location('existing_stable_recovery_reader',BASE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
row,raw=m.file_identity(PROFILE,keep=True,maximum=128<<20);need(row['sha256']==PROFILE_SHA,'exact reconciliation profile');p=m.strict(raw)
need((os.getuid(),os.getgid(),os.geteuid(),os.getegid())==(1000,1000,1000,1000) and os.sched_getaffinity(0)=={0},'ordinary CPU0 one-job reconciliation only')
normal=module(Path(p['normal_cleanup_engine']['path']),'existing_full_normal_census',p['normal_cleanup_engine']['sha256'])
ROOT=Path('/home/holden/mckernel-work/scratch');LEASE=ROOT/'native-running-external-modules.lease.json';COMMON=ROOT/'native-running-external-modules-operational-exclusion.json'
shared=types.SimpleNamespace(SHARED_HEAVY_LOCK_PATH=str(ROOT/'mckernel-heavy-operation.lock'))
RECORD_PATHS={str(LEASE),str(COMMON),shared.SHARED_HEAVY_LOCK_PATH}
OUT=D/'actual-owned-reconciliation-1';RELEASED_RECORDS=set();LOCKFD=None;MUTATED=False;COMPLETE=False;REQUESTED=[]
Refusal=m.Refusal;sha=m.sha;canonical=m.canonical
request=p['request_value'];CID=p['retirement_proof']['container']['id'];NAME=p['retirement_proof']['owner']['container_name'];NONCE=request['nonce']
# AST-only reuse: load no SDK owner entry/imports or compiler libraries.
def units(ref,names):
    path=Path(ref['path']);data=path.read_bytes();need(hashlib.sha256(data).hexdigest()==ref['sha256'],'exact AST reuse source')
    return [node for node in ast.parse(data).body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names]
def duplicate_pairs(items):return m.strict(json.dumps(dict(items))) if len(dict(items))==len(items) else (_ for _ in ()).throw(m.Refusal('duplicate JSON'))
def write_new(path,raw,mode=0o600):
    need(path.parent==OUT and mode==0o600,'fixed new archive directory');m.publish(path,raw)
def write_json(path,value):write_new(path,(json.dumps(value,sort_keys=True,indent=2)+'\n').encode())
def snapshot_json(path,label,expected=None):return m.read_json(Path(path),expected),m.file_identity(Path(path))[0]
guard=types.SimpleNamespace(_duplicates=duplicate_pairs,_write_new=write_new,_write_json=write_json,_read_json_snapshot=snapshot_json)
# The exact existing transport closes/reaps each fresh Docker client and records
# its own ledger, separate from the immutable original FAILED wait-client row.
bref=p['backend_source'];bpath=Path(bref['path']);braw=bpath.read_bytes();need(hashlib.sha256(braw).hexdigest()==bref['sha256'],'exact Docker backend')
bns=dict(Path=Path,json=json,os=os,uuid=uuid,signal=signal,time=time,subprocess=subprocess,hashlib=hashlib)
for node in ast.parse(braw).body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ENV','SUDO_DOCKER_PREFIX') for t in node.targets):exec(compile(ast.Module(body=[node],type_ignores=[]),str(bpath),'exec'),bns)
exec(compile(ast.Module(body=units(bref,{'docker_env','atomic','digest','Docker'}),type_ignores=[]),str(bpath),'exec'),bns)
host=types.SimpleNamespace(**bns)
sdk_units=units(p['sdk_owner_source'],{'safe_path','ExternalDocker','positive_clients','record_snapshot','release_owned_records'})
need(len(sdk_units)==5,'exact five SDK normal release units')
for node in sdk_units:
    text=ast.unparse(node)
    if node.name=='record_snapshot':
        old="need(expected.get('pid') == os.getpid() and expected.get('starttime') == image._proc_starttime(os.getpid()), 'foreign record owner')"
        need(text.count(old)==1,'exact original current-PID ownership predicate')
        text=text.replace(old,"need(expected.get('pid') == 635880 and expected.get('starttime') == '71676755', 'exact independently retired SDK owner required')\n        current_safety()",1)
    elif node.name=='release_owned_records':
        old='os.unlink(path.name, dir_fd=parent)';need(text.count(old)==1,'exact SDK release location')
        text=text.replace(old,old+"\n            RELEASED_RECORDS.add(str(path))",1)
    exec(compile(text,str(Path(p['sdk_owner_source']['path'])),'exec'),globals())
# Normal root full-process/Docker census predicates remain exact. Their only
# source additions are the current owner and host-retirement entry paths.
normal.CONTAINER=CID;normal.CONTAINER_NAME=NAME;normal.OWNER_NONCE=NONCE;normal.OWNER_PID=635880;normal.OWNER_START='71676755';normal.EXPECTED_EXIT=1;normal.BOOT_ID=m.BOOT
normal.WAITER_PIDS=tuple(p['required_absent_pids'])
normal.EXPECTED_CONTAINER=m.read_json(Path(p['retirement_proof']['container']['terminal_path']),p['retirement_proof']['container']['terminal_sha256'])
old='    for arg in argv:\n';need(normal.PROC_CODE.count(old)==1,'exact census predicate anchor')
paths=[p['bound_guard']['source'],'/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-semantic-sdk-owner-lifecycle-diagnosis-source-1/exact-pidfd-host-owner-retirement-source-1/recover_exact_sdk_quarantined_host_owner.py']
normal.PROC_CODE=normal.PROC_CODE.replace(old,'    if any(path in argv for path in '+repr(paths)+'): return True\n'+old,1)
normal.run_privileged=m.root_readonly;normal.run_privileged_large=m.root_readonly
m.LOCK=Path('/run/lock/mckernel-development.lock')
# Reuse the corrected bounded EOF proc reader for global lock observations.
def proc_bytes(path,maximum=65536):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
    try:
        data=bytearray()
        while True:
            chunk=os.read(fd,min(65536,maximum+1-len(data)))
            if not chunk:return bytes(data)
            data.extend(chunk);need(len(data)<=maximum,'proc observation exceeds bound')
    finally:os.close(fd)
m.proc_bytes=proc_bytes
class CleaningSignals:
    def check(self):pass
class FixedDocker(ExternalDocker):
    def call(self,args,**kwargs):
        op=args[0] if args else None
        need(op in ('ps','inspect','logs','rm'),'only selected reconciliation Docker verbs')
        if op in ('inspect','logs'):need(args[-1] in (CID,NAME),'exact selected CID inspect/logs')
        if op=='rm':need(list(args)==['rm','--',CID],'only exact stopped-owned CID removal')
        result=super().call(args,**kwargs)
        normal.WAITER_PIDS=tuple(sorted(set(p['required_absent_pids'])|{json.loads(q.read_text())['pid'] for q in OUT.glob('command-*/status.json')}))
        return result

def current_safety():
    need(LOCKFD is not None,'owned permanent root flock required')
    meta=os.fstat(LOCKFD);named=m.LOCK.lstat()
    need((meta.st_dev,meta.st_ino,meta.st_uid,meta.st_gid,stat.S_IMODE(meta.st_mode),meta.st_nlink,meta.st_size)==(27,4,0,0,420,1,0) and (named.st_dev,named.st_ino)==(27,4),'unchanged permanent mutex identity')
    m.require_lock_holder(os.getpid());m.boot_check()
    need(m.file_identity(Path(p['postjoin_acceptance']['path']))[0]['sha256']==p['postjoin_acceptance']['sha256'],'actual accepted postjoin record changed')
    need(not REQUESTED or MUTATED,'termination requested before first mutation')
    mount=json.loads(subprocess.check_output(['/usr/bin/findmnt','-J','-T',str(ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],timeout=10))['filesystems']
    need(mount==[p['root_mount']] and ROOT.stat().st_dev==1828,'scratch mount/UUID identity')
    for expected in p['protected_inputs']:
        path=Path(expected['path'])
        if str(path) in RELEASED_RECORDS:
            need(not os.path.lexists(path),'released owned record reappeared')
            name=('lease' if path==LEASE else 'common' if path==COMMON else 'shared')+'.record.raw'
            archived,_=m.file_identity(OUT/name)
            need(archived['sha256']==expected['sha256'] and archived['size']==expected['size'],'released record raw archive changed')
        else:need(m.file_identity(path)[0]==expected,'immutable raw input/FAILED-ledger drift:'+str(path))
    for path,wanted in p['preserved_inventories'].items():need(normal.metadata_inventory(Path(path))==wanted,'complete partial SDK artifact/evidence inventory drift')
    for path,wanted in p['preserved_directory_identities'].items():need(normal.observe_identity(Path(path))==wanted,'exact retained output/evidence directory changed')
    normal.process_absent()

def validate_release(path,expected):
    release=m.read_json(path,expected)
    need(release.get('schema')=='mckernel.sdk.quarantine-owned-container-three-record-reconciliation.release.v1' and release.get('status')=='PASS_EXECUTION_RELEASE' and type(release.get('execution_count')) is int and release['execution_count']==1 and release.get('profile_sha256')==PROFILE_SHA,'exact separately released reconciliation required')
    need(release.get('fetched_source_verified') is True and re.fullmatch('[0-9a-f]{40}',str(release.get('source_checkpoint',''))) and release.get('author'),'actual fetched source checkpoint/author')
    files={str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),str(PROFILE):PROFILE_SHA}
    need(release.get('files_sha256')==files,'exact reconciliation source/profile files map')
    review=m.read_json(Path(release['source_review']['path']),release['source_review']['sha256'])
    need(review.get('decision')=='PASS_SOURCE' and review.get('implementation_ownership') is False and review.get('reviewer') and review['reviewer']!=release['author'] and review.get('files_sha256')==files and review.get('profile_sha256')==PROFILE_SHA and review.get('source_checkpoint')==release['source_checkpoint'],'genuine consumable independent source/profile review')
    execution=m.read_json(Path(release['execution_review']['path']),release['execution_review']['sha256'])
    need(execution.get('decision')=='PASS_EXECUTION' and execution.get('implementation_ownership') is False and execution.get('reviewer') and execution['reviewer']!=release['author'] and execution.get('reviewed_release_payload_sha256')==m.sha(m.canonical({k:v for k,v in release.items() if k!='execution_review'})),'genuine exact independent reconciliation execution release')
    postjoin=m.read_json(Path(p['postjoin_acceptance']['path']),p['postjoin_acceptance']['sha256'])
    need(postjoin.get('schema')=='mckernel.bfd-semantic-sdk.post-host-retirement.independent-current-acceptance.v1' and postjoin.get('status')=='PASS_CURRENT_MUTEX_FREE_RECORDS_RETAINED' and postjoin.get('reviewer')=='/root/recovery_review' and postjoin.get('implementation_ownership') is False and postjoin.get('permanent_mutex')=={'device':27,'inode':4,'identity_unchanged':True,'free_before':True,'free_after':True,'flock_operations':0} and postjoin.get('three_owned_records_retained') is True and postjoin.get('container_cleanup_accepted') is False and postjoin.get('record_reconciliation_accepted') is False,'genuine actual FREE postjoin required')
    need(postjoin['process_recovery_acceptance_sha256']==p['process_recovery_acceptance']['sha256'],'actual accepted pidfd retirement chain')
    need(not os.path.lexists(OUT),'fresh one-shot reconciliation evidence root')
    return release

def main():
    global LOCKFD,MUTATED,COMPLETE
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--release',type=Path,required=True);parser.add_argument('--release-sha256',required=True);parser.add_argument('--execute',action='store_true');args=parser.parse_args();need(args.execute,'explicit execution release required')
    release=validate_release(args.release,args.release_sha256)
    previous={};docker=None;HOLD_REQUIRED=False
    oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,m.DEFERRED_SIGNALS)
    def defer(number,frame):
        if not REQUESTED:REQUESTED.append(number)
    for number in m.DEFERRED_SIGNALS:previous[number]=signal.signal(number,defer)
    signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)
    try:
        LOCKFD=m.acquire_root_lock()
        OUT.mkdir(mode=0o700)
        current_safety()
        need(normal.census(),'exact retained stopped container must be present before reconciliation')
        current_safety();need(normal.census(),'second exact stopped profile before mutation')
        docker=FixedDocker(OUT/'docker.log',CleaningSignals(),sudo=True)
        logged=docker.call(['logs','--',CID],timeout=30)
        oldlog=Path(next(row['path'] for row in p['protected_inputs'] if row['path'].endswith('/container.log'))).read_bytes()
        need((logged.stdout+logged.stderr).encode()==oldlog,'owned stopped-container logs changed')
        current_safety();need(normal.census(),'exact retained stopped profile immediately before rm')
        write_json(OUT/'PREPARED.json',{'scope':__doc__,'release_sha256':args.release_sha256,'postjoin_acceptance':p['postjoin_acceptance'],'container_id':CID,'records':p['record_values'],'failed_ledger_preserved':True,'owner_status_retired_remains_false':True})
        MUTATED=True
        removed=docker.call(['rm','--',CID],timeout=30);need(removed.stdout.strip()==CID,'exact owned CID rm result')
        need(not normal.census(),'exact owned container must now be absent')
        # Existing SDK normal absence proof uses all three exact filters.
        for query in ('name=^/'+NAME+'$','label=mckernel.owner='+NONCE,'id='+CID):need(docker.call(['ps','--all','--quiet','--no-trunc','--filter',query],timeout=30).stdout.strip()=='','exact owned absence filter')
        count=positive_clients(docker,OUT);current_safety()
        proof={'schema':'mckernel.sdk.quarantine-reconciliation.postflight.v1','container_absent':True,'all_clients_reaped':True,'new_cleanup_client_count':count,'original_clients_physically_absent':True,'original_FAILED_ledger_preserved':True,'original_owner_receipt_retired_remains_false':True,'pidfd_retirement_acceptance':p['process_recovery_acceptance'],'current_postjoin_acceptance':p['postjoin_acceptance']}
        archive=release_owned_records(request,{Path(path):value for path,value in p['record_values'].items()},OUT,proof,p['original_authority'])
        current_safety();need(not normal.census() and RELEASED_RECORDS==RECORD_PATHS,'terminal owned absence and exactly three releases')
        positive_clients(docker,OUT)
        result={'schema':'mckernel.sdk.quarantine-owned-container-three-record-reconciliation.result.v1','status':'PASS_EXACT_OWNED_CONTAINER_AND_THREE_RECORDS_RECONCILED','container_id':CID,'container_absent':True,'records_absent':sorted(RELEASED_RECORDS),'ownership_archive_sha256':host.digest(OUT/'ownership-archive.json'),'profile_sha256':PROFILE_SHA,'release_sha256':args.release_sha256,'source_workload_status':'FAIL','original_FAILED_ledger_preserved':True,'signals_sent':0,'mutex_inode':[27,4],'native_acceptance':False,'heavy_execution_released':False,'reader_pid':os.getpid(),'reader_starttime':m.proc_stat(os.getpid())[19]}
        write_json(OUT/'RESULT.json',result);COMPLETE=True;print(json.dumps(result,sort_keys=True));return 0
    except BaseException:
        HOLD_REQUIRED=not COMPLETE and (MUTATED or (docker is not None and docker.client_retirement_unproven))
        if HOLD_REQUIRED:
            m.QUARANTINE=OUT/'RECONCILIATION-UNCERTAIN.json';m.quarantine_hold(LOCKFD)
        raise
    finally:
        if not HOLD_REQUIRED and LOCKFD is not None and (not MUTATED or COMPLETE):os.close(LOCKFD);LOCKFD=None
        if not HOLD_REQUIRED and (not MUTATED or COMPLETE):
            oldmask2=signal.pthread_sigmask(signal.SIG_BLOCK,m.DEFERRED_SIGNALS)
            for number,handler in previous.items():signal.signal(number,handler)
            signal.pthread_sigmask(signal.SIG_SETMASK,oldmask2)
if __name__=='__main__':raise SystemExit(main())
