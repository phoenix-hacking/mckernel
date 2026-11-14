"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,sys
D=Path(__file__).resolve().parent
E=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/sdk5-session-readiness-1/current110-variant-1/capacity-binding-1/producer-implementation-1/real-consumer-1')
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('owned',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
a=D/'candidate2-attempt-1';a.mkdir()
# Freeze the complete prelaunch source/driver, including unsuccessful later output.
for p in D.iterdir():
 if p.is_file():(a/p.name).write_bytes(p.read_bytes())
(a/'SOURCE-BINDINGS.json').write_text(json.dumps([{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in a.iterdir() if p.is_file()],indent=2)+'\n')
os.sched_setaffinity(0,{6});os.environ['RUST_MIN_STACK']='2097152'
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
 joined=h.owned_capture(command,capture,90,lambda:None);h.write(capture/'result.json',joined)
 results.append({'label':label,'whole_join':joined})
 if joined['returncode']!=0 or not joined['direct_child_joined'] or not joined['group_absent'] or not joined['closed_streams'] or joined['error'] or joined['retirement_error']:break
status='PASS' if len(results)==len(commands) and all(r['whole_join']['returncode']==0 for r in results) else 'FAIL_STOP_FIRST_FAILURE'
h.write(a/'RESULT.json',{'scope':__doc__,'status':status,'results':results,'native_acceptance':False,'actual_hour_workload':False})
for p in D.rglob('*'):
 if p.is_file() and p.suffix!='.o' and p.name not in ('producer-tests','controlled-launcher'):
  q=E/p.relative_to(D);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
print(json.dumps({'status':status,'commands_completed':len(results),'last_label':results[-1]['label'],'returns':[r['whole_join']['returncode'] for r in results]}))
