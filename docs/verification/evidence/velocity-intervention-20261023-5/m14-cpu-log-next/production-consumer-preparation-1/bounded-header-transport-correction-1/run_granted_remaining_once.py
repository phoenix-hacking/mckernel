"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time,sys,dis,builtins,types
R=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assigns={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
tree=ast.parse(H.read_bytes());nodes=[]
for n in tree.body:
 if isinstance(n,(ast.Import,ast.ImportFrom)):nodes.append(n)
 elif isinstance(n,ast.FunctionDef) and n.name in functions:nodes.append(n)
 elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assigns for t in n.targets):nodes.append(n)
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
def globals_needed(code):
 out={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
 for v in code.co_consts:
  if isinstance(v,types.CodeType):out.update(globals_needed(v))
 return out
for n in functions:
 assert not (globals_needed(ns[n].__code__)-set(ns)-set(vars(builtins))),n



write=ns['write'];records=[];objects={};begin=time.monotonic();A=R/'actual-remaining-capture-1';os.umask(0o077);A.mkdir(mode=0o700);failure=None
def rows(t):return [x.split() for x in t.splitlines() if x.split()]
def unique(rs,n,kinds):
 a=[x for x in rs if x[-1]==n];assert len(a)==1 and a[0][-2] in kinds,(n,a);return a[0]
def stablefd(row):
 p=Path(row['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd);assert stat.S_ISREG(s.st_mode)
  for k,a in [('device','st_dev'),('inode','st_ino'),('uid','st_uid'),('gid','st_gid'),('nlink','st_nlink'),('size','st_size'),('mtime_ns','st_mtime_ns'),('ctime_ns','st_ctime_ns')]:assert row[k]==getattr(s,a),(str(p),k)
  assert row['mode']==oct(stat.S_IMODE(s.st_mode))
  a=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 finally:os.close(fd)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
try:
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:assert resource.getrlimit(k)==(v,v)
 os.environ['RUST_MIN_STACK']='2097152'
 RP=R/'EXECUTABLE-READY.REMAINING7.NOT-GRANTED.json';assert sha(RP)=='c035a59aa7f196c3bba6f2ec16af4a48c53c77f4aa53506175ffc4f103dc61e4'
 plan=json.loads(RP.read_bytes());CP=R/'EXACT-HEADER-CLOSURE-CORRECTION.json';assert sha(CP)=='75b6ae91152f45b297232a8a49f29d391bbdc31de00792d4889ad81d59e4a6f1';closure=json.loads(CP.read_bytes())
 for v in plan['retained_actual_artifacts_not_rehashed'].values():stablefd(v)
 # Only the corrected finite header/C transport is checked here; the accepted
 # 78-input Rust source tree/object is not rehashed or recompiled/replayed.
 for v in [*closure['new_header_closure'].values(),plan['private_C_source'],closure['added_canonical_header'],closure['witness_unchanged']['corrected_transport_path'],closure['selected_declaration_unchanged']['corrected_transport_path'],*plan['tools'].values()]:
  assert sha(Path(v['path']))==v['sha256'],v['path']
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];assert used<100
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 hv=os.statvfs('/home/holden');sv=os.statvfs('/home/holden/mckernel-work/scratch');bk=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bk.st_size-bk.st_blocks*512)
 fact={'MemAvailable':mem,'memory_required':19<<30,'HOST_available':hv.f_bavail*hv.f_frsize,'HOST_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':sv.f_bavail*sv.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bk.st_size,'backing_device':bk.st_dev,'backing_inode':bk.st_ino,'included_used_percent':used,'aggregate_jobs':7,'root_exclusive_CPU6_grant':True}
 write(R/'ACTUAL-HEADROOM.json',fact);assert mem>=fact['memory_required'] and fact['HOST_available']>=fact['HOST_required'] and fact['scratch_available']>=fact['scratch_required']
 write(R/'ACTUAL-PROFILE.json',{'scope':__doc__,'profile':plan['profile'],'ready_sha256':sha(RP),'driver_sha256':sha(Path(__file__)),'helper_sha256':sha(H),'helper_global_dependencies_checked':True,'TERM_INT_ALRM_registered':True,'retained_Rust_artifacts_readonly_FD_stat_bound_not_rehashed':True,'no_Rust_source78_hash_or_compile_or_preprocess_replay':True})
 oracle=json.loads(Path(plan['retained_exact_symbol_oracle']['path']).read_bytes());O=R/'output-1';O.mkdir(mode=0o700);os.chdir(O);signal.setitimer(signal.ITIMER_REAL,96)
 for i,item in enumerate(plan['commands']):
  left=90-(time.monotonic()-begin);assert left>0 and ns['cpu_used']()<60
  cap=A/item['label'];cap.mkdir(mode=0o700);cmd={'argv':item['argv'],'purpose':__doc__+' Sole headertransport correction '+item['label'],'cwd':str(O)};write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,left,lambda:None);write(cap/'whole-join.json',j);records.append({'name':item['label'],'join':j})
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  text=(cap/'stdout').read_text()
  if i in (1,5):
   n='cpu.c.o' if i==1 else 'cpu-rust-partial.o';objects[n]=ns['hashed'](O/n,32<<20);write(R/('DURABLE-'+n+'.json'),{'object':objects[n],'join':j,'hashed_once_before_observers':True})
  if i==2:
   cn=rows(text);unique(cn,plan['expected_C_target']['name'],{'U'})
   for n in plan['expected_C_callback_providers']:unique(cn,n,{'T'})
   d=unique(cn,plan['expected_data']['name'],{plan['expected_data']['kind']});assert int(d[-3],16)==plan['expected_data']['size']
  if i==3:
   section='';rel=[]
   for line in text.splitlines():
    if line.startswith('Relocation section '):section=line
    if 'x86_cpu_ulong_log_bridge' in line and '.rela.text' in section:rel.append(line)
   assert len(rel)==plan['expected_named_target_relocations'],rel
   write(R/'ACTUAL-DEFAULT-CPU-CALLBACK-RELOCATIONS.json',{'scope':__doc__,'target':'x86_cpu_ulong_log_bridge','actual_text_relocations':rel,'count':len(rel),'current_source_callers':plan['expected_real_C_callback_callers']})
  if i==6:
   pn=rows(text)
   for n in oracle['expected_T']+plan['expected_C_callback_providers']:unique(pn,n,{'T'})
   unique(pn,'kprintf',{'T'});assert not any(x[-1]=='x86_cpu_ulong_log_bridge' and x[-2]=='U' for x in pn)
   d=unique(pn,plan['expected_data']['name'],{plan['expected_data']['kind']});assert int(d[-3],16)==plan['expected_data']['size']
 for v in plan['retained_actual_artifacts_not_rehashed'].values():stablefd(v)
 for v in objects.values():stablefd(v)
except BaseException as exc:failure=type(exc).__name__+': '+str(exc)
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 gone=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] and x['join']['retirement_error'] is None for x in records)
 out={'scope':__doc__,'status':'PASS_SOLE_HEADER_TRANSPORT_CORRECTION_REMAINING7_COMPLETE_GCC9_CPU_ABI_RELOC_PARTIAL_WITH_RETAINED78_RUST_ONLY' if failure is None else 'STOP_CORRECTION_UNEXPECTED_FAILURE_EXPERT_NO_THIRD_JOB','error':failure,'completed_commands':len(records),'records':records,'objects':objects,'seconds':time.monotonic()-begin,'CPU_seconds':ns['cpu_used'](),'all_children_joined_groups_absent_streams_closed':gone,'CPU6_released':gone,'Rust_recompiled':False,'Rust_object_rehashed':False,'prior_PASSED_stages_replayed':False,'canonical_writes':0,'GCC14_defaultkernel_link_native':False,'failure_history_preserved':True}
 write(R/'ACTUAL-REMAINING7-WHOLE-JOIN.json',out);print(json.dumps({k:out[k] for k in ['status','error','completed_commands','seconds','CPU6_released']}))
if failure is not None:raise SystemExit(1)
