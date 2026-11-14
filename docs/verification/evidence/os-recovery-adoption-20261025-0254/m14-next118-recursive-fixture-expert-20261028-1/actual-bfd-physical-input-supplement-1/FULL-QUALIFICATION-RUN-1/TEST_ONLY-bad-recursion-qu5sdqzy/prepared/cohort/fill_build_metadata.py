"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Existing A4 static/handoff data API, current118-build slots; no capture/guard/approval.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json
D=Path(__file__).resolve().parent;E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
Q=D
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert isinstance(r,dict) and ref(r['path'])==r;return Path(r['path'])
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['static','handoff'],required=True);p.add_argument('--cohort-source-review');p.add_argument('--origin-binding-input');a=p.parse_args();f=read(D/'ROOT-ACTUAL-BUILD-FACTS.json');assert f['author']=='/root';A=Path(f['admission']);assert A.parent==E and A.name.startswith('ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-')
 for k in ['nonce_reservation','current_nonce_ledger','current_free','current_boundary','observer_schema','observer_schema_review']:auth(f[k])
 boundary=read(f['current_boundary']['path']);schema=read(f['observer_schema']['path']);review=read(f['observer_schema_review']['path']);assert f['current_boundary']==ref(D/'ROOT-ACTUAL-CURRENT-BOUNDARY.json') and boundary['nonce_ledger']==f['current_nonce_ledger'] and boundary['native_custody_clearance']==f['current_free']
 if a.phase=='static':
  assert not A.exists() and a.cohort_source_review and a.origin_binding_input;b=read(D/'ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');b.update(read(a.origin_binding_input));b.update(author='/root',decision='MATERIALIZE_REVIEWED_CURRENT118_STATIC_INPUTS_AND_HOLDER_ONLY',root_attests_exact_UID1000_readonly_exports=True,nonce=f['nonce'],admission=str(A),preparation_manifest=ref(D/'PREPARATION-MANIFEST.json'),nonce_ledger=f['current_nonce_ledger'],native_custody_clearance=f['current_free'],current_boundary=f['current_boundary'],source_adoption=f['source_adoption'],mechanical_source_profile_review=ref(Path(a.cohort_source_review)))
  for k in ['source_adoption','mechanical_source_profile_review','actual_origin_producer','actual_generated_header','actual_generated_metadata','actual_origin_binding','actual_Rust_environment','actual_CMake_origin','rust_export_manifest']:auth(b[k])
  write(D/'ROOT-ACTUAL-BINDINGS-1.json',b);print(json.dumps(dict(status='ROOT118_STATIC_DATA_ONLY',reference=ref(D/'ROOT-ACTUAL-BINDINGS-1.json'))));return
 b=read(D/'ROOT-ACTUAL-BINDINGS-1.json');assert b['nonce']==f['nonce'] and b['admission']==str(A) and not (A/'OUTPUT').exists()
 v=read(Q/'REVIEWER-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');refs=v['static_refs']
 for k,n in dict(profile='PROFILE.SOURCE-ONLY.json',input_export='ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json',request_payload='STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json',request_adoption='ROOT-REQUEST-ADOPTION.json',source_publication='ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json',runner='run_build_only.py',worker='build_only_worker.py',holder_source='hold_and_run_build_only.py',publisher_source='publish_approved_ready.py').items():refs[k]=ref(A/n)
 refs.update(nonce_ledger=f['current_nonce_ledger'],native_custody_clearance=f['current_free'],current_boundary=f['current_boundary'],observer_source=boundary['observer'],source_adoption=b['source_adoption'],source_review=b['independent_source_profile_review'],mechanical_review=b['mechanical_source_profile_review'],current_boundary_review=boundary['independent_current_boundary_review'],capture_source=ref(D/'capture_resources.py'),observer_schema=f['observer_schema'],observer_schema_review=f['observer_schema_review'])
 assert all(isinstance(r,dict) for r in refs.values())
 for k in ['nonce_ledger','native_custody_clearance','observer_source','current_boundary_review','observer_schema','observer_schema_review']:auth(refs[k])
 path=D/'boundary_join.py';assert ref(path)['sha256']=='5d6e57f561d108c81311ba63422f693e0091a60b37077687703090051c0b425b';s=importlib.util.spec_from_file_location('retained_A4_pure_six_join',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.validate_boundary_join(refs,boundary,schema,review)
 v.update(admission=str(A),nonce=f['nonce'],actual_postretirement_current_free=f['current_free'],actual_next_nonce_ledger=f['current_nonce_ledger']);write(D/'REVIEWER-ACTUAL-BINDINGS.json',v)
 z=read(Q/'ROOT-CAPTURE-PUBLISH-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');z.update(admission=str(A),nonce=f['nonce'],capture_source=refs['capture_source'],publisher_source=refs['publisher_source'],actual_postretirement_current_free=f['current_free'],actual_nonce_ledger=f['current_nonce_ledger']);write(D/'ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json',z)
 H=A/'FINITE-REVIEW-HANDOFF';H.mkdir(mode=0o700);print(json.dumps(dict(status='ROOT118_POSTPUB_COLD_DATA_ONLY_NO_APPROVER',reviewer=ref(D/'REVIEWER-ACTUAL-BINDINGS.json'),Rootcapture=ref(D/'ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json'),handoff=str(H))))
if __name__=='__main__':main()
