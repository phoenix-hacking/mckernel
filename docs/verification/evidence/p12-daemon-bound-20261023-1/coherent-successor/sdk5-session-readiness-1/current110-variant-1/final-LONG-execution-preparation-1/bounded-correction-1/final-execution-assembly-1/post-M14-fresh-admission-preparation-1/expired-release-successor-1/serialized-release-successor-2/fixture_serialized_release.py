"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused actual full release consumers. Historicalclock is TESTONLY; no owner/Docker/workload executed.
"""
import hashlib,importlib.util,json,os,sys
from pathlib import Path
D=Path(__file__).resolve().parent;OLD=D.parent;M='/home/holden/mckernel-work/scratch/p12s5l1/m.json';P='/home/holden/mckernel-work/native-runs/l12a1/p';T=Path('/home/holden/mckernel-work/scratch/p12-LONG-TESTONLY-renewal-1')
assert sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12) and os.getuid()==os.geteuid()==1000
assert T.is_dir() and T.stat().st_uid==1000 and T.stat().st_mode&0o777==0o700
O=D/'actual-serialized-fixture-data-1';O.mkdir(mode=0o700)
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);return g
def digest(b):return hashlib.sha256(b).hexdigest()
def write(p,b):
 with p.open('xb') as f:f.write(b)
def file(v,name):
 b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode();assert sum(p.stat().st_size for p in T.iterdir())+len(b)<=131072;p=T/name;write(p,b);write(O/name,b);return p,b
def rejected(fn,why):
 try:fn()
 except ValueError as e:assert str(e)==why,(str(e),why);return str(e)
 raise AssertionError('invalid serialization accepted')
g=load(OLD/'source/long_transport.py','actual_failed_release_transport');path=Path('/home/holden/mckernel-work/scratch/p12s5l1/r-renewal-1.json');raw=g.stable(path);assert digest(raw)=='293fc5c64fb2fbc1891ce8fdab1fd0c41bd627a23bc0c63ab22a9abc8c710030';v=json.loads(raw);payload={k:x for k,x in v.items() if k!='independent_review'};canonical=g.canonical(payload);write(O/'actual-failed-release.json',raw);write(O/'actual-failed-payload.canonical',canonical)
assert canonical[-1:]==b'\n' and v['independent_review']['payload_sha256']==digest(canonical[:-1]) and v['independent_review']['payload_sha256']!=digest(canonical)
clock=lambda:v['expires_unix']-300
why=rejected(lambda:g.validate_release(str(path),digest(raw),M,v['nonce'],P,clock=clock,boot_id=v['boot_id']),'independent exact long release review')
v['independent_review']['payload_sha256']=digest(canonical);p,b=file(v,'TESTONLY-serialization-corrected-original.json');assert g.validate_release(str(p),digest(b),M,v['nonce'],P,clock=clock,boot_id=v['boot_id'])==v
new=load(D/'source/long_transport.py','actual_new_release_transport');x=json.loads((D/'LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json').read_bytes());x.update(status='PASS_EXECUTION_RELEASE',boot_id='TESTONLY-historical-clock',expires_unix=1200,author='TESTONLY-author');x['independent_review']=dict(status='PASS',reviewer='TESTONLY-independent-reviewer',implementation_ownership=False,payload_sha256=new.digest(new.canonical({k:z for k,z in x.items() if k!='independent_review'})));p,b=file(x,'TESTONLY-serialization-new-cohort.json');assert new.validate_release(str(p),digest(b),M,x['nonce'],P,clock=lambda:1000,boot_id='TESTONLY-historical-clock')==x
x['independent_review']['payload_sha256']=new.digest(new.canonical({k:z for k,z in x.items() if k!='independent_review'})[:-1]);p,b=file(x,'TESTONLY-serialization-new-cohort-bad-no-LF.json');rejected(lambda:new.validate_release(str(p),digest(b),M,x['nonce'],P,clock=lambda:1000,boot_id='TESTONLY-historical-clock'),why)
# Full actual manifest consumer joins every frozen source hash and original app/archive oracle.
o=load(D/'source/native_diagnostic_container_owner.py','actual_new_owner');diag,manifest=o.bound_manifest(M,'6c3c80bff36af0f96ce05f73294c37f035a3e12d7fdc3aeeef88fc7532c11471');assert len(o.SOURCE_HASHES)==156 and len(o.EXTRA_READONLY)==39 and manifest['pair_long_session']==new.PROFILE
report=dict(scope=__doc__,status='PASS_FOCUSED_ACTUAL_SERIALIZED_CONSUMERS_TESTONLY_NOT_RELEASE',interpreter=sys.executable,version=sys.version,checks=5,failed_original_sha256=digest(raw),failed_no_LF_payload_sha256=digest(canonical[:-1]),production_LF_payload_sha256=digest(canonical),failure_clause=why,actual_original_full_validate_release_rejected=True,corrected_original_full_validate_release_pass=True,new_cohort_full_validate_release_pass=True,new_cohort_no_LF_rejected=True,full_bound_manifest_source_rows=156,readonly_roots=39,clock_override='Historical failed release expiry-300 and TESTONLY1000 only. Future final release MUST run realclock/no boot override.',root=0,Docker=0,workload=0,final_release_actual_consumer=None,native_acceptance=False,retained_TESTONLY_scratch_bytes=sum(p.stat().st_size for p in T.iterdir()))
write(D/'ACTUAL-SERIALIZED-CONSUMER-RESULT.json',(json.dumps(report,indent=2,sort_keys=True)+'\n').encode());print(json.dumps(report,sort_keys=True))
