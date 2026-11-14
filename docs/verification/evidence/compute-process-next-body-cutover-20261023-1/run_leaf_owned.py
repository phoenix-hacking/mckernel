# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
P=Path(__file__).resolve().parent
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=HELPER.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
tree=ast.parse(raw,str(HELPER));nodes=[]
for node in tree.body:
 if isinstance(node,ast.FunctionDef) and node.name in functions:nodes.append(node)
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in node.targets):nodes.append(node)
ns=globals();exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER),'exec'),ns)
recipe_path=P/'NEXT-LEAF-RECIPE.NOT-EXECUTED.json';recipe=json.loads(recipe_path.read_text());assert hashlib.sha256(recipe_path.read_bytes()).hexdigest()=='396a17b1eb529f9a720da5607ad1f9438bbdb300fff559527558e25ad7ef2e3d'
for rel,pin in recipe['files'].items():assert hashlib.sha256((P/rel).read_bytes()).hexdigest()==pin['sha256'],rel
bindings=json.loads((P/'SOURCE-BINDINGS.json').read_text())
for pin in bindings['source_inputs'].values():assert hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()==pin['sha256'],pin['path']
assert os.getuid()==os.geteuid()==1000
O=P/'actual-leaf-owned-capture-1';O.mkdir(mode=0o700)
def limits():
 os.sched_setaffinity(0,{6})
 for key,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(key,(value,value))
limits();os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
command=dict(argv=recipe['argv'],scope=recipe['scope'],purpose='Functional OS original-C/Rust set_timer equivalence and current-header ABI compile; no security testing.')
write(O/'command.json',command)
signal.setitimer(signal.ITIMER_REAL,96)
record=None
try: record=owned_capture(command,O,90,limits)
finally:signal.setitimer(signal.ITIMER_REAL,0)
assert record is not None
passed=record['returncode']==0 and record['direct_child_joined'] and record['group_absent'] and record['closed_streams'] and not record['error'] and not record['retirement_error'] and not record['timed_out'] and cpu_used()<=60
result=dict(scope=recipe['scope'],status='PASS_LEAF' if passed else 'FAIL_PRESERVED',record=record,helper_sha256=hashlib.sha256(raw).hexdigest(),recipe_sha256=hashlib.sha256(recipe_path.read_bytes()).hexdigest(),total_CPU_seconds=cpu_used(),CPU6_released=record['direct_child_joined'] and record['group_absent'] and record['closed_streams'],canonical_inputs_unchanged=all(hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()==pin['sha256'] for pin in bindings['source_inputs'].values()),whole_C_TU_default_kernel_native='OPEN')
write(O/'whole-join.json',result);print(json.dumps(result));raise SystemExit(0 if passed else 1)
