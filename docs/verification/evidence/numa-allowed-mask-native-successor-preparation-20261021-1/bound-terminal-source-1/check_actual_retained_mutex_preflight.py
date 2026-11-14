"""Exact retained-empty-mutex read-only validation; no cleanup/recover/effects.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
SOURCE ONLY: future root execution requires independent release and grant.
"""
import argparse,base64,hashlib,json,os,stat,traceback,types
from pathlib import Path
SOURCE=Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/bound-terminal-source-1/cleanup_pass_image.py')
SOURCE_SHA = '5f6716a8914564cfae06693931033fa2efacae49aaf2e21f18600463b376d21d'
MUTEX_EXPECTED = dict(path='/home/holden/mckernel-work/scratch/numa-allowed-mask-image-terminal-20261021-1.mutex',
                      device=1828,inode=116297,size=0,uid=1000,gid=1000,mode='0o600',nlink=1,
                      sha256='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
CAP=1<<20
def inner_completed_process(error):
    rows=[];tb=error.__traceback__
    while tb is not None:
        frame=tb.tb_frame
        if frame.f_code.co_filename==str(SOURCE) and frame.f_code.co_name=='root_command':
            cp=frame.f_locals.get('result')
            if cp is not None:
                row=dict(source_function='root_command',returncode=cp.returncode,argv=cp.args)
                for name in ('stdout','stderr'):
                    raw=getattr(cp,name)
                    if not isinstance(raw,bytes):raw=str(raw).encode()
                    row[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),complete=len(raw)<=CAP,base64=base64.b64encode(raw[:CAP]).decode())
                rows.append(row)
        tb=tb.tb_next
    return rows[:1]

def main():
    p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--release',type=Path,required=True);p.add_argument('--sha256',required=True);a=p.parse_args()
    if os.getuid()!=0 or os.geteuid()!=0:raise RuntimeError('separate reviewed root retained-mutex read-only preflight required')
    raw=SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise RuntimeError('exact corrected current source differs')
    m=types.ModuleType('_exact_retained_mutex_preflight');m.__file__=str(SOURCE);exec(compile(raw,str(SOURCE),'exec'),m.__dict__)
    tx=None;stage='configure(False)';result=None
    try:
        release=m.read_bounded(a.release)
        if m.digest(release)!=a.sha256:raise m.Refusal('actual released preflight data differs')
        m.configure(m.parse(release),execute=False)
        stage='Transaction() same27:4 root lock'
        tx=m.Transaction()
        def retained_state():
            if m.observe_identity(m.MUTEX)!=MUTEX_EXPECTED:
                raise m.Refusal('exact-retained-empty-mutex-binding')
            if (any(m.exists(tx.fd,path.name) for path in (m.PLAN,m.JOURNAL,m.CAPTURE,m.QUARANTINE)) or
                    any(m.exists(tx.parent_fd(path),name) for path,name in zip((m.ATTEMPT,m.SHARED),m.ARCHIVE_NAMES))):
                raise m.Refusal('retained-mutex-preflight-extra-transaction-state')
        stage='exact retained empty mutex and no other transaction state'
        retained_state()
        stage='actual Transaction.run(False) retained-mutex validation'
        validation=tx.run(False)
        if (not isinstance(validation,dict) or set(validation)!={'status','terminal','events','container_present','publisher_contract'} or
                validation.get('status')!='PASS_VALIDATE_ONLY' or validation.get('terminal') is not False or
                type(validation.get('events')) is not int or validation['events']!=0 or
                validation.get('container_present') is not True or validation.get('publisher_contract')!=m.PUBLISHER_CONTRACT):
            raise m.Refusal('exact-retained-mutex-validation-result')
        if tx.mutation_started is not False or tx.mfd is None or tx.root_locked is not True:
            raise m.Refusal('retained-mutex-read-only-lock-state')
        held=os.fstat(tx.mfd)
        if (not stat.S_ISREG(held.st_mode) or
                (held.st_dev,held.st_ino,held.st_size,held.st_uid,held.st_gid,stat.S_IMODE(held.st_mode),held.st_nlink)!=(1828,116297,0,1000,1000,0o600,1)):
            raise m.Refusal('retained-mutex-open-descriptor-binding')
        retained_state()
        result=dict(status='PASS_ACTUAL_RETAINED_MUTEX_PREFLIGHT_READ_ONLY',predicate_passed=True,
                    mutation_started=False,retained_mutex_opened=True,retained_mutex_locked_during_check=True,
                    retained_mutex=MUTEX_EXPECTED,engine_validation=validation,original_refusal_reason_recovered=False)
    except BaseException as error:
        frames=[dict(file=f.filename,line=f.lineno,function=f.name,source=f.line) for f in traceback.extract_tb(error.__traceback__) if f.filename==str(SOURCE)][-5:]
        result=dict(status='ACTUAL_RETAINED_MUTEX_PREFLIGHT_REFUSAL' if isinstance(error,m.Refusal) else 'ACTUAL_RETAINED_MUTEX_PREFLIGHT_EXCEPTION',predicate_passed=False,failed_stage=stage,error_type=type(error).__name__,message=str(error)[:4096],source_frames=frames,inner_completed_process=inner_completed_process(error))
    finally:
        if tx is not None:tx.close()
    closed=tx is None or (all(getattr(tx,name) is None for name in ('fd','mfd','rfd','nfd')) and tx.root_locked is False)
    if not closed:raise RuntimeError('retained-mutex preflight descriptors not closed')
    result.update(source_sha256=SOURCE_SHA,transaction_closed=True,engine_execution_enabled=False,no_cleanup_or_record_release=True)
    print(json.dumps(result,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
