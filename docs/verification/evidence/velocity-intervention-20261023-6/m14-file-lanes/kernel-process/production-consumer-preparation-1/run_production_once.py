"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One dump current78/wholeGCC9 process consumer14 job; explicit new root grant required.
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
 grant=json.loads((P/'ROOT-GRANT.json').read_text());assert grant['scope']==SCOPE and grant['CPU']==6 and grant['ready_sha256']==pin(READY)['sha256'] and grant['ordinary_jobs']==1 and grant['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 ready=json.loads(READY.read_text());assert pin(RF)==ready['Rust_recipe'] and pin(CF)==ready['C_recipe'] and pin(Path(__file__))==ready['driver']
 r=json.loads(RF.read_text());c=json.loads(CF.read_text());assert len(r['source_inputs'])==78 and len(c['commands'])==14
 assert r['source_identity']=='1003f481cae91c012256264ea0c4eb960cbaaf66ea1e1616e2bed3b0e7bf177d'
 for row in ready['evidence_bindings']:assert pin(Path(row['path']))==row,row['path']
 for row in r['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private'] and pin(Path(row['canonical_before']['path']))==row['canonical_before']
 for row in [r['accepted_prior_whole_join'],r['accepted_prior_Rust_recipe'],r['accepted_prior_Rust_symbols'],c['accepted_prior_complete_C_profile'],c['accepted_prior_whole_join'],c['private_source'],c['canonical_preimage'],c['ABI_witness'],*c['headers'].values(),*c['canonical_headers'].values(),*c['tools'].values()]:assert pin(Path(row['path']))==row,row['path']
 argv=r['argv'];assert len(argv)==48 and argv==c['commands'][0]['argv']
 assert argv[-12:-4]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage'] and argv[-4:-2]==['-C','codegen-units=1']
 assert pin(Path(argv[6]))['sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 write(P/'ROOT-COMPILER-CLARIFICATION.json',dict(scope=SCOPE,authority='Root explicit frozen dump current78 production grant; pinnednightly1.95-2026-02-18 compiler70eb48argv unchanged; prior corrected E0428 family retained2fb3/e9a/7a, no family reset.',compiler=pin(Path(argv[6])),recipe=pin(RF),before_any_compiler=True))
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
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=SCOPE,authority='Root explicit sole dump CPU6 current78 production grant bound by ROOT-GRANT.json; 70eb48argv; no competing ordinary CPU6 job or automatic retry',CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152,ready=pin(READY),Rust_recipe=pin(RF),C_recipe=pin(CF),driver=pin(Path(__file__)),cwd=str(O))
 write(P/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 log='vm_range_insert_log_bridge';selector='process_vm_range_insert_debug';entry='vm_range_insert_dump_bridge';gate='process_dump_tree_enabled';oldrows=nmrows(Path(r['accepted_prior_Rust_symbols']['path']).read_text());oldU={x[-1] for x in oldrows if x[-2]=='U'};oldT={x[-1] for x in oldrows if x[-2]=='T'}
 observed_delta={};rust_callback_relocs=[];dump_relocs=[];caller_witnesses=[];gate_metadata={}
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
   rows=nmrows(text);newU={x[-1] for x in rows if x[-2]=='U'};newT={x[-1] for x in rows if x[-2]=='T'}
   for symbol in (log,entry,'vm_range_insert','kprintf','virt_to_phys','clear_range_l3','x86_cpu_ulong_log_bridge'):unique(rows,symbol,{'T'})
   unique(rows,selector,{'U'});unique(rows,gate,{'U'})
   for label,old,new in [('U',oldU,newU),('T',oldT,newT)]:
    expected=r['expected_'+label+'_delta'];observed=dict(removed=sorted(old-new),added=sorted(new-old),before=len(old),after=len(new));assert observed==expected,(label,observed,expected);observed_delta[label]=observed
  elif name=='02-current78-Rust-ELF':
   rows=nmrows(text)
   for symbol in (log,entry):
    found=[row for row in rows if row[-1]==symbol];assert len(found)==1 and len(found[0])==8 and found[0][3:5]==['FUNC','GLOBAL'] and found[0][6]!='UND' and int(found[0][2])>0,found
  elif name=='03-current78-Rust-relocations':
   rustelf=Elf(O/'mckernel_rust.o');_,rust_callback_relocs=rustelf.function_bytes_and_relocations(log);_,dump_relocs=rustelf.function_bytes_and_relocations(entry)
   assert {'kprintf',selector}<={row['symbol'] for row in rust_callback_relocs},rust_callback_relocs
   assert {'kprintf',gate}<={row['symbol'] for row in dump_relocs},dump_relocs
  elif name=='05-selected-complete-process-preprocess':
   assert not re.search(r'\bvoid\s+vm_range_insert_log_bridge\s*\([^;{}]*\)\s*\{',text)
   assert not re.search(r'\bvoid\s+(?:vm_range_insert_dump_bridge|dump_tree|dtree)\s*\([^;{}]*\)\s*\{',text)
   assert re.search(r'const\s+int\s+process_dump_tree_enabled\s*=\s*0\s*;',text)
   match=re.search(r'process_vm_range_insert_debug\s*=\s*\{([^}]+)\}',text,re.S);assert match
   initializer=match.group(1);line=int(re.search(r'\.line\s*=\s*(\d+)',initializer).group(1));flags=int(re.search(r'\.flags\s*=\s*(0x[0-9a-fA-F]+|\d+)',initializer).group(1),0)
   assert line==2086 and flags==0 and '"vm_range_insert_log_bridge"' in initializer and str(Path(c['private_source']['path'])) in initializer,initializer
   metadata['preprocessed_exact_initializer']=initializer;metadata['line']=line;metadata['flags']=flags
  elif name=='07-selected-process-symbols':
   rows=nmrows(text);assert not [row for row in rows if row[-1] in {log,entry,'dtree','dump_tree'}];unique(rows,'vm_range_insert',{'U'});g=unique(rows,gate,{'R'});assert int(g[-3],16)==4;value=unique(rows,selector,{'D'});assert int(value[-3],16)==32
  elif name=='08-selected-process-relocations':
   refs=[line for line in text.splitlines() if re.search(r'\bvm_range_insert\s*\+',line)];assert len(refs)==2,refs
  elif name=='09-selected-process-ELF':
   celf=Elf(O/'process.c.o')
   gates=[row for row in celf.symbols if row['name']==gate];assert len(gates)==1;g=gates[0];assert g['bind']==1 and g['type']==1 and g['size']==4 and 0<g['section']<len(celf.sections)
   gsec=celf.sections[g['section']];assert not (gsec['flags']&1) and not (gsec['flags']&4);graw=celf.data(gsec)[g['value']:g['value']+4];assert graw==b'\0'*4
   gate_metadata=dict(symbol=g,section=gsec['name'],readonly=True,bytes=graw.hex(),value=0)
   matches=[row for row in celf.symbols if row['name']==selector];assert len(matches)==1
   row=matches[0];assert row['bind']==1 and row['type']==1 and row['size']==32 and 0<row['section']<len(celf.sections)
   sec=celf.sections[row['section']];assert sec['name']=='__verbose'
   start=row['value'];raw=celf.data(sec)[start:start+row['size']];assert len(raw)==32
   encoded=struct.unpack_from('<I',raw,3*8)[0];assert encoded==(metadata['flags']<<24)|metadata['line']
   assert raw[2*8:3*8]==b'\0'*8
   refs=[ref for ref in celf.relocations if ref['section']==sec['name'] and start<=ref['offset']<start+32];assert {ref['offset']-start for ref in refs}=={0,8}
   metadata.update(actual_descriptor_bytes=raw.hex(),actual_descriptor_section=sec['name'],actual_descriptor_symbol=row,actual_descriptor_pointer_relocations=refs,typed_Ddebug_layout_proof='actual Rust debug.rs reprC const assertions and reused1101 C/Rust runtime ABI/bitfield proof')
   write(P/'ACTUAL-DEBUG-METADATA-ABI.json',dict(scope=SCOPE,status='PASS_COMPLETE_C_DESCRIPTOR_PREPROCESS_ELF_AND_TYPED_ABI',metadata=metadata))
  elif name=='12-process-fullRust-partial-symbols':
   rows=nmrows(text)
   for symbol in (log,entry,'vm_range_insert','kprintf'):unique(rows,symbol,{'T'})
   unique(rows,selector,{'D'});g=unique(rows,gate,{'R'});assert int(g[-3],16)==4
  elif name=='13-process-fullRust-partial-relocations':
   partial=Elf(O/'process-rust-partial.o');celf=Elf(O/'process.c.o');partial.defined_function(entry)
   for caller in ('process_add_range_insert_bridge','process_split_range_insert_bridge'):
    before,brefs=celf.function_bytes_and_relocations(caller);after,arefs=partial.function_bytes_and_relocations(caller)
    assert before==after and brefs==arefs and len(arefs)==1 and arefs[0]['symbol']=='vm_range_insert',(caller,brefs,arefs)
    caller_witnesses.append(dict(name=caller,sha256=hashlib.sha256(after).hexdigest(),bytes=len(after),actual_relocations=arefs))
   assert len([ref for ref in partial.relocations if ref['symbol']=='vm_range_insert'])==2
   _,actual_dump_refs=partial.function_bytes_and_relocations(entry);assert dump_relocs==actual_dump_refs
   assert {'kprintf',gate}<={row['symbol'] for row in actual_dump_refs}
 for row in durable.values():
  st=Path(row['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(row['device'],row['inode'],row['size'],row['mtime_ns'],row['ctime_ns'])
 for row in r['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private'] and pin(Path(row['canonical_before']['path']))==row['canonical_before']
 assert ns['cpu_used']()<=60
 result=dict(scope=SCOPE,status='PASS_F02_DUMP_CURRENT78_COMPLETE_GCC9_PROCESS_REAL_ABI_CALLER_RELOCS_FULLRUST_PARTIAL',ready=pin(READY),Rust_recipe=pin(RF),C_recipe=pin(CF),grant=pin(P/'ROOT-GRANT.json'),records=records,objects=durable,source_count=78,source_identity=r['source_identity'],headers=73,actual_commands=14,actual_T_U_delta=observed_delta,debug_metadata=pin(P/'ACTUAL-DEBUG-METADATA-ABI.json'),Rust_log_relocations=rust_callback_relocs,Rust_dump_relocations=dump_relocs,actual_unchanged_C_callers=caller_witnesses,readonly_dump_gate=gate_metadata,selected_C_dump_compute_absent=True,Rust_dump_unique=True,kprintf_existing_Rust_provider=True,actual433and20commands_reused=ready['accepted_actual433_leaf'],failure_history=r['failure_history'],retained_C_debt=['Readonly original dump gate metadata','Other process.c compute bodies'],seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU6_released=True,canonical_mutations=0,full_default_GCC14_image_link=False,native=False,file_retired=False)
 write(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True,objects=durable)))
except BaseException as error:
 write(P/'PRODUCTION-FIRST-FAILURE-1.json',dict(scope=SCOPE,status='STOP_FIRST_UNEXPECTED_RESULT_PRESERVE_HISTORY_NO_AUTOMATIC_RETRY',error=type(error).__name__+': '+str(error),records=records,durable_objects=durable,CPU6_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
