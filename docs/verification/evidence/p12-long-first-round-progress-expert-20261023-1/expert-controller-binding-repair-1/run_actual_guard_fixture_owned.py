"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. One ordinary actualconsumer job."""
import ast,hashlib,json,os,resource,signal
from pathlib import Path
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'} for t in n.targets)];ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
out=D/'actual-controller-guard-fixture-1';out.mkdir(mode=0o700)
argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'fixture_actual_controller_guards.py')]
ns['write'](out/'command.json',dict(purpose=__doc__,argv=argv,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'fixture_actual_controller_guards.py',Path(__file__),D/'capture_root_LONG.NOT-RELEASED.py',*sorted((D/'source').glob('*.py'))]},profile=dict(cpu=[0],AS=2*2**30,CPU=30,wall=60,grace=6,FSIZE=32*2**20,NOFILE=256,core=0)))
def limits():
 os.sched_setaffinity(0,{0})
 for key,value in [(resource.RLIMIT_AS,2*2**30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32*2**20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(key,(value,value))
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
signal.setitimer(signal.ITIMER_REAL,60)
r=ns['owned_capture'](dict(argv=argv),out,60,limits);signal.setitimer(signal.ITIMER_REAL,0);ns['write'](out/'RESULT.json',r)
print(json.dumps(r,sort_keys=True))
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None,r
