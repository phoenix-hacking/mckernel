# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One exact Root ordinary HOST dispatch using retained finite capture API.
from pathlib import Path
import json,time,hashlib,secrets,os,signal,sys
D=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-startup-retirement-host-preparation-source-1')
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
pfile=D/'BOUND-RECIPE.NOT-GRANTED.json';assert ref(pfile)['sha256']=='bd22cbfdc0b67a80a6aa79b8983ef3ae1b353ab2fccc565af7edf3206fa44d1c'
p=json.loads(pfile.read_bytes());runner.validate_profile(p);runner.verify(p['inputs']+[x['plan'] for x in p['leaves']])
now=time.time();cpuobs=D/'ROOT-ACTUAL-CPU6-EXCLUSION-1.json';write(cpuobs,dict(goal=runner.THREAD,cpu=6,ordinary_jobs_live=0,authorized_by='Root',observed_wall=now,basis='Root sole actual grant owner: no other ordinary HOST command launched; source workers and independent reviews only. CURRENT114 actual runner/holder tool joined0, retain conservative heavy reservation until independent free.'))
g=json.loads((D/'ROOT-GRANT.SCHEMA.NOT-A-GRANT.json').read_bytes());g.update(task_id=p['task_id'],profile_sha256=ref(pfile)['sha256'],runner_sha256=ref(B/'run_new12h_host.py')['sha256'],goal=runner.THREAD,fixed_deadline_UTC=p['fixed_deadline_UTC'],fixed_cutoffs=p['fixed_cutoffs'],resources=p['resources'],authorized=True,authorized_by='Root',cpu6_exclusive=True,other_cpu6_jobs=0,nonce=secrets.token_hex(16),issued_wall=now,expires_wall=now+180,reserved_jobs_other=4,reserved_GiB_other=12,heavy_jobs_current=1,cpu6_exclusion_observation=ref(cpuobs))
gfile=D/'ROOT-ACTUAL-FIVE-STEP-HOST-GRANT-1.json';write(gfile,g);runner.validate_grant(g,p,ref(pfile)['sha256'],ref(B/'run_new12h_host.py')['sha256'],time.time())
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
 checker=load(D/'check_actual_outputs.py','actual_semantic_checker');checker.check_tests((out/'step2/stdout').read_bytes(),p['expected_test_names']);checker.check_readelf((out/'step4/stdout').read_bytes())
 for i in range(5):assert (out/('step'+str(i))/'stderr').read_bytes()==b'','retained actual diagnostics not empty'
 overlay=p['retained_overlay_source'];assert ref(Path(overlay['path']))==overlay;m=load(Path(overlay['path']),'retained_overlay_validator');m._check_collector(Path(p['production_output']).read_bytes())
 write(out/'RESULTS.json',dict(status='PASS_FIVE_HOST_STEPS_22_CONTROLS_STATIC_ELF_PENDING_INDEPENDENT_REVIEW',results=results,artifact=ref(Path(p['production_output'])),actual_controls=22,native_acceptance=False))
 print(json.dumps(dict(status='PASS_HOST_ONLY',steps=5,controls=22,artifact=ref(Path(p['production_output'])),results=ref(out/'RESULTS.json'))))
except BaseException as e:
 write(out/'FIRST-FAILURE.json',dict(error=repr(e),results=results));print('HOST_FAILURE retained at '+str(out));raise
