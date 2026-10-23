"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,c.stop)
os.sched_setaffinity(0,{0})
for k,v in [(resource.RLIMIT_AS,536870912),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,134217728),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
A=D/'actual-capture-1';A.mkdir(mode=0o700)
command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'test_mount_destinations.py')],'purpose':__doc__}
c.write(A/'command.json',command);c.write(A/'FROZEN-SOURCES.json',[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in [D/'run_capture.py',D/'test_mount_destinations.py',D.parent/'native_diagnostic_container_owner.py']])
signal.setitimer(signal.ITIMER_REAL,126)
try:r=c.owned_capture(command,A,120,lambda:None)
finally:signal.setitimer(signal.ITIMER_REAL,0)
c.write(A/'RESULT.json',r)
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None,r
print(json.dumps({'status':'PASS','seconds':r['seconds'],'cpu0_released':True}))
