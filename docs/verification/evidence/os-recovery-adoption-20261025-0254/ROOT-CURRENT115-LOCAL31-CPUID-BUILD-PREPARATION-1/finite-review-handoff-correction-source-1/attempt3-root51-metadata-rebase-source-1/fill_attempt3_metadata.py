"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root metadata fill only: actual newnonce/currentBoundary/static then postpub coldrefs.
No guard/query/staging/holder/approver/grant/compiler.
"""
from pathlib import Path
import argparse,json,hashlib
R=Path(__file__).resolve().parent;C=R.parent;D=C.parent;Q=C/'expert-root49-hot-schema-correction-source-1'
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert isinstance(r,dict) and ref(r['path'])==r;return Path(r['path'])
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['static','handoff'],required=True);a=p.parse_args();f=read(R/'ROOT-ACTUAL-ATTEMPT3-FACTS.json');assert f['author']=='/root';A=Path(f['admission']);assert A==D.parent/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-3' and f['nonce'] not in ['cf36b84313f404836ec6d80350e0e15a','92e8d698cfe12176ddd0375937cbaeb1']
 for k in ['nonce_reservation','current_nonce_ledger','current_free','current_boundary','observer_schema','observer_schema_review']:auth(f[k])
 boundary=read(f['current_boundary']['path']);assert f['current_boundary']==ref(R/'ROOT-ACTUAL-CURRENT-BOUNDARY.json')
 assert boundary['author']=='/root' and boundary['decision']=='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY' and boundary['root_attests_exact_current_boundary'] is True
 assert boundary['nonce_ledger']==f['current_nonce_ledger'] and boundary['native_custody_clearance']==f['current_free']
 schema=read(f['observer_schema']['path']);review=read(f['observer_schema_review']['path']);assert schema['observer']==boundary['observer'] and review['decision']=='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING' and review['independent'] is True and review['reviewed_observer_schema']==f['observer_schema']
 if a.phase=='static':
  assert not A.exists();b=read(R/'ROOT-BINDINGS.ATTEMPT3.SOURCE-TEMPLATE.json');b.update(author='/root',decision='MATERIALIZE_REVIEWED_CURRENT115_LOCAL31_CPUID_STATIC_INPUTS_AND_HOLDER_ONLY',root_attests_exact_UID1000_readonly_exports=True,nonce=f['nonce'],nonce_ledger=f['current_nonce_ledger'],native_custody_clearance=f['current_free'],current_boundary=f['current_boundary']);write(R/'ROOT-ACTUAL-BINDINGS-1.json',b);print(json.dumps(dict(status='ROOT_A3_STATIC_BINDINGS_ONLY',reference=ref(R/'ROOT-ACTUAL-BINDINGS-1.json'))));return
 b=read(R/'ROOT-ACTUAL-BINDINGS-1.json');assert b['nonce']==f['nonce'] and b['admission']==str(A)
 assert not (A/'OUTPUT').exists() and not (A/'HOLDER/ROOT-BUILD-GRANT.READY.json').exists()
 v=read(Q/'REVIEWER-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');refs=v['static_refs']
 paths=dict(profile=A/'PROFILE.SOURCE-ONLY.json',input_export=A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json',request_payload=A/'STATIC-REQUEST-PAYLOAD.SOURCE-ONLY.json',request_adoption=A/'ROOT-REQUEST-ADOPTION.json',source_publication=A/'ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json',runner=A/'run_build_only.py',worker=A/'build_only_worker.py',holder_source=A/'hold_and_run_build_only.py',publisher_source=A/'publish_approved_ready.py')
 for k,p in paths.items():refs[k]=ref(p)
 refs.update(nonce_ledger=f['current_nonce_ledger'],native_custody_clearance=f['current_free'],current_boundary=f['current_boundary'],observer_source=boundary['observer'],source_adoption=b['source_adoption'],source_review=b['independent_source_profile_review'],mechanical_review=b['mechanical_source_profile_review'],current_boundary_review=boundary['independent_current_boundary_review'],capture_source=ref(R/'capture_resources.py'),observer_schema=f['observer_schema'],observer_schema_review=f['observer_schema_review'])
 assert all(isinstance(x,dict) for x in refs.values());v.update(admission=str(A),nonce=f['nonce'],actual_postretirement_current_free=f['current_free'],actual_next_nonce_ledger=f['current_nonce_ledger']);write(R/'REVIEWER-ACTUAL-BINDINGS.json',v)
 z=read(Q/'ROOT-CAPTURE-PUBLISH-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');z.update(admission=str(A),nonce=f['nonce'],capture_source=refs['capture_source'],publisher_source=refs['publisher_source'],actual_postretirement_current_free=f['current_free'],actual_nonce_ledger=f['current_nonce_ledger']);write(R/'ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json',z)
 H=A/'FINITE-REVIEW-HANDOFF';H.mkdir(mode=0o700);print(json.dumps(dict(status='ROOT_A3_POSTPUBLICATION_METADATA_ONLY_NO_APPROVER',reviewer_bindings=ref(R/'REVIEWER-ACTUAL-BINDINGS.json'),Rootbindings=ref(R/'ROOT-ACTUAL-CAPTURE-PUBLISH-BINDINGS.json'),handoff=str(H))))
if __name__=='__main__':main()
