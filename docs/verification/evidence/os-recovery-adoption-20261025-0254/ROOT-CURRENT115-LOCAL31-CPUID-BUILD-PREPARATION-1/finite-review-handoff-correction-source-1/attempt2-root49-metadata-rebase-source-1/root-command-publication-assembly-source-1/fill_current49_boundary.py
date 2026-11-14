"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-authorized exact current49 boundary DATA fill only, no observer/guard/query.
"""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parents[3];C=D/'finite-review-handoff-correction-source-1';P=D/'current49-attempt2-observer-source-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
f=json.loads((P/'CURRENT49-OBSERVER-BINDING.FRAGMENT.NOT-AUTHORITY.json').read_text())
review=ref(P/'independent-source-review-1/REVIEW.json')
assert review['sha256']=='0d7fcf153012ba572d0ff91ba8ceba18b7e10d61c54c2d86a06bf37a5d633f3c'
for k in ['nonce_ledger','native_custody_clearance','observer']:assert ref(Path(f[k]['path']))==f[k]
b=dict(author='/root',decision='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY',nonce_ledger=f['nonce_ledger'],native_custody_clearance=f['native_custody_clearance'],observer=f['observer'],independent_current_boundary_review=review,root_attests_exact_current_boundary=True)
p=C/'ROOT-ACTUAL-CURRENT-BOUNDARY.json'
with p.open('x') as o:json.dump(b,o,indent=2);o.write('\n')
print(json.dumps(dict(status='ROOT_ACTUAL_CURRENT49_BOUNDARY_DATA_FILLED_NO_OBSERVATION',reference=ref(p))))
