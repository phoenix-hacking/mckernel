"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind existing actual Root/reviewer records into a non-authorizing review proposal.
"""
from pathlib import Path
import argparse,json
import mock64_contract as mc
import mock64_owner as owner

def two(path):
 r=mc.ref(Path(path));return {k:r[k] for k in ('path','sha256')}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-review',required=True,type=Path);p.add_argument('--current-admission',required=True,type=Path);args=p.parse_args()
 request=mc.json_bytes((mc.HERE/'MOCK64-REQUEST.json').read_bytes());mapping={key:mc.sha(Path(owner.RUNTIME_SOURCE_PATHS[key]).read_bytes()) for key in owner.SOURCES}
 owner.validate_runtime_source_bindings(mapping)
 source=mc.json_bytes(args.source_review.read_bytes());mc.need(source.get('decision')=='PASS_SOURCE' and source.get('implementation_ownership') is False and source.get('source_sha256')==mapping,'genuine exact independent source review required')
 payload=dict(schema='mckernel.daemon-mock64-release.v1',status='PASS_EXECUTION_RELEASE',author='/root',execution_count=1,request=two(mc.HERE/'MOCK64-REQUEST.json'),nonce=request['nonce'],boot_id=mc.BOOT,fetched_source_verified=True,terminal_policy=request['terminal_policy'],historical_observer=dict(path=str(owner.HISTORICAL_OBSERVER),sha256=owner.HISTORICAL_OBSERVER_SHA,prefix=list(owner.HISTORICAL_PREFIX),timeout_seconds=30),source_sha256=mapping,source_review=two(args.source_review),current_admission=two(args.current_admission))
 # This envelope cannot pass owner.authenticate: it has no release schema or execution_review.
 proposal=dict(status='PENDING_ACTUAL_INDEPENDENT_EXECUTION_REVIEW_NOT_A_RELEASE',proposed_release_payload=payload,reviewed_release_payload_sha256=mc.sha(mc.canonical(payload)),required_actual_execution_review_fields=dict(decision='PASS_EXECUTION',implementation_ownership=False,reviewer='ACTUAL_INDEPENDENT_REVIEWER',reviewed_release_payload_sha256=mc.sha(mc.canonical(payload))),actual_execution_review=None,actual_Root_release=None,runtime_authority=None)
 with (mc.HERE/'RELEASE-PAYLOAD.PENDING-INDEPENDENT-REVIEW.json').open('xb') as f:f.write(mc.canonical(proposal))
 print(json.dumps(dict(status=proposal['status'],payload_sha256=proposal['reviewed_release_payload_sha256'])))
if __name__=='__main__':main()
