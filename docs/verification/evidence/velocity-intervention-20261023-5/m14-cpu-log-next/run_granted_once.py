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

write=ns['write'];captures=[];begin=time.monotonic();A=R/'actual-owned-capture-1';os.umask(0o077);A.mkdir(mode=0o700);failure=None;objects={}
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
try:
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
 assert Path(sys.executable).resolve()==Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2]==(3,9)
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:assert resource.getrlimit(k)==(v,v)
 os.environ['RUST_MIN_STACK']='2097152'
 P=R/'EXECUTABLE-READY.NOT-EXECUTED.json';assert sha(P)=='a24b187be9ffffa580197a41a792b8ccff33e26e37bd0535044d7707c403ffe4'
 ready=R/'SOURCE-READY-HANDOFF.json';assert sha(ready)=='73183082745278bf72e5c0bf62a8c54a6967c0f0484c0aa6348da20c2e3ca732'
 plan=json.loads(P.read_bytes());assert len(plan['commands'])==13
 frozen=[]
 for key in ('preimages','postimages','fixture_sources','header_closure','tools'):
  for row in plan[key].values():
   p=Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],str(p)
   frozen.append(row)
 for row in [plan['patch'],plan['existing_kprintf_provider'],plan['profile_derivation']]:
  assert sha(Path(row['path']))==row['sha256'];frozen.append(row)
 write(A/'FROZEN-SOURCES.json',{'rows':frozen,'recipe_sha256':sha(P),'ready_sha256':sha(ready),'driver_sha256':sha(Path(__file__))})
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent'];assert used<100
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 hv=os.statvfs('/home/holden');sv=os.statvfs('/home/holden/mckernel-work/scratch');bk=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bk.st_size-bk.st_blocks*512)
 fact={'scope':__doc__,'MemAvailable':mem,'memory_required':19<<30,'HOST_available':hv.f_bavail*hv.f_frsize,'HOST_required':(16<<30)+gap+(128<<20)+679477248,'scratch_available':sv.f_bavail*sv.f_frsize,'scratch_required':(12<<30)+679477248,'full_sparse_gap':gap,'backing_size':bk.st_size,'backing_device':bk.st_dev,'backing_inode':bk.st_ino,'included_used_percent':used,'aggregate_jobs':7,'CPU6_root_exclusive_grant':True}
 write(A/'ADMISSION.json',fact);assert mem>=fact['memory_required'] and fact['HOST_available']>=fact['HOST_required'] and fact['scratch_available']>=fact['scratch_required']
 write(A/'PROFILE.json',{'scope':__doc__,'CPU':6,'jobs':1,'AS':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE':32<<20,'NOFILE':256,'core':0,'CGU':1,'RUST_MIN_STACK':2097152,'helper_sha256':sha(H),'all_helper_LOAD_GLOBAL_dependencies_checked':True,'TERM_INT_ALRM_registered_before_first_child':True})
 O=R/'output-1';O.mkdir(mode=0o700);os.chdir(R/'fixture');signal.setitimer(signal.ITIMER_REAL,96)
 for i,item in enumerate(plan['commands']):
  remaining=90-(time.monotonic()-begin);assert remaining>0 and ns['cpu_used']()<60
  cap=A/item['name'];cap.mkdir(mode=0o700);command={'argv':item['argv'],'purpose':item['purpose'],'cwd':str(R/'fixture')};write(cap/'command.json',command)
  j=ns['owned_capture'](command,cap,remaining,lambda:None);j['name']=item['name'];write(cap/'whole-join.json',j);captures.append(j)
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  if i in (0,2):
   name='logger.o' if i==0 else 'fixture';objects[name]=ns['hashed'](O/name,32<<20);write(A/('DURABLE-'+name+'.json'),{'object':objects[name],'join':j,'before_consumers':True})
 assert (A/'03-functional-original-C-Rust-6800pairs/stdout').read_text()=='PASS original_C_actual_Rust_ulong_log_pairs=6800 printed=2040 unknown_noops=4760 values=136 events=10 kprintf_returns=5 exact_formats=3\n'
 observation=json.loads((R/'ACTUAL-LEAF-SYMBOL-OBSERVATION.json').read_bytes());assert observation['Rust_one_T'] and observation['selected_C_U'] and observation['fallback_C_static_t']
 for row in frozen:assert sha(Path(row['path']))==row['sha256'],row['path']
except BaseException as exc:failure=type(exc).__name__+': '+str(exc)
finally:
 signal.setitimer(signal.ITIMER_REAL,0)
 gone=all(j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['retirement_error'] is None for j in captures)
 receipt={'scope':__doc__,'status':'PASS_ACTUAL_CPU_ULONG_LOG_6800_VARIADIC_TAPE_PAIRS_AND_REAL_HEADER_SELECTED_FALLBACK_PARTIAL_ONLY' if failure is None else 'FAIL_FIRST_UNEXPECTED_STOP_NO_RETRY','error':failure,'completed_commands':len(captures),'actual_pairs':6800 if failure is None else None,'captures':captures,'objects':objects,'seconds':time.monotonic()-begin,'CPU_seconds':ns['cpu_used'](),'all_children_joined_groups_absent_streams_closed':gone,'CPU6_released':gone,'actual_formatter_executed':False,'whole_production_Rust_current_CPU_TU_defaultlink_native':'OPEN','canonical_writes':0,'compiler_replay_authorized':False}
 write(R/'ACTUAL-CPU-LOG-WHOLE-JOIN.json',receipt);print(json.dumps({k:receipt[k] for k in ['status','error','completed_commands','actual_pairs','seconds','CPU6_released']}))
if failure is not None:raise SystemExit(1)
