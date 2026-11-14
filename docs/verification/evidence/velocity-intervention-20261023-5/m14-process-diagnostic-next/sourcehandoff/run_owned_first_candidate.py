"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-granted frozen13 functional log-body fixture/selected-leaf job on CPU7.
No root/Docker/kernel/IRQ/guest/native or canonical/frozen-image effects.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,re,resource,signal,stat,subprocess,time,sys
B=Path(__file__).resolve().parents[1];H=B/'sourcehandoff'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
READY=H/'EXECUTABLE-READY.json';RECIPE=H/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json'
started=False;records=[];durable={}
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,value):
 with p.open('x') as stream:json.dump(value,stream,sort_keys=True);stream.write('\n')
def rows(text):return [l.split() for l in text.splitlines() if l.split()]
def unique(symbols,name,kinds):
 found=[r for r in symbols if r[-1]==name];assert len(found)==1 and found[0][-2] in kinds,(name,kinds,found);return found[0]
try:
 assert pin(READY)['sha256']=='b4f6502f72d1698822232681a67b38bddaa7406a8beddb0784dd8076c70f2485'
 assert pin(RECIPE)['sha256']=='8acf6aee00975f4d64a6c9fce4d065651bc13678d2e8a40d7f45fe333d8dc2fc'
 recipe=json.loads(RECIPE.read_text());assert len(recipe['commands'])==13 and recipe['expected_functional_comparisons']==1101
 for row in [*recipe['input_bindings'].values(),*recipe['tools'].values(),*recipe['actual_real_header_closure'].values(),*recipe['current_canonical_header_preimages'].values(),recipe['accepted_C_profile_and_current78_provider'],recipe['accepted_kprintf_symbol_capture']]:assert pin(Path(row['path']))==row,row['path']
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:2]==(3,9)
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
 write(H/'HELPER-GLOBAL-DEPENDENCY-CHECK.json',dict(scope=SCOPE,helper=pin(helper),dependencies=sorted(deps),missing=[],dict_API=True,Python_executable=sys.executable,before_any_child=True))
 assert '#undef memset' in (B/'fixture/actual_parity.c').read_text()
 write(H/'HOSTED-MEMSET-SOURCE-PREFLIGHT.json',dict(scope=SCOPE,status='PASS_REUSED_KNOWN_LIBC_MEMSET_BOUNDARY_AFTER_REAL_HEADERS',source=pin(B/'fixture/actual_parity.c'),compiler_not_started=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,aggregate_job_cap=7,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(H/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O=B/'output-first-candidate-1';O.mkdir(mode=0o700);CAP=H/'actual-first-candidate-capture-1';CAP.mkdir(mode=0o700);os.chdir(O);os.sched_setaffinity(0,{7});os.environ['RUST_MIN_STACK']='2097152'
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=SCOPE,authority='Root explicit sole frozen13 ordinary CPU7 functional log body/consumer job, CPU6 excluded, no automatic retry',CPU=7,excluded_CPU=[1,6],jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152,recipe=pin(RECIPE),ready=pin(READY),driver=pin(Path(__file__)),cwd=str(O))
 write(H/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 observations={};entry='vm_range_insert_log_bridge';selector='process_vm_range_insert_debug'
 for command in recipe['commands']:
  remaining=90-(time.monotonic()-begin);assert remaining>0
  name=command['name'];cap=CAP/name;cap.mkdir(mode=0o700);cmd=dict(scope=SCOPE,purpose=command['purpose'],argv=command['argv'],cwd=str(O),profile=pin(H/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(name=name,command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  text=(cap/'stdout').read_text();observations[name]=dict(stdout=j['captures']['stdout'])
  for key,filename,trigger in [('Rust_fixture','actual_provider.o','01-actual-Rust-body-object'),('C_default','actual_default_consumer.o','04-actual-default-C-consumer'),('C_fallback','actual_fallback_consumer.o','05-actual-fallback-C-consumer'),('Rust_leaf','actual_production_leaf.o','06-actual-production-Rust-leaf'),('partial','actual_selected_partial.o','10-actual-selected-leaf-partial-link')]:
   if name==trigger:
    durable[key]=ns['hashed'](O/filename,32<<20);write(H/('DURABLE-'+key+'-OBJECT.json'),dict(scope=SCOPE,object=durable[key],join=records[-1]))
  if name=='03-actual-parity-execute':assert 'PASS 1101 actual-original-C/Rust process log comparisons' in text
  elif name=='07-default-C-symbols':
   symbols=rows(text);unique(symbols,entry,{'U'});d=unique(symbols,selector,{'D'});assert int(d[-3],16)==32
  elif name=='08-fallback-C-symbols':
   symbols=rows(text);unique(symbols,entry,{'t'});assert not [r for r in symbols if r[-1]==selector]
  elif name=='09-production-Rust-symbols':
   symbols=rows(text);unique(symbols,entry,{'T'});unique(symbols,selector,{'U'});unique(symbols,'kprintf',{'U'})
  elif name=='11-actual-selected-leaf-symbols':
   symbols=rows(text);unique(symbols,entry,{'T'});unique(symbols,selector,{'D'});unique(symbols,'kprintf',{'U'});assert {r[-1] for r in symbols if r[-2]=='U'}=={'kprintf'}
  elif name=='12-actual-selected-leaf-ELF-relocations':assert '__verbose' in text and 'kprintf' in text and selector in text
 for row in durable.values():
  st=Path(row['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(row['device'],row['inode'],row['size'],row['mtime_ns'],row['ctime_ns'])
 for row in recipe['input_bindings'].values():assert pin(Path(row['path']))==row
 assert ns['cpu_used']()<=60
 result=dict(scope=SCOPE,status='PASS_ACTUAL_C_RUST_LOG_BODY_VARIADIC_DEBUG_ABI_AND_DEFAULT_FALLBACK_SELECTED_LEAF',recipe=pin(RECIPE),ready=pin(READY),records=records,objects=durable,actual_comparisons=1101,exact_format_and_CULong_arguments=True,dynamic_flag_and_unknown_event_gates=True,ignored_logger_return_cases=True,real_header_and_actual_Rust_layout=True,debug_metadata_and_bitfield_packing=True,selected_C_descriptor_only=True,original_C_fallback=True,unique_Rust_log_callback_partial=True,existing_kprintf_provider_remains=True,C_compute_callback_retired_in_private_leaf=True,remaining_C_debt=['Declarative process_vm_range_insert_debug data','vm_range_insert_dump_bridge plus dump_tree/optional dtree','Other process.c compute bodies'],first_candidate_failures=0,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU7_released=True,canonical_mutations=0,complete_selected_C_TU=False,full_production_Rust_crate=False,default_image_link=False,native=False,file_retired=False)
 write(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),seconds=result['seconds'],CPU7_released=True)))
except BaseException as error:
 write(H/'FIRST-CANDIDATE-FAILURE-1.json',dict(scope=SCOPE,status='STOP_FIRST_UNEXPECTED_FAILURE_NO_RETRY',error=type(error).__name__+': '+str(error),records=records,durable_objects=durable,CPU7_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
