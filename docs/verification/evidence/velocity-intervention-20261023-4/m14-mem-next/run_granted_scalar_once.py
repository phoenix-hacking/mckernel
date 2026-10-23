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
write=ns['write'];captures=[];begin=time.monotonic();A=R/'actual-owned-capture-1'
os.umask(0o077);A.mkdir(mode=0o700);failure=None
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
try:
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:
  assert resource.getrlimit(k)==(v,v),(k,resource.getrlimit(k))
 os.environ['RUST_MIN_STACK']='2097152'
 P=R/'EXACT-SINGLE-ENTRY-RECIPE.CURRENT-WALK-CONSUMER.NOT-EXECUTED.json';assert sha(P)=='f0e9110d04534a777b1851de6d0a69d5060af1a8aa88492d1ac3136162656c09'
 plan=json.loads(P.read_bytes());assert len(plan['commands'])==15
 ready=R/'ROOTREADY-CURRENT-WALK-CONSUMER.json';assert sha(ready)=='d1d26f603c5a6db3fe8f43ff997bd921b254e81bb31f9a3f1a37f2e65b32c3eb'
 frozen=[]
 for key in ('preimages','postimages','fixture_sources','header_config_closure','tools'):
  for row in plan[key].values():
   p=Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],str(p)
   frozen.append(row)
 for row in (plan['actual_C_consumer']['source'],plan['actual_C_consumer']['retained_complete_GCC9_receipt']):
  assert sha(Path(row['path']))==row['sha256'];frozen.append(row)
 obj=plan['actual_C_consumer']['retained_object_not_rehashed'];st=Path(obj['path']).lstat()
 for key,attr in [('device','st_dev'),('inode','st_ino'),('uid','st_uid'),('gid','st_gid'),('nlink','st_nlink'),('size','st_size'),('mtime_ns','st_mtime_ns'),('ctime_ns','st_ctime_ns')]:assert obj[key]==getattr(st,attr),(key,obj[key],getattr(st,attr))
 assert obj['mode']==oct(stat.S_IMODE(st.st_mode))
 attr=R/'CURRENT78-COHERENCE.PROCESS-SUCCESSOR.ATTRIBUTION-ONLY.json';at=json.loads(attr.read_bytes())
 for rel,h,size in at['canonical_rows']:
  p=Path('/home/holden/mckernel')/rel;assert p.stat().st_size==size and sha(p)==h,rel
 write(A/'FROZEN-SOURCES.json',{'source_rows':frozen,'attribution':{'path':str(attr),'sha256':sha(attr)},'recipe':{'path':str(P),'sha256':sha(P)},'retained_object_stat_only':obj,'driver':{'path':str(Path(__file__)),'sha256':sha(Path(__file__))}})
 state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());used=state['last_rate_limits']['primary']['usedPercent'];assert used<100
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 hv=os.statvfs('/home/holden');sv=os.statvfs('/home/holden/mckernel-work/scratch');back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512)
 facts={'scope':__doc__,'MemAvailable':mem,'required_memory':19<<30,'host_available':hv.f_bavail*hv.f_frsize,'host_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':sv.f_bavail*sv.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':back.st_size,'backing_dev':back.st_dev,'backing_inode':back.st_ino,'included_used_percent':used,'root_CPU6_exclusive_grant':True,'aggregate_budget_jobs':7,'aggregate_budget_bytes':19<<30}
 write(A/'ADMISSION.json',facts)
 assert mem>=facts['required_memory'] and facts['host_available']>=facts['host_required'] and facts['scratch_available']>=facts['scratch_required']
 write(A/'PROFILE.json',{'scope':__doc__,'CPU':6,'AS':2<<30,'CPU':6,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE':32<<20,'NOFILE':256,'core':0,'CGU':1,'RUST_MIN_STACK':2097152,'helper_sha256':sha(H),'all_helper_LOAD_GLOBAL_dependencies_checked':True,'TERM_INT_ALRM_registered_before_first_child':True})
 O=R/'output-1';O.mkdir(mode=0o700)
 signal.setitimer(signal.ITIMER_REAL,96)
 for i,item in enumerate(plan['commands']):
  assert ns['cpu_used']()<60
  remaining=90-(time.monotonic()-begin);assert remaining>0
  cap=A/item['name'];cap.mkdir(mode=0o700);command={'argv':item['argv'],'purpose':item['purpose']};write(cap/'command.json',command)
  result=ns['owned_capture'](command,cap,remaining,lambda:None);result['name']=item['name'];write(cap/'whole-join.json',result);captures.append(result)
  assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and not result['timed_out'],result
  if i==0:write(A/'DURABLE-RUST-OBJECT.json',{'object':ns['hashed'](O/'single-entry.o',32<<20),'compiler_join':result,'before_observers':True})
 for row in frozen:assert sha(Path(row['path']))==row['sha256'],row['path']
 assert '4896' in (A/plan['commands'][3]['name']/'stdout').read_text()
 observation=json.loads((R/'ACTUAL-ABI-CONSUMER-OBSERVATION.json').read_bytes())
 assert observation['actual_ABI_words']==5 and observation['Rust_entry_one_T'] and observation['actual_C_pt_split_consumer_scalar_U_resolved_by_Rust']
except BaseException as exc:
 failure=type(exc).__name__+': '+str(exc)
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 joined=all(r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['retirement_error'] is None for r in captures)
 receipt={'scope':__doc__,'status':'PASS_ACTUAL_SCALAR_4896_PAIRS_FIVE_ABI_WORDS_AND_CURRENT_WALK_CONSUMER_PARTIAL_LINK_ONLY' if failure is None else 'FAIL_STOPPED_NO_RETRY','error':failure,'completed_commands':len(captures),'actual_pairs':4896 if failure is None else None,'actual_ABI_words':5 if failure is None else None,'captures':captures,'seconds':time.monotonic()-begin,'total_CPU_seconds':ns['cpu_used'](),'all_children_joined_groups_absent_streams_closed':joined,'CPU6_released':joined,'remaining_C_callbacks':13,'whole_production_Rust_current_C_TU_exactGCC14_defaultkernel_native':'OPEN','canonical_writes':0,'compiler_replay_authorized':False}
 write(R/'ACTUAL-SCALAR-WHOLE-JOIN.json',receipt)
 print(json.dumps({k:receipt[k] for k in ['status','error','completed_commands','actual_pairs','seconds','CPU6_released']}))
if failure is not None:raise SystemExit(1)
