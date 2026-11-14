"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-granted exact existing runner under reused h990 owner; no retry.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,stat,subprocess,time,sys
B=Path(__file__).resolve().parent.parent;H=B/'sourcehandoff';C=H/'actual-owned-first-candidate-capture-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
READY_SHA='7288a8d9682d30ee6a7be4a0ae70a754d03aab4b977b3a3254d4acbbaac1592d'
started=False;records=[]
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,value):
 with p.open('x') as f:json.dump(value,f,sort_keys=True);f.write('\n')
try:
 ready=H/'EXECUTABLE-READY.json';assert pin(ready)['sha256']==READY_SHA
 spec=json.loads(ready.read_text())
 for relative,sha in spec['input_sha256'].items():assert pin(B/relative)['sha256']==sha,relative
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:2]==(3,9)
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
 write(H/'HELPER-GLOBAL-DEPENDENCY-CHECK.json',dict(scope=SCOPE,helper=pin(helper),dependencies=sorted(deps),missing=[],Python_executable=sys.executable,Python_version=sys.version,dict_API=True,before_any_child=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(H/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 grant=H/'ROOT-CPU6-EXACT-GRANT.json'
 write(grant,dict(scope=SCOPE,ready_sha256=READY_SHA,ordinary_cpu=6,authority='Root explicit current exclusive CPU6 one ordinary candidate, independent source/ABI PASS64af/3f2c, preexecution fixture-only memset correction retained, no retry after unexpected failure'))
 C.mkdir(mode=0o700);os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=SCOPE,CPU=6,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,CGU=1,RUST_MIN_STACK=2097152,ready=pin(ready),driver=pin(Path(__file__)),grant=pin(grant))
 write(H/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,96);started=True
 command=dict(scope=SCOPE,purpose=SCOPE+' Execute exact prepared actual-original-C/Rust tree entry/body, header ABI and default/fallback selected leaf commands once.',argv=['/usr/bin/python3',str(H/'run_once.py'),'--root-grant',str(grant),'--attempt','ordinary-attempt-1'],cwd=str(B),profile=pin(H/'ACTUAL-PROFILE.json'))
 write(C/'command.json',command);j=ns['owned_capture'](command,C,90,lambda:None);write(C/'whole-join.json',j);records.append(j)
 assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
 result=json.loads((B/'fixture/ordinary-attempt-1/RESULT.json').read_text());assert result['status']=='PASS_PRIVATE_ACTUAL_ENTRY_BODY_PARITY_REAL_ABI_AND_SELECTED_LEAF_LINK',result
 assert pin(ready)['sha256']==READY_SHA and ns['cpu_used']()<=60
 receipt=dict(scope=SCOPE,status='PASS_EXACT_PREPARED_RUNNER_WHOLE_JOIN',result=pin(B/'fixture/ordinary-attempt-1/RESULT.json'),records=records,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU6_released=True,canonical_mutations=0,full_production_Rust_crate=False,default_GCC14_kernel_link=False,native=False,file_retired=False)
 write(H/'ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json',receipt);print(json.dumps(receipt))
except BaseException as error:
 write(H/'FIRST-CANDIDATE-FAILURE-1.json',dict(scope=SCOPE,status='STOP_FIRST_UNEXPECTED_FAILURE_NO_RETRY',error=type(error).__name__+': '+str(error),records=records,CPU6_released=all(j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] for j in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
