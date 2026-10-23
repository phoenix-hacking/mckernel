"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One authorized ordinary candidate6 source materialization. No compiler/root/build.
"""
import ast,hashlib,json,os,resource,signal,time
from pathlib import Path
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
body=[]
for n in ast.parse(raw,str(SOURCE)).body:
 if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets):body.append(n)
ns={'__file__':str(SOURCE)};exec(compile(ast.Module(body=body,type_ignores=[]),str(SOURCE),'exec'),ns)
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}
validator=D/'prepare_and_validate.py';assert hashlib.sha256(validator.read_bytes()).hexdigest()=='7b0e1a330ef6b223e9d337a71468b479788dca828db73fed86387772fcfc6423'
cap=D/'pure-validator-capture-1';cap.mkdir(mode=0o700)
command={'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exclusive candidate6 request preparation and one pure complete validator; no run/acquire/compiler/root.','argv':['/usr/bin/taskset','-c','0','/home/holden/anaconda3/bin/python3','-I','-B',str(validator)]}
ns['write'](cap/'command.json',command)
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CPU,(60,60));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
result=ns['owned_capture'](command,cap,90,limits);ns['write'](cap/'whole-join.json',result)
assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
print(json.dumps(result,sort_keys=True))
