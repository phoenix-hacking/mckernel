"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One frozen sync callback16-command ordinary CPU6 job; explicit new root grant required.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,stat,subprocess,time,sys
B=Path(__file__).resolve().parents[1];H=B/'sourcehandoff';RF=H/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json';READY=H/'EXECUTABLE-READY.NOT-GRANTED.json'
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
 grant=json.loads((H/'ROOT-GRANT.json').read_text());assert grant['scope']==SCOPE and grant['CPU']==6 and grant['ordinary_jobs']==1 and grant['ready_sha256']==pin(READY)['sha256']
 ready=json.loads(READY.read_text());assert pin(RF)==ready['recipe'] and pin(Path(__file__))==ready['driver']
 r=json.loads(RF.read_text());assert len(r['commands'])==16
 for row in [*r['input_bindings'].values(),*r['tools'].values(),*r['actual_header_closure'].values(),*r['current_canonical_header_preimages'].values(),*r['current_provider_pins'].values(),r['accepted_real_C_profile'],r['accepted_prior_production']]:assert pin(Path(row['path']))==row,row['path']
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
 # Same accepted ELF source; named-target counts preserve complete relocation lists.
 elfsrc=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-process-next/bounded-observer-correction-1/observe_retained_elf.py');assert pin(elfsrc)['sha256']=='d391d3d450282536049848e619925b2f1d92cb28b30032ad1e1b42204997cf15'
 nodes=[n for n in ast.parse(elfsrc.read_bytes()).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in {'need','textz'} or isinstance(n,ast.ClassDef) and n.name=='Elf'];ens={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(elfsrc),'exec'),ens);Elf=ens['Elf']
 mem=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,aggregate_job_cap=7,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(H/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O=B/'output-first-candidate-1';O.mkdir(mode=0o700);CAP=H/'actual-first-candidate-capture-1';CAP.mkdir(mode=0o700);os.chdir(O);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=SCOPE,authority='Root one exclusiveCPU6 exact frozen sync16 ordinary job from ROOT-GRANT.json; first unexpected STOP, no automatic correction',CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152,recipe=pin(RF),ready=pin(READY),driver=pin(Path(__file__)),cwd=str(O))
 write(H/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 entry='sync_one_page';selectors=['process_sync_one_page_entry_debug','process_sync_one_page_exit_debug'];actual_comparisons=0;caller_witnesses=[];selector_evidence=[];unresolved=[]
 for cmdrow in r['commands']:
  remaining=90-(time.monotonic()-begin);assert remaining>0
  name=cmdrow['name'];cap=CAP/name;cap.mkdir(mode=0o700);cmd=dict(scope=SCOPE,purpose=cmdrow['purpose'],argv=cmdrow['argv'],cwd=str(O),profile=pin(H/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(name=name,command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  text=(cap/'stdout').read_text()
  for label,filename,trigger in [('Rust_fixture','actual_provider.o','00-actual-Rust-fixture-body'),('Rust_leaf','actual_leaf.o','01-hosted-Rust-actual-leaf'),('Rust_caller','actual_caller.o','02-actual-existing-Rust-caller'),('partial','actual_selected_partial.o','13-actual-selected-consumer-partial-link')]:
   if name==trigger:durable[label]=ns['hashed'](O/filename,32<<20)
  if name=='05-actual-795-parity-execute':
   assert 'sync_one_page actual_original_C_Rust_comparisons=795 real_PTE_memobj_dispatch=1 controlled_TLB=1' in text;actual_comparisons=795
  elif name=='08-actual-C-selected-symbols':
   symbols=rows(text);assert not [row for row in symbols if row[-1]==entry]
   for selector in selectors:assert int(unique(symbols,selector,{'D'})[-3],16)==32
  elif name=='10-actual-C-fallback-symbols':
   symbols=rows(text);unique(symbols,entry,{'T'});assert not [row for row in symbols if row[-1] in selectors]
  elif name=='11-hosted-actual-Rust-leaf-symbols':
   symbols=rows(text);unique(symbols,entry,{'T'});unique(symbols,'kprintf',{'U'});unique(symbols,'fixture_tlb_effect',{'U'})
   for selector in selectors:unique(symbols,selector,{'U'})
   for name0 in ('pte_is_null','pte_is_fileoff','pte_is_dirty','pte_clear_dirty','pte_set_dirty','pte_get_phys','memobj_flush_page'):unique(symbols,name0,{'T'})
  elif name=='12-actual-existing-caller-relocations':
   caller=Elf(O/'actual_caller.o');_,refs=caller.function_bytes_and_relocations('sync_process_memory_range')
   target_refs=[ref for ref in refs if ref['symbol']==entry];assert len(target_refs)==1,(refs,target_refs)
  elif name=='14-actual-selected-consumer-partial-symbols':
   symbols=rows(text);unique(symbols,entry,{'T'});unique(symbols,'sync_process_memory_range',{'T'})
   for selector in selectors:assert int(unique(symbols,selector,{'D'})[-3],16)==32
   unresolved=sorted({row[-1] for row in symbols if row[-2]=='U'})
   for required in ('kprintf','fixture_tlb_effect','process_sync_memory_range_body_result','process_free_range_noirq_lock_bridge','process_free_range_noirq_unlock_bridge','process_visit_pte_range_bridge','process_sync_range_log_bridge'):unique(symbols,required,{'U'})
   assert not [row for row in symbols if row[-1]==entry and row[-2]=='U']
  elif name=='15-actual-selected-consumer-partial-ELF':
   partial=Elf(O/'actual_selected_partial.o');caller=Elf(O/'actual_caller.o');partial.defined_function(entry)
   before,brefs=caller.function_bytes_and_relocations('sync_process_memory_range');after,arefs=partial.function_bytes_and_relocations('sync_process_memory_range')
   assert before==after and brefs==arefs,(brefs,arefs)
   target_refs=[ref for ref in arefs if ref['symbol']==entry];assert len(target_refs)==1
   caller_witnesses.append(dict(name='sync_process_memory_range',bytes=len(after),sha256=hashlib.sha256(after).hexdigest(),actual_relocations=arefs,named_sync_target_refs=target_refs))
   assert len([ref for ref in partial.relocations if ref['symbol']==entry])==1
   for selector,line in zip(selectors,[2546,2574]):
    found=[row for row in partial.symbols if row['name']==selector];assert len(found)==1;row=found[0];assert row['bind']==1 and row['type']==1 and row['size']==32 and 0<row['section']<len(partial.sections)
    section=partial.sections[row['section']];assert section['name']=='__verbose';raw=partial.data(section)[row['value']:row['value']+32]
    assert len(raw)==32 and int.from_bytes(raw[24:28],'little')==line and raw[16:24]==b'\0'*8
    refs=[ref for ref in partial.relocations if ref['section']==section['name'] and row['value']<=ref['offset']<row['value']+32];assert {ref['offset']-row['value'] for ref in refs}=={0,8}
    selector_evidence.append(dict(symbol=row,section=section['name'],line=line,flags=0,raw=raw.hex(),pointer_relocations=refs))
 assert actual_comparisons==795
 for row in durable.values():
  st=Path(row['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(row['device'],row['inode'],row['size'],row['mtime_ns'],row['ctime_ns'])
 assert ns['cpu_used']()<=60
 result=dict(scope=SCOPE,status='PASS_F02_ACTUAL_SYNC_ONE_PAGE_C_RUST_795_REAL_ABI_ACTUAL_RUST_CALLER_SELECTED_FALLBACK',recipe=pin(RF),ready=pin(READY),grant=pin(H/'ROOT-GRANT.json'),records=records,objects=durable,actual_commands=16,actual_original_C_Rust_comparisons=795,real_Rust_PTE_atomics_and_memobj_dispatch=True,controlled_host_TLB_effect_only=True,native_asm_executed=False,exact_final_state_event_vararg_oracles=True,error_log_before_redirty=True,entry_TLB_flush_error_exit_mutation_cases=True,shortcircuit_NULL_args=True,actual_existing_Rust_caller=caller_witnesses,actual_debug_selector_metadata=selector_evidence,selected_C_callback_compute_excluded=True,exact_original_C_fallback=True,actual_partial_U_names=unresolved,remaining_provider_debt=r['remaining_provider_debt'],seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU6_released=True,canonical_mutations=0,full_current78=False,complete_selected_C_TU=False,default_image_native=False,file_retired=False,failure_history=r['failure_history'])
 write(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as error:
 write(H/'FIRST-CANDIDATE-FAILURE-1.json',dict(scope=SCOPE,status='STOP_FIRST_UNEXPECTED_RESULT_NO_RETRY',error=type(error).__name__+': '+str(error),records=records,durable_objects=durable,CPU6_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
