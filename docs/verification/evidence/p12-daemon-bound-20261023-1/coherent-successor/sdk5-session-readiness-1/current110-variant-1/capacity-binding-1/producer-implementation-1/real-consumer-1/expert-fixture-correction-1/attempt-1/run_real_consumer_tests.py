"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,resource,sys,signal,time,types
D=Path(__file__).resolve().parent
E=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/capacity-binding-1/producer-implementation-1/real-consumer-1/expert-fixture-correction-1')
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(H.read_text(),str(H))
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
constants={'D','FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
h=types.ModuleType('owned');h.__file__=str(H)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(H),'exec'),h.__dict__)
assert sys.argv[1]=='attempt-1'
os.environ['REAL_ATTEMPT']=sys.argv[1]
a=D/sys.argv[1];a.mkdir()
# Freeze the complete prelaunch source/driver, including unsuccessful later output.
for p in D.iterdir():
 if p.is_file():(a/p.name).write_bytes(p.read_bytes())
(a/'SOURCE-BINDINGS.json').write_text(json.dumps([{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in a.iterdir() if p.is_file()],indent=2)+'\n')
os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
started=time.monotonic()
for number in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(number,h.stop)
signal.setitimer(signal.ITIMER_REAL,90)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
assert state['last_rate_limits']['primary']['usedPercent']<100,'included-only guard'
mem=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
assert mem>=4<<30,'aggregate available RAM'
host=os.statvfs(D);scratch=os.statvfs('/home/holden/mckernel-work/scratch')
h.write(a/'ADMISSION.json',{'purpose':__doc__,'cpu':6,'mem_available_bytes':mem,'host_free_bytes':host.f_bavail*host.f_frsize,'scratch_free_bytes':scratch.f_bavail*scratch.f_frsize,'primary_usage_percent':state['last_rate_limits']['primary']['usedPercent'],'actual_native_launches':0})
assert host.f_bavail*host.f_frsize >= (16<<30)+(128<<20),'host floor+growth'
assert scratch.f_bavail*scratch.f_frsize >=12<<30,'scratch floor'
guard=[]
for p in D.iterdir():
 if p.is_file() and p.suffix in ('.c','.rs','.h','.inc'):
  q=D.parent/'candidate2-fixture-correction-1'/p.name
  allowed=p.name in ('bridge_fixture.c','tests.rs')
  same=p.read_bytes()==q.read_bytes()
  assert allowed or same,'unexpected production/gate source delta '+p.name
  guard.append({'name':p.name,'fixture_edit_allowed':allowed,'byte_equal':same,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
for name,pin in [('native_diagnostic.py','f417a029b43b1d7916e733742946a709584b0a606849f1ca2fc46647bd40dbef')]:
 p=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/source')/name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==pin
h.write(a/'SOURCE-GUARD.json',guard)
for k,v in ((resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)):resource.setrlimit(k,(v,v))
rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
gcc='/usr/bin/gcc-9';py='/home/holden/anaconda3/bin/python3'
commands=[('controlled-launcher-build',[gcc,'-std=gnu11','-O1',str(a/'controlled_launcher.c'),'-o',str(a/'controlled-launcher')],a),
('actual-retained-bridge-build',[gcc,'-std=gnu11','-O1','-g0','-Wall','-Wextra','-DPAIR_ROOT="."','-DPAIR_LAUNCHER="'+str(a/'controlled-launcher')+'"','-c',str(a/'bridge_fixture.c'),'-o',str(a/'bridge_fixture.o')],a),
('actual-old-trace-body-build',[gcc,'-std=gnu11','-O1','-g0','-c',str(a/'old_trace_witness.c'),'-o',str(a/'old_trace_witness.o')],a),
('rust-actual-loop-linked-bridge-build',[rust,'--edition=2021','--test','-C','codegen-units=1','-C','opt-level=1','-C','debuginfo=0','-C','linker=/usr/bin/gcc-9','-C','link-arg='+str(a/'bridge_fixture.o'),'-C','link-arg='+str(a/'old_trace_witness.o'),str(a/'pair_long_producer.rs'),'-o',str(a/'producer-tests')],a),
('actual-loop-regressions',[str(a/'producer-tests'),'--test-threads=1','--skip','actual_bridge_controlled_launch_and_strict_gate','--skip','actual_loop_full_report_trace_consumer_wire'],a)]
for mode in range(9):
 cwd=a/('bridge-'+str(mode)+'-work');cwd.mkdir();(cwd/'evidence').mkdir()
 commands.append(('actual-bridge-mode-'+str(mode),[str(a/'producer-tests'),'--exact','tests::actual_bridge_controlled_launch_and_strict_gate','--test-threads=1'],cwd))
commands += [('unchanged-full-pair-consumer-and-controlled-derivatives',[py,'-I','-B',str(D/'check_consumer.py'),'prepare'],a),('actual-rust-full-consumer-wire',[str(a/'producer-tests'),'--exact','tests::actual_loop_full_report_trace_consumer_wire','--test-threads=1'],a),('unchanged-full-long-consumer',[py,'-I','-B',str(D/'check_consumer.py'),'check'],a)]
results=[]
for label,argv,cwd in commands:
 os.chdir(cwd)
 if label.startswith('actual-bridge-mode-'):os.environ['BRIDGE_MODE']=label.rsplit('-',1)[1]
 os.environ['REAL_WIRE_ROOT']=str(a/'controlled-full-frames')
 capture=a/label;capture.mkdir();command={'argv':argv,'cwd':str(cwd),'purpose':__doc__,'shell':False}
 h.write(capture/'command.json',command)
 assert h.cpu_used()<60 and time.monotonic()-started<90
 joined=h.owned_capture(command,capture,min(90,90-(time.monotonic()-started)),lambda:None);h.write(capture/'result.json',joined)
 results.append({'label':label,'whole_join':joined})
 if joined['returncode']!=0 or not joined['direct_child_joined'] or not joined['group_absent'] or not joined['closed_streams'] or joined['error'] or joined['retirement_error']:break
status='PASS' if len(results)==len(commands) and all(r['whole_join']['returncode']==0 for r in results) else 'FAIL_STOP_FIRST_FAILURE'
h.write(a/'RESULT.json',{'scope':__doc__,'status':status,'results':results,'native_acceptance':False,'actual_hour_workload':False})
signal.setitimer(signal.ITIMER_REAL,0)
h.write(a/'CLOSED-RECEIPT.json',{'status':status,'whole_join':all(r['whole_join']['direct_child_joined'] and r['whole_join']['group_absent'] and r['whole_join']['closed_streams'] for r in results),'seconds':time.monotonic()-started,'cpu_seconds':h.cpu_used(),'cpu6_released_after_exit':True,'actual_native_launches':0,'actual_hour_workload':False})
for p in list(D.rglob('*')):
 if p.is_file() and p.suffix!='.o' and p.name not in ('producer-tests','controlled-launcher'):
  q=E/p.relative_to(D);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
print(json.dumps({'status':status,'commands_completed':len(results),'last_label':results[-1]['label'],'returns':[r['whole_join']['returncode'] for r in results]}))
