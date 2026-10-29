"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact source-bound pure release validation only; no guard, transport or main call.
"""
import ast, copy, hashlib, json, math, os, re, stat, time
from pathlib import Path

D=Path(__file__).resolve().parent
P=D.parent
R=P/'current-guardian-source-1'
def ref(p):
    p=Path(p);raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
payload_path=P/'ROOT-CURRENT118-NORMAL-RETIREMENT.ACTUAL-PAYLOAD.json'
payload_ref=ref(payload_path)
assert payload_ref['bytes']==6141 and payload_ref['sha256']=='daf8d639c4f083c25da851afa9018aac001fd06feb788e4a7a586c45e8e0a971'
source=(R/'retire_exact_current118_stopped_container.py').read_text()
tree=ast.parse(source)
names={'Refusal','need','canonical','strict','reference','authenticated','validate_retained','validate_release'}
pure=ast.Module(body=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names],type_ignores=[])
ns=dict(Path=Path,json=json,hashlib=hashlib,stat=stat,re=re,os=os,D=R,LOCK=Path('/run/lock/mckernel-development.lock'))
exec(compile(pure,str(R/'retire_exact_current118_stopped_container.py'),'exec'),ns)
r=ns['strict'](payload_path.read_bytes())
assert canonical(r)==payload_path.read_bytes() and 'execution_review' not in r
b=ns['authenticated'](r['bindings'],True)
files=json.loads((R/'RUNTIME-FILES.json').read_text())
assert r['files']==files
for row in files.values():ns['authenticated'](row)
ns['validate_retained'](b)
admission_path=P/'ROOT-ACTUAL-GUARD-ADMISSION-1.json'
admission=json.loads(admission_path.read_text())
assert admission['status']=='PASS_ACTUAL_GUARD' and admission['runtime_effects'] is False
assert admission['result'][0]==1793249913.300967 and len(admission['result'])==3
assert all(math.isfinite(x) and 0<x<c for x,c in zip(admission['result'],r['cutoffs']))
assert admission['resources']['/home/holden']>=16<<30
assert admission['resources']['/home/holden/mckernel-work/scratch']>=12<<30
assert r['cutoffs']==[1793253600.0,1035703.5689321246,1051041.695980609]
assert len(json.loads(Path(r['current_ledger']['path']).read_text())['consumed_nonces'])==72
review=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',decision='PASS_EXECUTION',reviewer='/root/recovery_review',independent=True,implementation_ownership=False,release_payload_sha256=hashlib.sha256(canonical(r)).hexdigest(),release_payload=payload_ref,files=files,bindings=r['bindings'],source_review=r['source_review'],source_checkpoint=r['source_checkpoint'],source_publication=r['source_publication'],actual_guard_admission=ref(admission_path),current_ledger=r['current_ledger'],maximum_invocations=1,signals_allowed=0,records_released=[],approved_parent_profile=dict(uid_gid=[1000,1000,1000,1000],affinity=[0],argv=['/usr/bin/python3','-I','-B',str(R/'retire_exact_current118_stopped_container.py'),'--release','ROOT_FINAL_RELEASE_ABSOLUTE_PATH','--release-sha256','ROOT_FINAL_RELEASE_SHA256','--execute'],child_preexec_rlimits=dict(RLIMIT_AS=[2147483648,2147483648],RLIMIT_FSIZE=[33554432,33554432],RLIMIT_NOFILE=[256,256],RLIMIT_CORE=[0,0]),start_new_session=True,stdout_stderr='regular capture files',direct_join='os.wait4(exact_child_pid,0), portable wait conversion, Popen.returncode set; close streams and retain actual parent/child births, argv, wait terminal/CPU/maxrss',timeout_signal_retry=False,parent_native_mutex_held=False),constraints=['Grant only exact stopped CID d980 retirement; no recovery replay, compiler/heavy/native/controller action or record release.','Executor must recheck actual guard, all clocks, account/holds, live process/ownership/cgroup/resource/physical predicates before every spawn, with final stop/clock test immediately before Popen. Source admission receipt is not a substitute for these runtime checks.','Executor requires UID1000 CPU0 and exact hard/soft limits at entry. Existing permanent27:4 mutex remains under its reviewed custody; no parent duplication or inode replacement.','Parent must produce a genuine direct wait4 and closed streams. Any successful spawn/retirement uncertainty retains custody with no automatic signal or retry.','Passing result and parent join still require full source2 current capture and genuine currentfree acceptance; original client2232653 remains UNKNOWN, native/wholeM14 acceptance remains open.'],current_free=False,original_client_status='UNKNOWN',native_custody_released=False,runtime_executed_by_reviewer=False)
review_path=D/'EXECUTION-REVIEW.ACTUAL.json'
assert not review_path.exists()
review_path.write_text(json.dumps(review,indent=2)+'\n')
complete=copy.deepcopy(r);complete['execution_review']=ref(review_path)
try:out=ns['validate_release'](complete,b,files)
except BaseException:
    review_path.unlink()
    raise
assert str(out)==r['output']
proof=dict(scope=review['scope'],status='PASS_EXISTING_PURE_RELEASE_VALIDATOR',payload=payload_ref,execution_review=ref(review_path),retained_inputs_authenticated=True,validate_release_pass=True,guard_calls=0,process_starts=0,output_created=False)
(D/'EXECUTION-CHECKS.ACTUAL.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(dict(review=ref(review_path),checks=ref(D/'EXECUTION-CHECKS.ACTUAL.json'))))
