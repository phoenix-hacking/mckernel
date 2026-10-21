"""Exact current fresh-attempt preflight only; no engine run/recover/effects."""
import argparse,base64,hashlib,json,os,traceback,types
from pathlib import Path
SOURCE=Path('/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/cleanup_pass_image.py')
SOURCE_SHA = '86654275eced623bb15ce289ca6555264b2820b56336e629fe084cb9aed96ce0'
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
    if os.getuid()!=0 or os.geteuid()!=0:raise RuntimeError('separate reviewed root read-only preflight required')
    raw=SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise RuntimeError('exact corrected current source differs')
    m=types.ModuleType('_exact_corrected_successor_preflight');m.__file__=str(SOURCE);exec(compile(raw,str(SOURCE),'exec'),m.__dict__)
    tx=None;stage='configure(False)';result=None
    try:
        release=m.read_bounded(a.release)
        if m.digest(release)!=a.sha256:raise m.Refusal('actual released preflight data differs')
        m.configure(m.parse(release),execute=False)
        stage='Transaction() same27:4 root lock'
        tx=m.Transaction()
        stage='actual Transaction.preflight_fresh()'
        tx.preflight_fresh()
        if tx.mutation_started or tx.mfd is not None:raise RuntimeError('fresh read-only preflight changed mutation/mutex state')
        result=dict(status='PASS_ACTUAL_FRESH_PREFLIGHT_READ_ONLY',predicate_passed=True,mutation_started=False,transaction_mutex_opened=False,original_refusal_reason_recovered=False)
    except BaseException as error:
        frames=[dict(file=f.filename,line=f.lineno,function=f.name,source=f.line) for f in traceback.extract_tb(error.__traceback__) if f.filename==str(SOURCE)][-5:]
        result=dict(status='ACTUAL_FRESH_PREFLIGHT_REFUSAL' if isinstance(error,m.Refusal) else 'ACTUAL_FRESH_PREFLIGHT_EXCEPTION',predicate_passed=False,failed_stage=stage,error_type=type(error).__name__,message=str(error)[:4096],source_frames=frames,inner_completed_process=inner_completed_process(error))
    finally:
        if tx is not None:tx.close()
    result.update(source_sha256=SOURCE_SHA,transaction_closed=True,engine_execution_enabled=False,no_cleanup_or_record_release=True)
    print(json.dumps(result,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
