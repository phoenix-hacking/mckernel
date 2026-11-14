"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted sole offline ELF observer on CPU7, reuse accepted990 ownership.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,stat,subprocess,time,sys
H=Path(__file__).resolve().parent;SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
started=False;records=[]
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,value):
 with p.open('x') as f:json.dump(value,f,sort_keys=True);f.write('\n')
try:
 assert pin(H/'observe_retained_elf.py')['sha256']=='d391d3d450282536049848e619925b2f1d92cb28b30032ad1e1b42204997cf15'
 assert pin(H/'INPUT-BINDINGS.json')['sha256']=='be44188d6766bf749be229ee33ed7a5986e084e3411bbcc1c7919f6fe78a6714'
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
 write(H/'HELPER-GLOBAL-DEPENDENCY-CHECK.json',dict(scope=SCOPE,helper=pin(helper),dependencies=sorted(deps),missing=[],dict_API=True,Python_executable=sys.executable,before_any_child=True))
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 capacity=dict(MemAvailable=mem,aggregate_required=19<<30,HOST_available=hs.f_bavail*hs.f_frsize,HOST_required=(16<<30)+gap+(32<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap,backing_size=bs.st_size,backing_device=bs.st_dev,backing_inode=bs.st_ino,campaign_emergency_preserved=679477248)
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];capacity['included_usage_percent']=used;assert used<100
 write(H/'ACTUAL-HEADROOM.json',capacity);assert mem>=capacity['aggregate_required'] and capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required'],capacity
 os.sched_setaffinity(0,{7});os.chdir(H)
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for k,v in [(resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,10),(resource.RLIMIT_FSIZE,8<<20),(resource.RLIMIT_NOFILE,128),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 profile=dict(scope=SCOPE,authority='Root explicit sole observer-only bounded correction using retained objects, no compiler/linker/replay; source SAFE literals exact .ltext fixed before first observer execution',CPU=7,jobs=1,AS_bytes=512<<20,CPU_seconds=10,wall_seconds=15,retirement_seconds=6,FSIZE_bytes=8<<20,NOFILE=128,core=0,observer=pin(H/'observe_retained_elf.py'),bindings=pin(H/'INPUT-BINDINGS.json'),driver=pin(Path(__file__)))
 write(H/'ACTUAL-PROFILE.json',profile);begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,21);started=True
 cap=H/'owned-observer-capture-1';cap.mkdir(mode=0o700)
 cmd=dict(scope=SCOPE,purpose=SCOPE+' Observe exact retained ELF sections, live undefined relocations and unchanged caller bytes once; no compiler/linker/runtime.',argv=['/home/holden/anaconda3/bin/python3',str(H/'observe_retained_elf.py')],cwd=str(H),profile=pin(H/'ACTUAL-PROFILE.json'))
 write(cap/'command.json',cmd);j=ns['owned_capture'](cmd,cap,15,lambda:None);write(cap/'whole-join.json',j);records.append(j)
 assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and j['error'] is None and j['retirement_error'] is None and not j['timed_out'],j
 result=json.loads((H/'OBSERVER-RESULT.json').read_text());assert result['status']=='PASS_OBSERVER_CORRECTION_RETAINED_ELF_SECTIONS_AND_LIVE_RELOCATIONS',result
 assert ns['cpu_used']()<=10
 receipt=dict(scope=SCOPE,status='PASS_SOLE_OBSERVER_CORRECTION_WHOLE_JOIN',result=pin(H/'OBSERVER-RESULT.json'),records=records,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU7_released=True,compiler_invocations=0,linker_invocations=0,replayed_previous_14_commands=False,canonical_mutations=0,full_crate=False,default_image=False,native=False)
 write(H/'ACTUAL-OBSERVER-WHOLE-JOIN.json',receipt);print(json.dumps(receipt))
except BaseException as error:
 write(H/'OBSERVER-FAILURE-1.json',dict(scope=SCOPE,status='STOP_ESCALATE_NO_RETRY',error=type(error).__name__+': '+str(error),records=records,CPU7_released=all(j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] for j in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
