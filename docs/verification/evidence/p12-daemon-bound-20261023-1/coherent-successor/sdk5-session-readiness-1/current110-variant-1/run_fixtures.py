"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource
H=Path(__file__).resolve().parent;helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
# Extract exact accepted imports/helpers/constants only, through owned_capture; no module main.
tree=ast.parse(raw,str(helper));nodes=[]
for n in tree.body:
 nodes.append(n)
 if isinstance(n,ast.FunctionDef)and n.name=='owned_capture':break
ns=dict(__file__=str(helper),__name__='accepted_owned_capture_extract');exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
os.sched_setaffinity(0,{6})
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
os.chdir(H);cap=H/'fixture-capture-1';cap.mkdir(mode=0o700);command=dict(purpose=__doc__,argv=['/usr/bin/python3','-I','-B',str(H/'test_suite.py')],cwd=str(H),shell=False)
with(cap/'command.json').open('x')as f:json.dump(command,f,indent=2);f.write('\n')
joined=ns['owned_capture'](command,cap,90,lambda:None)
with(cap/'WHOLE-JOIN.json').open('x')as f:json.dump(joined,f,indent=2);f.write('\n')
print(json.dumps(joined));assert joined['returncode']==0 and joined['direct_child_joined']and joined['group_absent']and joined['closed_streams']and not joined['error']and not joined['retirement_error']
