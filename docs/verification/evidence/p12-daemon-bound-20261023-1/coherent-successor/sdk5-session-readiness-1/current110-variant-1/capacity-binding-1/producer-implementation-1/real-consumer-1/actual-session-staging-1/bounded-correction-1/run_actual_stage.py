"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource
D=Path(__file__).resolve().parent
E=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/capacity-binding-1/producer-implementation-1/real-consumer-1/actual-session-staging-1/bounded-correction-1')
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('owned_capture',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
a=D/'attempt-1';a.mkdir()
for p in D.iterdir():
 if p.is_file():(a/p.name).write_bytes(p.read_bytes())
h.write(a/'SOURCE-BINDINGS.json',[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in a.iterdir() if p.is_file()])
os.sched_setaffinity(0,{6});os.chdir(D)
for k,v in ((resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,128<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)):resource.setrlimit(k,(v,v))
py='/home/holden/anaconda3/bin/python3'
commands=[('actual-capsule-fixtures',[py,'-I','-B',str(D/'fixture_stage_transform.py')]),('actual-HOST-stage',[py,'-I','-B',str(D/'stage_long_session.py'),'--binding',str(D/'ACTUAL-STAGE-BINDING.json')]),('actual-stage-verification',[py,'-I','-B',str(D/'verify_actual_stage.py')])]
results=[]
for label,argv in commands:
 c=a/label;c.mkdir();command={'argv':argv,'purpose':__doc__,'cwd':str(D),'shell':False};h.write(c/'command.json',command)
 r=h.owned_capture(command,c,120,lambda:None);h.write(c/'result.json',r);results.append({'label':label,'whole_join':r})
 if r['returncode']!=0 or not r['direct_child_joined'] or not r['group_absent'] or not r['closed_streams'] or r['error'] or r['retirement_error']:break
status='PASS' if len(results)==3 and all(x['whole_join']['returncode']==0 for x in results) else 'FAIL_STOP_FIRST_FAILURE'
h.write(a/'RESULT.json',{'scope':__doc__,'status':status,'results':results,'capacity_admission':None,'native_acceptance':False})
for p in D.rglob('*'):
 if p.is_file() and p.suffix!='.gz' and p.name!='collector-long-0755':
  q=E/p.relative_to(D);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
print(json.dumps({'status':status,'commands':len(results),'last_label':results[-1]['label'],'returns':[x['whole_join']['returncode'] for x in results]}))
