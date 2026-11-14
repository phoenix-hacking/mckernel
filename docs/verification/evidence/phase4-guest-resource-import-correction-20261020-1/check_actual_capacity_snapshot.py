"""One real capacity_snapshot entrypoint observation; no Docker/ownership/work."""
from pathlib import Path
import hashlib,json,resource,types,os
N=Path(__file__).resolve().parent
owner=types.ModuleType('actual_capacity_snapshot_entrypoint');owner.__file__=str(N/'current_fullcrate_owner.py')
exec(compile(Path(owner.__file__).read_bytes(),owner.__file__,'exec'),owner.__dict__)
request=json.loads((N/'request.json').read_bytes())
assert resource.getrlimit(resource.RLIMIT_FSIZE)==(33554432,33554432)
for key in ('work_root','owner_evidence_root','outer_capture_root','capacity_admission_root'):
 assert not os.path.lexists(request[key])
# Exercise exactly the entrypoint that failed before the journalled Docker info.
snapshot=owner.capacity_snapshot(request,'/home/holden')
assert snapshot['budgets']=={'host':1543503872,'scratch':771751936}
assert len(snapshot['records'])==3 and snapshot['devices']['host']!=snapshot['devices']['scratch']
for key in ('work_root','owner_evidence_root','outer_capture_root','capacity_admission_root'):
 assert not os.path.lexists(request[key])
raw=(json.dumps(snapshot,sort_keys=True,indent=2)+'\n').encode()
with (N/'actual-entrypoint-check-1'/'capacity-snapshot.json').open('xb') as f:f.write(raw)
print(json.dumps({'status':'PASS_ACTUAL_CAPACITY_SNAPSHOT_REAL_REQUEST_PRE_DOCKER','snapshot_sha256':hashlib.sha256(raw).hexdigest(),'devices':snapshot['devices'],'free':snapshot['free'],'budgets':snapshot['budgets'],'FSIZE':snapshot['FSIZE'],'Docker_calls':0,'ownership_records':0,'source_copies':0,'compilers':0}))
