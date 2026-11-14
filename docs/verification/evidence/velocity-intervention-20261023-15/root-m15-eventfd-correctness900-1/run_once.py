"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import json,os,hashlib,importlib.util,signal,resource,time
from pathlib import Path
D=Path(__file__).parent
P=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/eventfd-correctness-successor-1')
R=P/'SOURCE-CORRECTNESS-AND-ACTUAL-FIXTURE.READY-NOT-GRANTED.json'
assert hashlib.sha256(R.read_bytes()).hexdigest()=='ed1f85fd161c5b3b538755a11b6e858a8251ef4c01db4b958f3e32670b6dd978'
r=json.loads(R.read_text())
for ref in [r['source'],*r['fixtures'],r['commands'],*r['exact_provider_ABI']['actual_headers'],r['exact_provider_ABI']['actual_registration_consumer']]:
 assert hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()==ref['sha256']
assert not (P/'libihklib_eventfd.correctness.a').exists() and not (P/'ihklib_eventfd.correctness').exists()
assert os.getuid()==1000 and os.sched_getaffinity(0)=={0}
mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
assert mem>=25501368320
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('owned',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,h.stop)
for key,val in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(key,(val,val))
os.environ['RUST_MIN_STACK']='2097152'
h.write(D/'ROOT-GRANT.json',dict(scope=__doc__,CPU=6,ordinary_jobs=1,MemAvailable=mem,AS=2<<30,CPU_seconds=60,wall_seconds=90,retirement_seconds=6,ready_sha256=hashlib.sha256(R.read_bytes()).hexdigest(),independent_review='/root/m14_callback_review PASS_SOURCE_ABI_OWNEDFD_CORRECTNESS_AND_ONE_CONTROLLED_FIXTURE_READINESS'))
records=[];begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,102)
try:
 for i,c in enumerate(json.loads(Path(r['commands']['path']).read_text())):
  left=90-(time.monotonic()-begin);assert left>0
  out=D/str(i);out.mkdir();os.chdir(c['cwd'])
  command=dict(argv=['/usr/bin/taskset','-c','6',*c['argv']],purpose=c['purpose'])
  z=h.owned_capture(command,out,left,lambda:None);records.append(z);h.write(out/'WHOLE-JOIN.json',z)
  assert z['returncode']==0 and z['direct_child_joined'] and z['group_absent'] and z['closed_streams'] and z['error'] is None and z['retirement_error'] is None and not z['timed_out']
  if i==0:
   lines=[x.split('native-static-libs:',1)[1].strip() for x in (out/'stderr').read_text().splitlines() if 'native-static-libs:' in x]
   assert lines==['-lgcc_s -lutil -lrt -lpthread -lm -ldl -lc'],lines
 h.write(D/'RESULT.json',dict(status='PASS_ACTUAL_EVENTFD_CORRECTNESS_900_CONTROLLED_VECTORS',seconds=time.monotonic()-begin,records=records,native=False,default_library=False))
 print('PASS actual eventfd correctness900; no native/default claim')
except BaseException as e:
 h.write(D/'FIRST-FAILURE.json',dict(error=repr(e),records=records,seconds=time.monotonic()-begin));raise
finally:signal.setitimer(signal.ITIMER_REAL,0)
