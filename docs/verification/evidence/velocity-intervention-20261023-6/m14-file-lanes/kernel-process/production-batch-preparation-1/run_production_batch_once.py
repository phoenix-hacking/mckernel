"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One coherent process batch current78/wholeGCC9 consumer14 job; new root grant required.
Exact accepted productionnightly70eb, no compiler substitution/root/guest effects.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,re,resource,signal,stat,struct,subprocess,time,sys
P=Path(__file__).resolve().parent;B=P.parent;SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
RF=P/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json';CF=P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json';READY=P/'EXECUTABLE-READY.NOT-GRANTED.json'
started=False;records=[];durable={};metadata={}
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,value):
 with p.open('x') as stream:json.dump(value,stream,sort_keys=True);stream.write('\n')
def nmrows(text):return [line.split() for line in text.splitlines() if line.split()]
def unique(rows,name,kinds):
 found=[row for row in rows if row[-1]==name];assert len(found)==1 and found[0][-2] in kinds,(name,kinds,found);return found[0]
try:
 for path in (P/'output-1',P/'actual-production-capture-1',P/'PRODUCTION-FIRST-FAILURE-1.json',P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'):
  assert not path.exists(),('existing_output_or_failure',str(path))
 grant=json.loads((P/'ROOT-GRANT.json').read_text());assert grant['scope']==SCOPE and grant['CPU']==6 and grant['ready_sha256']==pin(READY)['sha256'] and grant['ordinary_jobs']==1
 ready=json.loads(READY.read_text());assert pin(RF)==ready['Rust_recipe'] and pin(CF)==ready['C_recipe'] and pin(Path(__file__))==ready['driver']
 r=json.loads(RF.read_text());c=json.loads(CF.read_text());assert len(r['source_inputs'])==78 and len(c['commands'])==14
 assert r['source_identity']=='e61b3f0a63a879f9013ccb51c933945cf650a3e8631043b398ee0c319ce6a279'
 for row in ready['evidence_bindings']:assert pin(Path(row['path']))==row,row['path']
 for row in r['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private'] and pin(Path(row['canonical_before']['path']))==row['canonical_before']
 for row in [*r['accepted_union_refs'],r['accepted_prior_whole_join'],r['accepted_prior_Rust_recipe'],r['accepted_prior_Rust_symbols'],c['accepted_prior_complete_C_profile'],c['accepted_prior_whole_join'],c['private_source'],c['canonical_preimage'],c['ABI_witness'],*c['headers'].values(),*c['canonical_headers'].values(),*c['tools'].values()]:assert pin(Path(row['path']))==row,row['path']
 argv=r['argv'];assert len(argv)==48 and argv==c['commands'][0]['argv']
 assert argv[-12:-4]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage'] and argv[-4:-2]==['-C','codegen-units=1']
 assert pin(Path(argv[6]))['sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 write(P/'ROOT-COMPILER-CLARIFICATION.json',dict(scope=SCOPE,authority='Root explicit frozen three-body process batch current78 production grant; pinnednightly1.95-2026-02-18 compiler70eb48argv unchanged; prior corrected E0428 family retained2fb3/e9a/7a, no family reset.',compiler=pin(Path(argv[6])),recipe=pin(RF),before_any_compiler=True))
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:2]==(3,9)
 competitors=[];races=[]
 for process in Path('/proc').iterdir():
  if not process.name.isdigit() or int(process.name)==os.getpid():continue
  try:
   if process.stat().st_uid==1000 and os.sched_getaffinity(int(process.name))=={6}:competitors.append(dict(pid=int(process.name),cmdline=(process/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')))
  except (FileNotFoundError,ProcessLookupError):races.append(int(process.name))
 write(P/'CPU6-ADMISSION-NO-EXCLUSIVE-COMPETITOR.json',dict(scope=SCOPE,competitors=competitors,transient_procfs_races=races,no_exclusive_competing_job=not competitors));assert not competitors,competitors
 helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert pin(helper)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)]
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 def globals_used(code):
  used={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for value in code.co_consts:
   if isinstance(value,type(code)):used.update(globals_used(value))
  return used
 deps=set()
 for name in names:deps.update(globals_used(ns[name].__code__))
 assert not deps-set(ns)-set(vars(builtins))
 write(P/'HELPER-GLOBAL-DEPENDENCY-CHECK.json',dict(scope=SCOPE,helper=pin(helper),dependencies=sorted(deps),missing=[],dict_API=True,Python_executable=sys.executable,before_any_child=True))
 # Reuse the already accepted exact ELF observer class, no new framework.
 elfsrc=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-process-next/bounded-observer-correction-1/observe_retained_elf.py');eraw=elfsrc.read_bytes();assert pin(elfsrc)['sha256']=='d391d3d450282536049848e619925b2f1d92cb28b30032ad1e1b42204997cf15'
 enodes=[n for n in ast.parse(eraw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in {'need','textz'} or isinstance(n,ast.ClassDef) and n.name=='Elf'];ens={};exec(compile(ast.Module(body=enodes,type_ignores=[]),str(elfsrc),'exec'),ens);Elf=ens['Elf']
 write(P/'REUSED-ACCEPTED-ELF-OBSERVER.json',dict(scope=SCOPE,source=pin(elfsrc),authority='accepted retainedELF observer9d58/9d26; class-only reuse for actual descriptor/function relocation checks',before_any_compiler=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,aggregate_job_cap=7,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248,root_heavy_affinity=[2,3,4,5],root_controller_cpu=7,ordinary_cpu=6)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(P/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O=P/'output-1';O.mkdir(mode=0o700);CAP=P/'actual-production-capture-1';CAP.mkdir(mode=0o700);os.chdir(O);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=SCOPE,authority='Root explicit sole process batch CPU6 current78 production grant bound by ROOT-GRANT.json; 70eb48argv; no competing ordinary CPU6 job or automatic retry',CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152,ready=pin(READY),Rust_recipe=pin(RF),C_recipe=pin(CF),driver=pin(Path(__file__)),cwd=str(O))
 write(P/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 targets=['sync_one_page','remap_one_page','process_sync_range_log_bridge'];log='vm_range_insert_log_bridge';dump='vm_range_insert_dump_bridge';gate='process_dump_tree_enabled';selector='process_vm_range_insert_debug'
 oldrows=nmrows(Path(r['accepted_prior_Rust_symbols']['path']).read_text());oldU={x[-1] for x in oldrows if x[-2]=='U'};oldT={x[-1] for x in oldrows if x[-2]=='T'}
 observed_delta={};callback_refs={};callers=[];metadata_objects=[];raw_C_retired_rows=[];partial_U=[]
 def allocated(elf,ref):return any(section['name']==ref['section'] and section['flags']&2 for section in elf.sections)
 def function(elf,name):
  value,section=elf.defined_function(name);assert section['flags']&2 and section['flags']&4
  return elf.function_bytes_and_relocations(name)
 def object_row(elf,name,size):
  found=[row for row in elf.symbols if row['name']==name];assert len(found)==1,(name,found);row=found[0]
  assert row['bind']==1 and row['type']==1 and row['size']==size and 0<row['section']<len(elf.sections)
  section=elf.sections[row['section']];assert section['flags']&2 and not section['flags']&4
  raw=elf.data(section)[row['value']:row['value']+size];assert len(raw)==size
  return row,section,raw
 for command in c['commands']:
  remaining=90-(time.monotonic()-begin);assert remaining>0
  name=command['name'];cap=CAP/name;cap.mkdir(mode=0o700);cmd=dict(scope=SCOPE,purpose=command['purpose'],argv=command['argv'],cwd=str(O),profile=pin(P/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(name=name,command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  text=(cap/'stdout').read_text()
  for key,filename,trigger in [('Rust','mckernel_rust.o','00-current78-production-Rust-compile'),('C','process.c.o','06-selected-complete-process-TU'),('partial','process-rust-partial.o','11-process-fullRust-partial-link')]:
   if name==trigger:
    durable[key]=ns['hashed'](O/filename,32<<20);write(P/('DURABLE-'+key+'-OBJECT.json'),dict(scope=SCOPE,object=durable[key],join=records[-1]))
  if name=='01-current78-Rust-symbols':
   symbols=nmrows(text);newU={row[-1] for row in symbols if row[-2]=='U'};newT={row[-1] for row in symbols if row[-2]=='T'}
   for symbol in [*targets,log,dump,'vm_range_insert','sync_process_memory_range','remap_process_memory_range','kprintf']:unique(symbols,symbol,{'T'})
   for symbol in [*r['expected_U_delta']['added'],'phys_to_page',gate,selector]:unique(symbols,symbol,{'U'})
   for label,before,after in [('U',oldU,newU),('T',oldT,newT)]:
    observed=dict(removed=sorted(before-after),added=sorted(after-before),before=len(before),after=len(after));assert observed==r['expected_'+label+'_delta'],(label,observed,r['expected_'+label+'_delta']);observed_delta[label]=observed
  elif name=='02-current78-Rust-ELF':
   symbols=nmrows(text)
   for symbol in targets:
    found=[row for row in symbols if row[-1]==symbol];assert len(found)==1 and len(found[0])==8 and found[0][3:5]==['FUNC','GLOBAL'] and found[0][6]!='UND' and int(found[0][2])>0,found
  elif name=='03-current78-Rust-relocations':
   rust=Elf(O/'mckernel_rust.o')
   required={'sync_one_page':{'kprintf','process_sync_one_page_entry_debug','process_sync_one_page_exit_debug'},'remap_one_page':{'kprintf','phys_to_page','process_remap_free_file','process_remap_free_line','process_remap_one_page_entry_debug','process_remap_one_page_rss_debug','process_remap_one_page_exit_debug'},'process_sync_range_log_bridge':{'kprintf'}}
   for symbol in targets:
    _,refs=function(rust,symbol);assert required[symbol]<={ref['symbol'] for ref in refs},(symbol,refs);callback_refs[symbol]=refs
   for caller,target in [('sync_process_memory_range','sync_one_page'),('remap_process_memory_range','remap_one_page')]:
    _,refs=function(rust,caller);named=[ref for ref in refs if ref['symbol']==target];assert len(named)==1,(caller,named,refs)
   del rust
  elif name=='05-selected-complete-process-preprocess':
   for symbol in [*targets,dump,'dump_tree','dtree',log]:assert not re.search(r'\b(?:void|int)\s+'+re.escape(symbol)+r'\s*\([^;{}]*\)\s*\{',text),symbol
   assert re.search(r'const\s+int\s+process_dump_tree_enabled\s*=\s*0\s*;',text)
   for symbol,line in c['metadata_lines'].items():
    match=re.search(re.escape(symbol)+r'\s*=\s*\{([^}]+)\}',text,re.S);assert match,symbol;initializer=match.group(1)
    assert int(re.search(r'\.line\s*=\s*(\d+)',initializer).group(1))==line and int(re.search(r'\.flags\s*=\s*(0x[0-9a-fA-F]+|\d+)',initializer).group(1),0)==0
    assert c['private_source']['path'] in initializer
   assert re.search(r'const\s+int\s+process_remap_free_line\s*=\s*2469\s*;',text)
   assert re.search(r'const\s+char\s*\*\s*const\s+process_remap_free_file\s*=\s*"'+re.escape(c['private_source']['path'])+r'"\s*;',text)
  elif name=='07-selected-process-symbols':
   symbols=nmrows(text);raw_C_retired_rows=[row for row in symbols if row[-1] in targets]
   assert not [row for row in raw_C_retired_rows if row[-2] in {'T','t','W','w'}],raw_C_retired_rows
   unique(symbols,'vm_range_insert',{'U'});assert int(unique(symbols,gate,{'R'})[-3],16)==4
   for symbol in c['metadata_lines']:assert int(unique(symbols,symbol,{'D'})[-3],16)==32
  elif name=='08-selected-process-relocations':
   ce=Elf(O/'process.c.o')
   assert not [ref for ref in ce.relocations if ref['symbol'] in targets and allocated(ce,ref)]
   assert len([ref for ref in ce.relocations if ref['symbol']=='vm_range_insert' and allocated(ce,ref)])==2
  elif name=='09-selected-process-ELF':
   ce=Elf(O/'process.c.o')
   row,section,raw=object_row(ce,gate,4);assert not section['flags']&1 and raw==b'\0'*4
   for symbol,line in c['metadata_lines'].items():
    row,section,raw=object_row(ce,symbol,32);assert section['name']=='__verbose' and int.from_bytes(raw[24:28],'little')==line and raw[16:24]==b'\0'*8
    refs=[ref for ref in ce.relocations if ref['section']==section['name'] and row['value']<=ref['offset']<row['value']+32];assert {ref['offset']-row['value'] for ref in refs}=={0,8} and all(allocated(ce,ref) for ref in refs)
    metadata_objects.append(dict(symbol=row,section=section['name'],source_line=line,flags=0,raw=raw.hex(),allocated_pointer_relocations=refs))
   row,section,raw=object_row(ce,'process_remap_free_line',4);assert int.from_bytes(raw,'little',signed=True)==c['tracked_free_line'];metadata_objects.append(dict(symbol=row,section=section['name'],raw=raw.hex(),source_line=c['tracked_free_line']))
   row,section,raw=object_row(ce,'process_remap_free_file',8);refs=[ref for ref in ce.relocations if ref['section']==section['name'] and row['value']<=ref['offset']<row['value']+8];assert len(refs)==1 and refs[0]['offset']==row['value'] and not refs[0]['undefined'] and allocated(ce,refs[0])
   metadata_objects.append(dict(symbol=row,section=section['name'],section_flags=section['flags'],source_const_pointer=True,static_lifetime=True,preprocessed_file=c['private_source']['path'],allocated_pointer_relocations=refs))
   write(P/'ACTUAL-PROCESS-METADATA-ABI.json',dict(scope=SCOPE,status='PASS_COMPLETE_C_REAL_HEADER_ABI_CPP_ALLOCATED_METADATA_RELOCS',objects=metadata_objects))
  elif name=='12-process-fullRust-partial-symbols':
   symbols=nmrows(text)
   for symbol in [*targets,log,dump,'vm_range_insert','kprintf']:unique(symbols,symbol,{'T'})
   for symbol in c['metadata_lines']:unique(symbols,symbol,{'D'})
   unique(symbols,'phys_to_page',{'U'});partial_U=sorted({row[-1] for row in symbols if row[-2]=='U'})
  elif name=='13-process-fullRust-partial-relocations':
   partial=Elf(O/'process-rust-partial.o');rust=Elf(O/'mckernel_rust.o');ce=Elf(O/'process.c.o')
   for source,caller,target in [(rust,'sync_process_memory_range','sync_one_page'),(rust,'remap_process_memory_range','remap_one_page'),(ce,'process_add_range_insert_bridge','vm_range_insert'),(ce,'process_split_range_insert_bridge','vm_range_insert')]:
    before,brefs=function(source,caller);after,arefs=function(partial,caller);assert before==after and brefs==arefs,(caller,brefs,arefs)
    named=[ref for ref in arefs if ref['symbol']==target];assert len(named)==1,(caller,named,arefs)
    callers.append(dict(name=caller,target=target,bytes=len(after),sha256=hashlib.sha256(after).hexdigest(),full_relocations=arefs,named_target_relocations=named))
   for symbol in targets:
    before,brefs=function(rust,symbol);after,arefs=function(partial,symbol);assert before==after and brefs==arefs,(symbol,brefs,arefs)
   assert len([ref for ref in partial.relocations if ref['symbol']=='vm_range_insert' and allocated(partial,ref)])==2
 for row in durable.values():
  st=Path(row['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(row['device'],row['inode'],row['size'],row['mtime_ns'],row['ctime_ns'])
 for row in r['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private'] and pin(Path(row['canonical_before']['path']))==row['canonical_before']
 assert ns['cpu_used']()<=60
 result=dict(scope=SCOPE,status='PASS_CURRENT78_COMPLETE_GCC9_PROCESS_THREE_BODY_BATCH_REAL_ABI_ALLOCATED_RELOCS_PARTIAL',ready=pin(READY),Rust_recipe=pin(RF),C_recipe=pin(CF),grant=pin(P/'ROOT-GRANT.json'),records=records,objects=durable,source_count=78,source_identity=r['source_identity'],headers=73,actual_commands=14,actual_T_U_delta=observed_delta,actual_Rust_callback_relocations=callback_refs,actual_unchanged_C_and_Rust_callers=callers,actual_allocated_metadata=pin(P/'ACTUAL-PROCESS-METADATA-ABI.json'),retired_C_raw_rows_preserved=raw_C_retired_rows,partial_raw_U_names=partial_U,accepted795_reused=r['accepted_sync795'],fixture_replayed=False,remaining_provider_debt=['Existing phys_to_page C forwarding provider and underlying lock/log callbacks','Existing page-unmap and tracked-free backend callbacks','Static C diagnostic/gate/tracked-free identity data','Other process.c compute bodies'],seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU6_released=True,canonical_mutations=0,full_default_GCC14_image_link=False,native=False,file_retired=False,failure_history=r['failure_history'])
 write(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json',result);print(json.dumps(dict(scope=SCOPE,status=result['status'],receipt=pin(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True,objects=durable)))
except BaseException as error:
 write(P/'PRODUCTION-FIRST-FAILURE-1.json',dict(scope=SCOPE,status='STOP_EXPERT_ESCALATION_NO_AUTOMATIC_CORRECTION_OR_RETRY',error=type(error).__name__+': '+str(error),records=records,durable_objects=durable,CPU6_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
