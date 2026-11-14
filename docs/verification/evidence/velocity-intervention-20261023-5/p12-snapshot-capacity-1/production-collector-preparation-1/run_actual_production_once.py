"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted one static collector production build and controlled terminal body checks.
Never executes the production init, accesses host kernel log, or starts guest work.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,stat,subprocess,sys,time
D=Path(__file__).resolve().parent;records=[];started=False;elf=None
RF=D/'EXACT-PRODUCTION-BUILD.GRANTED.json'
def pin(path):
 data=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
def write(path,value):
 with path.open('x') as f:json.dump(value,f,sort_keys=True);f.write('\n')
def identity(path):
 s=path.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
 return dict(path=str(path),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)),nlink=s.st_nlink,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
try:
 assert pin(RF)['sha256']=='96070b271f6978682cc89858507780393e63db1b9dbba96d4e2181281619582c'
 plan=json.loads(RF.read_bytes());assert len(plan['commands'])==17
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version.startswith('3.9.12 ')
 helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert pin(helper)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)]
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 def dependencies(code):
  out={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for c in code.co_consts:
   if isinstance(c,type(code)):out.update(dependencies(c))
  return out
 deps=set()
 for name in names:deps.update(dependencies(ns[name].__code__))
 assert not deps-set(ns)-set(vars(builtins))
 for row in plan['source_closure'].values():
  for key in ['accepted_preimage','selected','materialized']:assert pin(Path(row[key]['path']))==row[key]
 for key in ['accepted_production_plan','accepted_production_artifact','accepted_source_consumer','strict_preservation','patch','accepted_archive_identity','terminal_actual_body','terminal_fixture']:assert pin(Path(plan[key]['path']))==plan[key]
 src=(D/'production-source/pair_collector.c').read_text();body=(D/'terminal-capture.ACTUAL-BODY.inc').read_text();fixture=(D/'fixture_terminal_capture.c').read_text();assert src.count(body)==1 and fixture.count(body)==1 and '#include <stdlib.h>' in fixture and 'calloc(1048576u,1u)' in fixture
 assert len(plan['source_closure'])==17 and sum(r['unchanged'] for r in plan['source_closure'].values())==14
 assert not any('FIXTURE' in a or '-DTEST' in a for a in plan['commands'][0]['argv'])
 archive=Path(plan['Rust_archive_reuse']['path']);retained=json.loads(Path(plan['accepted_archive_identity']['path']).read_bytes());pre=identity(archive);assert pre=={k:v for k,v in retained.items() if k!='sha256'} and retained['sha256']==plan['Rust_archive_reuse']['expected_sha256']
 write(D/'REUSED-RUST-ARCHIVE.IDENTITY.json',dict(accepted_identity=plan['accepted_archive_identity'],actual_prebuild_stat=pre,expected_sha256=retained['sha256'],content_rehashes=0,Rust_compiler_invocations=0))
 write(D/'HELPER-INTERPRETER-PROVIDER.PREFLIGHT.json',dict(scope=plan['scope'],helper=pin(helper),namespace_dict_API=True,dependencies=sorted(deps),missing_globals=[],interpreter=sys.executable,version=sys.version,terminal_exact_body=plan['terminal_actual_body'],controlled_terminal_provider=True,actual_init_execution=False,before_any_child=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(D/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 assert not (D/'pair-long-collector').exists();CAP=D/'captures';CAP.mkdir(mode=0o700);(D/'terminal-cases').mkdir(mode=0o700)
 initial_cwd=os.getcwd();os.sched_setaffinity(0,{6})
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
 write(D/'ACTUAL-PROFILE.json',dict(scope=plan['scope'],recipe=pin(RF),driver=pin(Path(__file__)),CPU=[6],jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,stack_bytes=2<<20,GCC9='/usr/bin/gcc-9',Rust_archive_reused=retained['sha256'],first_unexpected_failure='STOP_NO_RETRY'))
 begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True;reads={}
 for operation in plan['commands']:
  label=operation['label'];command=dict(operation);command.pop('label');create=command.pop('create_fresh_cwd',False);env=command.pop('env_binding',{})
  if create:Path(command['cwd']).mkdir(mode=0o700)
  cap=CAP/label;cap.mkdir(mode=0o700);prior=os.getcwd();previous_env={k:os.environ.get(k) for k in env}
  try:
   os.chdir(command['cwd']);command['actual_cwd']=os.getcwd();assert command['actual_cwd']==command['cwd'];os.environ.update(env)
   write(cap/'command.json',command);remaining=90-(time.monotonic()-begin);assert remaining>0
   joined=ns['owned_capture'](command,cap,remaining,lambda:None);write(cap/'whole-join.json',joined);records.append(dict(label=label,capture=str(cap),command=pin(cap/'command.json'),whole_join=joined))
  finally:
   os.chdir(prior)
   for key,value in previous_env.items():
    if value is None:os.environ.pop(key,None)
    else:os.environ[key]=value
   write(cap/'CWD-RESTORED.json',dict(child_cwd=command['cwd'],restored_cwd=os.getcwd(),restored=os.getcwd()==prior))
  assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None and not joined['timed_out'],dict(label=label,join=joined)
  reads[label]=(cap/'stdout').read_text()
  if label=='production-static-LONG-ELF':
   elf=ns['hashed'](D/'pair-long-collector',32<<20)
   write(D/'ACTUAL-COMPILED-ELF.DURABLE.json',dict(scope=plan['scope'],status='ACTUAL_PRODUCTION_STATIC_ELF_COMPILED_OBSERVERS_PENDING',artifact=elf,source_closure=plan['source_closure'],compile_whole_join=joined,production_flags=command['argv'],native_execution=False,Rust_archive_reused=retained))
  if label=='ELF-symbols':
   symbols={}
   for line in reads[label].splitlines():
    f=line.split()
    if len(f)>=3:symbols.setdefault(f[-1],[]).append(f[-2])
   for symbol in plan['required_actual_output_checks']['unique_Rust_exports']:assert symbols.get(symbol)==['T'],symbol
   for symbol in plan['required_actual_output_checks']['real_production_callbacks_present']:assert symbols.get(symbol)==['t'],symbol
  if label=='ELF-undefined':assert not reads[label].strip()
  if label=='ELF-headers':
   h=reads[label];assert 'ELF64' in h and 'EXEC (Executable file)' in h and 'Advanced Micro Devices X86-64' in h and 'INTERP' not in h and 'There is no dynamic section' in h
  if label=='unchanged-strict-full-consumer':assert 'PASS_ACTUAL_FINAL_GATE_AND_DEFAULT_WORKSPACE_FULL_LONG_CONSUMER' in reads[label]
  if label.startswith('terminal-') and not label.startswith('terminal-compile-'):assert reads[label].startswith('PASS ACTUAL_TERMINAL_BODY CONTROLLED ')
  assert ns['cpu_used']()<=60
 post=identity(archive);assert pre==post;assert len(records)==17 and os.getcwd()==initial_cwd
 for row in plan['source_closure'].values():assert pin(Path(row['materialized']['path']))==row['materialized']
 result=dict(scope=plan['scope'],status='PASS_ACTUAL_PRODUCTION_STATIC_ELF_AND_UNCHANGED_CONSUMER_AND_10_CONTROLLED_TERMINAL_BODY_CASES',recipe=pin(RF),profile=pin(D/'ACTUAL-PROFILE.json'),source_closure=plan['source_closure'],actual_ELF=elf,commands=records,Rust_archive_pre=pre,Rust_archive_post=post,Rust_archive_accepted_sha256=retained['sha256'],Rust_archive_content_rehashes=0,Rust_compiler_invocations=0,GCC9_compiler_invocations=3,terminal_actual_body=plan['terminal_actual_body'],terminal_controlled_cases=10,terminal_caps_and_production_body_unchanged=True,stdlib_header_included=True,terminal_live_klog_calls=0,strict_gates_unchanged=plan['strict_preservation'],seconds=time.monotonic()-begin,total_CPU_seconds=ns['cpu_used'](),CPU6_released=True,native_ELF_execution=False,old_protocol_consumer_TESTONLY_controlled_derivatives=True,native_or_LONG_credit=0,actual_capsule=None,actual_runtime_release=None,independent_artifact_acceptance=None,round90_retirement='UNKNOWN_ACTUAL_BUFFER_NOT_EXPORTED')
 write(D/'ACTUAL-PRODUCTION-WHOLE-JOIN.json',result)
 print(json.dumps(dict(status=result['status'],receipt=pin(D/'ACTUAL-PRODUCTION-WHOLE-JOIN.json'),actual_ELF=elf,commands=len(records),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 write(D/'FAILURE-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_FAILURE_NO_RETRY',error=type(exc).__name__+': '+str(exc),records=records,actual_ELF=elf,CPU6_released=all(r['whole_join']['direct_child_joined'] and r['whole_join']['group_absent'] and r['whole_join']['closed_streams'] for r in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
 if 'initial_cwd' in globals():os.chdir(initial_cwd)
