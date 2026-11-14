"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only proposal/publication from actual supplied reviews; no runtime or clock.
"""
from pathlib import Path
import argparse,json
import adopt_contract as mc
import adopt_owner as owner

def two(path,sha):
 reference=dict(path=str(Path(path).resolve()),sha256=sha)
 return reference,owner.bound(reference)
def write(path,value):
 with Path(path).open('xb') as output:output.write(mc.canonical(value))
 Path(path).chmod(0o600)
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['propose','publish'])
 for name in ['source-review','source-review-sha256','admission','admission-sha256','execution-review','execution-review-sha256']:parser.add_argument('--'+name)
 args=parser.parse_args();request_path=mc.HERE/'ADOPT-REQUEST.json';rr=mc.ref(request_path);request=mc.json_bytes(request_path.read_bytes())
 proposal=mc.HERE/'RELEASE-PAYLOAD.PROPOSAL.json'
 if args.mode=='propose':
  sr,review=two(args.source_review,args.source_review_sha256);ar,admission=two(args.admission,args.admission_sha256)
  mapping={key:mc.sha(Path(owner.RUNTIME_SOURCE_PATHS[key]).read_bytes()) for key in owner.SOURCES};owner.validate_runtime_source_bindings(mapping)
  mc.need(review.get('decision')=='PASS_SOURCE' and review.get('implementation_ownership') is False and review.get('reviewer') not in (None,'','/root') and review.get('source_sha256')==mapping,'actual independent exact source review required')
  mc.need(admission.get('schema')=='mckernel.daemon-pinned-helper-suffix64-current-admission.v1' and admission.get('request')=={k:rr[k] for k in ('path','sha256')} and admission.get('nonce')==request['nonce'],'actual reproducer admission binding required')
  payload=dict(schema='mckernel.daemon-pinned-helper-suffix64-release.v1',status='PASS_EXECUTION_RELEASE',execution_count=1,request={k:rr[k] for k in ('path','sha256')},nonce=request['nonce'],boot_id=mc.BOOT,fetched_source_verified=True,terminal_policy='remove-owned-terminal',historical_observer=dict(path=str(owner.HISTORICAL_OBSERVER),sha256=owner.HISTORICAL_OBSERVER_SHA,prefix=list(owner.HISTORICAL_PREFIX),timeout_seconds=30),source_sha256=mapping,source_review=sr,current_admission=ar,author='/root')
  write(proposal,payload);print(json.dumps(dict(proposal=mc.ref(proposal),reviewed_release_payload_sha256=mc.sha(mc.canonical(payload)),runtime_authority=False)))
 else:
  payload=mc.json_bytes(proposal.read_bytes());er,review=two(args.execution_review,args.execution_review_sha256)
  mc.need(review.get('decision')=='PASS_EXECUTION' and review.get('implementation_ownership') is False and review.get('reviewer') not in (None,'','/root') and review.get('reviewed_release_payload_sha256')==mc.sha(mc.canonical(payload)),'actual exact independent execution review required')
  mc.need(payload['request']=={k:rr[k] for k in ('path','sha256')} and payload['nonce']==request['nonce'],'request changed')
  release=mc.HERE/'ACTUAL-REVIEWED-RELEASE.json';write(release,dict(payload,execution_review=er));print(json.dumps(dict(release=mc.ref(release),entry_performed=False)))
if __name__=='__main__':main()
