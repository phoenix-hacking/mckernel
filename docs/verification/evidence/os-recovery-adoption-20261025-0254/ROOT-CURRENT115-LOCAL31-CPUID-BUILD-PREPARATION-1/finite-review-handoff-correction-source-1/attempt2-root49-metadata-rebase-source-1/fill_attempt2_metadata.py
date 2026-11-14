"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root data fill only: exact freshA2 static binding or postpublication cold/handoff refs.
No guards/resource queries/producer/holder/compiler/grant/reviewer invocation.
"""
from pathlib import Path
import argparse,json,hashlib
R=Path(__file__).resolve().parent;C=R.parent;D=C.parent;N=C/'strict-json-final-publication-correction-source-1'
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['static','handoff'],required=True);a=p.parse_args();facts=read(R/'EXACT-ATTEMPT2-FACTS.NOT-AUTHORITY.json');A=Path(facts['admission']);boundary_path=C/'ROOT-ACTUAL-CURRENT-BOUNDARY.json';boundary=read(boundary_path)
 assert boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary'] is True
 assert boundary['nonce_ledger']==facts['actual_Root49'] and boundary['native_custody_clearance']==facts['actual_current_free']
 for k in ['nonce_ledger','native_custody_clearance','observer','independent_current_boundary_review']:auth(boundary[k])
 if a.phase=='static':
  assert not A.exists();b=read(R/'ROOT-BINDINGS.ATTEMPT2.SOURCE-TEMPLATE.json');b.update(author='/root',decision='MATERIALIZE_REVIEWED_CURRENT115_LOCAL31_CPUID_STATIC_INPUTS_AND_HOLDER_ONLY',root_attests_exact_UID1000_readonly_exports=True,current_boundary=ref(boundary_path));write(C/'ROOT-ACTUAL-BINDINGS-1.json',b)
  print(json.dumps(dict(status='ROOT_ATTEMPT2_STATIC_BINDING_ONLY',bindings=ref(C/'ROOT-ACTUAL-BINDINGS-1.json'))));return
 b=read(C/'ROOT-ACTUAL-BINDINGS-1.json');assert b['nonce']==facts['nonce'] and b['admission']==str(A)
 assert not (A/'OUTPUT').exists() and not (A/'HOLDER/ROOT-BUILD-GRANT.READY.json').exists()
 static=read(N/'REVIEWER-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');refs=static['static_refs']
 paths=dict(profile=A/'PROFILE.SOURCE-ONLY.json',input_export=A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json',request_payload=A/'STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json',request_adoption=A/'ROOT-REQUEST-ADOPTION.json',source_publication=A/'ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json',runner=A/'run_build_only.py',worker=A/'build_only_worker.py',holder_source=A/'hold_and_run_build_only.py',publisher_source=A/'publish_approved_ready.py')
 for k,v in paths.items():refs[k]=ref(v)
 refs.update(nonce_ledger=facts['actual_Root49'],native_custody_clearance=facts['actual_current_free'],current_boundary=ref(boundary_path),observer_source=boundary['observer'],source_adoption=facts['actual_source_adoption'],source_review=b['independent_source_profile_review'],mechanical_review=facts['corrected_finite_source_review'],current_boundary_review=boundary['independent_current_boundary_review'])
 assert all(isinstance(v,dict) for v in refs.values());static.update(admission=str(A),nonce=facts['nonce'],actual_postretirement_current_free=facts['actual_current_free'],actual_next_nonce_ledger=facts['actual_Root49']);write(R/'REVIEWER-ACTUAL-BINDINGS.json',static)
 root=read(N/'ROOT-CAPTURE-PUBLISH-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');root.update(admission=str(A),nonce=facts['nonce'],publisher_source=refs['publisher_source'],actual_postretirement_current_free=facts['actual_current_free'],actual_nonce_ledger=facts['actual_Root49']);write(R/'ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json',root)
 H=A/'FINITE-REVIEW-HANDOFF';H.mkdir(mode=0o700)
 print(json.dumps(dict(status='ROOT_POSTPUBLICATION_COLD_BINDINGS_ONLY_NO_REVIEW_INVOCATION',reviewer_bindings=ref(R/'REVIEWER-ACTUAL-BINDINGS.json'),Root_capture_bindings=ref(R/'ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json'),handoff=str(H))))
if __name__=='__main__':main()
