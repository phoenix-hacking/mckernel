"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure actual-body diagnostic fixture; host primitives modeled, no SDKmodule/native.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
P=Path(__file__).resolve().parent;F=P/'EXACT-ORDINARY-FIXTURE-RECIPE.OBSERVER-CORRECTED.GRANTED.json'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
assert pin(F)['sha256']=='370d41518775c7f75f94300cfa13c0566874098d210499aaf0136b0b36aeeb08';recipe=json.loads(F.read_text());bindings=json.loads((P.parent/'SOURCE-BINDINGS.json').read_text())
for row in [*recipe['source_files'].values(),*recipe['tools'].values(),recipe['source_bindings'],recipe['fixture_bindings']]:assert pin(Path(row['path']))==row
assert pin(P.parent/'SOURCE-BINDINGS.json')['sha256']=='0fc72271dc63446af24a19d4ff50fa0e7122e7ff5f6a11b415cb890e857ee945'
for row in bindings['changes'].values():
 assert pin(Path(row['selected_original']['path']))==row['selected_original']
 observed=pin(Path(row['canonical_preimage']['path']));expected=row['private_postimage']
 assert observed['sha256']==expected['sha256'] and observed['bytes']==expected['bytes']
assert os.getuid()==os.geteuid()==1000
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=H.read_bytes();assert pin(H)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;h=os.statvfs('/home/holden');s=os.statvfs('/home/holden/mckernel-work/scratch');back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512)
capacity=dict(MemAvailable_bytes=mem,minimum_memory_bytes=19<<30,HOST_available_bytes=h.f_bavail*h.f_frsize,scratch_available_bytes=s.f_bavail*s.f_frsize,HOST_floor=16<<30,scratch_floor=12<<30,full_sparse_gap_bytes=gap,HOST_output_reserve=64<<20)
assert mem>=19<<30 and capacity['HOST_available_bytes']>=(16<<30)+gap+(64<<20) and capacity['scratch_available_bytes']>=12<<30
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());capacity['included_usage_percent_observed']=state['last_rate_limits']['primary']['usedPercent'];assert capacity['included_usage_percent_observed']<100
write(P/'ACTUAL-CAPACITY.json',capacity);O=P/'fixture-output-1';O.mkdir(mode=0o700);C=P/'actual-owned-capture-1';C.mkdir(mode=0o700)
os.chdir(O);os.sched_setaffinity(0,{0});os.environ['RUST_MIN_STACK']='2097152'
for sig in STOP_SIGNALS:signal.signal(sig,stop)
def limits():
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
limits();profile=dict(scope=__doc__,authority=recipe['authority'],recipe=pin(F),**recipe['profile']);write(P/'ACTUAL-PROFILE.json',profile)
begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);records=[]
try:
 for command in recipe['commands']:
  cap=C/command['name'];cap.mkdir(mode=0o700);cmd=dict(scope=recipe['scope'],purpose=__doc__,argv=command['argv'],cwd=str(O),profile=pin(P/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
  j=owned_capture(cmd,cap,max(.1,90-(time.monotonic()-begin)),limits);write(cap/'whole-join.json',j);records.append(dict(name=command['name'],command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  if command['name']=='01-pure-actual-body-Rust-compile':write(P/'DURABLE-FIXTURE-BINARY.json',dict(scope=recipe['scope'],status='COMPILED_ONCE_RETAINED',binary=pin(O/'diagnostic-fixture'),command=pin(cap/'command.json'),join=pin(cap/'whole-join.json')))
 output=(C/recipe['commands'][2]['name']/'stdout').read_text();assert recipe['expected_output'] in output
 assert all(pin(Path(row['path']))==row for row in recipe['source_files'].values()) and cpu_used()<=60
 result=dict(scope=recipe['scope'],status='PASS_PURE_ACTUAL_BODY_DIAGNOSTIC_ONLY_NOT_SEMANTIC_REPAIR_OR_NATIVE',recipe=pin(F),profile=pin(P/'ACTUAL-PROFILE.json'),source_bindings=pin(P/'CURRENT-SOURCE-BINDINGS.json'),fixture_binary=pin(P/'DURABLE-FIXTURE-BINARY.json'),records=records,original_instrumented_memory_pairs=8195,conflict_masks=256,typed_origins=11,first_original_corrected_pairs=20,finite_actual_source_callers=11,metadata_completion_pairs=90,RPC_pairs=12,remote_reply_pairs=24,diagnostic_budget=16,existing_errors_claims_quarantine_and_calls_unchanged=True,diagnostics_before_quarantine=True,models=recipe['models'],compiler_invocations=1,actual_SDK7_failure_count=1,actual_SDK7_correction_count=1,seconds=time.monotonic()-begin,total_CPU_seconds=cpu_used(),CPU0_released=True,canonical_failed_SDK7_postimages_unchanged=all(pin(Path(row['canonical_preimage']['path']))['sha256']==row['private_postimage']['sha256'] for row in bindings['changes'].values()),actual_failure_cause='UNRESOLVED_INSTRUMENTATION_CANDIDATE_ONLY',SDK7_module_compile_or_native=None,observer_failure_preserved=recipe['observer_only_correction'],failure_history=recipe['failure_history'])
 write(P/'ACTUAL-FIXTURE-RECEIPT.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(P/'ACTUAL-FIXTURE-RECEIPT.json'),seconds=result['seconds'],CPU0_released=True)))
except BaseException as exc:
 write(P/'FAILURE-1.json',dict(scope=recipe['scope'],status='FAIL_PRESERVED_NO_AUTOMATIC_REPLAY',error=type(exc).__name__+': '+str(exc),records=records,CPU0_released=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in records)));raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
