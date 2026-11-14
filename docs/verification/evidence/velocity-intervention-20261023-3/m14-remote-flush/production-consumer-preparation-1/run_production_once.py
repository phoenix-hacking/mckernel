"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact78 production Rust + selected completeGCC9memTU/ABI/reloc/partiallink only.
No kernel/module/guest/native execution or canonical mutation.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,re,resource,signal,stat,struct,subprocess,time
P=Path(__file__).resolve().parent
RF=P/'EXACT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json'
CF=P/'EXACT-SELECTED-GCC9-MEM-CONSUMER.NOT-EXECUTED.json'
records=[];started=False;durable={}
def pin(q):
 b=q.read_bytes();return dict(path=str(q),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(q,v):
 with q.open('x') as f:json.dump(v,f,sort_keys=True);f.write(chr(10))
def nmrows(text):return [line.split() for line in text.splitlines() if line.split()]
def named(rows,name):return [r for r in rows if r[-1]==name]
def unique(rows,name,kinds):
 found=named(rows,name);assert len(found)==1 and found[0][-2] in kinds,(name,kinds,found)
 return found[0]
try:
 assert pin(RF)['sha256']=='242b848b41cad987645651844c2d4016884418f69f3f696f78a37d8179430029'
 assert pin(CF)['sha256']=='eb727035db27bfb5364349e9a6a437ff95bc98f3cd65df034b91fb67bf8cc358'
 r=json.loads(RF.read_text());c=json.loads(CF.read_text())
 assert r['source_identity']=='7d5368b40a19863cdff7e9c18bf382ef4809449039f3a0ac91d360c4deb9983c'
 assert len(r['source_inputs'])==78 and r['profile']==c['profile'] and r['profile']==dict(CPU=6,jobs=1,AS=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE=32<<20,NOFILE=256,core=0,RUST_MIN_STACK=2097152)
 for row in r['source_inputs'].values():
  assert pin(Path(row['private']['path']))==row['private']
  assert pin(Path(row['canonical_before']['path']))==row['canonical_before']
 for row in [r['baseline_recipe'],r['baseline_receipt'],r['baseline_profile'],r['baseline_nm'],r['candidate_source'],r['accepted_patch'],r['accepted_actual_leaf'],c['accepted_actual_GCC9_command'],c['accepted_actual_GCC9_receipt'],c['actual_mem_dependency_descriptor'],c['private_source'],c['canonical_preimage'],c['ABI_witness'],*c['actual_header_closure'].values(),*c['current_canonical_headers'].values(),*c['tools'].values()]:assert pin(Path(row['path']))==row,row['path']
 old=json.loads(Path(r['baseline_recipe']['path']).read_text());argv=r['argv'];assert len(argv)==48 and [i for i,(a,b) in enumerate(zip(argv,old['argv'])) if a!=b]==[46,47]
 assert argv[-12:-4]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage'] and argv[-4:-2]==['-C','codegen-units=1']
 assert pin(Path(argv[6]))['sha256']==r['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 tools={q:pin(Path(q)) for q in [argv[0],argv[6],'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld','/usr/bin/gcc-9']}
 assert os.getuid()==os.geteuid()==1000
 H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert pin(H)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw,str(H)).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
 ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
 def globals_used(code):
  used={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for value in code.co_consts:
   if isinstance(value,type(code)):used.update(globals_used(value))
  return used
 deps=set()
 for name in functions:deps.update(globals_used(ns[name].__code__))
 assert not deps-set(ns)-set(vars(builtins))
 write(P/'HELPER-GLOBAL-DEPENDENCY-CHECK.json',dict(helper=pin(H),missing=[],dependencies=sorted(deps),before_any_child=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,ordinary_HOST_reserve=128<<20,campaign_emergency_preserved=679477248,root_heavy_reserved_bytes=12<<30,root_CPU7_owner_reserved_bytes=2<<30,ordinary_CPU6_reserved_bytes=2<<30)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(P/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O=P/'output-1';O.mkdir(mode=0o700);CAP=P/'actual-production-capture-1';CAP.mkdir(mode=0o700);os.chdir(O);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=__doc__,authority='RootexclusiveCPU6ONEordinaryjob RustfirstthenGCC9iffirstPASS;2GiB60CPU90+6FSIZE32MiBFD256core0CGU1stack2MiB;P12heavy12GiBCPUs2-5+ownerCPU7retained,aggregate19GiB/floors/fullgap;firstunexpectedfailureSTOPnoreset',profile=r['profile'],Rust_recipe=pin(RF),C_recipe=pin(CF),tools=tools,driver=pin(Path(__file__)),affinity=sorted(os.sched_getaffinity(0)))
 write(P/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 def capture(label,command):
  remaining=90-(time.monotonic()-begin);assert remaining>0
  out=CAP/label;out.mkdir(mode=0o700);cmd=dict(scope=r['scope'],purpose=__doc__+' '+label,argv=command,cwd=str(O),profile=pin(P/'ACTUAL-PROFILE.json'))
  write(out/'command.json',cmd);j=ns['owned_capture'](cmd,out,remaining,lambda:None);write(out/'whole-join.json',j);records.append(dict(label=label,command=pin(out/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  return (out/'stdout').read_text()
 capture('00-production-Rust-compile',argv)
 obj=O/'mckernel_rust.o';durable['Rust']=ns['hashed'](obj,32<<20);write(P/'COMPILE-OBJECT-RECEIPT.json',dict(scope=r['scope'],status='ACTUAL78_RUST_COMPILE_PASS_OBJECT_HASHED_ONCE_BEFORE_OBSERVERS',object=durable['Rust'],compiler_invocations=1,compiler_join=records[-1],recipe=pin(RF),profile=pin(P/'ACTUAL-PROFILE.json')))
 rn=nmrows(capture('01-production-Rust-NM',['/usr/bin/nm','-g',str(obj)]));re=nmrows(capture('02-production-Rust-ELF',['/usr/bin/readelf','--wide','--syms',str(obj)]))
 baseline=nmrows(Path(r['baseline_nm']['path']).read_text());oldU={x[-1] for x in baseline if len(x)>=2 and x[-2]=='U'};newU={x[-1] for x in rn if len(x)>=2 and x[-2]=='U'};expected=r['expected_U_delta'];assert len(oldU)==expected['before'] and len(newU)==expected['after'] and sorted(oldU-newU)==expected['removed'] and sorted(newU-oldU)==expected['added'],(len(oldU),len(newU),oldU-newU,newU-oldU)
 oldT={x[-1] for x in baseline if len(x)>=3 and x[-2]=='T'};newT={x[-1] for x in rn if len(x)>=3 and x[-2]=='T'};assert not oldT-newT and newT-oldT==set(r['expected_new_exports'])
 for name in r['expected_new_exports']+r['expected_preserved_exports']:unique(rn,name,{'T'})
 for name in r['expected_new_exports']:
  er=named(re,name);assert len(er)==1 and len(er[0])==8 and er[0][3]=='FUNC' and er[0][4]=='GLOBAL' and er[0][6]!='UND' and int(er[0][2])>0
 write(P/'ACTUAL-RUST-CONSUMER-RECEIPT.json',dict(scope=r['scope'],status='PASS_ACTUAL78_RUST_CONSUMER_AND_ENTRY_ABI_SYMBOLS_ONLY',object=durable['Rust'],compiler_invocations=1,source_identity=r['source_identity'],source_count=78,expected_T=r['expected_new_exports'],preserved_all_prior_T=True,U_delta=dict(before=len(oldU),after=len(newU),removed=sorted(oldU-newU),added=sorted(newU-oldU)),records=records.copy(),whole_C_TU_default_link_native='OPEN'))
 texts={}
 for command in c['commands']:
  text=capture(command['label'],command['argv']);texts[command['label']]=text
  if command['label']=='selected-complete-mem-TU':
   durable['C_mem']=ns['hashed'](O/'mem.c.o',32<<20);write(P/'DURABLE-C-MEM-OBJECT.json',dict(scope=r['scope'],object=durable['C_mem'],command_join=records[-1],before_NM_readelf=True))
  if command['label']=='actual-mem-fullRust-partial-link':
   durable['partial']=ns['hashed'](O/'mem-rust-partial.o',32<<20);write(P/'DURABLE-PARTIAL-OBJECT.json',dict(scope=r['scope'],object=durable['partial'],command_join=records[-1],before_NM=True))
  if command['label']=='selected-complete-mem-preprocess':
   assert re.search(r'\bremote_flush_tlb_array_cpumask\s*\([^;{}]*\)\s*\{',text,re.S) is None,'Centrybodyselected'
  if command['label']=='selected-mem-symbols':
   cn=nmrows(text);unique(cn,'remote_flush_tlb_array_cpumask',{'U'})
   for name in c['expected_C_callback_providers']:unique(cn,name,{'T'})
   geometry=unique(cn,'mem_remote_tlb_geometry',{'R'});assert int(geometry[-3],16)==12
   unique(cn,'tlb_flush_vector',{'B','C'})
  if command['label']=='selected-mem-relocations':assert 'remote_flush_tlb_array_cpumask' in text
  if command['label']=='actual-partial-symbols':
   pn=nmrows(text)
   for name in c['expected_partial_Rust_providers']+c['expected_C_callback_providers']:unique(pn,name,{'T'})
   unique(pn,'mem_remote_tlb_geometry',{'R'});unique(pn,'tlb_flush_vector',{'B','C'})
 # Preserve durable object identities with metadata only; no large repeat hash.
 for key,name in [('Rust','mckernel_rust.o'),('C_mem','mem.c.o'),('partial','mem-rust-partial.o')]:
  st=(O/name).stat();row=durable[key];assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(row['device'],row['inode'],row['size'],row['mtime_ns'],row['ctime_ns'])
 assert all(pin(Path(row['private']['path']))==row['private'] for row in r['source_inputs'].values())
 assert ns['cpu_used']()<=60
 result=dict(scope=r['scope'],status='PASS_ACTUAL78_PRODUCTION_RUST_AND_COMPLETE_GCC9_MEM_TU_ABI_RELOCATION_PARTIAL_LINK_ONLY',Rust_recipe=pin(RF),C_recipe=pin(CF),profile=pin(P/'ACTUAL-PROFILE.json'),headroom=pin(P/'ACTUAL-HEADROOM.json'),source_identity=r['source_identity'],source_count=78,only_private_Rust_override=r['only_delta'],compiler_Rust_invocations=1,objects=durable,object_hash_once_before_observers=True,records=records,actual_U_delta=dict(before=len(oldU),after=len(newU),removed=sorted(oldU-newU),added=sorted(newU-oldU)),prior_Rust_T_preserved=True,C_entry_excluded=True,new_Rust_entry_unique=True,actual_callback_ABI_checks=12,C_callback_providers=12,remaining_C_callback_debt=13,total_CPU_seconds=ns['cpu_used'](),seconds=time.monotonic()-begin,CPU6_released=True,canonical_worker_mutations=0,exact_GCC14_default_kernel_link_native=False,failure_history=r['failure_history'])
 write(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 write(P/'PRODUCTION-FAILURE-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_FAILURE_NO_SELF_CORRECTION_OR_REPLAY',error=type(exc).__name__+': '+str(exc),records=records,objects_retained=durable,CPU6_released=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
