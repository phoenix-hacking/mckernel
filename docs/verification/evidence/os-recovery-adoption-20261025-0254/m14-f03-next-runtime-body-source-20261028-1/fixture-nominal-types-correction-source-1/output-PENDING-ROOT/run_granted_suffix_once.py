#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import ast, datetime, hashlib, json, os, resource, signal, time
from pathlib import Path
OUT=Path(__file__).resolve().parent
HERE=OUT.parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def save(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 begin=time.monotonic();records=[]
 grantpath=HERE/'ROOT-ORDINARY-HOST-SUFFIX-GRANT.json';grant=json.loads(grantpath.read_text())
 planpath=HERE/'FUTURE-HOST-SUFFIX-PLAN.NOT-GRANTED.json'
 assert ref(planpath)==grant['command_plan']
 plan=json.loads(planpath.read_text())
 manifest=json.loads((HERE/'SOURCE-READY.json').read_text())
 for row in manifest['inputs']+manifest['files']:
  assert ref(Path(row['path']))==row, row['path']
 assert os.getuid()==1000 and grant['cpu']==6 and grant['jobs']==1
 assert grant['maximum_commands']==len(plan['commands'])==2
 assert grant['credit_run_id']=='7f4af94a83b14cc08f97401f5891d965'
 assert grant['fixed_epoch_stop']==1793253600
 assert ref(HERE.parent/'output-PENDING-ROOT/callbacks.o')['sha256']==grant['reused_Rust_object']
 assert grant['AS_bytes']==2<<30 and grant['CPU_seconds']==60 and grant['wall_seconds']==90
 helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
 raw=helper.read_bytes()
 assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
 assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 capture=OUT/'actual-two-command-suffix-capture-1';capture.mkdir(mode=0o700)
 os.chdir('/home/holden/mckernel');os.sched_setaffinity(0,{6})
 os.environ.update(LC_ALL='C',RUST_MIN_STACK='2097152',OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1',CARGO_BUILD_JOBS='1',MAKEFLAGS='-j1')
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 save(capture/'profile.json',dict(scope=SCOPE,grant=ref(grantpath),plan=ref(planpath),helper=ref(helper),manifest=ref(HERE/'SOURCE-READY.json'),affinity=sorted(os.sched_getaffinity(0)),jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,runner=ref(Path(__file__).resolve()),started_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 try:
  for command in plan['commands']:
   assert time.time()+90<grant['fixed_epoch_stop']
   assert time.monotonic()+90<grant['operation_monotonic_stop']
   assert time.clock_gettime(time.CLOCK_BOOTTIME)+90<grant['boot_stop']
   for row in manifest['files']:assert ref(Path(row['path']))==row,row['path']
   path=capture/command['label'];path.mkdir(mode=0o700);save(path/'command.json',command)
   def limits():
    os.sched_setaffinity(0,{6})
    for key,value in ((resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,64<<20),(resource.RLIMIT_CORE,0)):resource.setrlimit(key,(value,value))
   before=resource.getrusage(resource.RUSAGE_CHILDREN);wall=time.monotonic();stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
   joined=ns['owned_capture'](command,path,90,limits)
   after=resource.getrusage(resource.RUSAGE_CHILDREN)
   metrics=dict(started_UTC=stamp,wall_seconds=time.monotonic()-wall,user_CPU_seconds=after.ru_utime-before.ru_utime,system_CPU_seconds=after.ru_stime-before.ru_stime,fresh_batch_peak_child_RSS_KiB=after.ru_maxrss,RSS_scope='actual cumulative child high water; per-command RSS unknown')
   save(path/'metrics.json',metrics);records.append(dict(command=command,join=joined,metrics=metrics))
   if joined['returncode']!=0 or not all(joined[k] for k in ('direct_child_joined','group_absent','closed_streams')) or any(joined[k] for k in ('timed_out','error','retirement_error')):raise RuntimeError('first failure STOP; preserve source/grant/plan/captures')
  stdout=(capture/plan['commands'][1]['label']/'stdout').read_text()
  assert stdout.strip()==plan['expected_stdout']
  result=dict(scope=SCOPE,status='PASS_ACTUAL_TWO_COMMAND_SUFFIX_PERF_MMAP_ABI18_160_PAIRS',records=records,actual_stdout=stdout,elapsed_seconds=time.monotonic()-begin,grant=ref(grantpath),plan=ref(planpath),canonical_writes=0,native=False,production_link=False,whole_file_retired=False)
 except BaseException as error:
  result=dict(scope=SCOPE,status='FAIL_STOP_PRESERVE_ORIGINAL_EVIDENCE',error=repr(error),records=records,elapsed_seconds=time.monotonic()-begin,grant=ref(grantpath),plan=ref(planpath),canonical_writes=0,native=False)
 save(OUT/'ACTUAL-HOST-RESULT.json',result)
 print(json.dumps(dict(status=result['status'],result=ref(OUT/'ACTUAL-HOST-RESULT.json'))))
 return 0 if result['status'].startswith('PASS') else 2
if __name__=='__main__':raise SystemExit(main())
