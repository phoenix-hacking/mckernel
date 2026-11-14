"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded remaining8 header-transport correction. Prior4005 actual cases reused, never rerun.
Controlled host callbacks only; no root/Docker/guest/canonical changes.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,re,resource,signal,stat,sys,time
N=Path(__file__).resolve().parent;D=N.parent;F=D/'fixture';A=N/'actual-remaining8-1';A.mkdir(mode=0o700);RF=N/'EXACT-REMAINING8.HEADER-TRANSPORT.NOT-GRANTED.json'
records=[];armed=False;initial=os.getcwd()
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True);f.write('\n')
try:
 assert pin(RF)['sha256']=='b6d770bef98954133581f4d27a7eab541fb1050a1872119df3b904792d807dc1';plan=json.loads(RF.read_bytes())
 assert pin(D/'sourcehandoff/IMPLEMENTATION-AND-FIXTURE.READY.json')['sha256']=='60d3d3206305543755ec5009a5caf3e6d270e96a5857d88bb716012422f27818'
 def meta(p):
  z=p.lstat();assert stat.S_ISREG(z.st_mode) and z.st_nlink==1
  return dict(path=str(p),device=z.st_dev,inode=z.st_ino,uid=z.st_uid,gid=z.st_gid,mode=oct(stat.S_IMODE(z.st_mode)),nlink=z.st_nlink,size=z.st_size,mtime_ns=z.st_mtime_ns,ctime_ns=z.st_ctime_ns)
 for row in plan['retained_artifact_identities']:assert meta(Path(row['path']))==row
 for row in plan['retained_prior_captures']:assert pin(Path(row['path']))==row
 for key in ['canonical','private']:assert pin(Path(plan['header_transport'][key]['path']))==plan['header_transport'][key]

 for row in [*plan['source_inputs'].values(),*plan['unchanged_boundary_headers'].values(),plan['GCC9_profile_reused'],plan['Rust192_profile_reused']]:assert pin(Path(row['path']))==row
 assert len(plan['commands'])==8 and os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version.startswith('3.9.12 ')
 helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert pin(helper)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)];ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 def deps(code):
  found={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for c in code.co_consts:
   if isinstance(c,type(code)):found.update(deps(c))
  return found
 needed=set()
 for name in names:needed.update(deps(ns[name].__code__))
 assert not needed-set(ns)-set(vars(builtins))
 assert Path(plan['Rust_compiler']).is_file() and Path('/usr/bin/gcc-9').is_file()
 fixture=(F/'signalfd_create_actual.c').read_text();assert '#include <string.h>' in fixture and not any(a.startswith('-I') for a in plan['commands'][1]['argv']);assert 'IHK_DMA_ALIGN\n' in fixture
 write(A/'HELPER-TOOL-PROVIDER-PREFLIGHT.json',dict(scope=__doc__,helper=pin(helper),missing_globals=[],namespace_dict_API=True,dependencies=sorted(needed),interpreter=sys.executable,version=sys.version,Rust192=plan['Rust_compiler'],gcc9='/usr/bin/gcc-9',kernelstring_memset_dependency_in_hosted_leaf=False,controlled_host_callbacks=True,before_first_child=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,aggregate_jobs_ceiling=7,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(A/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']=str(2<<20)
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
 write(A/'ACTUAL-PROFILE.json',dict(scope=__doc__,recipe=pin(RF),driver=pin(Path(__file__)),CPU=[6],jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,stack_bytes=2<<20,authority='Root must grant sole bounded remaining8 headertransport correction; no replay00..03, furtherunexpectedfailureSTOPexpert'))
 begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);armed=True
 for operation in plan['commands']:
  label=operation['label'];cap=A/label;cap.mkdir(mode=0o700);cmd={k:operation[k] for k in ['argv','cwd','purpose']};cmd['scope']=plan['scope'];prior=os.getcwd()
  try:
   os.chdir(cmd['cwd']);cmd['actual_cwd']=os.getcwd();write(cap/'command.json',cmd);remaining=90-(time.monotonic()-begin);assert remaining>0
   joined=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',joined);records.append(dict(label=label,capture=str(cap),whole_join=joined))
  finally:os.chdir(prior)
  assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None and not joined['timed_out'],dict(label=label,join=joined)
  output=(cap/'stdout').read_text()
  if label=='03-actual-equivalence-and-baseline-errors':assert output.startswith('PASS_SIGNALFD_CREATE_ACTUAL_C_RUST direct=2880 unchanged_helper_create=800 existing_fd=320 frontend_errors=5 hostFD_then_publish_ENOMEM=80 '),output
  if label=='06-selected-full-TU-preprocess':assert re.search(r'\bsyscall_signalfd_create_bridge\s*\([^;{}]*\)\s*\{',output,re.S) is None,'selected C body remains'
  if label in ['08-selected-C-ownership','09-actual-Rust-ownership','11-partial-linked-ownership']:
   found=[line.split() for line in output.splitlines() if line.split()[-1:]==['syscall_signalfd_create_bridge']]
   if label=='08-selected-C-ownership':assert not any(row[-2] in ['T','t'] for row in found),found
   else:assert len(found)==1 and found[0][-2]=='T',found
  assert ns['cpu_used']()<=60
 assert len(records)==8
 for row in plan['retained_artifact_identities']:assert meta(Path(row['path']))==row
 for row in [*plan['source_inputs'].values(),*plan['unchanged_boundary_headers'].values()]:assert pin(Path(row['path']))==row
 result=dict(scope=__doc__,status='PASS_F03_REMAINING8_REAL_HEADERS_SELECTED_GCC9_TU_AND_PARTIAL_LINK_REUSING_PRIOR4005_CASES',recipe=pin(RF),profile=pin(A/'ACTUAL-PROFILE.json'),source_bindings=pin(D/'sourcehandoff/SOURCE-BINDINGS.json'),patch=pin(D/'patch/signalfd-create-selected-body.patch'),records=records,prior_actual_cases=4005,current_case_replays=0,prior_actual_direct_vectors=2880,prior_unchanged_helper_create_cases=800,prior_existingFD_cases=320,prior_frontend_error_cases=5,prior_hostFD_then_publish_ENOMEM_controls=80,retained_prior_captures=plan['retained_prior_captures'],retained_artifact_identities=plan['retained_artifact_identities'],bounded_correction=plan['header_transport'],canonical_changes=False,complete_C_TU=True,partial_link=True,full78_production_Rust=False,GCC14_default_link=False,native=False,file_retired=False,CPU6_released=True,seconds=time.monotonic()-begin,total_CPU_seconds=ns['cpu_used']())
 write(A/'ACTUAL-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(A/'ACTUAL-WHOLE-JOIN.json'),commands=len(records),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 write(A/'FAILURE-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_RESULT_NO_RETRY',error=type(exc).__name__+': '+str(exc),records=records,CPU6_released=all(r['whole_join']['direct_child_joined'] and r['whole_join']['group_absent'] and r['whole_join']['closed_streams'] for r in records)));raise
finally:
 if armed:signal.setitimer(signal.ITIMER_REAL,0)
 os.chdir(initial)
