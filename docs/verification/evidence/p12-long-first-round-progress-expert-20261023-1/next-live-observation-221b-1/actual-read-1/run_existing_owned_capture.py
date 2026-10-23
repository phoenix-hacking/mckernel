"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Single root-granted existing ordinary read, literal PID/birth only; no secondread/runtime controls.
"""
import ast,hashlib,json,os,resource,signal,time
from pathlib import Path
A=Path(__file__).resolve().parent;D=A.parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'} for t in n.targets)];ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
reader=D/'read_live_LONG_prefix.py';assert hashlib.sha256(reader.read_bytes()).hexdigest()=='3ca95d3914df4d93571db86d4981aece3df165bf5a04f1776b06100dd9538588'
argv=json.loads((D/'ORDINARY-CPU0-READ-ARGV.PENDING-LIVE-ANCHOR.json').read_bytes());assert argv[-2:]==[None,None];argv[-2:]=['3876675','58130649']
ns['write'](A/'command.json',dict(scope=__doc__,argv=argv,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [reader,Path(__file__)]},grant='Root explicit one first221b ordinary read after authenticatedstarted ec73774e; no secondread.',inner_start_monotonic_seconds=581306.49,profile=dict(cpu=[0],AS=2**31,CPU=10,wall=20,grace=6,FSIZE=32*2**20,NOFILE=256,core=0)))
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
remaining=581306.49+30-time.monotonic()
if remaining>0:time.sleep(min(remaining,30))
assert time.monotonic()>=581306.49+30
ns['write'](A/'launch-clock.json',dict(monotonic_seconds=time.monotonic(),inner_age_seconds=time.monotonic()-581306.49))
def limits():
 os.sched_setaffinity(0,{0})
 for key,value in [(resource.RLIMIT_AS,2**31),(resource.RLIMIT_CPU,10),(resource.RLIMIT_FSIZE,32*2**20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(key,(value,value))
signal.setitimer(signal.ITIMER_REAL,20)
r=ns['owned_capture'](dict(argv=argv),A,20,limits);signal.setitimer(signal.ITIMER_REAL,0);ns['write'](A/'RESULT.json',r)
print(json.dumps(dict(returncode=r['returncode'],seconds=r['seconds'],direct_child_joined=r['direct_child_joined'],group_absent=r['group_absent'],closed_streams=r['closed_streams'],error=r['error'],retirement_error=r['retirement_error'],stdout=r['captures']['stdout'],stderr=r['captures']['stderr']),sort_keys=True))
assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None,r
