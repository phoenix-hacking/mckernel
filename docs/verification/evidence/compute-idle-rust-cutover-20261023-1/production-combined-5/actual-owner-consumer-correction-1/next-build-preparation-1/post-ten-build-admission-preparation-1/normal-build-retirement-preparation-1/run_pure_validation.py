"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw);names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
A=D/'pure-current-guard-capture-1';A.mkdir();os.chdir(D);os.sched_setaffinity(0,{6})
for k,v in ((resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)):resource.setrlimit(k,(v,v))
for number in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(number,stop)
signal.setitimer(signal.ITIMER_REAL,90)
need(json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent']<100,'included guard')
write(A/'SOURCE-BINDINGS.json',[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in (D/'pure_current_guard_validation.py',D/'run_pure_validation.py',D/'bound-current-normal-image-source-1/cleanup_pass_image.py',D/'bound-current-normal-image-source-1/observe_current_pass_image_retirement.py',D/'bound-current-normal-image-source-1/PASS-CASE-STATIC.json')])
command={'purpose':__doc__,'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'pure_current_guard_validation.py')],'cwd':str(D),'shell':False}
write(A/'command.json',command);joined=owned_capture(command,A,90,lambda:None)
signal.setitimer(signal.ITIMER_REAL,0);write(A/'RESULT.json',joined)
print(json.dumps({'returncode':joined['returncode'],'whole_join':joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'],'seconds':joined['seconds'],'CPU6_released_after_exit':True}))
