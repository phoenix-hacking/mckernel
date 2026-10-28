"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root preclock static row assembly using cached123 refs; no source-export traversal.
"""
from pathlib import Path
import hashlib,json
D=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/prepared118-current63-1/cohort');repo=Path('/home/holden/mckernel')
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
z=read(D/'PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json');f=read(D/'ROOT-ACTUAL-BUILD-FACTS.json');assert f['author']=='/root';A=Path(f['admission']);p=read(A/'PROFILE.SOURCE-ONLY.json');t=read(D/'PROFILE.TEMPLATE.SOURCE-ONLY.json');assert p['actual_nonce']==f['nonce'] and p['exact_commands']==t['exact_commands'] and p['inputs']['objects']==t['inputs']['objects']
rows=list(z['cached_source_refs']);seen={r['actual']['path'] for r in rows}
def add(r):
 if r['path'] not in seen:rows.append(dict(actual=r,fetched_equivalent_path=str(Path(r['path']).relative_to(repo))));seen.add(r['path'])
for n in z['future_static_names']:add(ref(A/n))
for directory in p['inputs']['source_directory_exports']:
 for source in read(directory['manifest']['path'])['files']:add(source['snapshot'])
for source in p['inputs']['postimages']:add(source['postimage'])
for source in p['inputs']['external_relative_modules']:add(source['source'])
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

# Publication-only correction: explicit loader roles; retained payloads remain opaque.
core_ref={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/prepared118-current63-1/typed_current_boundary.py', 'bytes': 12354, 'sha256': '00483f2b97dbd03d76ee397ab9c80c050821ba1f705168d3606822b796e87514'}
assert ref(core_ref['path'])==core_ref
import importlib.util
publication_helper_ref={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/publication-runtime-closure-correction-source-1/publication_runtime_closure.py', 'bytes': 15921, 'sha256': '2b4c4be8e7dd2c1a0ff0c3b5853d09d5b21b5564d9a6d0ffb2fabf1feae58a1c'}
assert ref(publication_helper_ref['path'])==publication_helper_ref
add(publication_helper_ref);add(ref(__file__))
_spec=importlib.util.spec_from_file_location('exact118_runtime_data_closure',publication_helper_ref['path'])
_typed=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_typed)
typed_ref=actual_binding['typed_current_boundary_binding']
selection_ref={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-recursive-fixture-expert-20261028-1/next-current-boundary-successor-1/prepared118-current63-1/UPSTREAM-SELECTION.SOURCE-ONLY.json', 'bytes': 2114, 'sha256': '596600fab7c3e8551c564187cce52e8207ecf088fe4ac618cf74028eeaee5312'}
aliases_ref=actual_binding['runtime_data_fetched_aliases'];assert ref(aliases_ref['path'])==aliases_ref
aliases=read(aliases_ref['path']);assert aliases['author']=='/root' and aliases['runtime_authority'] is None
add(aliases_ref)
for closure_row in _typed.runtime_data_rows(typed_ref,selection_ref,ref(D/'ROOT-OPERATION-BINDINGS.json')):
 source=closure_row['actual']
 if source['path'] in seen:continue
 if closure_row['requires_explicit_fetched_alias']:
  alias=aliases['aliases'][source['path']]
  actual=ref(repo/alias);assert (actual['bytes'],actual['sha256'])==(source['bytes'],source['sha256'])
  rows.append(dict(actual=source,fetched_equivalent_path=alias));seen.add(source['path'])
 else:add(source)

v=dict(scope=z['scope'],status='ROOT118_CACHED_PUBLICATION_ROWS_PREPARED_NOT_FETCH_PROOF',runtime_authority=None,rows=rows,actual_fetched_commit=None,source_export_traversal_replayed=False)
f=A/'PUBLICATION-ROWS.PREPARED.json'
with f.open('x') as o:json.dump(v,o,indent=2);o.write('\n')
print(json.dumps(dict(status=v['status'],reference=ref(f),rows=len(rows))))
