"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root preclock static row assembly using cached121 refs; no source-export traversal.
"""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;repo=Path('/home/holden/mckernel')
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
z=read(D/'PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json');f=read(D/'ROOT-ACTUAL-BUILD-FACTS.json');assert f['author']=='/root';A=Path(f['admission']);p=read(A/'PROFILE.SOURCE-ONLY.json');t=read(D/'PROFILE.TEMPLATE.SOURCE-ONLY.json');assert p['actual_nonce']==f['nonce'] and p['exact_commands']==t['exact_commands'] and p['inputs']['objects']==t['inputs']['objects']
rows=list(z['cached_source_refs']);seen={r['actual']['path'] for r in rows}
def add(r):
 if r['path'] not in seen:rows.append(dict(actual=r,fetched_equivalent_path=str(Path(r['path']).relative_to(repo))));seen.add(r['path'])
for n in z['future_static_names']:add(ref(A/n))
for n in z['future_private_metadata_names']:add(ref(D/n))
b=read(f['current_boundary']['path'])
for k in z['future_observer_refs_from_boundary']:
 assert ref(b[k]['path'])==b[k];add(b[k])
# Actual cohort review is an ordinary frozen source artifact, not runtime PASS.
actual_binding=read(D/'ROOT-ACTUAL-BINDINGS-1.json');add(actual_binding['mechanical_source_profile_review'])
# Publish the explicit new-window consumer closure before PREWARM and clocks.
add(ref(D/'PREPARATION-MANIFEST.json'))
operation=read(D/'ROOT-OPERATION-BINDINGS.json');assert operation['author']=='/root'
add(ref(D/'ROOT-OPERATION-BINDINGS.json'))
for key in ['successor','independent_review']:add(operation[key])
for row in operation['expected_subjects'].values():add(row)
v=dict(scope=z['scope'],status='ROOT116_CACHED_PUBLICATION_ROWS_PREPARED_NOT_FETCH_PROOF',runtime_authority=None,rows=rows,actual_fetched_commit=None,source_export_traversal_replayed=False)
f=A/'PUBLICATION-ROWS.PREPARED.json'
with f.open('x') as o:json.dump(v,o,indent=2);o.write('\n')
print(json.dumps(dict(status=v['status'],reference=ref(f),rows=len(rows))))
