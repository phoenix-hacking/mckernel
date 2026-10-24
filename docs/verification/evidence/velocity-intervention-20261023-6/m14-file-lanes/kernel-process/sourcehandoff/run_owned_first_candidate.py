"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted exclusive CPU6 exact20 dump body/ABI/default-fallback job once.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,stat,subprocess,time,sys
B=Path(__file__).resolve().parents[1];H=B/'sourcehandoff';RF=H/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json';READY=H/'EXECUTABLE-READY.json'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
started=False;records=[];durable={}
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,value):
 with p.open('x') as stream:json.dump(value,stream,sort_keys=True);stream.write('\n')
def rows(text):return [line.split() for line in text.splitlines() if line.split()]
def unique(symbols,name,kinds):
 found=[row for row in symbols if row[-1]==name];assert len(found)==1 and found[0][-2] in kinds,(name,kinds,found);return found[0]
try:
 assert pin(READY)['sha256']=='36aafee2021d12f1d8b13bc790703382f3debf3b14f3c55ad5046303f53e8f4d'
 assert pin(RF)['sha256']=='7b6a421e98e319a9dacbbcb15901215514ee1f12df9e8d190539e1ccfd86577d'
 r=json.loads(RF.read_text());assert len(r['commands'])==20
 for row in [*r['input_bindings'].values(),*r['tools'].values(),*r['actual_header_closure'].values(),*r['current_canonical_header_preimages'].values(),r['accepted_real_C_profile'],r['accepted_prior_production']]:assert pin(Path(row['path']))==row,row['path']
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:2]==(3,9)
 competitors=[];races=[]
 for entry in Path('/proc').iterdir():
  if not entry.name.isdigit() or int(entry.name)==os.getpid():continue
  try:
   if entry.stat().st_uid==1000 and os.sched_getaffinity(int(entry.name))=={6}:
    competitors.append(dict(pid=int(entry.name),cmdline=(entry/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')))
  except (FileNotFoundError,ProcessLookupError):races.append(int(entry.name))
 write(H/'CPU6-ADMISSION-NO-EXCLUSIVE-COMPETITOR.json',dict(scope=SCOPE,authority='Root exactexclusiveCPU6 grant; bounded local UID1000 exactCPU6 affinity census before job. Broad-affinity system tasks are not claimed retired.',competitors=competitors,transient_procfs_races=races,no_exclusive_competing_job=not competitors));assert not competitors,competitors
 helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert pin(helper)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 def globals_used(code):
  used={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for value in code.co_consts:
   if isinstance(value,type(code)):used.update(globals_used(value))
  return used
 deps=set()
 for name in functions:deps.update(globals_used(ns[name].__code__))
 assert not deps-set(ns)-set(vars(builtins))
 write(H/'HELPER-GLOBAL-DEPENDENCY-CHECK.json',dict(scope=SCOPE,helper=pin(helper),missing=[],dependencies=sorted(deps),dict_API=True,Python_executable=sys.executable,before_any_child=True))
 mem=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,aggregate_job_cap=7,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(H/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O=B/'output-first-candidate-1';O.mkdir(mode=0o700);CAP=H/'actual-first-candidate-capture-1';CAP.mkdir(mode=0o700);os.chdir(O);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=SCOPE,authority='Root one exclusiveCPU6 frozen36aaf/7b6a exact20 ordinary job; no automatic correction',CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152,recipe=pin(RF),ready=pin(READY),driver=pin(Path(__file__)),cwd=str(O))
 write(H/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 entry='vm_range_insert_dump_bridge';gate='process_dump_tree_enabled';actual_comparisons=0
 for cmdrow in r['commands']:
  remaining=90-(time.monotonic()-begin);assert remaining>0
  name=cmdrow['name'];cap=CAP/name;cap.mkdir(mode=0o700);cmd=dict(scope=SCOPE,purpose=cmdrow['purpose'],argv=cmdrow['argv'],cwd=str(O),profile=pin(H/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(name=name,command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  text=(cap/'stdout').read_text()
  if name=='00-actual-Rust-fixture-body-object':durable['Rust_fixture']=ns['hashed'](O/'actual_provider.o',32<<20)
  elif name=='01-actual-Rust-production-leaf':durable['Rust_leaf']=ns['hashed'](O/'actual_production_leaf.o',32<<20)
  elif name=='040-actual-parity-execute-gate-0':assert 'tree_dump_debug=0 actual_original_C_Rust_comparisons=217' in text;actual_comparisons+=217
  elif name=='041-actual-parity-execute-gate-1':assert 'tree_dump_debug=1 actual_original_C_Rust_comparisons=216' in text;actual_comparisons+=216
  elif name.startswith('actual-default-C-consumer-gate-') and name.endswith('-symbols'):
   symbols=rows(text);unique(symbols,entry,{'U'});data=unique(symbols,gate,{'R'});assert int(data[-3],16)==4
   assert not [row for row in symbols if row[-1] in {'dtree','dump_tree'}]
  elif name.startswith('actual-fallback-C-consumer-gate-') and name.endswith('-symbols'):
   symbols=rows(text);unique(symbols,entry,{'t'});assert not [row for row in symbols if row[-1]==gate]
   unique(symbols,'dump_tree',{'t'})
   if '-gate-1-' in name:unique(symbols,'dtree',{'t'})
  elif name=='production-Rust-leaf-symbols':
   symbols=rows(text);unique(symbols,entry,{'T'});unique(symbols,gate,{'U'});unique(symbols,'kprintf',{'U'})
  elif name=='actual-selected-default-partial-link':durable['partial']=ns['hashed'](O/'actual_selected_partial.o',32<<20)
  elif name=='actual-selected-default-partial-symbols':
   symbols=rows(text);unique(symbols,entry,{'T'});unique(symbols,gate,{'R'});assert {row[-1] for row in symbols if row[-2]=='U'}=={'kprintf'}
 assert actual_comparisons==433
 for row in durable.values():
  st=Path(row['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(row['device'],row['inode'],row['size'],row['mtime_ns'],row['ctime_ns'])
 assert ns['cpu_used']()<=60
 result=dict(scope=SCOPE,status='PASS_F02_ACTUAL_DUMP_BODY_C_RUST_ABI_DEBUG_GATES_DEFAULT_FALLBACK_SELECTED_LEAF',recipe=pin(RF),ready=pin(READY),records=records,objects=durable,actual_commands=20,actual_original_C_Rust_comparisons=433,disabled_comparisons=217,enabled_comparisons=216,independent_tree_order_format_width_UL_ABI_oracles=True,root_after_header_parent_fields_after_left_and_right_after_logger=True,disabled_NULL_noop=True,selected_C_compute_helpers_excluded=True,selected_C_readonly_gate_only=True,exact_C_fallback=True,Rust_entry_unique_in_partial=True,only_unresolved_provider='existing Rust kprintf',seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU6_released=True,canonical_mutations=0,full_current78=False,complete_selected_C_TU=False,default_image_native=False,file_retired=False)
 write(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as error:
 write(H/'FIRST-CANDIDATE-FAILURE-1.json',dict(scope=SCOPE,status='STOP_FIRST_UNEXPECTED_RESULT_NO_RETRY',error=type(error).__name__+': '+str(error),records=records,durable_objects=durable,CPU6_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
