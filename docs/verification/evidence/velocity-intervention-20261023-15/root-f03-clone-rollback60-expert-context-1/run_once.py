"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import os,sys,json,hashlib,importlib.util,signal,resource,time
D=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
S=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-clone-caller-rollback-source-1/actual-rollback-consumer-preparation-1/bounded-null-mut-context-correction-1/run_clone_rollback_actual_once.EXPERT-PENDING.py')
assert hashlib.sha256(S.read_bytes()).hexdigest()=='c4ec62e1b881057d0b3106bdeb59f9a9dd53d14cc7d15ab6b9c8504588de96dc'
assert os.getuid()==1000 and os.sched_getaffinity(0)=={0}
m=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
assert m>=25501368320
spec=importlib.util.spec_from_file_location('owned',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,h.stop)
for key,val in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(key,(val,val))
os.environ['RUST_MIN_STACK']='2097152'
command=dict(argv=['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(S)],purpose=__doc__+' One exact original-C/Rust caller rollback60 and27actualABI checks with genuine trackedfree/atomic providers; no constructor/guest.')
h.write(D/'ROOT-GRANT.json',dict(command=command,MemAvailable=m,profile='CPU6 one job AS2GiB CPU60 wall90+6 F32MiB FD256 core0 stack2MiB; outer observer CPU0',prior_failure_retained=True))
signal.setitimer(signal.ITIMER_REAL,108)
os.chdir(S.parent)
os.environ['PYTHONDONTWRITEBYTECODE']='1'
r=h.owned_capture(command,D,102,lambda:None)
h.write(D/'WHOLE-JOIN.json',r)
signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps({k:r.get(k) for k in ['returncode','seconds','direct_child_joined','group_absent','closed_streams','error','retirement_error','timed_out']}))
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
