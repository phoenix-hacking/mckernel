"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal
D=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('capture',H);c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,c.stop)
os.sched_setaffinity(0,{6})
for k,v in [(resource.RLIMIT_AS,2147483648),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,33554432),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
A=D/'actual-stage-capture-1';A.mkdir(mode=0o700)
def free(p):s=os.statvfs(p);return s.f_bavail*s.f_frsize
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
facts={'memory_available':mem,'memory_required':19*1024**3,'host_available':free('/home/holden/mckernel-work'),'host_floor':140534349824,'scratch_available':free('/home/holden/mckernel-work/scratch'),'scratch_floor':13899923456};c.write(A/'FRESH-HEADROOM.json',facts);assert mem>=facts['memory_required'] and facts['host_available']>=facts['host_floor'] and facts['scratch_available']>=facts['scratch_floor']
c.write(A/'FROZEN-SOURCES.json',[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in [D/'metadata/stage_bound_successor.py',D/'run_stage.py',D/'SOURCE-ACCEPTANCE.INPUT.json',D/'SOURCE-REVIEW.NORMALIZED-ROOT-RECORD.json']])
command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'metadata/stage_bound_successor.py'),'--execute'],'purpose':__doc__};c.write(A/'command.json',command)
signal.setitimer(signal.ITIMER_REAL,126)
try:r=c.owned_capture(command,A,120,lambda:None)
finally:signal.setitimer(signal.ITIMER_REAL,0)
c.write(A/'RESULT.json',r)
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None,r
print(json.dumps({'status':'PASS_SOURCE_STAGE','seconds':r['seconds'],'cpu6_released':True}))
