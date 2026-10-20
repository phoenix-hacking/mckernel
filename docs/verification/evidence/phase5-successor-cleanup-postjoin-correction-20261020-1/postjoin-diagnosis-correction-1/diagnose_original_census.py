"""Pinned original postjoin census only; preserve suppressed child failure evidence."""
import argparse,base64,fcntl,hashlib,json,os,resource,traceback,types
from pathlib import Path
POSTJOIN=Path('/home/holden/mckernel-work/host-preparation/phase5-image-postbuild-terminal-preparation-20261020-1/failure-case-1/successor-cleanup-preparation-1/entry-guard-correction-1/postjoin_readback.py')
POSTJOIN_SHA='a60c92024f699961eec4ddd2e214fcecee44ee797f15e666b8134553d30204b2'
CAP=65536

def load():
    raw=POSTJOIN.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=POSTJOIN_SHA:raise RuntimeError('pinned postjoin source differs')
    p=types.ModuleType('_exact_closed_postjoin');p.__file__=str(POSTJOIN)
    exec(compile(raw,str(POSTJOIN),'exec'),p.__dict__)
    return p

def completed_failure(error,engine):
    tb=error.__traceback__;rows=[]
    while tb is not None:
        frame=tb.tb_frame
        if frame.f_code.co_filename==str(engine) and frame.f_code.co_name=='root_command':
            cp=frame.f_locals.get('result')
            if cp is not None:
                row=dict(returncode=cp.returncode,executable=cp.args[0],argument_count=len(cp.args),argv_sha256=hashlib.sha256(json.dumps(cp.args,separators=(',',':')).encode()).hexdigest(),source_function='root_command')
                for key in ('stdout','stderr'):
                    raw=getattr(cp,key);raw=raw if isinstance(raw,bytes) else str(raw).encode()
                    row[key]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
                    if key=='stderr':row[key].update(complete=len(raw)<=CAP,base64=base64.b64encode(raw[:CAP]).decode())
                row['rejected_conditions']=dict(nonzero_returncode=bool(cp.returncode),nonempty_stderr=bool(cp.stderr),stdout_over_limit=len(cp.stdout)>frame.f_locals['limit'])
                rows.append(row)
        tb=tb.tb_next
    return rows[:1]

def main():
    a=argparse.ArgumentParser(allow_abbrev=False);a.add_argument('--release',type=Path,required=True);a.add_argument('--sha256',required=True);a.add_argument('--cleanup-result',type=Path,required=True);args=a.parse_args()
    if os.getuid()!=0 or os.geteuid()!=0:raise RuntimeError('separate root read-only admission required')
    resource.setrlimit(resource.RLIMIT_AS,(1073741824,2147483648));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432))
    p=load();m=p.load(p.ENGINE,p.ENGINE_SHA)
    raw=args.release.read_bytes();p.need(hashlib.sha256(raw).hexdigest()==args.sha256,'exact release differs')
    r=json.loads(raw);obs=r['observation'];target=obs['target'];result=json.loads(args.cleanup_result.read_bytes())
    p.need(r['status']=='PASS_EXECUTION_RELEASE' and result['status']=='PASS_EXECUTED' and result['terminal'] and result['container_absent'],'positive released cleanup required')
    p.need(result['container_id']==target['container_id'] and result['release_sha256']==m.digest(m.canonical(r)),'exact cleanup/release binding')
    parent,_=m.directory(m.ROOT_LOCK.parent);lock=None;held=False;report=None
    try:
        lock=os.open(m.ROOT_LOCK.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        p.need((os.fstat(lock).st_dev,os.fstat(lock).st_ino)==(27,4),'root lock differs')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);held=True
        p.need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==obs['boot_id'],'boot differs')
        m.BOOT_ID=obs['boot_id'];m.OWNER_PID=target['owner_pid'];m.OWNER_START=target['owner_starttime'];m.WAITER_PIDS=tuple(x['pid'] for x in obs['client_ledger'])
        m.CONTAINER=target['container_id'];m.CONTAINER_NAME=target['container_name'];m.OWNER_NONCE=target['owner_nonce'];m.EXPECTED_EXIT=target['exit_code'];m.EXPECTED_CONTAINER=obs['container_inspect']
        p.bind_readback(m,r)
        try:
            present=p.census_at_2g(m)
            report=dict(status='PASS_ORIGINAL_CENSUS_READ_ONLY' if not present else 'ORIGINAL_CENSUS_TARGET_PRESENT',predicate_passed=not present,container_present=present)
        except BaseException as error:
            report=dict(status='ORIGINAL_CENSUS_READ_ONLY_REFUSAL',predicate_passed=False,error_type=type(error).__name__,message=str(error)[:4096],inner_completed_process=completed_failure(error,m.__file__),source_frames=[dict(file=f.filename,line=f.lineno,function=f.name,source=f.line) for f in traceback.extract_tb(error.__traceback__) if f.filename in (str(POSTJOIN),str(m.__file__))][-5:])
    finally:
        if held:fcntl.flock(lock,fcntl.LOCK_UN)
        if lock is not None:os.close(lock)
        os.close(parent)
    report.update(root_lock_released=True,postjoin_sha256=POSTJOIN_SHA,engine_sha256=p.ENGINE_SHA,cleanup_replayed=False,postjoin_or_archive_run=False,original_failure_cause_recovered=False)
    print(json.dumps(report,sort_keys=True));return 0 if report['predicate_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
