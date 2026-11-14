"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused real-header C/Rust entry ABI fixture; target TLB/IRQ callbacks compile
only and are never executed. No wholeTU/fullcrate/kernel/native claim.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,time,subprocess,stat,dis,builtins,sys
P=Path(__file__).resolve().parent;F=P/'EXACT-FIXTURE-REPRODUCER.NOT-GRANTED.json'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def initial_write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True);f.write('\n')
records=[];started=False
try:
 assert pin(F)['sha256']=='c2009d7aba5dca1047454f86142d15f4f40103eed139c237a91e3e9f69554aa6';recipe=json.loads(F.read_text());assert pin(Path(recipe['prior_recipe']['path']))==recipe['prior_recipe'];base_recipe=json.loads(Path(recipe['prior_recipe']['path']).read_text());bindings=json.loads(Path(base_recipe['source_binding']['path']).read_text())
 for row in [base_recipe['source_binding'],*recipe['source_files'].values(),*recipe['unchanged_inputs'].values(),*recipe['tools'].values(),*recipe['header_closure'].values()]:assert pin(Path(row['path']))==row,row['path']
 for row in bindings['preimages'].values():assert pin(Path(row['path']))==row
 retained_before={}
 for row in recipe['reuse_retained_objects']:
  q=Path(row['path']);assert pin(q)==row
  st=q.stat();retained_before[str(q)]=[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns]
 assert os.getuid()==os.geteuid()==1000
 assert sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:2]==(3,9)

 H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert pin(H)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
 # Validate every extracted helper LOAD_GLOBAL (including nested code) before
 # any child launch; attribute names are not mistaken for globals.
 def global_dependencies(code):
  found={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for value in code.co_consts:
   if isinstance(value,type(code)):found.update(global_dependencies(value))
  return found
 dependencies=set()
 for name in names:dependencies.update(global_dependencies(globals()[name].__code__))
 missing=dependencies-set(globals())-set(vars(builtins));assert not missing,missing
 initial_write(P/'HELPER-GLOBAL-DEPENDENCY-CHECK.json',dict(scope=__doc__,helper=pin(H),dependencies=sorted(dependencies),missing=[],before_any_child=True))
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;h=os.statvfs('/home/holden');s=os.statvfs('/home/holden/mckernel-work/scratch');back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512)
 capacity=dict(MemAvailable_bytes=mem,minimum_memory_bytes=19<<30,HOST_available_bytes=h.f_bavail*h.f_frsize,scratch_available_bytes=s.f_bavail*s.f_frsize,HOST_floor=16<<30,scratch_floor=12<<30,full_sparse_gap_bytes=gap,HOST_output_reserve=64<<20)
 assert mem>=19<<30 and capacity['HOST_available_bytes']>=(16<<30)+gap+(64<<20) and capacity['scratch_available_bytes']>=(12<<30)+(64<<20)
 state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());capacity['included_usage_percent_observed']=state['last_rate_limits']['primary']['usedPercent'];assert capacity['included_usage_percent_observed']<100
 initial_write(P/'ACTUAL-CAPACITY.json',capacity);O=P/'output-1';O.mkdir(mode=0o700);C=P/'actual-owned-capture-1';C.mkdir(mode=0o700)
 os.chdir(O);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
 for sig in STOP_SIGNALS:signal.signal(sig,stop)
 def limits():
  for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 limits();profile=dict(scope=__doc__,authority='RootexplicitCPU6ONEjob exactrecipe c2009d7a/proposal b5a61001; compile host adapter/reuse retained Rust40a90553+C019db85e; 2GiBAS60CPU90wall+6 FSIZE32MFD256core0/GCC9/CGU1/2MiBstack/h990; stop first unexpected failure/no retry',CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,RUST_MIN_STACK=2097152,recipe=pin(F),driver=pin(Path(__file__)));initial_write(P/'ACTUAL-PROFILE.json',profile)
 initial_write(P/'REUSED-OBJECT-IDENTITIES.json',dict(scope=__doc__,expected_objects=recipe['reuse_retained_objects'],stat_before=retained_before,Rust_compiler_invocations=0,C_recorder_recompiles=0))
 begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 for command in recipe['commands']:
  cap=C/command['name'];cap.mkdir(mode=0o700);cmd=dict(scope=recipe['scope'],purpose=command['purpose'],argv=command['argv'],cwd=str(O),profile=pin(P/'ACTUAL-PROFILE.json'));initial_write(cap/'command.json',cmd)
  j=owned_capture(cmd,cap,max(.1,90-(time.monotonic()-begin)),limits);initial_write(cap/'whole-join.json',j);records.append(dict(name=command['name'],command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  if command['name']=='00-Rust-actual-export-compile':initial_write(P/'DURABLE-RUST-OBJECT.json',dict(scope=recipe['scope'],status='COMPILED_ONCE_OBJECT_HASHED_ONCE_BEFORE_POSTPROCESSORS',object=pin(O/'rust-entry.o'),command=pin(cap/'command.json'),whole_join=pin(cap/'whole-join.json')))
  if command['name']=='02-focused-C-Rust-recorder-link':initial_write(P/'DURABLE-FIXTURE-BINARY.json',dict(scope=recipe['scope'],binary=pin(O/'fixture'),command=pin(cap/'command.json'),whole_join=pin(cap/'whole-join.json')))
 output=(C/'03-functional-original-C-Rust-entry-pairs/stdout').read_text();assert 'PASS actual_original_C_Rust_entry_pairs=1792 full_signature_arguments=20 callback_identities=12 ignored_returns=8' in output
 observation=json.loads((P/'ACTUAL-ABI-SELECTION-OBSERVATION.json').read_text());assert observation['status']=='PASS_FOCUSED_ENTRY_ABI_HEADER_SELECTION_AND_PARTIAL_LINK_ONLY'
 assert all(pin(Path(row['path']))==row for row in [*recipe['source_files'].values(),*recipe['unchanged_inputs'].values()]) and cpu_used()<=60
 retained_after={str(q):[q.stat().st_dev,q.stat().st_ino,q.stat().st_size,q.stat().st_mtime_ns,q.stat().st_ctime_ns] for q in map(Path,retained_before)};assert retained_after==retained_before
 initial_write(P/'REUSED-OBJECT-POST-IDENTITIES.json',dict(scope=__doc__,stat_after=retained_after,unchanged=True))
 result=dict(scope=recipe['scope'],status='PASS_ACTUAL_LEAF_ENTRY_ABI_CALLBACK_BINDING_HEADER_SELECTION_PARTIAL_LINK_ONLY',recipe=pin(F),profile=pin(P/'ACTUAL-PROFILE.json'),source_bindings=base_recipe['source_binding'],Rust_object_receipt=pin(P/'REUSED-OBJECT-IDENTITIES.json'),fixture_binary_receipt=pin(P/'DURABLE-FIXTURE-BINARY.json'),actual_observation=pin(P/'ACTUAL-ABI-SELECTION-OBSERVATION.json'),records=records,actual_original_C_Rust_pairs=1792,full_signature_arguments=20,callback_identities=12,ignored_return_cases=8,actual_header_layout_words=15,actual_geometry=observation['actual_header_geometry'],compiler_Rust_invocations=0,C_compiler_invocations=4,seconds=time.monotonic()-begin,total_CPU_seconds=cpu_used(),product_failures=0,observer_failures=2,observer_corrections=1,expert_fixture_repairs=1,preserved_original_failure=pin(P.parent/'FAILURE-1.json'),helper_global_dependency_check=pin(P/'HELPER-GLOBAL-DEPENDENCY-CHECK.json'),CPU6_released=True,canonical_preimages_unchanged=all(pin(Path(row['path']))==row for row in bindings['preimages'].values()),underlying_Rust_body_algorithm_executed=False,callbacks_remaining_C_debt=13,whole_C_TU=False,production_Rust_fullcrate=False,default_kernel_link=False,native=False)
 initial_write(P/'ACTUAL-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(P/'ACTUAL-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 initial_write(P/'FAILURE-EXPERT-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_FAILURE_PRESERVED_NO_AUTOMATIC_RETRY',error=type(exc).__name__+': '+str(exc),records=records,CPU6_released=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
