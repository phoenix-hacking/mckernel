# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One exact Root ordinary HOST dispatch using retained finite capture API.
from pathlib import Path
import json,time,hashlib,secrets,os,signal,sys
D=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-host-preparation-source-1')
E=D.parent;B=E/'ordinary-host-new12h-runner-source-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
import importlib.util
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
runner=load(B/'run_new12h_host.py','ordinary_runner')
assert ref(B/'run_new12h_host.py')['sha256']=='6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
pfile=D/'BOUND-RECIPE.NOT-GRANTED.json';assert ref(pfile)['sha256']=='e56a1e915c2bb696d6c5bf4e4c8887fa95be3c589a0646be14b185e5f206e8d4'
p=json.loads(pfile.read_bytes());runner.validate_profile(p);runner.verify(p['inputs']+[x['plan'] for x in p['leaves']])
os.sched_setaffinity(0,{6})
now=time.time();cpuobs=D/'ROOT-ACTUAL-CPU6-EXCLUSION-1.json';write(cpuobs,dict(goal=runner.THREAD,cpu=6,ordinary_jobs_live=0,authorized_by='Root',observed_wall=now,basis='Root allpriorordinary jobs positivejoined; F06lastreader12590PASS. A2holder1831939/birth95475556 unlaunched/reserved4CPU12GiB, noREADY/Runner/Output/Docker; counted conservatively. No otherCPU6job.'))
g=dict(scope=p['scope'],task_id=p['task_id'],profile_sha256=ref(pfile)['sha256'],runner_sha256=ref(B/'run_new12h_host.py')['sha256'],goal=runner.THREAD,fixed_deadline_UTC=p['fixed_deadline_UTC'],fixed_cutoffs=p['fixed_cutoffs'],resources=p['resources'],authorized=True,authorized_by='Root',cpu6_exclusive=True,other_cpu6_jobs=0,nonce=secrets.token_hex(16),issued_wall=now,expires_wall=now+180,reserved_jobs_other=4,reserved_GiB_other=12,heavy_jobs_current=1,cpu6_exclusion_observation=ref(cpuobs),source_profile_review=ref(D/'independent-source-profile-review-1/REVIEW.json'),prior_complete_Root49=ref(E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER49.json'),maximum_invocations=1,native_authority=None)
gfile=D/'ROOT-ACTUAL-THREE-STEP-HOST-GRANT-1.json';write(gfile,g);runner.validate_grant(g,p,ref(pfile)['sha256'],ref(B/'run_new12h_host.py')['sha256'],time.time())
write(D/'ROOT-ACTUAL-DISPATCH-STARTED.json',dict(pid=os.getpid(),starttime=int(Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split()[19]),grant=ref(gfile),source=ref(Path(__file__))))
admit=load(B/'admission_new12h.py','ordinary_admission').admission;cap=load(runner.CAPTURE,'ordinary_capture')
assert ref(runner.CAPTURE)['sha256']==runner.CAPTURE_SHA
for sig in cap.STOP_SIGNALS:signal.signal(sig,cap.stop)
os.sched_setaffinity(0,{6})
def guard():
 assert time.time()<g['expires_wall'];runner.verify(p['inputs']+[x['plan'] for x in p['leaves']]);return admit(p)
initial=guard();out=Path(p['capture_root']);output=Path(p['leaves'][0]['output']);assert not out.exists() and not output.exists();out.mkdir(mode=0o700);output.mkdir(mode=0o700)
cap.write(out/'CONSUMED-GRANT.json',dict(nonce=g['nonce'],profile=ref(pfile),grant=ref(gfile),admission=initial,source=ref(Path(__file__))))
os.environ.clear();os.environ.update(PATH='/usr/bin:/bin',LC_ALL='C',RUST_BACKTRACE='0',PYTHONDONTWRITEBYTECODE='1')
results=[]
try:
 for i,c in enumerate(p['commands']):
  admission=guard();step=out/('step'+str(i));step.mkdir(mode=0o700);cap.write(step/'command.json',c);cap.write(step/'admission.json',admission);os.chdir(c['cwd']);j=cap.owned_capture(c,step,90,runner.limits);cap.write(step/'whole-join.json',j);results.append(dict(index=i,purpose=c['purpose'],join=j));cap.write(out/('STEP'+str(i)+'.json'),results[-1]);assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'],'first HOST failure; preserve prefix'
 checker=load(D/'check_actual_outputs.py','actual_semantic_checker');facts=checker.qualify(p)
 write(D/'ACTUAL-COLLECTOR-BINDING-FACTS.json',facts)
 write(out/'RESULTS.json',dict(status='PASS_THREE_HOST_STEPS_26_CONTROLS_REUSED_GENERIC_ELF_PENDING_INDEPENDENT_REVIEW',results=results,artifact=p['reused_actual_collector_artifact'],actual_controls=26,production_recompiled=False,native_acceptance=False))
 print(json.dumps(dict(status='PASS_HOST_ONLY',steps=3,controls=26,artifact=p['reused_actual_collector_artifact'],results=ref(out/'RESULTS.json'))))
except BaseException as e:
 write(out/'FIRST-FAILURE.json',dict(error=repr(e),results=results));print('HOST_FAILURE retained at '+str(out));raise
