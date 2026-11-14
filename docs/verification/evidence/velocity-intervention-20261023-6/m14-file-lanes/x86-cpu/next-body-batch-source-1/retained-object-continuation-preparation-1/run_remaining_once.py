"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time,sys,dis,builtins,types
D=Path(__file__).resolve().parent.parent
A=D/'actual-retained-continuation-1'
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,message):
 if not ok:raise ValueError(message)
need(sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8','accepted990 helper bytes')
fns={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assigns={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[]
for n in ast.parse(H.read_bytes()).body:
 if isinstance(n,(ast.Import,ast.ImportFrom)):nodes.append(n)
 elif isinstance(n,ast.FunctionDef) and n.name in fns:nodes.append(n)
 elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assigns for t in n.targets):nodes.append(n)
ns={'__file__':str(H)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),ns)
def globals_needed(c):
 out={x.argval for x in dis.get_instructions(c) if x.opname=='LOAD_GLOBAL'}
 for v in c.co_consts:
  if isinstance(v,types.CodeType):out.update(globals_needed(v))
 return out
for n in fns:need(not(globals_needed(ns[n].__code__)-set(ns)-set(vars(builtins))),'helper globals '+n)
write=ns['write']
need(not A.exists(),'fresh retained-continuation capture root')
A.mkdir(mode=0o700)
for s in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(s,ns['stop'])
records=[];objects={};failure=None;stage='preflight';beg=time.monotonic();attempted=False
def rows(t):return [x.split() for x in t.splitlines() if x.split()]
def unique(rs,name,kinds):
 rr=[r for r in rs if r[-1]==name];need(len(rr)==1 and rr[0][-2] in kinds,(name,rr));return rr[0]
def headroom():
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];need(used<100,'included usage guard')
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 hv=os.statvfs('/home/holden');sv=os.statvfs('/home/holden/mckernel-work/scratch');bk=Path('/home/holden/mckernel-work/scratch.ext4').stat()
 gap=max(0,bk.st_size-bk.st_blocks*512)
 fact={'MemAvailable':mem,'memory_required':19<<30,'HOST_available':hv.f_bavail*hv.f_frsize,'HOST_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':sv.f_bavail*sv.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bk.st_size,'backing_device':bk.st_dev,'backing_inode':bk.st_ino,'included_used_percent':used,'aggregate_jobs':7}
 need(mem>=fact['memory_required'] and fact['HOST_available']>=fact['HOST_required'] and fact['scratch_available']>=fact['scratch_required'],'19GiB/HOST/scratch/fullgap floors')
 return fact
try:
 need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6},'ordinary CPU6 uid1000')
 need(Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve(),'accepted Python')
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:
  need(resource.getrlimit(k)==(v,v),'exact resource '+str(k))
 need(os.environ.get('RUST_MIN_STACK')=='2097152','explicit Rust stack')
 rp=D/'PROPOSED-ORDINARY-BATCH-RECIPE.json';pp=D/'CURRENT-CONTEXT-PRECHECK-SUCCESSOR.json'
 need(sha(rp)=='4028d77c55bb65826f05ed60b82943b4d8198271d7d52cc8255f6604802d801b','frozen16 recipe')
 need(sha(pp)=='5e78c5e8b6e0e524b767422739b2d23207e70b64a1fcffaa34e5846b9c849f28','accepted additive context precheck')
 plan=json.loads(rp.read_bytes());pre=json.loads(pp.read_bytes());hand=json.loads((D/'SOURCE-BATCH-HANDOFF.json').read_bytes())
 need(sha(D/'SOURCE-BATCH-HANDOFF.json')=='bb304481673e2f275756e5c91af89106f712ef0b3549f653452c8bcc3743a349','frozen source handoff')
 cr=D/'retained-object-continuation-preparation-1/EXACT-REMAINING15.NOT-GRANTED.json'
 need(sha(cr)=='51429f0a871a94d9e40dc405526cb1758bc5713e5f9967267e74c755b9343a32','sealed exact retained continuation')
 cont=json.loads(cr.read_bytes());need(cont['commands']==plan['commands'][1:],'exact15 unshifted remaining argv')
 fr=Path(cont['retained_failure_ready']['path']);need(sha(fr)==cont['retained_failure_ready']['sha256'],'reviewed0460 failure ready')
 retained=json.loads(fr.read_bytes())
 for row in [cont['original_driver'],cont['original_wholejoin']]:need(sha(row['path'])==row['sha256'],'authenticated retained producer '+row['path'])
 prior=json.loads(Path(cont['original_wholejoin']['path']).read_bytes())
 need(prior['completed_commands']==1 and len(prior['records'])==1,'only prioractual00')
 reused=prior['records'][0];need(reused['index']==0 and reused['command']['argv']==plan['commands'][0]['argv'] and reused['command']['cwd']==plan['commands'][0]['cwd'],'exact actual producer argv/cwd')
 j0=reused['result'];need(j0['returncode']==0 and j0['direct_child_joined'] and j0['group_absent'] and j0['closed_streams'] and not j0['timed_out'] and j0['error'] is None and j0['retirement_error'] is None,'positive retained00 producer join')
 need(not j0['remaining_group_members'] and not j0['unexpected_group_members'],'retained00 absence')
 for name,row in j0['captures'].items():need(sha(row['path'])==row['sha256'],'retained00 '+name)
 original_object=cont['retained_actual_Rust_object_stat_NO_HISTORICAL_SHA']
 need(original_object['sha256'] is None and original_object['actual_object_hashed'] is False,'no fabricated historical objectSHA')
 def stable_identity(row,is_dir=False):
  p=Path(row['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   meta=os.fstat(fd);need(stat.S_ISDIR(meta.st_mode) if is_dir else stat.S_ISREG(meta.st_mode),'retained type')
   for key,attr in [('device','st_dev'),('inode','st_ino'),('uid','st_uid'),('gid','st_gid'),('nlink','st_nlink'),('mtime_ns','st_mtime_ns'),('ctime_ns','st_ctime_ns')]:
    need(row[key]==getattr(meta,attr),('retained metadata',key,str(p)))
   if not is_dir:need(row['size']==meta.st_size,'retained size')
   need(row['mode']==oct(stat.S_IMODE(meta.st_mode)),'retained mode')
   after=p.lstat();need(all(getattr(meta,k)==getattr(after,k) for k in ['st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns']),'stable retained FD/path')
  finally:os.close(fd)
 stable_identity(cont['owned_existing_output_directory'],True);stable_identity(original_object)
 need(sorted(p.name for p in Path(cont['owned_existing_output_directory']['path']).iterdir())==cont['allowed_existing_output_members'],'existingoutput contains only retained Rust object')
 records.append(dict(reused,REUSED_PRIOR_ACTUAL_COMPILE_NOT_NEW_COMMAND=True))
 for row in pre['expected_canonical_before_child'].values():need(sha(row['path'])==row['sha256'],'current context base '+row['path'])
 for row in hand['source_files'].values():need(sha(row['path'])==row['sha256'],'frozen actual input '+row['path'])
 for row in plan['tool_authority'].values():need(sha(row['path'])==row['sha256'],'pinned tool '+row['path'])
 # Refuse another ordinary profile pinned exclusively to our granted CPU.
 allowed={os.getpid()};p=os.getppid()
 while p>1:
  allowed.add(p)
  try:p=int(Path('/proc/'+str(p)+'/stat').read_text().rsplit(')',1)[1].split()[1])
  except FileNotFoundError:break
 competitors=[];exempt_kernel_threads=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name) in allowed:continue
  try:
   status=(p/'status').read_text()
   line=next(l for l in status.splitlines() if l.startswith('Cpus_allowed_list:'))
   state=next(l for l in status.splitlines() if l.startswith('State:'))
   if line.split(':',1)[1].strip()=='6' and 'Z' not in state:
    tail=(p/'stat').read_text().rsplit(')',1)[1].split()
    ppid=int(tail[1]);flags=int(tail[6]);birth=int(tail[19])
    status_ppid=int(next(l for l in status.splitlines() if l.startswith('PPid:')).split()[1])
    if flags&0x00200000 and ppid==status_ppid==2:
     exempt_kernel_threads.append({'pid':int(p.name),'start':birth,'flags':flags,'PF_KTHREAD':True,'PPid':ppid,'comm':(p/'comm').read_text().strip()})
     continue
    competitors.append({'pid':int(p.name),'start':birth,'cmdline':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')[:300]})
  except (FileNotFoundError,ProcessLookupError,PermissionError):continue
 need(not competitors,('competing CPU6 profiles',competitors))
 admission=headroom();write(A/'ADMISSION.json',{'scope':__doc__,'fresh_facts':admission,'competing_CPU6_profiles':competitors,'positive_PF_KTHREAD_PPid2_exemptions':exempt_kernel_threads,'root_exclusive_grant':True})
 os.umask(0o077)
 write(A/'ACTUAL-PROFILE.json',{'scope':__doc__,'recipe_sha256':sha(rp),'context_precheck_sha256':sha(pp),'profile':plan['profile'],'actual_limits':{'AS':resource.getrlimit(resource.RLIMIT_AS),'CPU':resource.getrlimit(resource.RLIMIT_CPU),'FSIZE':resource.getrlimit(resource.RLIMIT_FSIZE),'NOFILE':resource.getrlimit(resource.RLIMIT_NOFILE),'CORE':resource.getrlimit(resource.RLIMIT_CORE),'STACK':resource.getrlimit(resource.RLIMIT_STACK)},'RUST_MIN_STACK':os.environ['RUST_MIN_STACK'],'helper_sha256':sha(H),'helper_globals_verified':True,'TERM_INT_ALRM_registered':True,'driver_sha256':sha(Path(__file__)),'raw_NMI_IRQ_IRET_kernelstack_execution':False})
 signal.setitimer(signal.ITIMER_REAL,max(.1,96-(time.monotonic()-beg)))
 # This is the genuine FIRST hash of the actual prior Rust object, not a
 # historical compiler-time SHA and not a recompile/replay.
 first=ns['hashed'](Path(original_object['path']),32<<20)
 for key in ['path','device','inode','uid','gid','mode','nlink','size','mtime_ns','ctime_ns']:need(first[key]==original_object[key],('FIRSTHASH metadata',key))
 stable_identity(original_object)
 objects[Path(first['path']).name]=first
 write(A/'DURABLE-actual_bodies.o.FIRSTHASH_NOW.json',{'object':first,'qualification':'GENUINE_FIRST_HASH_NOW_REUSED_PRIOR_ACTUAL00_NO_HISTORICAL_SHA','producer':reused,'reviewed_failure_ready_sha256':cont['retained_failure_ready']['sha256'],'Rust_recompiled':False,'prior_actual_command_replayed':False})
 for i,item in enumerate(plan['commands'][1:],start=1):
  stage=item['label'];headroom();left=90-(time.monotonic()-beg);need(left>0 and ns['cpu_used']()<60,'whole wall/CPU budget')
  if '-o' in item['argv']:
   produced=Path(item['argv'][item['argv'].index('-o')+1])
   need(not os.path.lexists(produced),'fresh remaining output before producer '+str(produced))
  cap=A/('%02d-%s'%(i,item['label']));cap.mkdir(mode=0o700)
  command=dict(item);command['profile_ref']=str(A/'ACTUAL-PROFILE.json')
  write(cap/'command.json',command);os.chdir(item['cwd']);attempted=True
  j=ns['owned_capture'](command,cap,left,lambda:None)
  write(cap/'RESULT.json',j);records.append({'index':i,'label':item['label'],'command':command,'result':j})
  need(j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['timed_out'] and j['error'] is None and j['retirement_error'] is None,('actual command failure',i,j))
  prefix='--emit=obj='
  emitted=[arg for arg in item['argv'] if arg.startswith(prefix)]
  need(len(emitted)<=1,'single declared obj emit')
  for arg in emitted:
   p=Path(arg[len(prefix):]);need(p.is_absolute(),'declared absolute object output')
   need(p==D/'output-1/actual_bodies.o','exact frozen00 output')
   row=ns['hashed'](p,32<<20);objects[p.name]=row;write(A/('DURABLE-'+p.name+'.json'),{'object':row,'compiler_result':j,'hashed_once_before_observers':True})
  if '-o' in item['argv']:
   p=Path(item['argv'][item['argv'].index('-o')+1])
   row=ns['hashed'](p,32<<20);objects[p.name]=row;write(A/('DURABLE-'+p.name+'.json'),{'object':row,'producer_result':j,'hashed_once_before_observers':True})
  text=(cap/'stdout').read_text()
  if i==6:need(text.splitlines()==plan['expected_fixture_stdout'],('strict8000fixture output',text))
  if i==7:
   rr=rows(text)
   for n in plan['observers']['Rust_exports_once']:unique(rr,n,{'T'})
  if i==10:
   rr=rows(text)
   for n in plan['observers']['default_C_no_definitions']:need(not any(r[-1]==n and r[-2] in {'T','t'} for r in rr),('C duplicate',n))
   for n in plan['observers']['default_C_expected_imports']:unique(rr,n,{'U'})
  if i==13:
   rr=rows(text)
   for n,k in plan['observers']['fallback_C_definitions'].items():unique(rr,n,{k})
  if i==15:
   rr=rows(text)
   for n in plan['observers']['Rust_exports_once']:unique(rr,n,{'T'});need(not any(r[-1]==n and r[-2]=='U' for r in rr),('partial unresolved',n))
 stable_identity(original_object)
 for row in pre['expected_canonical_before_child'].values():need(sha(row['path'])==row['sha256'],'postflight context base '+row['path'])
 for row in hand['source_files'].values():need(sha(row['path'])==row['sha256'],'postflight frozen input '+row['path'])
except BaseException as exc:
 failure=type(exc).__name__+': '+str(exc)
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 gone=all(x['result']['direct_child_joined'] and x['result']['group_absent'] and x['result']['closed_streams'] and x['result']['retirement_error'] is None for x in records)
 out={'scope':__doc__,'status':'PASS_FROZEN16_CONTROLLED8000_AND_REAL_ABI_SELECTED_FALLBACK_LEAF_ONLY' if failure is None and len(records)==16 else 'STOP_FIRST_ACTUAL_UNEXPECTED_FAILURE_NO_RETRY','error':failure,'last_stage':stage,'new_commands':sum(not x.get('REUSED_PRIOR_ACTUAL_COMPILE_NOT_NEW_COMMAND',False) for x in records),'reused_commands':sum(x.get('REUSED_PRIOR_ACTUAL_COMPILE_NOT_NEW_COMMAND',False) for x in records),'total_bound_commands':len(records),'records':records,'durable_objects_hashed_once':objects,'seconds':time.monotonic()-beg,'CPU_seconds':ns['cpu_used'](),'all_children_joined_groups_absent_streams_closed':gone,'CPU6_released':gone,'raw_NMI_IRQ_IRET_kernel_stack_traversal_executed':False,'known_NMI_NULL_native_gap_preserved':True,'default_GCC14_kernel_native_acceptance':False,'canonical_writes':0}
 write(A/'ACTUAL-WHOLE-JOIN.json',out)
 print(json.dumps({k:out[k] for k in ['status','error','last_stage','new_commands','reused_commands','total_bound_commands','seconds','CPU_seconds','CPU6_released']}))
if failure is not None:raise SystemExit(1)
