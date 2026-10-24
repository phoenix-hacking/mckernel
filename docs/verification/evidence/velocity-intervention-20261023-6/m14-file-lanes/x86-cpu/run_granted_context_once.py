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


write=ns['write'];captures=[];objects={};begin=time.monotonic();A=R/'actual-owned-capture-1';os.umask(0o077);A.mkdir(mode=0o700);failure=None
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
try:
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:assert resource.getrlimit(k)==(v,v)
 os.environ['RUST_MIN_STACK']='2097152'
 P=R/'EXECUTABLE-READY.NOT-EXECUTED.json';READY=R/'SOURCE-READY-HANDOFF.json'
 assert sha(P)=='31dcc3f2f36978d174e1109975020a07ef0ccd12569dadeac486f0f26c11faba'
 assert sha(READY)=='63c4f173481454290635ed92df6be19f41eef6e8a596ef0298404e571bd29dfb'
 plan=json.loads(P.read_bytes());assert len(plan['commands'])==13
 frozen=[]
 for key in ('postimages','fixture_sources','tools','actual_witness_header_closure'):
  for row in plan[key].values():
   p=Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],str(p);frozen.append(row)
 for row in [plan['patch'],plan['debug_provider'],plan['profile_derivation'],*plan['accepted_private_base'].values()]:
  assert sha(Path(row['path']))==row['sha256'],row['path'];frozen.append(row)
 # The ready's observed_canonical is historical pre-logger metadata. Root's
 # actual logger integration notice explicitly binds live2d29/26180 instead.
 for rel,key in [('arch/x86_64/kernel/cpu.c','C'),('kernel/rust/x86_cpu_helpers.rs','Rust')]:
  assert sha(Path('/home/holden/mckernel')/rel)==plan['accepted_private_base'][key]['sha256'],rel
 notice=R/'ACTUAL-CPU-LOGGER-CANONICAL-BASE-NOTICE.json';assert sha(notice)=='dbb0b1c7f44ed1be6b378ccfbf2cb393707f3f26768230cbdb2f8f21964e8337'
 write(A/'FROZEN-SOURCES.json',{'rows':frozen,'recipe_sha256':sha(P),'ready_sha256':sha(READY),'root_actual_canonical_base_notice_sha256':sha(notice),'historical_observed_canonical_not_relabelled':plan['observed_canonical'],'driver_sha256':sha(Path(__file__))})
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];assert used<100
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 hv=os.statvfs('/home/holden');sv=os.statvfs('/home/holden/mckernel-work/scratch');bk=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bk.st_size-bk.st_blocks*512)
 fact={'MemAvailable':mem,'memory_required':19<<30,'HOST_available':hv.f_bavail*hv.f_frsize,'HOST_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':sv.f_bavail*sv.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bk.st_size,'backing_device':bk.st_dev,'backing_inode':bk.st_ino,'included_used_percent':used,'aggregate_jobs':7,'root_exclusive_CPU6_grant':True}
 write(A/'ADMISSION.json',fact);assert mem>=fact['memory_required'] and fact['HOST_available']>=fact['HOST_required'] and fact['scratch_available']>=fact['scratch_required']
 write(A/'PROFILE.json',{'scope':__doc__,'CPU':6,'jobs':1,'AS':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE':32<<20,'NOFILE':256,'core':0,'CGU':1,'RUST_MIN_STACK':2097152,'helper_sha256':sha(H),'helper_global_dependencies_checked':True,'TERM_INT_ALRM_registered':True})
 O=R/'output-1';O.mkdir(mode=0o700);os.chdir(R/'fixture');signal.setitimer(signal.ITIMER_REAL,96)
 for i,item in enumerate(plan['commands']):
  left=90-(time.monotonic()-begin);assert left>0 and ns['cpu_used']()<60
  cap=A/item['name'];cap.mkdir(mode=0o700);cmd={'argv':item['argv'],'purpose':item['purpose'],'cwd':str(R/'fixture')};write(cap/'command.json',cmd)
  j=ns['owned_capture'](cmd,cap,left,lambda:None);j['name']=item['name'];write(cap/'whole-join.json',j);captures.append(j)
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  if i in (0,2):
   name='context-logger.o' if i==0 else 'fixture';objects[name]=ns['hashed'](O/name,32<<20);write(A/('DURABLE-'+name+'.json'),{'object':objects[name],'join':j,'hashed_once_before_consumers':True})
 assert (A/'03-actual-C-Rust-context-pairs/stdout').read_text()=='PASS actual_C_Rust_context_logger_direct_pairs=10880 actual_Rust_caller_lock_span_pairs=1360 total=12240 exact_events=9 provider_channels=2 return_values=5\n'
 observation=json.loads((R/'ACTUAL-LEAF-SYMBOL-OBSERVATION.json').read_bytes());assert observation['Rust_unique_T'] and observation['C_selected_U'] and observation['C_fallback_original_T']
 for row in frozen:assert sha(Path(row['path']))==row['sha256'],row['path']
except BaseException as exc:failure=type(exc).__name__+': '+str(exc)
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 gone=all(j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['retirement_error'] is None for j in captures)
 result={'scope':__doc__,'status':'PASS_COMPLETE_CONTEXT_LOG_12240_ACTUAL_C_RUST_AND_ACTUAL_RUST_CALLER_LOCK_SPAN_PAIRS_REAL_HEADER_FALLBACK_PARTIAL_ONLY' if failure is None else 'FAIL_FIRST_UNEXPECTED_STOP_NO_RETRY','error':failure,'completed_commands':len(captures),'captures':captures,'objects':objects,'actual_direct_pairs':10880 if failure is None else None,'actual_Rust_caller_pairs':1360 if failure is None else None,'seconds':time.monotonic()-begin,'CPU_seconds':ns['cpu_used'](),'all_children_joined_groups_absent_streams_closed':gone,'CPU6_released':gone,'formatter_executed':False,'stack_formatter_tested':False,'wholeCPU_fullproduction_defaultlink_native':'OPEN','canonical_writes':0,'compiler_replay_authorized':False}
 write(R/'ACTUAL-CONTEXT-WHOLE-JOIN.json',result);print(json.dumps({k:result[k] for k in ['status','error','completed_commands','seconds','CPU6_released']}))
if failure is not None:raise SystemExit(1)
