"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite Root publication AFTER actual independent PASS of the supplied grant SHA.
Root explicitly supplies that approved SHA; this helper never performs a review.
No launch, process observation, signals, waiting, retry or lifecycle changes.
"""
import hashlib
import json
import types
import os
from pathlib import Path
import sys
# Pinned sibling works under the reviewed isolated (-I) interpreter too.
prepare_path=Path(__file__).resolve().parent/'prepare_retirement_grant.py'
prepare_raw=prepare_path.read_bytes()
if hashlib.sha256(prepare_raw).hexdigest()!='06ab808e7331d64d6e30afb63ebed10b8bcd32475628b8c023f186b443a19425':raise ValueError('exact-preparation-helper-source')
p=types.ModuleType('_exact_retirement_prepare');p.__file__=str(prepare_path)
exec(compile(prepare_raw,str(prepare_path),'exec'),p.__dict__)


def publish(prep,approved_grant_sha,*,evidence_root=p.EVIDENCE):
 prep=Path(prep);expected,packet=p.build_grant(prep,evidence_root=evidence_root)
 grant,ref=p.read_regular(prep/p.GRANT_NAME)
 p.need(len(approved_grant_sha)==64 and all(c in '0123456789abcdef' for c in approved_grant_sha) and ref['sha256']==approved_grant_sha,'actual-independently-approved-grant-sha-required')
 p.need(grant==expected,'unchanged-exact-new-keeper-grant')
 review_path=prep/p.REVIEW_NAME;command_path=prep/'INBOX/command-000000.json'
 p.need(not os.path.lexists(review_path) and not os.path.lexists(command_path),'fresh-review-and-command-required')
 review=dict(scope=p.SCOPE,author='/root',recorded_by='/root',reviewer='/root/custody_release_review',status='PASS_EXECUTION_RELEASE',root_grant_sha256=approved_grant_sha,pipeline_sources=packet['pipeline_sources'],operation='ONE_EXACT_PREDECESSOR_PIDFD_RETIREMENT',pidfd_signal_budget=1,numeric_group_signal_budget=0,later_adoption_shared_release_budget=0,retry=False,root_explicit_review_attestation=dict(approved_grant_sha256=approved_grant_sha,source='Root CLI supplied after actual independent PASS',automated_review=False))
 review_ref=p.exclusive(prep,p.REVIEW_NAME,p.canonical(review),mode=0o644)
 command=dict(operation=p.OPERATION,root_grant=ref,independent_execution_review=review_ref)
 # Any partial publication is retained for diagnosis. Never overwrite or retry.
 command_ref=p.exclusive(prep/'INBOX','command-000000.json',p.canonical(command))
 return dict(root_grant=ref,independent_execution_review=review_ref,command=command_ref,keeper=grant['keeper'],root_explicitly_supplied_approved_grant_sha256=approved_grant_sha)


def main(argv=None):
 p.need(os.getuid()==os.geteuid()==0,'uid0-reviewed-publication-only')
 args=sys.argv[1:] if argv is None else argv;p.need(len(args)==2,'usage: publish_reviewed_retirement.py PREP APPROVED_GRANT_SHA')
 print(json.dumps(publish(Path(args[0]),args[1]),sort_keys=True));return 0

if __name__=='__main__':raise SystemExit(main())
