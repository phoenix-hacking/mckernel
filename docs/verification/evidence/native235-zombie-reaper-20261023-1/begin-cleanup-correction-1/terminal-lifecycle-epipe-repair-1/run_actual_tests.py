# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import importlib.util,json,os,hashlib
P=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('accepted_owned_capture',H);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
used=state['last_rate_limits']['primary']['usedPercent'];assert used<100
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
assert mem>=4<<30
capacity={}
for name,root,floor in [('host',Path('/home/holden/mckernel'),16<<30),('scratch',Path('/home/holden/mckernel-work/scratch'),12<<30)]:
 st=os.statvfs(root);free=st.f_bavail*st.f_frsize;assert free>floor+(64<<20);capacity[name]=free
os.environ['RUST_MIN_STACK']='2097152'
base=['/usr/bin/taskset','--cpu-list','6','/usr/bin/prlimit','--as=2147483648','--cpu=60','--core=0','--fsize=33554432','--nofile=256','--']
commands=[('compile-1',base+['/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc','--edition=2021','-D','warnings','-C','codegen-units=1','--test',str(P/'actual_lifecycle_tests.rs'),'-o',str(P/'actual_lifecycle_tests-1')]),('tests-1',base+[str(P/'actual_lifecycle_tests-1'),'--test-threads=1','--nocapture'])]
for name,argv in commands:
 out=P/name;out.mkdir(mode=0o700)
 command={'argv':argv,'functional_scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'}
 m.write(out/'command.json',command)
 result=m.owned_capture(command,out,90,lambda:None)
 result.update(scope=command['functional_scope'],profile=dict(cpu=6,as_bytes=2<<30,cpu_seconds=60,wall_seconds=90,core=0,fsize_bytes=32<<20,nofile=256,rust_min_stack=2097152),capacity=capacity,mem_available=mem,included_usage_percent=used)
 m.write(out/'status.json',result)
 print(json.dumps(dict(name=name,returncode=result['returncode'],direct_child_joined=result['direct_child_joined'],group_absent=result['group_absent'],closed_streams=result['closed_streams'],seconds=result['seconds'])))
 if result['returncode']!=0 or not result['direct_child_joined'] or not result['group_absent'] or result['error'] or result['retirement_error']:raise SystemExit(1)
