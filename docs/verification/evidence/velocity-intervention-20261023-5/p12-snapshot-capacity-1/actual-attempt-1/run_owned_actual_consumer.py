"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted actual controlled selected consumer: no real klog/guest/kernel actions.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,stat,subprocess,time,sys
A=Path(__file__).resolve().parent;B=A.parent;RF=B/'EXACT-ACTUAL-CONSUMER-FIXTURE.NOT-GRANTED.json'
records=[];started=False
def pin(p):
 data=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True);f.write(chr(10))
try:
 assert pin(RF)['sha256']=='84ada557981d3ca1c0a4260ca65e6ba275d202b9e8f1d051395a216aea31409a'
 assert pin(B/'EXECUTABLE-READY.json')['sha256']=='03481794425af3b89adbe36ebe946531ca48f711189e050a24c78a96e6454ebc'
 recipe=json.loads(RF.read_text())
 for row in [*recipe['source_inputs'].values(),*recipe['tools'].values(),recipe['source_contract'],recipe['actual_round90_facts'],recipe['patch']]:assert pin(Path(row['path']))==row,row['path']
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:2]==(3,9)
 helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=helper.read_bytes();assert pin(helper)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)]
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 def dependencies(code):
  found={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for value in code.co_consts:
   if isinstance(value,type(code)):found.update(dependencies(value))
  return found
 deps=set()
 for name in names:deps.update(dependencies(ns[name].__code__))
 assert not deps-set(ns)-set(vars(builtins))
 fixture=(B/'fixture_capacity.c').read_text();assert '#define klogctl forbidden_klogctl' in fixture and 'long_provider.snapshot=snapshot' in fixture
 assert '#include <string.h>' not in fixture or not any(v.startswith('-I') for v in recipe['commands'][0]['argv'])
 write(A/'HELPER-AND-PROVIDER-PREFLIGHT.json',dict(scope=__doc__,helper=pin(helper),missing_globals=[],dependencies=sorted(deps),actual_namespace_dict_API=True,interpreter=sys.executable,version=sys.version,forbidden_real_klog=True,controlled_snapshot_only=True,before_any_child=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(A/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 O=B/'output-1';O.mkdir(mode=0o700);CAP=A/'captures';CAP.mkdir(mode=0o700);os.chdir(O);os.sched_setaffinity(0,{6})
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=__doc__,authority='Root one exclusiveCPU6 ready03481794/recipe84ada557; AS2G60CPU90wall+6FSIZE32MFD256core0/GCC9/h990/fresh19Gfloorsfullgap; firstunexpectedfailureSTOPno retry',CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,recipe=pin(RF),driver=pin(Path(__file__)))
 write(A/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 for command in recipe['commands']:
  if command.get('create_fresh_cwd'):Path(command['cwd']).mkdir(mode=0o700)
  cap=CAP/command['name'];cap.mkdir(mode=0o700);cmd=dict(scope=recipe['scope'],purpose=command['purpose'],argv=command['argv'],cwd=command['cwd'],profile=pin(A/'ACTUAL-PROFILE.json'));write(cap/'command.json',cmd)
  remaining=90-(time.monotonic()-begin);assert remaining>0
  j=ns['owned_capture'](cmd,cap,remaining,lambda:None);write(cap/'whole-join.json',j);records.append(dict(name=command['name'],command=pin(cap/'command.json'),join=j))
  assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
  if command['name'].startswith('build-'):
   name='capacity-candidate' if command['name']=='build-candidate' else 'capacity-original';write(A/('DURABLE-'+name+'.json'),dict(scope=recipe['scope'],binary=ns['hashed'](O/name,32<<20),command_join=records[-1]))
  else:assert (cap/'stdout').read_text().startswith('PASS ')
 assert len(records)==25 and all(pin(Path(row['path']))==row for row in recipe['source_inputs'].values()) and ns['cpu_used']()<=60
 result=dict(scope=recipe['scope'],status='PASS_ACTUAL_CONTROLLED_READ_ALL_BOUNDARY_25_COMMANDS_UNCHANGED_STRICT_GATE',recipe=pin(RF),ready=pin(B/'EXECUTABLE-READY.json'),profile=pin(A/'ACTUAL-PROFILE.json'),headroom=pin(A/'ACTUAL-HEADROOM.json'),records=records,compiler_invocations=2,actual_controlled_consumers=23,strict_gate_byteexact=True,construct_full_valid_suffix_bytes=1048576,constructed_suffix_is_not_round90=True,actual_round90_retirement='UNKNOWN_BUFFER_NOT_EXPORTED',caps_deadlines_ledgers_unchanged=True,actual_real5s_neverSettles=True,actual_real80ms_outerdeadline=True,total_CPU_seconds=ns['cpu_used'](),seconds=time.monotonic()-begin,CPU6_released=True,canonical_mutations=0,live_klog_calls=0,native=False)
 write(A/'ACTUAL-WHOLE-JOIN.json',result);print(json.dumps(dict(status=result['status'],receipt=pin(A/'ACTUAL-WHOLE-JOIN.json'),seconds=result['seconds'],CPU6_released=True)))
except BaseException as exc:
 write(A/'FAILURE-1.json',dict(scope=__doc__,status='STOP_FIRST_UNEXPECTED_FAILURE_PRESERVED_NO_RETRY',error=type(exc).__name__+': '+str(exc),records=records,CPU6_released=all(x['join']['direct_child_joined'] and x['join']['group_absent'] and x['join']['closed_streams'] for x in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
