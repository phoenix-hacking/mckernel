"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,sys
D=Path(__file__).resolve().parent;E=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/capsule-successor-preparation-1/coherent-source-successor-1/admission-bounded-correction-1/path-policy-fixtures-1')
h=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=h.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
t=ast.parse(raw,str(h));end=next(i for i,x in enumerate(t.body) if isinstance(x,ast.FunctionDef) and x.name=='owned_capture');ns={'__file__':str(h)};exec(compile(ast.Module(body=t.body[:end+1],type_ignores=[]),str(h),'exec'),ns)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
os.sched_setaffinity(0,{0})
for k,v in [(resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,128<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
cap=D/'actual-selected-predicate-1';cap.mkdir();command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'fixture_selected_admission.py')],'purpose':__doc__,'shell':False,'source_sha256':hashlib.sha256((D/'fixture_selected_admission.py').read_bytes()).hexdigest()};ns['write'](cap/'command.json',command)
j=ns['owned_capture'](command,cap,120,lambda:None);ns['write'](cap/'whole-join.json',j)
r={'scope':__doc__,'status':'PASS_COHERENT_CONSUMER_WHOLE_JOIN' if j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'] else 'FAIL_FIRST_COHERENT_CONSUMER_CAPTURE_RETAINED','whole_join':j,'CPU0_released':j['direct_child_joined'] and j['group_absent'] and j['closed_streams'],'native_acceptance':False};ns['write'](D/'ACTUAL-SELECTED-PREDICATE-WHOLE-JOIN.json',r)
for p in [D/'ACTUAL-SELECTED-PREDICATE-WHOLE-JOIN.json',*cap.iterdir(),*[D/n for n in ['ACTUAL-SELECTED-QUERY-PREDICATE-RESULT.json'] if (D/n).exists()]]:
 q=E/p.relative_to(D);q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():assert q.read_bytes()==p.read_bytes()
 else:
  with q.open('xb') as f:f.write(p.read_bytes())
print(json.dumps(r))
