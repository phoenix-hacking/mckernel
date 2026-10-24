"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-granted pure CPU0 retained consumer; no compiler/link/tool replay.
"""
from pathlib import Path
import ast,builtins,dis,hashlib,json,os,resource,signal,sys,time
P=Path(__file__).resolve().parent;SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
records=[];started=False

def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
try:
 ready=json.loads((P/'EXECUTABLE-READY.json').read_text());assert ready['scope']==SCOPE
 for key in ['observer','bindings','driver']:assert pin(Path(ready[key]['path']))==ready[key]
 assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:2]==(3,9)
 helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert pin(helper)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
 names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'};assign={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
 nodes=[n for n in ast.parse(helper.read_bytes()).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assign for t in n.targets)]
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 def globals_used(code):
  used={i.argval for i in dis.get_instructions(code) if i.opname=='LOAD_GLOBAL'}
  for value in code.co_consts:
   if isinstance(value,type(code)):used.update(globals_used(value))
  return used
 deps=set()
 for name in names:deps.update(globals_used(ns[name].__code__))
 assert not deps-set(ns)-set(vars(builtins))
 mem=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024;hs=os.statvfs('/home/holden');ss=os.statvfs('/home/holden/mckernel-work/scratch');bs=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,bs.st_size-bs.st_blocks*512)
 admission=dict(scope=SCOPE,MemAvailable=mem,aggregate_floor=19<<30,aggregate_jobs=7,host_available=hs.f_bavail*hs.f_frsize,host_required=(16<<30)+gap+(16<<20)+679477248,scratch_available=ss.f_bavail*ss.f_frsize,scratch_required=(12<<30)+(16<<20),full_backing_gap=gap)
 assert mem>=admission['aggregate_floor'] and admission['host_available']>=admission['host_required'] and admission['scratch_available']>=admission['scratch_required'],admission
 used=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())['last_rate_limits']['primary']['usedPercent'];assert used<100;admission['included_usage_percent']=used
 write(P/'ACTUAL-ADMISSION.json',admission)
 os.chdir(P);os.sched_setaffinity(0,{0})
 for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
 for kind,value in [(resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,10),(resource.RLIMIT_FSIZE,16<<20),(resource.RLIMIT_NOFILE,128),(resource.RLIMIT_CORE,0)]:resource.setrlimit(kind,(value,value))
 profile=dict(scope=SCOPE,root_authority=ready['root_authority'],ready=pin(P/'EXECUTABLE-READY.json'),driver=pin(Path(__file__)),helper=pin(helper),helper_dict_API=True,helper_missing_globals=[],cwd=str(P),**ready['profile']);write(P/'ACTUAL-PROFILE.json',profile)
 cap=P/'actual-observer-capture-1';cap.mkdir(mode=0o700);command=dict(scope=SCOPE,purpose=SCOPE+' Consume retained production objects after one exact observer-only named-target correction; no compiler/link/NM/readelf replay.',argv=['/home/holden/anaconda3/bin/python3',str(P/'observe_retained_production.py')],cwd=str(P),profile=pin(P/'ACTUAL-PROFILE.json'));write(cap/'command.json',command)
 signal.setitimer(signal.ITIMER_REAL,35);started=True;begin=time.monotonic();join=ns['owned_capture'](command,cap,30,lambda:None);write(cap/'whole-join.json',join);records.append(join)
 assert join['returncode']==0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams'] and join['error'] is None and join['retirement_error'] is None and not join['timed_out'],join
 result=json.loads((P/'OBSERVER-RESULT.json').read_text());assert result['status'].startswith('PASS_') and ns['cpu_used']()<=10
 receipt=dict(scope=SCOPE,status='PASS_ONE_ROOT_GRANTED_RETAINED_OBSERVER_WHOLE_JOIN',result=pin(P/'OBSERVER-RESULT.json'),ready=pin(P/'EXECUTABLE-READY.json'),command=pin(cap/'command.json'),join=join,seconds=time.monotonic()-begin,CPU_seconds=ns['cpu_used'](),CPU0_released=True,compiler_or_linker_invocations=0,old14commands_replayed=False,large_objects_rehashed=False,canonical_mutations=0,default_image_native_file_credit=False)
 write(P/'ACTUAL-OBSERVER-WHOLE-JOIN.json',receipt);print(json.dumps(dict(scope=SCOPE,status=receipt['status'],whole_join=pin(P/'ACTUAL-OBSERVER-WHOLE-JOIN.json'),result=receipt['result'],seconds=receipt['seconds'],CPU0_released=True)))
except BaseException as error:
 write(P/'OBSERVER-CORRECTION-FAILURE-1.json',dict(scope=SCOPE,status='STOP_EXPERT_ESCALATION_NO_FURTHER_CORRECTION',error=type(error).__name__+': '+str(error),records=records,CPU0_released=all(j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] for j in records)));raise
finally:
 if started:signal.setitimer(signal.ITIMER_REAL,0)
