#!/usr/bin/python3
"""Run only after dispatcher grant; CPU6, one serial child, 1GiB planning cap."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,time,resource
ROOT=Path(__file__).resolve().parent
RUSTC='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
if len(sys.argv)!=2:raise SystemExit('Usage: run-harness.py FRESH_OUTPUT_DIRECTORY; dispatcher admission required')
OUT=Path(sys.argv[1]);OUT.mkdir(exist_ok=False)
if os.sched_getaffinity(0)!={6}:raise SystemExit('CPU6-only inherited affinity required')
for manifest in [ROOT/'SOURCE-FREEZE.json',ROOT/'harness-1/HARNESS-FREEZE.json']:
 data=json.loads(manifest.read_text())
 for record in data['files']:
  p=ROOT/record['path']
  if hashlib.sha256(p.read_bytes()).hexdigest()!=record['sha256']:raise SystemExit('Frozen input mismatch: '+str(p))
(OUT/'PROFILE.json').write_text(json.dumps({'cpus':[6],'jobs':1,'memory_plan_bytes':1073741824,'swap_expansion':False,'subprocesses':'one direct child at a time','compile_timeout_seconds':60,'test_timeout_seconds':30,'native_execution':False})+'\n')
def limits():
 # Leave 64MiB planning headroom for the Python observer. No child recursion.
 resource.setrlimit(resource.RLIMIT_AS,(1006632960,1006632960))
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
def capture(label,command,seconds):
 (OUT/(label+'.command.json')).write_text(json.dumps(command)+'\n')
 start=time.monotonic();p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=limits,env=dict(os.environ,RUST_TEST_THREADS='1',RAYON_NUM_THREADS='1'))
 (OUT/(label+'.pid')).write_text(str(p.pid)+'\n')
 timed_out=False
 try:stdout,stderr=p.communicate(timeout=seconds)
 except subprocess.TimeoutExpired:
  timed_out=True
  import signal
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:stdout,stderr=p.communicate(timeout=5)
  except subprocess.TimeoutExpired:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   stdout,stderr=p.communicate()
  (OUT/(label+'.timeout')).write_text('timeout\n')
 (OUT/(label+'.stdout')).write_bytes(stdout);(OUT/(label+'.stderr')).write_bytes(stderr)
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 record={'pid':p.pid,'returncode':p.returncode,'timed_out':timed_out,'waited':True,'owned_group_absent':absent,'elapsed_seconds':time.monotonic()-start}
 (OUT/(label+'.wait.json')).write_text(json.dumps(record)+'\n')
 if timed_out or p.returncode or not absent:raise SystemExit('Preserved first failure: '+label)
 return stdout
for variant,count in [('original',1),('candidate',5)]:
 source=ROOT/'harness-1'/variant/'actual.rs';binary=OUT/(variant+'-actual')
 command=[RUSTC,'--edition=2021','--test','-Ccodegen-units=1',str(source),'-o',str(binary)]
 if variant=='original':command[1:1]=['--cfg','original']
 capture(variant+'-compile',command,60)
 stdout=capture(variant+'-test',[str(binary),'--test-threads=1','--nocapture'],30)
 expected=f'{count} passed; 0 failed; 0 ignored; 0 measured; 0 filtered out'.encode()
 if expected not in stdout:raise SystemExit('Unexpected test count: '+variant)
(OUT/'RESULT.json').write_text(json.dumps({'status':'PASS_ACTUAL_BODY_ADAPTER_ONLY','original_expected_defect_witnesses':1,'candidate_cases':5,'native_acceptance':False})+'\n')
print('One baseline witness and five candidate actual-body cases passed; adapter-only, no native acceptance.')
