"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root preclock cached-A2 publication row assembly; only newmetadata hashes, no120walk.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;D=R.parents[1];root=Path('/home/holden/mckernel')
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
z=read(R/'PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json');A=Path(z['actual_A4']);f=read(R/'ROOT-ACTUAL-ATTEMPT3-FACTS.json');p=read(A/'PROFILE.SOURCE-ONLY.json');t=read(D/'PROFILE.TEMPLATE.SOURCE-ONLY.json')
assert f['author']=='/root' and f['nonce']==z['nonce']==p['actual_nonce'] and f['admission']==str(A)
assert p['exact_commands']==t['exact_commands'] and p['inputs']['objects']==t['inputs']['objects']
rows=list(z['cached_rows']);seen={x['actual']['path'] for x in rows}
for name in z['new_staged_paths']:
 q=Path(name)
 if str(q) not in seen:rows.append(dict(actual=ref(q),fetched_equivalent_path=str(q.relative_to(root))));seen.add(str(q))
b=read(f['current_boundary']['path']);extra=[b['observer'],b['independent_current_boundary_review'],f['observer_schema'],f['observer_schema_review']]
for r in extra:
 assert ref(r['path'])==r
 if r['path'] not in seen:rows.append(dict(actual=r,fetched_equivalent_path=str(Path(r['path']).relative_to(root))));seen.add(r['path'])
v=dict(scope=z['scope'],status='ROOT_A4_CACHED_PUBLICATION_ROWS_PREPARED_NOT_FETCH_PROOF',runtime_authority=None,rows=rows,actual_fetched_commit=None,cached_actual120source_rehash=False)
f=A/'PUBLICATION-ROWS.PREPARED.json'
with f.open('x') as o:json.dump(v,o,indent=2);o.write('\n')
print(json.dumps(dict(status=v['status'],reference=ref(f),rows=len(rows))))
