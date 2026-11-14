"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root41 exact current-boundary wrapper; no cleanup, holder, release or retry.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,time
D=Path(__file__).resolve().parent
LEDGER_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER41.json', 'bytes': 4318, 'sha256': '0a841176630b6c4b5a6c7bb6840d342ef5da4e5f9be7a3507932f5621e7526ba'}
FREE_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-startup-native-entry-source-1/correct-rust-collector-native-entry-source-1/root40-current-binding-delta-1/root-adopted-correct-entry-1/independent-actual-native-review-1/CURRENT-FREE.json', 'bytes': 11241, 'sha256': 'd9e0c9fbf7eda3f3d4ccd96b3808c6609a5641e365a75f73a02da23f3a95d081'}
EXACT_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-startup-native-entry-source-1/correct-rust-collector-native-entry-source-1/root40-current-binding-delta-1/root-adopted-correct-entry-1/independent-actual-native-review-1/FRESH-EXACT-CONTAINER-AND-ACTORS.json', 'bytes': 60247, 'sha256': '4304785b84148bce98d83a17b69484448c403b214b0c87b3042fe91167599d21'}
BASE_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current113-qualified-lock4-next4-scalar4-union-source-1/corrected-scalar4-next4-accepted112-source-1/abi-private-field-correction-source-1/root38-correction-admission-source-1/observe_root38_current.py', 'bytes': 5305, 'sha256': 'eb7a8d45a065ab88d94afd905c68c18d8eb04b069eac00ccd641e6b3977d0238'}

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def read(p):return json.loads(Path(p).read_bytes())
def observe():
 assert os.getuid()==os.geteuid()==1000
 ledger=read(auth(LEDGER_REF));review=read(auth(FREE_REF));exact=read(auth(EXACT_REF));auth(BASE_REF)
 assert ledger['latest_accepted_free_boundary']==FREE_REF and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_POSITIVE_CORRECTED_STARTUP_FAILED_CASE_RETIREMENT_AND_CURRENT_FREE' and review['normal_owned_retirement'] is True and review['current_free'] is True
 assert review['owned_client_retirement']['actual_commands']==25 and review['owned_client_retirement']['all_exact_reaped'] is True
 commands=exact['all_actual_Docker_commands'];assert len(commands)==25 and all(x['command']['reaped'] is True and x['command']['returncode']==x['returncode'] for x in commands)
 result=review['actual_statuses']['owner_result'];assert result['status']=='FAIL' and result['absence_verified'] is True and result['lease_retained'] is False and result['secondary']==[]
 assert review['actual_statuses']['cleanup']=={'errors':[],'reaped':True}
 spec=importlib.util.spec_from_file_location('root41_retained_original_root38_observer',auth(BASE_REF));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 original=module.observe()  # Original Root38/37/36 contracts are preserved, not latest admission authority.
 actors=review['fresh_current']['all28_owned_pids_and_groups_absent'];assert len(actors)==28 and actors[:3]==[1757372,1757368,1757186]
 assert all(not Path('/proc',str(pid)).exists() for pid in actors)
 census=original['group_membership_observation'];assert not census['errors'] and not any(x['pgrp'] in actors for x in census['rows'])
 queries=[]
 for expected in exact['queries']:
  child=subprocess.run(expected['argv'],capture_output=True,text=True,timeout=15)
  assert child.returncode==expected['returncode'] and child.stdout==expected['stdout'] and child.stderr==expected['stderr']
  queries.append(dict(argv=expected['argv'],returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 assert len(queries)==5 and Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text().strip()=='0'
 return dict(status='PASS_ROOT41_EXACT_FAILED_STARTUP_CURRENT_PENDING_ROOT_ACCEPTANCE',scope=review['scope'],runtime_authority=None,observed_at=time.time(),Root41=LEDGER_REF,accepted_failed_startup=FREE_REF,original_observer=BASE_REF,original_Root38_observation=original,known_numeric_controls_absent=original['known_numeric_controls_absent']+actors,group_membership_observation=census,closed_exclusive_probes=original['closed_exclusive_probes'],new_exact25_clients_reaped=True,new_exact28_actors=actors,new_exact_container_absent=review['container'],new_exact_queries=queries,retained_failed113_container=original['retained_failed113_container'],retained_failed113_container_exit=1,artifact_acceptance=False,native_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
