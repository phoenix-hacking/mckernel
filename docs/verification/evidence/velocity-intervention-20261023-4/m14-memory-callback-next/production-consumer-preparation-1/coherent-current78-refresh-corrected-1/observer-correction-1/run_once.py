"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-granted CPU7 retained-only observer execution, no build/relink.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,sys
D=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,c.stop)
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7};assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
for k,v in [(resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,10),(resource.RLIMIT_FSIZE,8<<20),(resource.RLIMIT_NOFILE,128),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
os.umask(0o077);A=D/'actual-capture-1';A.mkdir(mode=0o700)
command=dict(argv=[sys.executable,'-I','-B',str(D/'check_retained.py')],cwd=str(D),purpose=__doc__)
c.write(A/'PRELAUNCH-SOURCE-PROFILE.json',dict(command=command,observer_sha256=sha(D/'check_retained.py'),driver_sha256=sha(Path(__file__)),CPU=7,AS=512<<20,CPU_seconds=10,wall=15,retirement=6,FSIZE=8<<20,NOFILE=128,core=0,interpreter=sys.executable,version=sys.version,helper_sha256=sha(H)))
signal.setitimer(signal.ITIMER_REAL,21)
try:
 result=c.owned_capture(command,A,15,lambda:None);c.write(A/'WHOLE-JOIN.json',result)
 assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
 actual=json.loads((A/'stdout').read_text());assert actual['status']=='PASS_RETAINED_SECTION_AWARE_TWO_CALLBACK_RELOCATIONS_AND_ALL_PRIOR_PRODUCTION_CHECKS'
 c.write(D/'FINAL-RETAINED-OBSERVER-CORRECTION-RECEIPT.json',dict(scope=__doc__,status=actual['status'],join=result,CPU7_released=True,source=actual['observer_source_sha256'],actual=actual,no_compiler_relink_source_or_object_mutation=True));print(json.dumps(dict(status=actual['status'],seconds=result['seconds'],CPU7_released=True)))
except BaseException as e:
 c.write(A/'FAILURE.STOP.json',dict(scope=__doc__,error=repr(e),CPU7_released=True,no_retry=True));raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
