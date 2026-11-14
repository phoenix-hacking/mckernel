#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact Root-granted three-command ordinary batch; uses unchanged h990 ownership.
"""
import ast,datetime,hashlib,json,os,resource,signal,time,importlib.util,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
RECIPE=HERE/'SOURCE-HANDOFF.NOT-GRANTED.json'
RECIPE_SHA='a640afabdcb6fca3fa621ab1353e4df44c3e339de87f8e4847402ac432bb7ec3'
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
EXPERT=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-selected-residual-implementation-20261026-1/next-process-vm-selected-1/next-prctl-getter-selected-1/actual-host-getter-1/reviewed-account-supervisor-correction-1')
EXPERT_SHA='e8b84de39128433542b213fc3a374dd50d3e12f232bd397dddaa24859349a805'
CAPTURE=HERE/'actual-three-command-capture-1'
OUTPUT=HERE/'output-PENDING-ROOT'
RESULT=HERE/'ACTUAL-THREE-COMMAND-RESULT.json'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 begin=time.monotonic();records=[]
 if any(p.exists() for p in (OUTPUT,CAPTURE,RESULT)):raise RuntimeError('attempt exists; no replay')
 if ref(RECIPE)['sha256']!=RECIPE_SHA:raise RuntimeError('frozen recipe changed')
 recipe=json.loads(RECIPE.read_text())
 supplement=json.loads((HERE/'PINNED-GENUINE-HEADER-BINDINGS.json').read_text())
 for row in list(recipe['input_refs'].values())+list(recipe['tool_refs'].values())+list(recipe.get('canonical_origins',{}).values()):
  if ref(Path(row['path']))!=row:raise RuntimeError('frozen input/tool changed: '+row['path'])
 if ref(EXPERT/'run_sealed.py')['sha256']!=EXPERT_SHA:raise RuntimeError('reviewed admission source drift')
 sys.path.insert(0,str(EXPERT))
 spec=importlib.util.spec_from_file_location('accepted_f06_admission',EXPERT/'run_sealed.py');reviewed=importlib.util.module_from_spec(spec);spec.loader.exec_module(reviewed)
 def admission():
  observed=reviewed.admission()
  host=os.statvfs('/home/holden/mckernel');scratch=os.statvfs('/home/holden/mckernel-work/scratch')
  observed['HOST_available_bytes']=host.f_bavail*host.f_frsize;observed['scratch_available_bytes']=scratch.f_bavail*scratch.f_frsize
  if observed['HOST_available_bytes']<16*2**30 or observed['scratch_available_bytes']<12*2**30:raise RuntimeError('existing HOST/scratch floor guard')
  return observed
 initial_admission=admission()
 if os.getuid()!=1000 or 6 not in os.sched_getaffinity(0):raise RuntimeError('ordinary uid1000 CPU6 availability')
 raw=HELPER.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=HELPER_SHA:raise RuntimeError('accepted h990 helper changed')
 functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
 assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
 namespace={'__file__':str(HELPER)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER),'exec'),namespace)
 OUTPUT.mkdir(mode=0o700);CAPTURE.mkdir(mode=0o700)
 os.chdir('/home/holden/mckernel');os.sched_setaffinity(0,{6})
 os.environ['LC_ALL']='C';os.environ['RUST_MIN_STACK']='2097152';os.environ['OMP_NUM_THREADS']='1';os.environ['RAYON_NUM_THREADS']='1'
 env={k:os.environ.get(k) for k in ('PATH','LC_ALL','LANG','RUST_MIN_STACK','OMP_NUM_THREADS','RAYON_NUM_THREADS','CARGO_BUILD_JOBS','MAKEFLAGS','C_INCLUDE_PATH','LIBRARY_PATH','LD_LIBRARY_PATH','RUSTFLAGS','RUSTUP_TOOLCHAIN')}
 for sig in namespace['STOP_SIGNALS']:signal.signal(sig,namespace['stop'])
 profile=dict(scope=SCOPE,authority='Explicit Root ROOTGRANT of exact frozen three argv; no extra workload authorized',jobs=1,affinity=[6],AS_bytes=2<<30,CPU_seconds_per_command=60,FSIZE_bytes=64<<20,core=0,wall_seconds_per_command=90,environment_relevant=env,recipe=ref(RECIPE),helper=ref(HELPER),started_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewed_admission_source=ref(EXPERT/'run_sealed.py'),initial_admission=initial_admission,CPU6_slot_authority='Root explicitly reserves sole ordinary CPU6 slot for this exact CURRENT NEXT10 sync-child3 batch until joined')
 save(CAPTURE/'profile.json',profile)
 try:
  for command in recipe['commands']:
   for row in list(recipe['input_refs'].values())+list(recipe['tool_refs'].values())+list(recipe.get('canonical_preimages',{}).values())+[recipe['genuine_header_profile']]+supplement['headers']:
    if ref(Path(row['path']))!=row:raise RuntimeError('frozen per-command source/tool/header drift: '+row['path'])
   current_admission=admission()
   capture=CAPTURE/command['label'];capture.mkdir(mode=0o700);save(capture/'command.json',command)
   def limits():
    for key,value in ((resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,64<<20),(resource.RLIMIT_CORE,0)):
     resource.setrlimit(key,(value,value))
   before=resource.getrusage(resource.RUSAGE_CHILDREN);wall=time.monotonic();stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
   joined=namespace['owned_capture'](command,capture,90,limits)
   after=resource.getrusage(resource.RUSAGE_CHILDREN)
   metrics=dict(started_UTC=stamp,wall_seconds=time.monotonic()-wall,child_user_CPU_seconds=after.ru_utime-before.ru_utime,child_system_CPU_seconds=after.ru_stime-before.ru_stime,fresh_batch_peak_child_RSS_KiB=after.ru_maxrss,peak_RSS_scope='fresh batch cumulative actual child rusage high water; not an invented per-command peak',environment_relevant=env)
   metrics['admission']=current_admission;save(capture/'actual-metrics.json',metrics);records.append(dict(command=command,join=joined,metrics=metrics))
   if joined['returncode']!=0 or not all(joined[k] for k in ('direct_child_joined','group_absent','closed_streams')) or any(joined[k] for k in ('timed_out','error','retirement_error')):raise RuntimeError('first failure STOP preserve prefix no replay')
  actual=(CAPTURE/recipe['commands'][2]['label']/'stdout').read_text()
  if 'PASS sync-child entry:3072 original-C/Rust graph pairs +9 null/leader controls +49 layout/8 offset/4 attr ABI words and inherit pattern' not in actual:raise RuntimeError('expected3072graphs/9controls/49layout8offset4attr-pattern sync observation absent')
  result=dict(scope=SCOPE,status='PASS_ACTUAL_THREE_COMMANDS_SYNC3072_CONTROLS9_LAYOUT49_OFFSETS8_ATTR4',records=records,seconds=time.monotonic()-begin,peak_child_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,actual_stdout=actual,first_compiler_UTC=records[0]['metrics']['started_UTC'],canonical_mutations=0,native=False,default_link=False,whole_file_retired=False)
 except BaseException as error:
  result=dict(scope=SCOPE,status='FAIL_STOP_PRESERVE_PREFIX_NO_REPLAY',error=repr(error),records=records,seconds=time.monotonic()-begin,canonical_mutations=0,native=False)
 save(RESULT,result);print(json.dumps(dict(status=result['status'],result=ref(RESULT))))
 return 0 if result['status'].startswith('PASS') else 2
if __name__=='__main__':raise SystemExit(main())
