"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw)
names={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(SOURCE),'exec'))
A=D/'attempt-1';A.mkdir();os.chdir(D);os.sched_setaffinity(0,{0})
os.environ['RUST_MIN_STACK']='2097152'
for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(r,(v,v))
started=time.monotonic()
for number in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(number,stop)
signal.setitimer(signal.ITIMER_REAL,90)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
need(state['last_rate_limits']['primary']['usedPercent']<100,'included usage guard')
h=os.statvfs(D);s=os.statvfs('/home/holden/mckernel-work/scratch')
need(h.f_bavail*h.f_frsize >= (16<<30)+(128<<20),'hostfloor+boundedgrowth')
need(s.f_bavail*s.f_frsize >=12<<30,'scratchfloor')
mem=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
need(mem>=4<<30,'aggregate RAM available')
write(A/'ADMISSION.json',{'purpose':__doc__,'cpu':0,'mem_available_bytes':mem,'host_free_bytes':h.f_bavail*h.f_frsize,'scratch_free_bytes':s.f_bavail*s.f_frsize,'primary_usage_percent':state['last_rate_limits']['primary']['usedPercent']})
pins=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in sorted(D.iterdir()) if p.is_file()]
write(A/'SOURCE-BINDINGS.json',pins)
need(hashlib.sha256((D/'begin_readiness.rs').read_bytes()).hexdigest()=='13d066654384b585f400a35b2e9de2425f7eeeef611a5232d9f8a82fc034c4c9','exact unchanged Rust readiness')
rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
gcc='/usr/bin/gcc-9'
commands=[
('exact-rust-staticlib',[rust,'--edition=2021','--crate-type=staticlib','-C','codegen-units=1','-C','opt-level=2','-C','panic=abort',str(D/'begin_readiness.rs'),'-o',str(A/'libbegin_readiness.a')],D),
('original-real-reader-fixture-build',[gcc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-DORIGINAL','-ffunction-sections','-fdata-sections',str(D/'real_reader_fixture.c'),str(A/'libbegin_readiness.a'),'-Wl,--gc-sections','-o',str(A/'original-reader')],D),
('corrected-real-reader-fixture-build',[gcc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections',str(D/'real_reader_fixture.c'),str(A/'libbegin_readiness.a'),'-Wl,--gc-sections','-o',str(A/'corrected-reader')],D),
('retained-lifecycle-fixture-build',[gcc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections',str(D/'fixture.c'),str(A/'libbegin_readiness.a'),'-Wl,--gc-sections','-o',str(A/'lifecycle-fixture')],D),
('retained-lifecycle-fixture',[str(A/'lifecycle-fixture')],D)]
for mode in ('original-collision','pending','arrival','collision','missing-procfs','read-error','nonempty-procfs'):
 cwd=A/mode;cwd.mkdir()
 binary=A/('original-reader' if mode=='original-collision' else 'corrected-reader')
 commands.append(('real-reader-'+mode,[str(binary),mode,str(D/'retained7589-console-klog-LF.kmsg'),str(D/'controlled-epoch2-pending.kmsg')],cwd))
commands += [
('actual-full-static-collector-build',[gcc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static','-fno-pie','-no-pie','-Wl,-z,noexecstack','-MMD','-MF',str(A/'collector.d'),str(D/'collector.c'),str(A/'libbegin_readiness.a'),'-Wl,--gc-sections','-o',str(A/'collector.init')],D),
('actual-static-ELF-undefined',['/usr/bin/nm','-u',str(A/'collector.init')],D),
('actual-static-ELF-symbols',['/usr/bin/nm','-g','--defined-only',str(A/'collector.init')],D),
('actual-static-ELF-headers',['/usr/bin/readelf','-h','-l','-d',str(A/'collector.init')],D)]
write(A/'EXACT-COMMANDS-BEFORE-EXECUTION.json',[{'role':label,'argv':argv,'cwd':str(cwd),'purpose':__doc__} for label,argv,cwd in commands])
results=[]
for label,argv,cwd in commands:
 need(time.monotonic()-started<90 and cpu_used()<60,'whole CPU/wall bounds')
 os.chdir(cwd)
 path=A/('capture-'+label);path.mkdir()
 command={'argv':argv,'cwd':str(cwd),'purpose':__doc__,'shell':False};write(path/'command.json',command)
 result=owned_capture(command,path,min(90,90-(time.monotonic()-started)),lambda:None)
 write(path/'result.json',result);results.append({'role':label,'whole_join':result})
 if result['returncode']!=0 or not result['direct_child_joined'] or not result['group_absent'] or not result['closed_streams'] or result['error'] or result['retirement_error']:break
signal.setitimer(signal.ITIMER_REAL,0)
status='PASS' if len(results)==len(commands) and all(r['whole_join']['returncode']==0 for r in results) else 'FAIL_STOP_FIRST_EXPERT_CANDIDATE'
write(A/'RESULT.json',{'scope':__doc__,'status':status,'operations':results,'elapsed_seconds':time.monotonic()-started,'CPU_seconds':cpu_used(),'all_joined_group_gone_closed':all(x['whole_join']['direct_child_joined'] and x['whole_join']['group_absent'] and x['whole_join']['closed_streams'] for x in results),'CPU0_released_after_exit':True,'native_acceptance':False})
print(json.dumps({'status':status,'completed':len(results),'last':results[-1]['role'],'returns':[r['whole_join']['returncode'] for r in results]}))
