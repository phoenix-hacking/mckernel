#!/usr/bin/python3
"""Execute only after dispatcher admits CPU6; single bounded compile/test."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,time,resource,signal
ROOT=Path(__file__).resolve().parent
RUSTC=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
if len(sys.argv)!=2:raise SystemExit('Fresh output directory required after CPU6 grant')
if os.sched_getaffinity(0)!={6}:raise SystemExit('CPU6-only inherited affinity required')
for row in json.loads((ROOT/'SOURCE-FREEZE.json').read_text())['files']:
 p=ROOT/row['path']
 if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise SystemExit('Frozen input mismatch: '+str(p))
if int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024<2*2**30:raise SystemExit('MemAvailable below 2GiB')
for p,floor in [('/home/holden',16*2**30),('/home/holden/mckernel-work/scratch',12*2**30)]:
 v=os.statvfs(p)
 if v.f_bavail*v.f_frsize<floor+64*2**20:raise SystemExit('Insufficient storage growth headroom')
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
usage=state.get('last_rate_limits',{}).get('primary',{}).get('usedPercent')
if state.get('phase')!='running' or state.get('pause_reason') or not isinstance(usage,(int,float)) or usage>=100:raise SystemExit('Included service guard not running below 100 percent')
OUT=Path(sys.argv[1]);OUT.mkdir(exist_ok=False)
(OUT/'PROFILE.json').write_text(json.dumps({'cpu':6,'jobs':1,'aggregate_plan_bytes':1073741824,'child_as_bytes':1006632960,'swap_expansion':False,'native_execution':False,'rustc_sha256':hashlib.sha256(RUSTC.read_bytes()).hexdigest()})+'\n')
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(1006632960,1006632960))
 resource.setrlimit(resource.RLIMIT_CPU,(30,30))
 resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
def capture(label,argv,seconds):
 (OUT/(label+'.command.json')).write_text(json.dumps(list(map(str,argv)))+'\n')
 start=time.monotonic();timed_out=False
 with (OUT/(label+'.stdout')).open('xb') as stdout,(OUT/(label+'.stderr')).open('xb') as stderr:
  p=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=limits,env=dict(os.environ,RUST_TEST_THREADS='1',RAYON_NUM_THREADS='1'))
  (OUT/(label+'.pid')).write_text(str(p.pid)+'\n')
  try:code=p.wait(timeout=seconds)
  except subprocess.TimeoutExpired:
   timed_out=True;os.killpg(p.pid,signal.SIGTERM)
   try:code=p.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 row={'pid':p.pid,'returncode':code,'timed_out':timed_out,'positive_wait':True,'owned_group_absent':absent,'elapsed_seconds':time.monotonic()-start}
 (OUT/(label+'.wait.json')).write_text(json.dumps(row)+'\n')
 if timed_out or code or not absent:raise SystemExit('First failed candidate preserved: '+label)
 return (OUT/(label+'.stdout')).read_bytes()
binary=OUT/'adoption-method-tests'
capture('compile',[str(RUSTC),'--edition=2021','--test','-Ccodegen-units=1',str(ROOT/'actual.rs'),'-o',str(binary)],35)
stdout=capture('test',[str(binary),'--test-threads=1'],15)
if b'3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out' not in stdout:raise SystemExit('Exact test witness absent')
(OUT/'RESULT.json').write_text(json.dumps({'status':'PASS_ACTUAL_BODY_ADAPTER_ONLY','test_cases':3,'negative_vectors':23,'native_acceptance':False,'postexit_producer_available':False,'destructor_ack':False})+'\n')
print('Three exact-body adoption differential tests passed; adapters only, no Linux ABI, module or native acceptance.')
