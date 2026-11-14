"""Functional OS only; no security testing. Exact previous normalcleanup physical facts, no admission."""
from pathlib import Path
import hashlib,json
ACCEPTANCE={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/CURRENT290-ATTEMPT3-INDEPENDENT-NORMAL-CLEANUP-CURRENT-PHYSICAL-ACCEPTANCE.json', 'sha256': '08860bb3032cbdf974c88d0fc417fc960aaa2c6f87783b9c4bb21835077c1f2c', 'bytes': 4386}
POSTRETURN={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-CURRENT290-ATTEMPT3-NORMAL-CLEANUP-POSTRETURN-FREE-PROOF.json', 'sha256': '578a242c6af1ae01a4ae10d016cd2460a67b1ec8bb36998f00bfb939a67edf7c', 'bytes': 3765}
def auth(row):
 p=Path(row['path']);raw=p.read_bytes()
 if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise RuntimeError('exact08860 currentphysicalbytes')
 return json.loads(raw)
def validate(acceptance,postjoin):
 if acceptance!=ACCEPTANCE or postjoin!=POSTRETURN:raise RuntimeError('exact08860/postreturnrefs')
 a=auth(acceptance);auth(postjoin)
 if a['schema']!='mckernel.current290.attempt3.normal-cleanup.current-physical.acceptance.v1' or a['decision']!='PASS_EXACT_CURRENT290_ATTEMPT3_NORMAL_CLEANUP_AND_POSTRETURN_CURRENT_PHYSICAL' or a['reviewer']!='/root/review18h' or a['implementation_ownership'] is not False:raise RuntimeError('independent08860physicaldecision')
 for key in ('normal_cleanup_complete','caller_tool_joined','owner935300_and_cleanup945340_joined_and_absent','caller_owner_cleanup_groups_empty','common_and_shared_records_archived_and_absent','target_container_absent_at_engine_completion','no_Docker_or_mount_actions_since_engine_completion','no_other_heavy'):
  if a[key] is not True:raise RuntimeError('positive08860fact:'+key)
 if a['permanent_mutex']!={'device':27,'inode':4,'preserved':True,'free':True,'root_free_observations':2} or a['postreturn_proof']!=postjoin or a['build_status']!='FAIL' or a['native_or_language_retirement_acceptance'] is not False or a['new_workload_admission'] is not False:raise RuntimeError('08860scope/mutex')
 return True
