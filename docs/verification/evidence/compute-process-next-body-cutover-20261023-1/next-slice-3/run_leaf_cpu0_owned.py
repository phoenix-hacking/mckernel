"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Proposed ordinary leaf only: original C macro/actual Rust dynamic diagnostic and hosted variadic sink.
No root, Docker, guest, kernel, target lock/IRQ/state instructions or fullcrate.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
P=Path(__file__).resolve().parent;F=P/'EXACT-LEAF-CPU0-RECIPE.GRANTED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
assert sha(F)=='a256aaa63017f39d48a6a6edb6c45e6e610a810dfdfc18bf852fc57a252ca094';recipe=json.loads(F.read_text())
for row in [*recipe['source_files'].values(),*recipe['tools'].values(),*recipe['actual_header_config_closure'].values()]:assert pin(Path(row['path']))==row
bindings=json.loads((P/'SOURCE-BINDINGS.json').read_text())
for row in [*[x['before'] for x in bindings['changes'].values()],*bindings['references'].values()]:assert pin(Path(row['path']))==row
assert os.getuid()==os.geteuid()==1000
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
O=P/'leaf-output-1';O.mkdir(mode=0o700);CAP=P/'actual-leaf-cpu0-owned-capture-1';CAP.mkdir(mode=0o700)
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;h=os.statvfs('/home/holden');s=os.statvfs('/home/holden/mckernel-work/scratch');back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512)
capacity=dict(MemAvailable_bytes=mem,minimum_memory_bytes=19<<30,HOST_available_bytes=h.f_bavail*h.f_frsize,scratch_available_bytes=s.f_bavail*s.f_frsize,HOST_floor=16<<30,scratch_floor=12<<30,full_sparse_gap_bytes=gap,HOST_output_reserve=64<<20)
assert mem>=19<<30 and capacity['HOST_available_bytes']>=(16<<30)+gap+(64<<20) and capacity['scratch_available_bytes']>=12<<30
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());capacity['included_usage_percent_observed']=state['last_rate_limits']['primary']['usedPercent'];assert capacity['included_usage_percent_observed']<100
write(P/'ACTUAL-CAPACITY.json',capacity)
os.chdir(O);os.sched_setaffinity(0,{0});os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
limits();profile=dict(scope=__doc__,authority='Root exact CPU0 ordinary leaf grant for this recipe; no production profile grant implied',recipe=pin(F),**recipe['profile']);write(P/'ACTUAL-LEAF-PROFILE.json',profile)
begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,126);records=[]
def run(command):
 cap=CAP/command['name'];cap.mkdir(mode=0o700);cmd=dict(scope=recipe['scope'],purpose=__doc__,argv=command['argv'],cwd=str(O),profile=pin(P/'ACTUAL-LEAF-PROFILE.json'));write(cap/'command.json',cmd)
 j=owned_capture(cmd,cap,max(.1,120-(time.monotonic()-begin)),limits);write(cap/'whole-join.json',j);records.append(dict(name=command['name'],join=j,command=pin(cap/'command.json')))
 assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
 if command['name']=='00-actual-Rust':write(P/'DURABLE-RUST-OBJECT.json',dict(scope=recipe['scope'],status='COMPILED_ONCE_OBJECT_RETAINED_BEFORE_OBSERVERS',object=pin(O/'actual.o'),command=pin(cap/'command.json'),join=pin(cap/'whole-join.json')))
 return (cap/'stdout').read_text()
try:
 outputs={}
 for cmd in recipe['commands']:outputs[cmd['name']]=run(cmd)
 assert 'PASS pairs=32000 flags=256 real_descriptor_layout_words=6' in outputs['04-functional-diagnostic-equivalence']
 def kinds(text,name):return [x.split()[-2] for x in text.splitlines() if x.split()[-1:]==[name]]
 nm=outputs['actual-nm'];pub=outputs['public-nm'];fallback=outputs['fallback-nm'];selected=outputs['selected-nm']
 assert kinds(nm,'process_sched_migrate_log_bridge')==['T'] and kinds(nm,'process_sched_migrate_debug')==['U'] and kinds(nm,'kprintf')==['U']
 assert kinds(pub,'process_sched_migrate_debug')==['D'] and not kinds(pub,'process_sched_migrate_log_bridge')
 assert kinds(fallback,'process_sched_migrate_log_bridge')==['t'] and not kinds(fallback,'process_sched_migrate_debug')
 assert kinds(selected,'process_sched_migrate_log_bridge')==['T'] and kinds(selected,'process_sched_migrate_debug')==['D'] and kinds(selected,'kprintf')==['U']
 for name in ['public','fallback','selected']:assert '__verbose' in outputs[name+'-readelf']
 assert all(pin(Path(row['path']))==row for row in [*recipe['source_files'].values(),*recipe['actual_header_config_closure'].values()]) and cpu_used()<=60
 result=dict(scope=recipe['scope'],status='PASS_FOCUSED_REAL_HEADER_ORIGINAL_C_ACTUAL_RUST_DYNAMIC_DIAGNOSTIC_ONLY',recipe=pin(F),profile=pin(P/'ACTUAL-LEAF-PROFILE.json'),capacity=pin(P/'ACTUAL-CAPACITY.json'),compiler_object=pin(P/'DURABLE-RUST-OBJECT.json'),pairs=32000,flag_states=256,layout_words=6,actual_original_macro_and_existing_Rust_descriptor_control=True,existing_C_selector_identity_preserved=True,selected_fragment_partial_link=True,records=records,failures=0,corrections=0,total_CPU_seconds=cpu_used(),seconds=time.monotonic()-begin,CPU0_released=True,canonical_inputs_unchanged=all(pin(Path(x['before']['path']))==x['before'] for x in bindings['changes'].values()),whole_C_TU_default_link_native='OPEN',qualification='Hosted variadic sink and exact originalmacro/actualRust diagnostic only. Declarative Cdescriptor remains; no fullprocessTU/defaultkernel/defaultlink/native proof.')
 write(P/'ACTUAL-LEAF-RECEIPT.json',result);print(json.dumps(dict(status=result['status'],seconds=result['seconds'],receipt=pin(P/'ACTUAL-LEAF-RECEIPT.json'),CPU0_released=True)))
except BaseException as exc:
 write(P/'FAILURE-1.json',dict(scope=recipe['scope'],status='FAIL_PRESERVED_NO_AUTOMATIC_REPLAY',error=type(exc).__name__+': '+str(exc),records=records,CPU0_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
