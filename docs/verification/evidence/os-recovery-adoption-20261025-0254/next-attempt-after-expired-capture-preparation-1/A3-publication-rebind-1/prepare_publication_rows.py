"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mechanical A3 publication rebind of independently accepted role-aware producer.
assemble() is read-only metadata composition; __main__ alone writes fresh row output.
"""
from pathlib import Path
import hashlib,json
D=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort');repo=Path('/home/holden/mckernel')
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def reviewer_static_refs(A,f,b,boundary):
 # Match the existing handoff filler's exact static_refs, except the publication
 # proof which can only exist after these rows have been fetched and verified.
 refs=read(D/'REVIEWER-BINDINGS.TEMPLATE.NOT-AUTHORITY.json')['static_refs']
 refs.pop('source_publication')
 for k,n in dict(profile='PROFILE.SOURCE-ONLY.json',input_export='ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json',request_payload='STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json',request_adoption='ROOT-REQUEST-ADOPTION.json',runner='run_build_only.py',worker='build_only_worker.py',holder_source='hold_and_run_build_only.py',publisher_source='publish_approved_ready.py').items():refs[k]=ref(A/n)
 refs.update(nonce_ledger=f['current_nonce_ledger'],native_custody_clearance=f['current_free'],current_boundary=f['current_boundary'],observer_source=boundary['observer'],source_adoption=b['source_adoption'],source_review=b['independent_source_profile_review'],mechanical_review=b['mechanical_source_profile_review'],current_boundary_review=boundary['independent_current_boundary_review'],capture_source=ref(D/'capture_resources.py'),observer_schema=f['observer_schema'],observer_schema_review=f['observer_schema_review'])
 assert len(refs)==25 and all(type(row)is dict for row in refs.values())
 return refs
CACHE_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-publication-rebind-1/PUBLICATION-ROWS.CACHED-SOURCE-REFS.A3.json', 'bytes': 24431, 'sha256': '209e88b5d31476432228a3ab0d5ad375ff30fe3980b6a73d77d034e297e4cf3e'}
ROOT_BINDINGS_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/cohort/ROOT-ACTUAL-BINDINGS-1.json', 'bytes': 6990, 'sha256': 'b36717972afe751fb65e8add1a7ff11500d9317e926337273641a2deda2676ac'}
CORE_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/typed_current_boundary.py', 'bytes': 23327, 'sha256': 'f893832e6f3b5a547bf357aa9c6b79525dbe17c64096c50c81f0462eb5b29b90'}
HELPER_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-publication-rebind-1/a3_runtime_data_rows.py', 'bytes': 2605, 'sha256': 'b2991d45870ac405c0571e8e85bf80dce9192d1314849c64c58f3231f4a1a584'}
SELECTION_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/UPSTREAM-SELECTION.SOURCE-ONLY.json', 'bytes': 2114, 'sha256': '596600fab7c3e8551c564187cce52e8207ecf088fe4ac618cf74028eeaee5312'}
FILES_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/FILES.json', 'bytes': 18054, 'sha256': '13b57bbb7f2b223d04873af1beba337aad5e4eac2ca94a1761bab0a14023e685'}
MAP_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/EXACT-OPERATION-SOURCE-SUBJECTS.json', 'bytes': 12105, 'sha256': '1d618153a6b8309a47e69edb4c6524faaab353853dcf4b6dbb81070175b86bf3'}
SOURCE_REVIEW_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-next118-restart-independent-review-20261028-1/A3-SOURCE-CORRECTION-REVIEW-1/REVIEW.json', 'bytes': 7993, 'sha256': '9b5c34b791302b8d9d54696be059b6dba2caa86d841590e14b846bae13a3286f'}
ACTUAL_MANIFEST_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261028T1911/CURRENT118-FRESH-A3-1/PREPARATION-MANIFEST.SCHEMA-ROW-CORRECTED.json', 'bytes': 12031, 'sha256': '3e8b1a3a5b1085cb7471f48a340ae716d9eb636f71a9bc982ad763bbef12194e'}
FRONTIER_INPUTS_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/FRONTIER-INPUTS.SOURCE-ONLY.json', 'bytes': 5918, 'sha256': 'a46f6b41ea220d1297e92f1747b33311f4a11a61355714d94c6a971f1936910c'}
JOB_ALIAS_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261028T1911/CURRENT118-TYPED-INTEGRATION-1/AGGREGATE-JOB-AUTHORIZATION-ALIAS.json', 'bytes': 767, 'sha256': '454c57276bd462222ae06c07936ea80f41d8e1e66765d339fc19184ba6459f8d'}

def assemble():
 assert ref(CACHE_REF['path'])==CACHE_REF;z=read(CACHE_REF['path']);f=read(D/'ROOT-ACTUAL-BUILD-FACTS.json');assert f['author']=='/root';A=Path(f['admission']);p=read(A/'PROFILE.SOURCE-ONLY.json');t=read(D/'PROFILE.TEMPLATE.SOURCE-ONLY.json');assert p['actual_nonce']==f['nonce'] and p['exact_commands']==t['exact_commands'] and p['inputs']['objects']==t['inputs']['objects']
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
 assert ref(ROOT_BINDINGS_REF['path'])==ROOT_BINDINGS_REF;actual_binding=read(ROOT_BINDINGS_REF['path']);actual_manifest_ref=actual_binding['preparation_manifest'];add(actual_binding['mechanical_source_profile_review'])
 for row in reviewer_static_refs(A,f,actual_binding,b).values():add(row)
 # Publish the explicit new-window consumer closure before PREWARM and clocks.
 assert actual_manifest_ref==ACTUAL_MANIFEST_REF and ref(actual_manifest_ref['path'])==actual_manifest_ref;add(actual_manifest_ref)
 operation=read(D/'ROOT-OPERATION-BINDINGS.json');assert operation['author']=='/root'
 add(ref(D/'ROOT-OPERATION-BINDINGS.json'))
 for key in ['successor','independent_review']:add(operation[key])
 for row in operation['expected_subjects'].values():add(row)
 
 # Publication-only correction: explicit loader roles; retained payloads remain opaque.
 core_ref=CORE_REF
 assert ref(core_ref['path'])==core_ref
 import importlib.util
 publication_helper_ref=HELPER_REF
 assert ref(publication_helper_ref['path'])==publication_helper_ref
 add(publication_helper_ref);add(ref(__file__))
 for row in [CACHE_REF,FILES_REF,MAP_REF,SOURCE_REVIEW_REF,FRONTIER_INPUTS_REF]:add(row)
 _spec=importlib.util.spec_from_file_location('exact118_runtime_data_closure',publication_helper_ref['path'])
 _typed=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_typed)
 typed_ref=actual_binding['typed_current_boundary_binding']
 selection_ref=SELECTION_REF
 aliases_ref=actual_binding['runtime_data_fetched_aliases'];assert ref(aliases_ref['path'])==aliases_ref
 aliases=read(aliases_ref['path']);assert aliases['author']=='/root' and aliases['runtime_authority'] is None
 add(aliases_ref)
 assert ref(JOB_ALIAS_REF['path'])==JOB_ALIAS_REF
 job_alias=read(JOB_ALIAS_REF['path']);assert job_alias['author']=='/root' and job_alias['runtime_authority'] is None
 assert job_alias['actual']['path'] not in aliases['aliases'];aliases['aliases'][job_alias['actual']['path']]=job_alias['fetched_equivalent_path']
 add(JOB_ALIAS_REF)
 job_actual=ref(repo/job_alias['fetched_equivalent_path']);assert (job_actual['bytes'],job_actual['sha256'])==(job_alias['actual']['bytes'],job_alias['actual']['sha256'])
 rows.append(dict(actual=job_alias['actual'],fetched_equivalent_path=job_alias['fetched_equivalent_path']));seen.add(job_alias['actual']['path'])
 for closure_row in _typed.runtime_data_rows(typed_ref,selection_ref,ref(D/'ROOT-OPERATION-BINDINGS.json')):
  source=closure_row['actual']
  if source['path'] in seen:continue
  if closure_row['requires_explicit_fetched_alias']:
   alias=aliases['aliases'][source['path']]
   actual=ref(repo/alias);assert (actual['bytes'],actual['sha256'])==(source['bytes'],source['sha256'])
   rows.append(dict(actual=source,fetched_equivalent_path=alias));seen.add(source['path'])
  else:add(source)
 
 v=dict(scope=z['scope'],status='ROOT118_CACHED_PUBLICATION_ROWS_PREPARED_NOT_FETCH_PROOF',runtime_authority=None,rows=rows,actual_fetched_commit=None,source_export_traversal_replayed=False)
 return A,v

if __name__=='__main__':
 A,v=assemble();f=A/'PUBLICATION-ROWS.PREPARED.json'
 with f.open('x')as o:json.dump(v,o,indent=2);o.write('\n')
 print(json.dumps(dict(status=v['status'],reference=ref(f),rows=len(v['rows']))))
