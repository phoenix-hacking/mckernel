"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted exact refreshed78 Rust/full selected GCC9 process TU/partial only.
No root/Docker/kernel/IRQ/guest/native effects, product or canonical mutation.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,re,resource,signal,stat,subprocess,time,sys
P=Path(__file__).resolve().parent;PREVIOUS=P.parent;B=PREVIOUS.parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
RF=P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json';CF=P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-EXECUTED.json'
started=False;records=[];durable={}
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,value):
 with p.open('x') as f:json.dump(value,f,sort_keys=True);f.write('\n')
def nmrows(text):return [line.split() for line in text.splitlines() if line.split()]
def unique(rows,name,kinds):
 found=[r for r in rows if r[-1]==name];assert len(found)==1 and found[0][-2] in kinds,(name,kinds,found);return found[0]
try:
 assert pin(PREVIOUS/'PRODUCTION-CONSUMER-READY.json')['sha256']=='d10bf5fe2b30e9d9cefc83e30537b080f99e42a927620eb07201c9993dea3eac'
 old=json.loads((PREVIOUS/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json').read_text());r=json.loads(RF.read_text());c=json.loads(CF.read_text())
 assert len(r['source_inputs'])==len(old['source_inputs'])==78 and r['cfg_count']==4 and r['CGU']==1 and r['closure_external_modules']==2
 expected={'kernel/rust/x86_cpu_helpers.rs':'a6e7465d7924755c97e5d72919a97c2985aacd35cf9db417c4ee981b4d5d071a','kernel/rust/x86_memory_helpers.rs':'ec83294bfbdb9b649b6cc313c017d0eef934dbfc638a0a84b257b50b30539c0d'}
 changes={}
 for key,row in r['source_inputs'].items():
  assert pin(Path(row['private']['path']))==row['private'] and pin(Path(row['canonical_before']['path']))==row['canonical_before'],key
  if row['private']['sha256']!=old['source_inputs'][key]['private']['sha256']:changes[key]=dict(before=old['source_inputs'][key]['private'],after=row['private'],canonical=row['canonical_before'])
 assert set(changes)==set(expected)
 for key,sha in expected.items():assert changes[key]['after']['sha256']==sha
 assert r['source_inputs']['kernel/rust/process_helpers.rs']['private']['sha256']=='3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e'
 assert c['private_source']['sha256']=='64af918855ea361bd850d6ad7480d304634c28814e04127fe3dec8c013f21044'
 for row in [c['private_source'],c['canonical_preimage'],c['actual_process_compile_database'],c['actual_dependency_descriptor'],c['ABI_witness'],*c['headers'].values(),*c['canonical_headers'].values(),*c['tools'].values()]:assert pin(Path(row['path']))==row,row['path']
 assert len(c['commands'])==12 and c['commands'][0]['argv']==r['argv'] and len(r['argv'])==48
 assert r['argv'][-12:-4]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage'] and r['argv'][-4:-2]==['-C','codegen-units=1']
 assert pin(Path(r['argv'][6]))['sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 write(P/'COHERENT-TWO-INPUT-REFRESH-AND-ROOT-GRANT.json',dict(scope=SCOPE,authority='Root explicit one exclusive CPU6 production job after coherent TWO canonical Rust refresh only; accepted walk698ba7 and CPU4291/158a, source behavior unchanged.',old_ready=pin(PREVIOUS/'PRODUCTION-CONSUMER-READY.json'),new_ready=pin(P/'PRODUCTION-CONSUMER-READY.json'),Rust_recipe=pin(RF),C_recipe=pin(CF),new_identity=r['source_identity'],exact_current_two_changes=changes,unchanged_other_private_inputs=76,override_process_unchanged=True,C64af_unchanged=True,headers73_unchanged=True,old_recipe_preserved=True,fulltree_provider_debt_and_evidence_preserved=True,before_any_compiler=True))
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:2]==(3,9)
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
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,aggregate_job_cap=7,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(P/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O=P/'output-1';O.mkdir(mode=0o700);CAP=P/'actual-production-capture-1';CAP.mkdir(mode=0o700);os.chdir(O);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=SCOPE,authority='Root explicit sole exclusive CPU6 exact refreshed12 command job; stop first unexpected failure, no self retry',CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152,Rust_recipe=pin(RF),C_recipe=pin(CF),refresh=pin(P/'COHERENT-TWO-INPUT-REFRESH-AND-ROOT-GRANT.json'),driver=pin(Path(__file__)))
 write(P/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 observations={};entry='vm_range_insert';callbacks=['vm_range_insert_log_bridge','vm_range_insert_dump_bridge']
 for command in c['commands']:
  remaining=90-(time.monotonic()-begin);assert remaining>0
  label=command['label'];cap=CAP/label;cap.mkdir(mode=0o700);cmd=dict(scope=SCOPE,purpose=command['purpose'],argv=command['argv'],cwd=str(O),profile=pin(P/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(label=label,command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  text=(cap/'stdout').read_text();observations[label]=dict(stdout=j['captures']['stdout'])
  for name,filename,trigger in [('Rust','mckernel_rust.o','00-current78-production-Rust-compile'),('C','process.c.o','05-selected-complete-process-TU'),('partial','process-rust-partial.o','09-process-fullRust-partial-link')]:
   if label==trigger:
    durable[name]=ns['hashed'](O/filename,32<<20);write(P/('DURABLE-'+name+'-OBJECT.json'),dict(scope=SCOPE,object=durable[name],compiler_or_link_join=records[-1]))
  if label=='01-current78-Rust-symbols':
   rows=nmrows(text);unique(rows,entry,{'T'})
   for callback in callbacks:unique(rows,callback,{'U'})
   unique(rows,'virt_to_phys',{'T'})
  elif label=='02-current78-Rust-ELF':
   rows=[line.split() for line in text.splitlines() if line.split()];found=[row for row in rows if row[-1]==entry]
   assert len(found)==1 and len(found[0])==8 and found[0][3:5]==['FUNC','GLOBAL'] and found[0][6]!='UND' and int(found[0][2])>0,found
  elif label=='04-selected-complete-process-preprocess':assert not re.search(r'\bint\s+vm_range_insert\s*\([^;{}]*\)\s*\{',text)
  elif label=='06-selected-process-symbols':
   rows=nmrows(text);unique(rows,entry,{'U'})
   for callback in callbacks:unique(rows,callback,{'T'})
   for caller in ('process_add_range_insert_bridge','process_split_range_insert_bridge'):unique(rows,caller,{'T'})
  elif label=='07-selected-process-relocations':
   refs=[line for line in text.splitlines() if re.search(r'\bvm_range_insert\s*\+',line)];assert len(refs)==2,refs
  elif label=='10-process-fullRust-partial-symbols':
   rows=nmrows(text);unique(rows,entry,{'T'})
   for callback in callbacks:unique(rows,callback,{'T'})
   unique(rows,'virt_to_phys',{'T'})
   for caller in ('process_add_range_insert_bridge','process_split_range_insert_bridge'):unique(rows,caller,{'T'})
 for row in durable.values():
  st=Path(row['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(row['device'],row['inode'],row['size'],row['mtime_ns'],row['ctime_ns'])
 for row in r['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private'] and pin(Path(row['canonical_before']['path']))==row['canonical_before']
 assert ns['cpu_used']()<=60
 result=dict(scope=SCOPE,status='PASS_CURRENT78_RUST_COMPLETE_SELECTED_GCC9_PROCESS_TU_ABI_RELOC_AND_FULLRUST_PARTIAL_LINK',Rust_recipe=pin(RF),C_recipe=pin(CF),refresh=pin(P/'COHERENT-TWO-INPUT-REFRESH-AND-ROOT-GRANT.json'),source_count=78,source_identity=r['source_identity'],actual_commands=12,records=records,objects=durable,header_count=len(c['headers']),Rust_entry_unique=True,selected_C_entry_imported_no_definition=True,actual_C_caller_relocations=2,partial_entry_and_both_C_callbacks_uniquely_defined=True,retained_C_callback_debt=callbacks,whole_tree_other_U_symbols_not_erased=True,accepted_prior_1088_and14commands_and_observer_reused=True,prior_failure_and_correction_history_preserved=True,CPU_seconds=ns['cpu_used'](),seconds=time.monotonic()-begin,CPU6_released=True,compiler_invocations=2,linker_invocations=1,canonical_mutations=0,default_GCC14_kernel_link=False,native=False,file_retired=False)
 write(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True,objects=durable)))
except BaseException as error:
 write(P/'PRODUCTION-FIRST-FAILURE-1.json',dict(scope=SCOPE,status='STOP_FIRST_UNEXPECTED_RESULT_NO_RETRY',error=type(error).__name__+': '+str(error),records=records,durable_objects=durable,CPU6_released=all(row['join']['direct_child_joined'] and row['join']['group_absent'] and row['join']['closed_streams'] for row in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
