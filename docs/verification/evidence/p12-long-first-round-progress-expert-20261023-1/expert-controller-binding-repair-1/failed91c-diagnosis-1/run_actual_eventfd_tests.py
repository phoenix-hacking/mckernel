"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
CPU0 ordinary Rust1.92 actual decoder/dispatch-body compile+fixture; no module/build/root/guest.
"""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,sys,time
D=Path(__file__).resolve().parent
E=Path('/home/holden/mckernel/docs/verification/evidence/p12-long-first-round-progress-expert-20261023-1/expert-controller-binding-repair-1/failed91c-diagnosis-1')
assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3'
h=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');raw=h.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
t=ast.parse(raw);end=next(i for i,n in enumerate(t.body) if isinstance(n,ast.FunctionDef) and n.name=='owned_capture');ns={'__file__':str(h)};exec(compile(ast.Module(body=t.body[:end+1],type_ignores=[]),str(h),'exec'),ns)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,ns['stop'])
os.sched_setaffinity(0,{0})
for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
os.environ['RUST_MIN_STACK']='2097152'
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());used=state['last_rate_limits']['primary']['usedPercent'];assert used<100
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;assert mem>=19<<30
capacity={}
for label,p,floor in [('HOST',Path('/home/holden/mckernel-work'),16<<30),('scratch',Path('/home/holden/mckernel-work/scratch'),12<<30)]:
 st=os.statvfs(p);available=st.f_bavail*st.f_frsize;assert available>=floor+(64<<20);capacity[label]=available
compiler=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
profile=dict(scope=__doc__,CPU=[0],AS_bytes=2<<30,CPU_seconds=60,wall_seconds=120,retirement_grace_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,RUST_MIN_STACK=2097152,codegen_units=1,MemAvailable=mem,aggregate_authorized_bytes=19<<30,capacity=capacity,included_usage_percent=used,compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((D/'smp_service.rs').read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256((D/'actual_eventfd_tests.rs').read_bytes()).hexdigest())
ns['write'](D/'PROFILE-AND-HEADROOM.json',profile)
commands=[('compile-1',[str(compiler),'--edition=2021','-D','warnings','-C','codegen-units=1','--test',str(D/'actual_eventfd_tests.rs'),'-o',str(D/'actual_eventfd_tests-1')]),('tests-1',[str(D/'actual_eventfd_tests-1'),'--test-threads=1','--nocapture'])]
results=[]
for name,argv in commands:
 out=D/name;out.mkdir(mode=0o700);command=dict(argv=argv,purpose=__doc__,shell=False,profile=profile);ns['write'](out/'command.json',command)
 result=ns['owned_capture'](command,out,120,lambda:None);ns['write'](out/'whole-join.json',result);results.append(dict(name=name,whole_join=result))
 if name=='compile-1' and result['returncode']==0:
  p=D/'actual_eventfd_tests-1';ns['write'](D/'DURABLE-COMPILED-FIXTURE-RECEIPT.json',dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,profile=profile))
 ok=result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None
 if not ok:break
final=dict(scope=__doc__,status='PASS_ACTUAL_RUST_EVENTFD_DECODER_AND_DISPATCH_FIXTURES' if len(results)==2 and ok else 'FAIL_FIRST_CANDIDATE_RETAINED',results=results,profile=profile,CPU0_released=all(r['whole_join']['direct_child_joined'] and r['whole_join']['group_absent'] and r['whole_join']['closed_streams'] for r in results),native_credit=False,notification_type_actual91c=None)
ns['write'](D/'ACTUAL-RUST-FIXTURE-RESULT.json',final)
for p in D.rglob('*'):
 if p.is_file() and p.name!='actual_eventfd_tests-1':
  q=E/p.relative_to(D);q.parent.mkdir(parents=True,exist_ok=True)
  if q.exists():assert q.read_bytes()==p.read_bytes()
  else:
   with q.open('xb') as f:f.write(p.read_bytes())
print(json.dumps(final))
