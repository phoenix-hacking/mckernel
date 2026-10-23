"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,time
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('accepted_supervisor','/home/holden/mckernel/scripts/application-tests/supervisor.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
commands=json.loads((H/'TWO-ORDINARY-COMMANDS.ACTUAL.json').read_bytes());results=[];start=time.monotonic()
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
for index,argv in enumerate(commands['argvs'],1):
 cap=H/('actual-ordinary-'+str(index));report=H/('ACTUAL-ORDINARY-'+str(index)+'-CAPTURE-RESULT.json');assert not cap.exists()and not report.exists();r=s.run_supervised(argv,cwd=str(H),env=dict(PATH='/usr/bin:/bin',HOME=str(H),TMPDIR=str(H),LC_ALL='C'),attempt_dir=str(cap),timeout_seconds=30,cleanup_timeout_seconds=3,stdout_limit_bytes=8388608,stderr_limit_bytes=8388608);save(report,r);results.append(dict(index=index,report=ref(report),status=r['status'],wait_status=r.get('wait_status'),seconds=r['elapsed_seconds']));print(json.dumps(results[-1]),flush=True)
 good=r['status']=='COMPLETED'and r['cleanup_complete']and r['wait_status']==dict(kind='exited',code=0)and r['descendants']==[]and all(v['eof']and not v['truncated']and not v['discarded_observed_bytes']for v in r['streams'].values())
 if not good:save(H/'FIRST-ORDINARY-FAILURE.json',dict(scope=__doc__,results=results,automatic_retry=False));raise RuntimeError('stopfirstordinaryfailure')
save(H/'TWO-ORDINARY-WHOLE-JOIN.json',dict(scope=__doc__,status='PASS_COHERENT_OBSERVER_SOURCE_AND_REUSED_MANIFEST_PACKET_ONLY',steps=results,seconds=time.monotonic()-start,root_operations=0,Docker_operations=0,compiler_operations=0,CPIO_repatches=0,native_runs=0));print('PASS2ordinarywholejoin',flush=True)
