# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Root actual data fill only; no spawn/query/guard.
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
A=D.parent/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
r=json.loads((A/'ROOT-REQUEST-ADOPTION.json').read_text())
c=json.loads((D/'ROOT-ACTUAL-CURRENT-BOUNDARY.json').read_text())
b=json.loads((D/'ROOT-ACTUAL-OTHER-RESERVATIONS.json').read_text())
assert b['author']=='/root' and b['actual_reservations_attested'] is True
b.update(author='/root',decision='BIND_CURRENT110_ACTUAL_HELD_BUILD_RESOURCES',maximum_invocations=1,root_attests_only_intervening_holder_preparation=True,nonce=r['nonce'],request_sha256=r['request_sha256'],profile=ref(A/'PROFILE.SOURCE-ONLY.json'),request=ref(A/'ROOT-REQUEST-ADOPTION.json'),source_publication=ref(A/'ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json'),physical_observation=ref(A/'ROOT-PREHOLDER-PHYSICAL-1.json'),runner=ref(A/'run_build_only.py'),worker=ref(A/'build_only_worker.py'),input_export_authority=ref(A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'),nonce_ledger=c['nonce_ledger'],native_custody_clearance=c['native_custody_clearance'],current_boundary=ref(D/'ROOT-ACTUAL-CURRENT-BOUNDARY.json'))
with (A/'ROOT-ACTUAL-RESOURCE-INPUT-1.json').open('x') as f:json.dump(b,f,indent=2);f.write('\n')
print(json.dumps(dict(status='ROOT_ACTUAL_RESOURCE_DATA_FILLED',reference=ref(A/'ROOT-ACTUAL-RESOURCE-INPUT-1.json'))))
