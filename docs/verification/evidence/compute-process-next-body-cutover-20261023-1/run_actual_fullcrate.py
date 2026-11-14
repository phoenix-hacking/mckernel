"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact granted78-input production Rust object compile ONCE, then read-only symbols.
No root, image, Docker, guest, kernel link or canonical mutation.
"""
from pathlib import Path
import ast,hashlib,json,os,re,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
P=D/'NEXT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)=='295d258e7c22789993770d6b155c21dfc16863179d992d92405aa6792b4790d3'
p=json.loads(P.read_text());argv=p['argv'];assert len(argv)==48
assert argv[-12:-4]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage']
assert argv[-4:-2]==['-C','codegen-units=1']
assert sha(Path(argv[6]))=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
assert len(p['source_inputs'])==78
for row in p['source_inputs'].values():assert sha(Path(row['private']['path']))==row['private']['sha256']
paths={Path(r['private']['path']).resolve() for r in p['source_inputs'].values()}
for row in p['source_inputs'].values():
 path=Path(row['private']['path']);text=path.read_text()
 for rel in re.findall(r'#\[path\s*=\s*"([^\"]+)"\]',text):
  if rel.endswith('mckernel_guest_sysfs.rs'):continue
  assert (path.parent/rel).resolve() in paths
 for macro in ('include!','include_str!','include_bytes!'):assert macro not in text
assert sum('host-kernel/native-rust/' in key for key in p['source_inputs'])==2
# Parse/qualify the exact output before spending any compiler work.
emit=argv[-2];prefix='--emit=obj=';assert emit.startswith(prefix)
obj=Path(emit[len(prefix):]);assert obj.is_absolute() and obj.parent==D/'fullcrate-preparation-1' and not obj.exists()
assert argv[-1]==str(D/'fullcrate-preparation-1/source/kernel/rust/lib.rs')
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
assert os.getuid()==os.geteuid()==1000
os.chdir(obj.parent);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for kind,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(kind,(value,value))
limits()
profile={'scope':__doc__,'authority':'Parent exact295d258e recipe grant; identical accepted textend0997/textmapf601 nightly1.95/CGU1/4cfg/2external-module ordinary profile','recipe_sha256':sha(P),'prior_actual_profile_recipe':p['prior_exact_profile'],'CPU':6,'jobs':1,'AS_bytes':2<<30,'CPU_seconds':60,'wall_seconds':90,'retirement_seconds':6,'FSIZE_bytes':32<<20,'NOFILE':256,'core':0,'RUST_MIN_STACK':2097152,'compiler':{'path':argv[6],'sha256':sha(Path(argv[6]))},'affinity_observed':sorted(os.sched_getaffinity(0)),'source_count':78}
write(D/'ACTUAL-FULLCRATE-PROFILE.json',profile)
cap=D/'actual-fullcrate-compiler-capture-1';cap.mkdir(mode=0o700);cmd={'argv':argv,'purpose':__doc__,'cwd':str(Path.cwd()),'profile':profile,'extra_environment':{'RUST_MIN_STACK':'2097152'}};write(cap/'command.json',cmd)
begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96)
j=owned_capture(cmd,cap,90,limits);j['profile_sha256']=sha(D/'ACTUAL-FULLCRATE-PROFILE.json');write(cap/'whole-join.json',j)
if not(j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error']):
 write(D/'ACTUAL-FULLCRATE-RESULT.json',{'scope':__doc__,'status':'FAIL_COMPILER_PRESERVED_STOP','profile':profile,'join':j});raise SystemExit(1)
# Durable compiler/object receipt precedes every symbol observer operation.
compiled={'scope':__doc__,'status':'PASS_COMPILE_ARTIFACT_RETAINED_PENDING_SYMBOLS','profile':profile,'compiler_join':j,'object':hashed(obj,32<<20),'compiler_invocations':1,'artifact_not_to_be_recompiled_for_observer_failure':True}
write(D/'COMPILE-OBJECT-RECEIPT.json',compiled)
cap=D/'actual-fullcrate-nm-capture-1';cap.mkdir(mode=0o700);cmd={'argv':['/usr/bin/nm','-g',str(obj)],'purpose':__doc__,'profile_sha256':sha(D/'ACTUAL-FULLCRATE-PROFILE.json')};write(cap/'command.json',cmd)
n=owned_capture(cmd,cap,max(0.1,90-(time.monotonic()-begin)),limits);write(cap/'whole-join.json',n);assert n['returncode']==0 and n['direct_child_joined'] and n['group_absent'] and n['closed_streams'] and not n['error'] and not n['retirement_error']
rows=[line.split() for line in (cap/'stdout').read_text().splitlines()];symbols={}
for name,kind in [('set_timer','T'),('timer_set_timer_body_result','T'),('process_sched_set_timer_bridge','T'),('get_this_cpu_local_var','T'),('time_sharing','U'),('process_timer_runtime_offsets','U'),('process_timer_spin_lock_bridge','U'),('process_timer_spin_unlock_bridge','U'),('process_timer_lapic_enable_bridge','U'),('process_timer_lapic_disable_bridge','U'),('x86_init_text_end_bridge','T'),('_end','U'),('x86_init_text_map_kernel_start_bridge','T'),('x86_init_normal_set_large_bridge','T'),('x86_map_kernel_start_geometry','U')]:
 matches=[row for row in rows if row and row[-1]==name];assert len(matches)==1 and matches[0][-2]==kind,matches;symbols[name]=matches
undefined_count=sum(row[-2]=='U' for row in rows if len(row)>=2)
assert undefined_count==597,undefined_count
assert cpu_used()<=60
signal.setitimer(signal.ITIMER_REAL,0)
assert sha(obj)==compiled['object']['sha256']
assert all(sha(Path(r['private']['path']))==r['private']['sha256'] for r in p['source_inputs'].values())
write(D/'ACTUAL-FULLCRATE-RESULT.json',{'scope':__doc__,'status':'PASS_ACTUAL_78INPUT_PRIVATE_PRODUCTION_RUST_OBJECT_ONLY','profile':profile,'source_inputs_unchanged':True,'object':compiled['object'],'symbols':symbols,'undefined_count':undefined_count,'total_CPU_seconds':cpu_used(),'compiler_join':j,'nm_join':n,'compiler_invocations':1,'compiler_failures':0,'observer_failures':0,'canonical_existing_bridge_exports_preserved':True,'default_kernel_link':False,'native':False,'whole_file_retirement':False,'CPU6_released':True})
print('PASS exact78-input production Rust object: one set_timer T/no U; actual currentCPU/timer T, descriptor/fourcallbacks/time_sharing U; prior memory exports retained; 597 U; compiled once; CPU6 released')
