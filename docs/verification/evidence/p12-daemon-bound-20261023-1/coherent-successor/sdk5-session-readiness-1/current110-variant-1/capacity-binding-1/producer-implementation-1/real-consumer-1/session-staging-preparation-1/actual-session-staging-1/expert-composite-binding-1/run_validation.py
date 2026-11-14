"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=H.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw);names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'))
A=D/'attempt-1';A.mkdir();os.chdir(D);os.sched_setaffinity(0,{6})
for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
started=time.monotonic()
for number in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(number,stop)
signal.setitimer(signal.ITIMER_REAL,90)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
need(state['last_rate_limits']['primary']['usedPercent']<100,'included-only100 guard')
h=os.statvfs(D);s=os.statvfs('/home/holden/mckernel-work/scratch')
need(h.f_bavail*h.f_frsize >= (16<<30)+(32<<20),'HOSTfloor+outputgrowth')
need(s.f_bavail*s.f_frsize >=12<<30,'scratchfloor')
mem=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
need(mem>=4<<30,'aggregate available RAM')
write(A/'ADMISSION.json',{'purpose':__doc__,'cpu':6,'mem_available_bytes':mem,'host_free_bytes':h.f_bavail*h.f_frsize,'scratch_free_bytes':s.f_bavail*s.f_frsize,'primary_usage_percent':state['last_rate_limits']['primary']['usedPercent']})
write(A/'SOURCE-BINDINGS.json',[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(D.rglob('*')) if p.is_file()])
commands=[{'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'validate_existing_stage.py'),mode],'cwd':str(D),'purpose':__doc__,'role':mode,'shell':False} for mode in ('authorities','full-consumer')]
write(A/'EXACT-COMMANDS-BEFORE-EXECUTION.json',commands)
results=[]
for command in commands:
 need(cpu_used()<30 and time.monotonic()-started<90,'whole bounds')
 capture=A/command['role'];capture.mkdir();write(capture/'command.json',command)
 joined=owned_capture(command,capture,min(90,90-(time.monotonic()-started)),lambda:None)
 write(capture/'result.json',joined);results.append({'role':command['role'],'whole_join':joined})
 if joined['returncode']!=0 or not joined['direct_child_joined'] or not joined['group_absent'] or not joined['closed_streams'] or joined['error'] or joined['retirement_error']:break
signal.setitimer(signal.ITIMER_REAL,0)
status='PASS' if len(results)==2 and all(x['whole_join']['returncode']==0 for x in results) else 'FAIL_STOP_FIRST_EXPERT_CANDIDATE'
write(A/'RESULT.json',{'scope':__doc__,'status':status,'operations':results,'elapsed_seconds':time.monotonic()-started,'CPU_seconds':cpu_used(),'CPU6_released_after_exit':True,'native_acceptance':False})
print(json.dumps({'status':status,'completed':len(results),'returns':[x['whole_join']['returncode'] for x in results]}))
