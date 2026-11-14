"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual selected C/Rust full entry comparisons with HOST modeled CPU/MSR callbacks;
real header, complete selected GCC9 CPU TU and inert partial link, no native effects.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,stat,subprocess,time,sys,re
B=Path(__file__).resolve().parent.parent;H=B/'sourcehandoff';RF=H/'EXACT-ORDINARY-FIXTURE-AND-CONSUMER.NOT-GRANTED.json'
records=[];started=False;durable={}
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def initial_write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True);f.write(chr(10))
def nmrows(t):return [l.split() for l in t.splitlines() if l.split()]
def unique(rows,name,kinds):
 found=[r for r in rows if r[-1]==name];assert len(found)==1 and found[0][-2] in kinds,(name,kinds,found);return found[0]
try:
 assert pin(RF)['sha256']=='38011edaaafb6814f9ac9b01fbd674b1a5172f6cb83a82416ee8f0a4aeafaefe'
 recipe=json.loads(RF.read_text());assert pin(Path(recipe['source_bindings']['path']))==recipe['source_bindings'];binding=json.loads(Path(recipe['source_bindings']['path']).read_text())
 for row in [*binding['preimages'].values(),*binding['postimages'].values(),binding['patch'],*recipe['fixture_sources'].values(),*recipe['tools'].values(),*recipe['header_closure'].values(),*recipe['actual_C_profile_derivation'].values()]:
  if isinstance(row,dict) and 'path' in row:assert pin(Path(row['path']))==row,row['path']
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:2]==(3,9)
 # Source-only preflight for the previous hosted memset failure family. The
 # fixture uses the host standard headers; no kernel include directory/macro.
 hosted=recipe['commands'][1]['argv'];assert '-nostdinc' not in hosted and not any(v.startswith('-I') or v.startswith('-D') for v in hosted)
 fixture=(B/'fixture/compare_entry.c').read_text();constants=(B/'fixture/actual_msr_constants.h').read_text()
 assert '#include <string.h>' in fixture and '__inline_memset' not in fixture and '#define memset' not in fixture
 assert all(not l.startswith('#include') for l in constants.splitlines())
 initial_write(H/'HOSTED-MEMSET-SOURCE-PREFLIGHT.json',dict(scope=__doc__,status='PASS_HOST_STANDARD_STRING_HEADER_NO_KERNEL_MACRO',hosted_compile_argv=hosted,fixture=pin(B/'fixture/compare_entry.c'),constant_header=pin(B/'fixture/actual_msr_constants.h'),before_any_child=True))
 helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert pin(helper)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)]
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 def globals_used(code):
  used={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for value in code.co_consts:
   if isinstance(value,type(code)):used.update(globals_used(value))
  return used
 deps=set()
 for name in names:deps.update(globals_used(ns[name].__code__))
 assert not deps-set(ns)-set(vars(builtins))
 initial_write(H/'HELPER-GLOBAL-DEPENDENCY-CHECK.json',dict(scope=__doc__,helper=pin(helper),dependencies=sorted(deps),missing=[],Python_executable=sys.executable,Python_version=sys.version,dict_API=True,before_any_child=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 initial_write(H/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O=B/'output-1';O.mkdir(mode=0o700);CAP=H/'actual-first-candidate-capture-1';CAP.mkdir(mode=0o700);os.chdir(O);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=__doc__,authority='Root explicit one exclusive CPU6 firstcandidate38011eda/53bf6482/02d4bdea/independentSOURCE_ABI_PASS; no replay after unexpected failure',CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152,recipe=pin(RF),driver=pin(Path(__file__)))
 initial_write(H/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 observations={}
 for command in recipe['commands']:
  cap=CAP/command['name'];cap.mkdir(mode=0o700);cmd=dict(scope=recipe['scope'],purpose=command['purpose'],argv=command['argv'],cwd=command['cwd'],profile=pin(H/'ACTUAL-PROFILE.json'));initial_write(cap/'command.json',cmd)
  remaining=90-(time.monotonic()-begin);assert remaining>0
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);initial_write(cap/'whole-join.json',j);records.append(dict(name=command['name'],command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  name=command['name'];text=(cap/'stdout').read_text()
  for label,filename,trigger in [('Rust_leaf','actual-entry.o','00-actual-Rust-entry-body-compile'),('C_complete','cpu.c.o','05-complete-selected-cpu-TU-compile'),('partial','cpu-rust-partial.o','08-selected-complete-cpu-entry-partial-link')]:
   if name==trigger:
    durable[label]=ns['hashed'](O/filename,32<<20);initial_write(H/('DURABLE-'+label+'-OBJECT.json'),dict(scope=recipe['scope'],object=durable[label],join=records[-1]))
  if name=='03-functional-original-C-Rust-entry-pairs':assert 'PASS actual_selected_C_Rust_entry_pairs=18432 original_fallback_Rust_pairs=18432 missing_callback_masks=15' in text
  if name=='06-selected-complete-cpu-symbols':
   rows=nmrows(text);unique(rows,'init_pstate_and_turbo',{'U'})
   for callback in recipe['expected_symbols']['C_bridge_providers']:unique(rows,callback,{'T'})
   data=unique(rows,'no_turbo',{'D'});assert int(data[-3],16)==4
  if name=='07-leaf-Rust-symbols':
   rows=nmrows(text);unique(rows,'init_pstate_and_turbo',{'T'});unique(rows,'x86_init_pstate_turbo_body_result',{'T'})
  if name=='09-partial-entry-symbols':
   rows=nmrows(text);unique(rows,'init_pstate_and_turbo',{'T'});unique(rows,'x86_init_pstate_turbo_body_result',{'T'})
   for callback in recipe['expected_symbols']['C_bridge_providers']:unique(rows,callback,{'T'})
  observations[name]=dict(stdout=j['captures']['stdout'])
 for row in durable.values():
  st=Path(row['path']).stat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)==(row['device'],row['inode'],row['size'],row['mtime_ns'],row['ctime_ns'])
 assert all(pin(Path(row['path']))==row for row in binding['postimages'].values()) and ns['cpu_used']()<=60
 result=dict(scope=recipe['scope'],status='PASS_ACTUAL_PSTATE_ENTRY_C_RUST_PARITY_SELECTED_COMPLETE_GCC9_CPU_TU_HEADER_ABI_PARTIAL_LINK_ONLY',recipe=pin(RF),source_binding=pin(Path(recipe['source_bindings']['path'])),records=records,objects=durable,actual_selected_C_Rust_pairs=18432,actual_original_fallback_Rust_pairs=18432,fallback_CPUID_KVM_MSR_primitives_modeled=True,missing_callback_masks=15,remaining_C_callbacks=4,header_closure=len(recipe['header_closure']),C_complete_TU=True,GCC9=True,unique_Rust_entry_partial_link=True,compiler_Rust_leaf_invocations=1,C_compiler_invocations=3,total_CPU_seconds=ns['cpu_used'](),seconds=time.monotonic()-begin,CPU6_released=True,canonical_mutations=0,full_production_Rust_crate=False,default_GCC14_kernel_link=False,native=False,file_retired=False)
 initial_write(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 initial_write(H/'FIRST-CANDIDATE-FAILURE-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_FAILURE_NO_RETRY',error=type(exc).__name__+': '+str(exc),records=records,objects_retained=durable,CPU6_released=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
