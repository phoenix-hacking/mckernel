"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only existing publisher adapter AFTER actual independently-run finite PASS.
Durable O_EXCL claim precedes existing publisher/READY; never invokes approver.
"""
from pathlib import Path
import argparse,importlib.util,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from handoff_common import *
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bindings',required=True);p.add_argument('--handoff',required=True);a=p.parse_args();b=read_json(a.bindings);A=Path(b['admission']);H=Path(a.handoff);no_launch(A)
 passed=read_json(H/'INDEPENDENT-FINITE-REVIEW.PASS.json');need(passed['decision']=='PASS_EXACT_BUILD_ONLY_EXECUTION' and passed['independent'] is True and passed['implementation_ownership'] is False and type(passed['maximum_invocations']) is int and passed['maximum_invocations']==1 and passed['payload_sha256']==passed['approved_input_sha256'] and passed['reviewer']==REVIEWER and passed['nonce']==b['nonce'],'actual independent finite PASS only')
 need(passed['verifier']==b['finite_verifier'] and passed['prewarm_ready']==reference(H/'PREWARM_READY.json') and passed['complete_root_capture']==reference(H/'ROOT-HELD-CAPTURE.COMPLETE.json'),'exact reviewed independent/capture chain')
 need(passed['pending_input']==reference(A/'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json') and passed['approved_input_sha256']==passed['pending_input']['sha256'],'exact approved pending SHA')
 resource=read_json_ref(passed['resource_authority']);now=clocks();in_window(now,passed['earliest_clamps']);need(0<=now[0]-resource['observed_at_epoch']<=120,'original120s freshness at publication')
 publisher=verify_ref(b['publisher_source']);need(publisher==A/'publish_approved_ready.py','existing actual admission publisher only')
 claim=atomic_json(H/'ROOT-PUBLICATION.ONCE-CLAIM.json',dict(scope=SCOPE,author='/root',nonce=b['nonce'],actual_independent_PASS=reference(H/'INDEPENDENT-FINITE-REVIEW.PASS.json'),approved_pending_input_sha256=passed['approved_input_sha256'],publisher=b['publisher_source'],fresh_clocks=now))
 s=importlib.util.spec_from_file_location('existing_original_build_publisher',publisher);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 # Existing publisher retains its own120s/empty-output/nonce checks and writes
 # review/grant/READY O_EXCL. Only original holder consumes READY and spawns build.
 result=m.publish(A,passed['approved_input_sha256']);print(json.dumps(dict(status='EXISTING_PUBLISHER_AFTER_ACTUAL_INDEPENDENT_PASS',claim=claim,result=result)))
if __name__=='__main__':main()
