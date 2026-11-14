from pathlib import Path
import hashlib,json,runpy,os
C=Path(__file__).resolve().parent;L=C.parent
assert os.getuid()==os.geteuid()==1000
r=json.loads((C/'pinned-launcher-request.PAYLOAD-NOT-RELEASED.json').read_bytes());original=dict(r);r['provenance_sha256']='0'*64
assert [k for k in r if r[k]!=original[k]]==['provenance_sha256']
results=[]
for name,path,digest,expected in [('OLD',L/'bound-reviewed-source-1/launcher_only_container_owner.py','d8a8a789be0a5f2df8ebbb82566fbe6ddb1dd26025c90c490a62ef85a11e9ad1','offline driver release hash'),('CORRECTED',C/'bound-source-1/launcher_only_container_owner.py','c9eb78a4c1113f6bee6b809fc07d215978b2914f6edefe73d85757e32dea2f42','offline provenance bytes differ')]:
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest;m=runpy.run_path(str(path))
 try:m['_validate_request'](r)
 except m['OwnerError'] as exc:
  assert type(exc)is m['OwnerError'] and str(exc)==expected,(name,type(exc).__name__,str(exc));results.append(dict(module=name,source_sha256=digest,refusal=str(exc),exception_type=type(exc).__name__));print(json.dumps(results[-1]),flush=True)
 else:raise AssertionError('required refusal missing '+name)
print(json.dumps(dict(status='PASS_ACTUAL_OLD_NEW_DRIVER_BOUNDARY_CONTROL',only_in_memory_request_change='provenance_sha256=64zero',cases=results,production_driver_sha256=r['driver_sha256'],actual_build=False,native_acceptance=False)),flush=True)
