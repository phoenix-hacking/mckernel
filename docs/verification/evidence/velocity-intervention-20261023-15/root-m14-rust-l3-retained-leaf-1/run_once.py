"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import os,sys,json,hashlib,importlib.util,signal,resource,time
D=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
S=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/rust-owned-l3-callback-observer-correction-1/check_retained_C_callback_leaf.NOT-EXECUTED.py')
assert hashlib.sha256(S.read_bytes()).hexdigest()=='a79aef9ac7ad7af03030fcdc4512c8b910d4c7ba6e4bf3f0c9b33859a56949be'
assert os.getuid()==1000 and os.sched_getaffinity(0)=={0}
m=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
assert m>=25501368320
spec=importlib.util.spec_from_file_location('owned',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,h.stop)
for key,val in [(resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,10),(resource.RLIMIT_FSIZE,16<<20),(resource.RLIMIT_NOFILE,128),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(key,(val,val))
os.environ['RUST_MIN_STACK']='2097152'
command=dict(argv=['/usr/bin/taskset','-c','0','/home/holden/anaconda3/bin/python3','-I','-B',str(S)],purpose=__doc__+' Single retained C callback object leaf, no compiler/full driver import/artifact write.')
h.write(D/'ROOT-GRANT.json',dict(command=command,MemAvailable=m,profile='CPU0 one job AS512MiB CPU10 wall30+5 F16MiB FD128 core0 stack2MiB',prior_failure_retained=True))
signal.setitimer(signal.ITIMER_REAL,41)
os.chdir(S.parent)
os.environ['PYTHONDONTWRITEBYTECODE']='1'
r=h.owned_capture(command,D,35,lambda:None)
h.write(D/'WHOLE-JOIN.json',r)
signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps({k:r.get(k) for k in ['returncode','seconds','direct_child_joined','group_absent','closed_streams','error','retirement_error','timed_out']}))
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
