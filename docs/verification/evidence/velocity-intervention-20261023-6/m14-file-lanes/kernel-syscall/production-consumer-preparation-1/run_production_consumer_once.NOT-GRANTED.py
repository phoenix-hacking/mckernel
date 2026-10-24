"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One current78 signalfd-only production Rust compile; reuse actual4005/GCC9 whole TU/ABI; no kernel execution.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,re,resource,signal,stat,struct,subprocess,time,sys
P=Path(__file__).resolve().parent
RF=P/'EXACT-CURRENT78-RUST.NOT-GRANTED.json';CF=P/'REUSED-WHOLE-GCC9-TU-REAL-ABI.NOT-GRANTED.json';EF=P/'EXACT-SIX-COMMANDS.NOT-GRANTED.json'
records=[];started=False;durable={};initial=os.getcwd()
def pin(q):
 b=q.read_bytes();return dict(path=str(q),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(q,v):
 with q.open('x') as f:json.dump(v,f,sort_keys=True);f.write(chr(10))
def nmrows(text):return [line.split() for line in text.splitlines() if line.split()]
def unique(rows,name,kinds):
 found=[r for r in rows if r[-1]==name];assert len(found)==1 and found[0][-2] in kinds,(name,kinds,found)
 return found[0]
def meta(q):
 s=q.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
 return dict(path=str(q),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)),nlink=s.st_nlink,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def retained(q):
 assert meta(Path(q['path']))=={k:q[k] for k in meta(Path(q['path']))}
try:
 assert pin(RF)['sha256']=='1beb8f61b54274135d7c560efe0db251ec66055866fbe6352837ffeba0c615bb' and pin(CF)['sha256']=='a77a9796a8f951cbacae898073b794054af2a5cfc495f622aa8472f065eef1f7' and pin(EF)['sha256']=='ec50f1c85c8acc59e4c3f5cb06e355842ab7b8c3383e42ad0d5137e13e010319'
 r=json.loads(RF.read_bytes());c=json.loads(CF.read_bytes());execution=json.loads(EF.read_bytes())
 assert len(r['source_inputs'])==78 and len(execution['commands'])==6 and execution['profile']==r['profile']
 for row in r['source_inputs'].values():
  for key in ['canonical_before','private']:assert pin(Path(row[key]['path']))==row[key]
 for key in ['baseline_accepted_profile','baseline_driver','baseline_actual_NM','baseline_actual_NM_command_progress','baseline_actual_NM_receipt','accepted_actual4005_and_GCC9','warning_qualification','overlay_C_source']:
  row=r[key];assert pin(Path(row['path']))==row
 for key in ['source','source_preimage','header_source','warning_qualification']:
  row=c[key];assert pin(Path(row['path']))==row
 for row in c['boundary_headers'].values():assert pin(Path(row['path']))==row
 for key in ['parser','original_leaf_recipe']:
  row=execution[key];assert pin(Path(row['path']))==row
 leaf=json.loads(Path(execution['original_leaf_recipe']['path']).read_bytes())
 for row in [*leaf['source_inputs'].values(),*leaf['unchanged_boundary_headers'].values()]:assert pin(Path(row['path']))==row
 assert pin(Path('/home/holden/mckernel/kernel/syscall.c'))['sha256']==c['source_preimage']['sha256']
 old=json.loads(Path(r['baseline_accepted_profile']['path']).read_bytes());argv=r['argv']
 assert len(argv)==48 and [i for i,(a,b) in enumerate(zip(argv,old['argv'])) if a!=b]==[46,47]
 assert pin(Path(argv[6]))['sha256']==r['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 tools={q:pin(Path(q)) for q in [argv[0],argv[6],'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld','/usr/bin/gcc-9','/home/holden/anaconda3/bin/python3']}
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version.startswith('3.9.12 ')
 durable['C_syscall']=c['retained_C_object'];Cobj=Path(durable['C_syscall']['path']);retained(durable['C_syscall'])
 for row in [c['actual_GCC9_whole_TU'],*c['retained_real_ABI'],c['retained_selection_NM']]:
  j=row['whole_join'];assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None
  for name,cap in j['captures'].items():
   b=Path(cap['path']).read_bytes();assert len(b)==cap['size'] and hashlib.sha256(b).hexdigest()==cap['sha256']
 cn=nmrows(Path(c['retained_selection_NM']['whole_join']['captures']['stdout']['path']).read_text())
 assert not any(x[-1]=='syscall_signalfd_create_bridge' and x[-2] in ['T','t'] for x in cn)
 for name in c['C_callback_providers']:unique(cn,name,{'T'})
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
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=__doc__,authority='Root explicit exclusiveCPU6 F03 signalfd full78 productionRust thenreusepassedwholeSyscall partiallink; actual4005/remaining8 accepted; old header/prechild failures preserved;2GiB60CPU90+6FSIZE32MiBFD256core0CGU1stack2MiB;P12heavy12GiBCPUs2-5+ownerCPU7retained,aggregate19GiB/floors/fullgap;firstunexpectedfailureSTOPnoreset',profile=r['profile'],Rust_recipe=pin(RF),C_recipe=pin(CF),execution_recipe=pin(EF),tools=tools,driver=pin(Path(__file__)),affinity=sorted(os.sched_getaffinity(0)))
 write(P/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 def capture(label,command):
  remaining=90-(time.monotonic()-begin);assert remaining>0
  out=CAP/label;out.mkdir(mode=0o700);cmd=dict(scope=r['scope'],purpose=__doc__+' '+label,argv=command,cwd=str(O),profile=pin(P/'ACTUAL-PROFILE.json'))
  write(out/'command.json',cmd);j=ns['owned_capture'](cmd,out,remaining,lambda:None);write(out/'whole-join.json',j);records.append(dict(label=label,command=pin(out/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  return (out/'stdout').read_text()
 texts={}
 for command in execution['commands']:
  label=command['label'];texts[label]=capture(label,command['argv'])
  if label=='00-production-Rust-compile':
   durable['Rust']=ns['hashed'](O/'mckernel_rust.o',32<<20)
   write(P/'COMPILE-OBJECT-RECEIPT.json',dict(scope=r['scope'],status='ACTUAL78_RUST_COMPILE_PASS_OBJECT_HASHED_ONCE_BEFORE_OBSERVERS',object=durable['Rust'],compiler_invocations=1,compiler_join=records[-1],recipe=pin(RF),profile=pin(P/'ACTUAL-PROFILE.json')))
  if label=='02-production-Rust-ELF':
   rn=nmrows(texts['01-production-Rust-NM']);er=nmrows(texts[label]);baseline=nmrows(Path(r['baseline_actual_NM']['path']).read_text())
   deltas={}
   for kind in ['T','U']:
    before={x[-1] for x in baseline if len(x)>=2 and x[-2]==kind};after={x[-1] for x in rn if len(x)>=2 and x[-2]==kind};expect=r['expected_'+kind+'_delta']
    delta=dict(before=len(before),after=len(after),added=sorted(after-before),removed=sorted(before-after));assert delta==dict(before=expect['before'],after=expect['after'],added=sorted(expect['added']),removed=sorted(expect['removed'])),(kind,delta,expect);deltas[kind]=delta
   for name in ['syscall_signalfd_create_bridge','syscall_signalfd_publish_bridge','sys_signalfd4','signalfd4_body_result']:
    unique(rn,name,{'T'});found=[x for x in er if x[-1:]==[name]];assert len(found)==1 and len(found[0])==8 and found[0][3:5]==['FUNC','GLOBAL'] and found[0][6]!='UND' and int(found[0][2])>0
   unique(rn,'do_syscall',{'U'})
   write(P/'ACTUAL-RUST-CONSUMER-RECEIPT.json',dict(scope=r['scope'],status='PASS_ACTUAL78_SIGNALFD_ONLY_RUST_CONSUMER_SYMBOLS',source_count=78,source_identity=r['source_identity'],object=durable['Rust'],deltas=deltas,records=records.copy(),default_link_native=False))
  if label=='03-actual-signalfd-caller-relocations':
   relocation=json.loads(texts[label]);assert relocation['status']=='PASS_ACTUAL_SIGNALFD_CALLER_AND_CREATE_ALLOCATED_RELOCATIONS'
  if label=='04-actual-whole-syscall-fullRust-partial-link':
   durable['partial']=ns['hashed'](O/'syscall-fullRust-partial.o',32<<20);write(P/'DURABLE-PARTIAL-OBJECT.json',dict(scope=r['scope'],object=durable['partial'],before_NM=True,join=records[-1]))
  if label=='05-partial-symbols':
   pn=nmrows(texts[label])
   for name in ['syscall_signalfd_create_bridge','syscall_signalfd_publish_bridge','sys_signalfd4','signalfd4_body_result',*c['C_callback_providers']]:unique(pn,name,{'T'})
  assert ns['cpu_used']()<=60
 for row in durable.values():retained(row)
 for row in r['source_inputs'].values():
  for key in ['canonical_before','private']:assert pin(Path(row[key]['path']))==row[key]
 assert pin(Path('/home/holden/mckernel/kernel/syscall.c'))['sha256']==c['source_preimage']['sha256']
 result=dict(scope=r['scope'],status='PASS_ACTUAL_CURRENT78_SIGNALFD_RUST_REUSED_COMPLETE_GCC9_SYSCALL_TU_ABI_CALLER_RELOCATION_PARTIAL_LINK_ONLY',Rust_recipe=pin(RF),C_recipe=pin(CF),execution_recipe=pin(EF),profile=pin(P/'ACTUAL-PROFILE.json'),headroom=pin(P/'ACTUAL-HEADROOM.json'),source_identity=r['source_identity'],source_count=78,objects=durable,records=records,actual_T_U_deltas=deltas,actual_allocated_caller_relocations=relocation,reused_actual4005=True,leaf_replays=0,Rust_compiler_invocations=1,new_C_compiler_invocations=0,pendingmask_actual=None,sigsuspend_actual=None,default_GCC14_link=False,native=False,file_retired=False,canonical_mutations=0,seconds=time.monotonic()-begin,total_CPU_seconds=ns['cpu_used'](),CPU6_released=True,failure_history=r['retained_failure_history'])
 write(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(P/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 write(P/'PRODUCTION-FAILURE-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_FAILURE_NO_SELF_CORRECTION_OR_REPLAY',error=type(exc).__name__+': '+str(exc),records=records,objects_retained=durable,CPU6_released=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
 os.chdir(initial)
