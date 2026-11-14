"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,stat
D=Path(__file__).resolve().parent;CAP=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(CAP.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('capture',CAP);cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,cap.stop)
os.sched_setaffinity(0,{0})
for k,v in [(resource.RLIMIT_AS,536870912),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,134217728),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
A=D/'actual-fixture-1';A.mkdir(mode=0o700)
cap.write(A/'FROZEN-PRELAUNCH-SOURCES.json',{'scope':__doc__,'files':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in sorted(D.glob('*.py'))]})
source=D.parent/'typed-capsule-preparation-1/actual-stage-1/manifest.json';raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()=='2b9115a45ddfffddeecf95f5d7c2da5670ef80272e34d8f2bdbdfe34f2c4de7e'
S=Path('/home/holden/mckernel-work/scratch');assert S.stat().st_dev==1828
sp=S/'m07s1';sp.mkdir(mode=0o700);assert sp.lstat().st_dev==1828 and sp.lstat().st_uid==1000 and stat.S_IMODE(sp.lstat().st_mode)==0o700
fd=os.open(sp/'m.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
assert (sp/'m.json').lstat().st_dev==1828 and (sp/'m.json').lstat().st_uid==1000 and stat.S_IMODE((sp/'m.json').lstat().st_mode)==0o600
H=Path('/home/holden/mckernel-work/native-runs');assert H.stat().st_dev==66306
hp=H/'m07s1';hp.mkdir(mode=0o700);p=hp/'p';p.mkdir(mode=0o700)
for x in (hp,p):assert x.lstat().st_dev==66306 and x.lstat().st_uid==1000 and stat.S_IMODE(x.lstat().st_mode)==0o700 and not x.is_symlink()
cap.write(A/'PUBLICATION.json',{'scope':__doc__,'manifest':cap.hashed(sp/'m.json',4<<20),'host_parent':{'path':str(p),'dev':p.stat().st_dev,'inode':p.stat().st_ino,'mode':p.stat().st_mode,'uid':p.stat().st_uid},'authorization':'Parent root explicit fresh exclusive scratch m07s1/m.json and HOST native-runs/m07s1/p + one fixture child only; no execution release.'})
command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'test_runtime_bindings.py')],'purpose':__doc__};cap.write(A/'command.json',command)
signal.setitimer(signal.ITIMER_REAL,126)
try:result=cap.owned_capture(command,A,120,lambda:None)
finally:signal.setitimer(signal.ITIMER_REAL,0)
cap.write(A/'RESULT.json',result)
assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
cap.write(A/'FINAL-RESULT.json',{'scope':__doc__,'status':'PASS_ACTUAL_COHERENT_SINGLE_APP_RUNTIME_SOURCE_FIXTURE','capture':result,'fixture':json.loads((D/'FIXTURE-RESULT.json').read_bytes()),'runtime_execution_release':None,'native_result':None,'cpu0_released':True})
print(json.dumps({'status':'PASS','seconds':result['seconds'],'cpu0_released':True}))
