"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time,sys,dis,builtins,types
P=Path(__file__).resolve().parent;A=P/'actual-correction-1';A.mkdir(mode=0o700)
import importlib.util
_spec=importlib.util.spec_from_file_location('allocated_memmove_oracle',P/'allocated_memmove_oracle.py');memmove_oracle=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(memmove_oracle)
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(b,message):
 if not b:raise ValueError(message)
need(sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','accepted990 helper')
fns={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assigns={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[]
for n in ast.parse(H.read_bytes()).body:
 if isinstance(n,(ast.Import,ast.ImportFrom)):nodes.append(n)
 elif isinstance(n,ast.FunctionDef) and n.name in fns:nodes.append(n)
 elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assigns for t in n.targets):nodes.append(n)
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
def required(c):
 out={x.argval for x in dis.get_instructions(c) if x.opname=='LOAD_GLOBAL'}
 for v in c.co_consts:
  if isinstance(v,types.CodeType):out.update(required(v))
 return out
for n in fns:need(not(required(ns[n].__code__)-set(ns)-set(vars(builtins))),'helper globals '+n)
write=ns['write']
for s in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(s,ns['stop'])
records=[];objects={};failure=None;stage='preflight';begin=time.monotonic()
def stable(row):
 p=Path(row['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd);need(stat.S_ISREG(s.st_mode),'retained regular')
  for key,attr in [('device','st_dev'),('inode','st_ino'),('uid','st_uid'),('gid','st_gid'),('nlink','st_nlink'),('size','st_size'),('mtime_ns','st_mtime_ns'),('ctime_ns','st_ctime_ns')]:need(row[key]==getattr(s,attr),('retained stat',key,str(p)))
  need(row['mode']==oct(stat.S_IMODE(s.st_mode)),'retained mode')
  t=p.lstat();need(all(getattr(s,k)==getattr(t,k) for k in ns['FIELDS']),'stable retained FD/path')
 finally:os.close(fd)
def rows(text):return [x.split() for x in text.splitlines() if x.split()]
def unique(rs,name,kinds):
 rr=[r for r in rs if r[-1]==name];need(len(rr)==1 and rr[0][-2] in kinds,(name,rr));return rr[0]
def headroom():
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];need(used<100,'included usage guard')
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 hv=os.statvfs('/home/holden');sv=os.statvfs('/home/holden/mckernel-work/scratch');bk=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bk.st_size-bk.st_blocks*512)
 d={'MemAvailable':mem,'required_memory':19<<30,'HOST_available':hv.f_bavail*hv.f_frsize,'HOST_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':sv.f_bavail*sv.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bk.st_size,'backing_device':bk.st_dev,'backing_inode':bk.st_ino,'included_used_percent':used,'aggregate_jobs':7}
 need(mem>=d['required_memory'] and d['HOST_available']>=d['HOST_required'] and d['scratch_available']>=d['scratch_required'],'fresh aggregate/floors/fullgap')
 return d
try:
 need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6},'uid1000 exactCPU6')
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:need(resource.getrlimit(k)==(v,v),'exactresource'+str(k))
 need(os.environ.get('RUST_MIN_STACK')=='2097152','explicitRust2Mstack')
 ready=P/'EXECUTABLE-READY.NOT-GRANTED.json';need(sha(ready)=='8540d67840726b8f06966a126924d2871a88841883c93b398a34034170150986','frozen bounded correction ready')
 plan=json.loads(ready.read_bytes())
 for ref in [plan['Rust_recipe'],plan['exact_symbol_oracle']]:need(sha(ref['path'])==ref['sha256'],'sealedrecipe/oracle')
 rust=json.loads(Path(plan['Rust_recipe']['path']).read_bytes());oracle=json.loads(Path(plan['exact_symbol_oracle']['path']).read_bytes())
 need(rust['source_identity']=='b8d4f94d25bc1199eb7ca7df79646ce88a8c3417f972f75c686408bab641c039' and len(rust['source_inputs'])==78,'exactcurrent78')
 for row in rust['source_inputs'].values():
  for key in ['canonical','accepted_actual_union_source','private']:need(sha(row[key]['path'])==row[key]['sha256'],'bound source '+row[key]['path'])
 for row in plan['current_canonical_header_closure_verified_equal'].values():need(sha(row['path'])==row['sha256'],'current header '+row['path'])
 need(sha(plan['actual_current_C_source']['path'])==plan['actual_current_C_source']['sha256'],'privatecompleteCPU source5574')
 need(sha(plan['actual_real_header_ABI_source']['path'])==plan['actual_real_header_ABI_source']['sha256'],'retained realheader ABI source')
 for row in plan['tools'].values():need(sha(row['path'])==row['sha256'],'pinned tool '+row['path'])
 compiler=Path(plan['commands'][5]['argv'][6]);need(sha(compiler)==rust['compiler_sha256'],'pinnednightly70eb')
 need(len(plan['commands'][5]['argv'])==48 and plan['commands'][5]['argv'][plan['commands'][5]['argv'].index('--crate-name')+1]=='mckernel_rust','explicit crate/48argv')
 reused=[plan['actual_reused_complete_GCC9_CPU_object_NOT_rehashed'],plan['actual_reused_real_header_ABI_object_NOT_rehashed']]+plan['retained_leaf_C_objects_not_rehashed']+[plan['genuine_check_signal_provider']['object_NOT_rehashed']]
 for row in plan['correction_inputs'].values():need(sha(row['path'])==row['sha256'],'bounded source correction input '+row['path'])
 provider=plan['genuine_check_signal_provider']
 for key in ['authority','actual_C_source','canonical_current_C_source','actual_root_union_partial_NM']:need(sha(provider[key]['path'])==provider[key]['sha256'],'genuine provider authority '+key)
 need(provider['actual_C_source']['sha256']==provider['canonical_current_C_source']['sha256'],'actual provider matches current canonical syscall source')
 old_provider_rows=rows(Path(provider['actual_root_union_partial_NM']['path']).read_text());unique(old_provider_rows,'check_signal',{'T'})
 need(not any(r[-1]=='check_signal' and r[-2]=='U' for r in old_provider_rows),'actual root provider not unresolved')
 for row in reused:stable(row)
 allowed={os.getpid()};pid=os.getppid()
 while pid>1:
  allowed.add(pid)
  try:pid=int(Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[1])
  except FileNotFoundError:break
 competitors=[];kernels=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name) in allowed:continue
  try:
   st=(p/'status').read_text()
   aff=next(l.split(':',1)[1].strip() for l in st.splitlines() if l.startswith('Cpus_allowed_list:'))
   state=next(l for l in st.splitlines() if l.startswith('State:'))
   if aff=='6' and 'Z' not in state:
    tail=(p/'stat').read_text().rsplit(')',1)[1].split();ppid=int(tail[1]);flags=int(tail[6]);birth=int(tail[19])
    status_ppid=int(next(l.split()[1] for l in st.splitlines() if l.startswith('PPid:')))
    row={'pid':int(p.name),'start':birth,'PPid':ppid,'flags':flags,'comm':(p/'comm').read_text().strip()}
    if flags&0x00200000 and ppid==status_ppid==2:kernels.append(row)
    else:competitors.append(row)
  except (FileNotFoundError,ProcessLookupError,PermissionError):continue
 need(not competitors,('competingordinaryCPU6',competitors))
 write(A/'ADMISSION.json',{'scope':__doc__,'facts':headroom(),'competing_userspace_CPU6':competitors,'positive_PF_KTHREAD_PPid2_exemptions':kernels,'root_exclusive_grant':True})
 O=Path(plan['fresh_output_directory']);L=Path(plan['fresh_leaf_output_directory'])
 for output in [O,L]:
  need(not os.path.lexists(output),'fresh changed-source output '+str(output));output.mkdir(mode=0o700)
 os.umask(0o077)
 write(A/'ROOT-GRANT-AND-ACTUAL-PROFILE.json',{'scope':__doc__,'root_granted_ready_sha256':sha(ready),'source_identity':rust['source_identity'],'profile':plan['profile'],'actual_limits':{str(k):resource.getrlimit(k) for k in [resource.RLIMIT_AS,resource.RLIMIT_CPU,resource.RLIMIT_FSIZE,resource.RLIMIT_NOFILE,resource.RLIMIT_CORE,resource.RLIMIT_STACK]},'RUST_MIN_STACK':os.environ['RUST_MIN_STACK'],'helper_sha256':sha(H),'helper_globals_verified':True,'TERM_INT_ALRM_registered':True,'driver_sha256':sha(Path(__file__)),'retained_CPU_ABI_FD_stat_bound_not_rehashed':reused,'current78_sources_headers_verified':True,'explicit_parent_CWD':str(P)})
 signal.setitimer(signal.ITIMER_REAL,max(.1,96-(time.monotonic()-begin)))
 for i,item in enumerate(plan['commands']):
  stage=item['label'];left=90-(time.monotonic()-begin);need(left>0 and ns['cpu_used']()<60,'whole90wall60CPU')
  headroom()
  cap=A/('%02d-%s'%(i,item['label']));cap.mkdir(mode=0o700);command=dict(item);command['profile_ref']=str(A/'ROOT-GRANT-AND-ACTUAL-PROFILE.json')
  write(cap/'command.json',command);os.chdir(item['cwd'])
  j=ns['owned_capture'](command,cap,left,lambda:None)
  write(cap/'RESULT.json',j);records.append({'index':i,'label':item['label'],'command':command,'result':j})
  need(j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['timed_out'] and j['error'] is None and j['retirement_error'] is None,('first actual command failure',i,j))
  if i==5:
   prefix='--emit=obj=';emitted=[s[len(prefix):] for s in item['argv'] if s.startswith(prefix)]
   need(emitted==[str(O/'mckernel_rust.o')],'exactabsoluteRustobject')
   row=ns['hashed'](Path(emitted[0]),32<<20);objects['mckernel_rust.o']=row
   write(A/'DURABLE-mckernel_rust.o.json',{'object':row,'producer_result':j,'hashed_once_before_observers':True})
   allocated=memmove_oracle.observe(O/'mckernel_rust.o')
   write(A/'ACTUAL-ALLOCATED-MEMMOVE-ABSENCE.json',{'object':row,'oracle_source':plan['allocated_memmove_oracle'],'observation':allocated})
  if i==0:
   prefix='--emit=obj=';emitted=[x[len(prefix):] for x in item['argv'] if x.startswith(prefix)]
   need(emitted==[str(L/'actual_bodies.o')],'exact corrected leaf object')
   row=ns['hashed'](L/'actual_bodies.o',32<<20);objects['actual_bodies.o']=row
   write(A/'DURABLE-actual_bodies.o.json',{'object':row,'producer_result':j,'hashed_once_before_observers':True})
  if i==1:
   row=ns['hashed'](L/'fixture',32<<20);objects['fixture']=row
   write(A/'DURABLE-fixture.json',{'object':row,'producer_result':j,'hashed_once_before_observers':True})
  if i==2:
   need((cap/'stdout').read_text().splitlines()==plan['changed_source_leaf_expected_stdout'],'strict actual8000 counts and NOTEXECUTED qualifiers')
   need((cap/'stderr').stat().st_size==0,'controlled fixture empty stderr')
  if i==3:
   rr=rows((cap/'stdout').read_text())
   for n in ['__print_stack','mod_nmi_ctx','interrupt_exit']:unique(rr,n,{'T'})
   need(not any(r[-1]=='memmove' and r[-2]=='U' for r in rr),'leaf no memmove U')
  if i==9:
   row=ns['hashed'](O/'cpu-fullRust-partial.o',32<<20);objects['cpu-fullRust-partial.o']=row
   write(A/'DURABLE-cpu-fullRust-partial.o.json',{'object':row,'producer_result':j,'hashed_once_before_observers':True})
  if i==6:
   rr=rows((cap/'stdout').read_text());ts={r[-1] for r in rr if r[-2]=='T'};us={r[-1] for r in rr if r[-2]=='U'}
   need(ts==set(oracle['expected_T']) and len(ts)==3068,'exactglobalT3068');need(us==set(oracle['expected_U']) and len(us)==572,'exactglobalU572')
   for n in oracle['expected_T']:unique(rr,n,{'T'})
   write(A/'ACTUAL-RUST-SYMBOLS.json',{'T_count':len(ts),'U_count':len(us),'all3065priorT_preserved':True,'new_T':oracle['new_T'],'U_removed':oracle['U_removed'],'U_added':oracle['U_added'],'object':objects['mckernel_rust.o'],'source_identity':rust['source_identity']})
  if i==10:
   rr=rows((cap/'stdout').read_text())
   for n in oracle['expected_T']+plan['preserved_actual_C_providers']:unique(rr,n,{'T'})
   for n in ['__print_stack','mod_nmi_ctx','interrupt_exit']:need(not any(r[-1]==n and r[-2]=='U' for r in rr),'partialnewentryU '+n)
   data=unique(rr,'no_turbo',{'D'});need(int(data[-3],16)==4,'no_turboD4')
   need(not any(r[-1] in ['check_signal','memmove'] and r[-2]=='U' for r in rr),'genuine check_signal resolved; no memmove provider')
 for row in reused:stable(row)
 for row in rust['source_inputs'].values():
  for key in ['canonical','private']:need(sha(row[key]['path'])==row[key]['sha256'],'postflightsource '+row[key]['path'])
 for row in plan['current_canonical_header_closure_verified_equal'].values():need(sha(row['path'])==row['sha256'],'postflightheader '+row['path'])
except BaseException as exc:failure=type(exc).__name__+': '+str(exc)
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 gone=all(r['result']['direct_child_joined'] and r['result']['group_absent'] and r['result']['closed_streams'] and r['result']['retirement_error'] is None for r in records)
 out={'scope':__doc__,'status':'PASS_CHANGED_SOURCE8000_CURRENT78_3068T572U_NO_ALLOCATED_MEMMOVE_GENUINE_CHECK_SIGNAL_PARTIAL_ONLY' if failure is None and len(records)==12 else 'STOP_FIRST_UNEXPECTED_NO_RETRY_EXPERT','error':failure,'last_stage':stage,'new_commands':len(records),'planned_commands':12,'leaf_commands':5,'production_commands':7,'strict8000_expected':plan['expected_unchanged_8000_counts'] if 'plan' in globals() else None,'records':records,'objects_hashed_once':objects,'seconds':time.monotonic()-begin,'CPU_seconds':ns['cpu_used'](),'all_children_joined_groups_absent_streams_closed':gone,'CPU6_released':gone,'retained_CPU_ABI_recompiled_or_rehashed':False,'native_raw_NMI_IRQ_IRET_kernelstack_execution':False,'inherited_NULL_freeze_HOLD':True,'canonical_Git_P12_writes':0}
 write(A/'ACTUAL-WHOLE-JOIN.json',out)
 print(json.dumps({k:out[k] for k in ['status','error','last_stage','new_commands','seconds','CPU_seconds','CPU6_released']}))
if failure is not None:raise SystemExit(1)
