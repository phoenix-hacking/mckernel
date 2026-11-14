"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact granted78-input production Rust compile ONCE; read-only NM/readelf afterwards.
No root/Docker/guest/kernel link/canonical/candidate9 mutation.
"""
from pathlib import Path
import ast,hashlib,json,os,re,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent;P=D/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
assert sha(P)=='d34cfadf3107672c46687ca8db898ca7f806beea69bcc3507e5bc9d230324373'
p=json.loads(P.read_text());argv=p['argv'];assert len(argv)==48
assert argv[-12:-4]==['--cfg','native_linux_irq_work_v6_12','--cfg','enable_profile','--cfg','enable_perf','--cfg','enable_rusage']
assert argv[-4:-2]==['-C','codegen-units=1']
assert sha(Path(argv[6]))==p['compiler_sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
assert pin(Path(p['prior_actual_profile']['path']))==p['prior_actual_profile']
assert pin(Path(p['prior_actual_receipt']['path']))==p['prior_actual_receipt']
assert pin(Path(p['source_leaf_review']['path']))==p['source_leaf_review']
assert len(p['source_inputs'])==78
for row in p['source_inputs'].values():assert pin(Path(row['private']['path']))==row['private']
paths={Path(r['private']['path']).resolve() for r in p['source_inputs'].values()}
for row in p['source_inputs'].values():
 path=Path(row['private']['path']);text=path.read_text()
 for rel in re.findall(r'#\[path\s*=\s*"([^\"]+)"\]',text):
  if rel.endswith('mckernel_guest_sysfs.rs'):continue
  assert (path.parent/rel).resolve() in paths
 for macro in ('include!','include_str!','include_bytes!'):assert macro not in text
assert sum('host-kernel/native-rust/' in k for k in p['source_inputs'])==2
assert sum(r['modified_target'] for r in p['source_inputs'].values())==1 and p['source_inputs']['kernel/rust/sched_helpers.rs']['modified_target']
prefix='--emit=obj=';assert argv[-2].startswith(prefix);obj=Path(argv[-2][len(prefix):]);assert obj.parent==D/'fullcrate-preparation-1' and not obj.exists()
assert argv[-1]==str(D/'fullcrate-preparation-1/source/kernel/rust/lib.rs')
assert os.getuid()==os.geteuid()==1000
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert sha(H)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
# Exact live ordinary headroom/floors/full sparse growth before compiler invocation.
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');backing=Path('/home/holden/mckernel-work/scratch.ext4');bs=backing.stat();gap=max(0,bs.st_size-bs.st_blocks*512)
capacity=dict(MemAvailable_bytes=mem,minimum_MemAvailable_bytes=19<<30,HOST_available_bytes=hs.f_bavail*hs.f_frsize,HOST_floor_bytes=16<<30,scratch_available_bytes=ss.f_bavail*ss.f_frsize,scratch_floor_bytes=12<<30,backing_path=str(backing),backing_device=bs.st_dev,backing_inode=bs.st_ino,backing_size=bs.st_size,backing_allocated=bs.st_blocks*512,full_backing_gap_bytes=gap,ordinary_HOST_output_reserve_bytes=128<<20,ordinary_scratch_growth_bytes=0)
assert mem>=19<<30 and capacity['HOST_available_bytes']>=(16<<30)+gap+(128<<20) and capacity['scratch_available_bytes']>=12<<30
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());used=state['last_rate_limits']['primary']['usedPercent'];assert used<100
capacity['included_usage_percent_observed']=used
write(D/'ACTUAL-CAPACITY-BEFORE-COMPILER.json',capacity)
os.chdir(obj.parent);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
limits();profile=dict(scope=__doc__,authority='Parent explicit exact priorproduction78/nightly1.95 grant clarified nightlycompiler;120wall+6 ordinary CPU6 profile',prior_profile=p['prior_actual_profile'],recipe=pin(P),compiler=pin(Path(argv[6])),CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=120,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,RUST_MIN_STACK=2097152,affinity=sorted(os.sched_getaffinity(0)),source_count=78,tools={str(Path(t)):pin(Path(t)) for t in [argv[0],argv[6],'/usr/bin/nm','/usr/bin/readelf']})
write(D/'ACTUAL-FULLCRATE-PROFILE.json',profile)
begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,126)
def capture(name,argv):
 cap=D/name;cap.mkdir(mode=0o700);cmd=dict(argv=argv,purpose=__doc__,cwd=str(Path.cwd()),profile_sha256=sha(D/'ACTUAL-FULLCRATE-PROFILE.json'),extra_environment={'RUST_MIN_STACK':'2097152'});write(cap/'command.json',cmd)
 result=owned_capture(cmd,cap,max(.1,120-(time.monotonic()-begin)),limits);write(cap/'whole-join.json',result)
 assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None and not result['timed_out'],result
 return result
j=capture('actual-fullcrate-compiler-capture-1',argv)
# Hash object once and persist before any postprocessor. Never recompile for observer failure.
compiled=dict(scope=__doc__,status='PASS_COMPILER_DURABLE_ARTIFACT_PENDING_POSTPROCESSORS',profile=pin(D/'ACTUAL-FULLCRATE-PROFILE.json'),compiler_join=j,compiler_invocations=1,object=hashed(obj,32<<20),no_compiler_replay_for_observer=True)
write(D/'COMPILE-OBJECT-RECEIPT.json',compiled)
try:
 n=capture('actual-fullcrate-nm-capture-1',['/usr/bin/nm','-g',str(obj)])
 r=capture('actual-fullcrate-readelf-capture-1',['/usr/bin/readelf','--wide','--syms',str(obj)])
 rows=[line.split() for line in (D/'actual-fullcrate-nm-capture-1/stdout').read_text().splitlines() if line.strip()]
 priorreceipt=json.loads(Path(p['prior_actual_receipt']['path']).read_text());priornm=Path(priorreceipt['nm_command']['path']).parent/'stdout';assert sha(priornm)==json.loads((priornm.parent/'whole-join.json').read_text())['captures']['stdout']['sha256']
 oldrows=[line.split() for line in priornm.read_text().splitlines() if line.strip()]
 oldU={x[-1] for x in oldrows if len(x)>=2 and x[-2]=='U'};newU={x[-1] for x in rows if len(x)>=2 and x[-2]=='U'}
 assert len(oldU)==560 and len(newU)==559 and oldU-newU=={'spin_sleep_or_schedule'} and newU-oldU==set(),(len(oldU),len(newU),oldU-newU,newU-oldU)
 symbols={}
 for name,kind in [('spin_sleep_or_schedule','T'),('sched_spin_sleep_or_schedule_body_result','T'),('get_this_cpu_local_var','T'),('ihk_mc_get_processor_id','T'),('set_timer','T'),('timer_set_timer_body_result','T'),('process_sched_set_timer_bridge','T'),('x86_init_text_end_bridge','T'),('_end','U'),('x86_init_text_map_kernel_start_bridge','T'),('x86_init_normal_set_large_bridge','T'),('x86_map_kernel_start_geometry','U')]:
  found=[x for x in rows if x[-1]==name];assert len(found)==1 and found[0][-2]==kind,(name,found);symbols[name]=found
 assert 'spin_sleep_or_schedule' not in newU and 'process_sched_runqueue_offsets' not in newU
 elfrows=[line.split() for line in (D/'actual-fullcrate-readelf-capture-1/stdout').read_text().splitlines() if line.strip()];elfsymbols={}
 for name in ['spin_sleep_or_schedule','sched_spin_sleep_or_schedule_body_result','get_this_cpu_local_var','ihk_mc_get_processor_id','set_timer','timer_set_timer_body_result']:
  found=[x for x in elfrows if x[-1:]==[name]];assert len(found)==1 and len(found[0])==8 and found[0][3]=='FUNC' and found[0][4]=='GLOBAL' and found[0][6]!='UND' and int(found[0][2])>0,(name,found);elfsymbols[name]=found
 assert all(pin(Path(row['private']['path']))==row['private'] for row in p['source_inputs'].values())
 # Read-only tools must leave object metadata exactly as captured; no second big hash.
 st=obj.stat();assert st.st_size==compiled['object']['size'] and st.st_ino==compiled['object']['inode'] and st.st_dev==compiled['object']['device'] and st.st_mtime_ns==compiled['object']['mtime_ns'] and st.st_ctime_ns==compiled['object']['ctime_ns']
 assert cpu_used()<=60
 result=dict(scope=__doc__,status='PASS_ACTUAL_78INPUT_PRIVATE_PRODUCTION_RUST_OBJECT_ONLY',recipe=pin(P),actual_profile=pin(D/'ACTUAL-FULLCRATE-PROFILE.json'),capacity=pin(D/'ACTUAL-CAPACITY-BEFORE-COMPILER.json'),object=compiled['object'],compiler_invocations=1,compiler_failures=0,observer_failures=0,corrections=0,compiler_seconds=j['seconds'],total_CPU_seconds=cpu_used(),compiler_join=j,nm_join=n,readelf_join=r,symbols=symbols,readelf_GLOBAL_FUNC_definitions=elfsymbols,production_U_delta=dict(before=560,after=559,removed=['spin_sleep_or_schedule'],added=[]),source_count=78,only_actual_Rust_source_delta='kernel/rust/sched_helpers.rs',all_source_inputs_unchanged=True,object_hashed_once_before_observers=True,CPU6_released=True,canonical_candidate9_changes=0,whole_C_TU_default_link_native='OPEN')
 write(D/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json',result);print(json.dumps(dict(status=result['status'],compiler_seconds=j['seconds'],receipt=pin(D/'ACTUAL-PRODUCTION-FULLCRATE-RECEIPT.json'),CPU6_released=True)))
except BaseException as exc:
 write(D/'OBSERVER-FAILURE-1.json',dict(scope=__doc__,status='FAIL_OBSERVER_COMPILER_OBJECT_RETAINED_NO_REPLAY',error=type(exc).__name__+': '+str(exc),object=compiled['object'],compiler_invocations=1));raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
