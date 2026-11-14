# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
tree=ast.parse(raw)
names={'stop','need','write','hashed','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS','stopping'} for t in n.targets)]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(SOURCE),'exec'))
for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,stop)
signal.setitimer(signal.ITIMER_REAL,90)
os.chdir(D)
os.environ['RUST_MIN_STACK']='2097152'
def limits():
 os.sched_setaffinity(0,{6})
 for r,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]: resource.setrlimit(r,(v,v))
bindings=json.loads((D/'FROZEN-SOURCES.json').read_text())
for name,row in bindings.items():assert hashlib.sha256((D/name).read_bytes()).hexdigest()==row['sha256']
os.environ['REAL_ATTEMPT']='attempt-1'
a=D/'attempt-1';a.mkdir()
for f in D.iterdir():
 if f.is_file() and f.suffix in ('.rs','.c','.h','.inc','.py'):(a/f.name).write_bytes(f.read_bytes())
(a/'evidence').mkdir()
for name in ['actual-failure-snapshot.normalized.log','actual-later-retirement.serial-record.log']:(a/name).write_bytes((D/name).read_bytes())
rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
gcc='/usr/bin/gcc-9';py='/home/holden/anaconda3/bin/python3'
flags=['-std=gnu11','-O2','-Wall','-Wextra','-Werror','-static','-fno-pie','-no-pie','-Wl,-z,noexecstack','-DND_CORE_THREADS','-DND_PAIR_LAUNCH_EXPANSION']
seed='/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/candidate/pair_collector.c'
commands=[('controlled-launcher-build',[gcc,'-std=gnu11','-O1',str(a/'controlled_launcher.c'),'-o',str(a/'controlled-launcher')],a),
('actual-retained-bridge-build',[gcc,'-std=gnu11','-O1','-g0','-Wall','-Wextra','-DPAIR_ROOT="."','-DPAIR_LAUNCHER="'+str(a/'controlled-launcher')+'"','-c',str(a/'bridge_fixture.c'),'-o',str(a/'bridge_fixture.o')],a),
('original-trace-body-build',[gcc,'-std=gnu11','-O1','-g0','-c',str(a/'old_trace_witness.c'),'-o',str(a/'old_trace_witness.o')],a),
('Rust-full-loop-actual-target-build',[rust,'--edition=2021','--test','-C','codegen-units=1','-C','opt-level=1','-C','debuginfo=0','-C','linker=/usr/bin/gcc-9','-C','link-arg='+str(a/'bridge_fixture.o'),'-C','link-arg='+str(a/'old_trace_witness.o'),str(a/'pair_long_producer.rs'),'-o',str(a/'producer-tests')],a),
('preserved-loop-regressions',[str(a/'producer-tests'),'--test-threads=1','--skip','actual_bridge_controlled_launch_and_strict_gate','--skip','actual_loop_full_report_trace_consumer_wire'],a)]
for mode in range(9):
 cwd=a/('bridge-'+str(mode)+'-work');cwd.mkdir();(cwd/'evidence').mkdir()
 commands.append(('actual-bridge-mode-'+str(mode),[str(a/'producer-tests'),'--exact','tests::actual_bridge_controlled_launch_and_strict_gate','--test-threads=1'],cwd))
commands.append(('unchanged-full-pair-prepare',[py,'-I','-B',str(D/'check_consumer.py'),'prepare'],a))
for mode in [0,1,2,3,4,5,6,7,9,10]:
 commands.append(('actual-final-mode-'+str(mode),[str(a/'producer-tests'),'--exact','tests::actual_loop_full_report_trace_consumer_wire','--test-threads=1'],a))
commands += [('unchanged-full-LONG-consumer',[py,'-I','-B',str(D/'check_consumer.py'),'check'],a),
('Rust-staticlib',[rust,'--edition=2021','--crate-type=staticlib','-C','codegen-units=1','-C','opt-level=2','-C','panic=abort',str(a/'pair_long_static.rs'),'-o',str(a/'libpair_long.a')],a),
('actual-failure-order-build',[gcc,'-std=gnu11','-O1','-g0','-Wall','-Wextra','-DPAIR_ROOT="."',str(a/'failure_order_fixture.c'),str(a/'libpair_long.a'),'-Wl,--gc-sections','-o',str(a/'failure-order-fixture')],a)]
for mode in range(6):
 cwd=a/('failure-'+str(mode)+'-work');cwd.mkdir()
 commands.append(('actual-failure-order-'+str(mode),[str(a/'failure-order-fixture'),str(mode)],cwd))
commands.append(('unchanged-full-failure-consumer',[py,'-I','-B',str(D/'check_failure_consumer.py')],a))

commands.append(('actual-settlement-fixture-build',[gcc,'-std=gnu11','-O1','-g0','-Wall','-Wextra','-ffunction-sections','-fdata-sections','-DPAIR_ROOT="."',str(a/'settlement_fixture.c'),'-Wl,--gc-sections','-o',str(a/'settlement-fixture')],a))
for mode in range(16):
 cwd=a/('settlement-'+str(mode)+'-work');cwd.mkdir()
 commands.append(('actual-settlement-mode-'+str(mode),[str(a/'settlement-fixture'),str(mode)],cwd))

results=[]
for label,argv,cwd in commands:
 os.chdir(cwd)
 if label.startswith('actual-bridge-mode-'):os.environ['BRIDGE_MODE']=label.rsplit('-',1)[1]
 if label.startswith('actual-final-mode-'):
  mode=label.rsplit('-',1)[1];os.environ['FINAL_MODE']=mode;os.environ['FINAL_WIRE_PATH']=str(a/('wire-final-'+mode))
 os.environ['REAL_WIRE_ROOT']=str(a/'controlled-full-frames')
 capture=a/label;capture.mkdir();command={'argv':argv,'cwd':str(cwd),'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','shell':False}
 write(capture/'command.json',command)
 result=owned_capture(command,capture,90,limits);write(capture/'result.json',result);results.append(dict(label=label,whole_join=result))
 if result['returncode']!=0 or not result['direct_child_joined']or not result['group_absent']or not result['closed_streams']or result['error']or result['retirement_error']:break
write(a/'RESULT.json',dict(status='PASS'if len(results)==len(commands)else'FAIL_STOP_FIRST_FAILURE',operations=results,native_acceptance=False))
signal.setitimer(signal.ITIMER_REAL,0)
print(json.dumps(dict(completed=len(results),total=len(commands),last=results[-1]['label'],returncode=results[-1]['whole_join']['returncode'])))
