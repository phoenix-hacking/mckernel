"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import os,sys,json,hashlib,importlib.util,signal,resource,time
D=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
S=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-exec-filename-admission-source-1/admission-descriptor-actual-fixture-preparation-1/run_admission_descriptor_fixture_once.NOT-GRANTED.py')
assert hashlib.sha256(S.read_bytes()).hexdigest()=='a9d1f71cb4ee4cfd8e9709b56b51585e4315e97020ad569c6f61073da916b983'
assert os.getuid()==1000 and os.sched_getaffinity(0)=={0}
m=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
assert m>=25501368320
spec=importlib.util.spec_from_file_location('owned',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,h.stop)
for key,val in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(key,(val,val))
os.environ['RUST_MIN_STACK']='2097152'
command=dict(argv=['/usr/bin/taskset','-c','6','/home/holden/anaconda3/bin/python3','-I','-B',str(S)],purpose=__doc__+' Root grants one exact F03 admission-descriptor original-C/public-Rust fixture, eight commands; unexpected failure stops expert.')
h.write(D/'ROOT-GRANT.json',dict(command=command,MemAvailable=m,profile='CPU6 one job AS2GiB CPU60 wall90+6 F32MiB FD256 core0 stack2MiB; outer observer CPU0',prior_failure_retained=True))
signal.setitimer(signal.ITIMER_REAL,108)
r=h.owned_capture(command,D,102,lambda:None)
h.write(D/'WHOLE-JOIN.json',r)
signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps({k:r.get(k) for k in ['returncode','seconds','direct_child_joined','group_absent','closed_streams','error','retirement_error','timed_out']}))
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
